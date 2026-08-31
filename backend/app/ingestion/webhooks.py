"""
Receives Razorpay test-mode webhooks for subscription payment failures,
verifies the signature, normalizes the payload, and creates a RecoveryCase
at status=DETECTED — deduped by the underlying Razorpay payment id so a
retried webhook delivery never creates a second case (NFR-idempotency).

Field mapping notes — VERIFY against a real test-mode payload before relying
on this beyond the hackathon demo (https://razorpay.com/docs/webhooks/subscriptions/):
  - subscription_id   <- payload.subscription.entity.id
  - customer_id       <- payload.subscription.entity.customer_id
  - amount_paise      <- payload.payment.entity.amount
  - error_code        <- payload.payment.entity.error_code
  - error_reason      <- payload.payment.entity.error_reason
  - source_payment_id <- payload.payment.entity.id  (idempotency key)
  - mandate_status    <- derived: "revoked" if subscription status == "cancelled",
    else "active". Razorpay subscription statuses include created,
    authenticated, active, pending, halted, cancelled, completed, expired.
    "halted" (after repeated failures) is arguably closer to revoked too —
    deliberately left as "active" here so it still flows through the
    recovery loop instead of being silently dropped; revisit this mapping
    once real test-mode payloads confirm the actual behavior you see.

parse_subscription_charge_failed() is a pure function (no DB, no network)
and is fully unit-tested without any dependencies installed. verify_signature()
is also dependency-free — it doesn't use the razorpay SDK's own utility
method so it can be tested offline; either approach is fine at runtime.
handle_payment_failed_event() is the only part that touches the DB/config
and needs the real app stack to run.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any


class InvalidWebhookSignature(Exception):
    pass


def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    HMAC-SHA256 over the raw body, compared against the X-Razorpay-Signature
    header using constant-time comparison to avoid timing attacks.
    """
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_subscription_charge_failed(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Pure function: Razorpay webhook JSON -> normalized case input dict.
    Raises KeyError if the payload doesn't have the expected shape — fail
    loud rather than silently create a malformed case.
    """
    subscription = payload["payload"]["subscription"]["entity"]
    payment = payload["payload"].get("payment", {}).get("entity", {})

    return {
        "subscription_id": subscription["id"],
        "customer_id": subscription.get("customer_id"),
        "amount_paise": payment.get("amount", 0),
        "error_code": payment.get("error_code"),
        "error_reason": payment.get("error_reason"),
        "source_payment_id": payment.get("id"),
        "mandate_status": "revoked" if subscription.get("status") == "cancelled" else "active",
    }


def parse_payment_outcome_event(payload: dict[str, Any], event: str) -> dict[str, Any]:
    """
    Normalizes a Razorpay success-outcome event into
    {case_id, subscription_id, amount_paise, source_payment_id}.

    case_id is populated only when we find our own reflo_case_id in notes
    (set by execution/razorpay_client.py when WE created the payment link) —
    that's the reliable match. For payment.captured events that didn't
    originate from our payment link (e.g. Razorpay's own automatic Smart
    Retry succeeding), case_id will usually be None and the caller must fall
    back to matching by subscription_id + most recent EXECUTING case, which
    is best-effort, not guaranteed correct — flagged clearly in
    handle_payment_outcome_event() below.
    """
    if event == "payment_link.paid":
        link_entity = payload["payload"]["payment_link"]["entity"]
        payment_entity = payload["payload"].get("payment", {}).get("entity", {})
        notes = link_entity.get("notes") or {}
        return {
            "case_id": notes.get("reflo_case_id") or None,
            "subscription_id": notes.get("reflo_subscription_id") or None,
            "amount_paise": link_entity.get("amount_paid") or payment_entity.get("amount", 0),
            "source_payment_id": payment_entity.get("id"),
        }

    if event == "payment.captured":
        payment_entity = payload["payload"]["payment"]["entity"]
        notes = payment_entity.get("notes") or {}
        return {
            "case_id": notes.get("reflo_case_id") or None,
            "subscription_id": payment_entity.get("subscription_id") or notes.get("reflo_subscription_id"),
            "amount_paise": payment_entity.get("amount", 0),
            "source_payment_id": payment_entity.get("id"),
        }

    raise ValueError(f"parse_payment_outcome_event: unsupported event {event!r}")


def handle_payment_outcome_event(raw_body: bytes, signature: str, event: str, db) -> Any:
    """
    Full handler: verify -> parse -> match to a RecoveryCase -> mark RESOLVED.

    Returns the updated RecoveryCase, or None if no matching case was found
    (logged, not raised — an unmatched outcome event shouldn't 500 the
    webhook endpoint, since Razorpay will retry a failing endpoint and that
    just creates noise for an event we've already decided not to act on).
    """
    import json

    from app.audit.logger import log_stage
    from app.config import RAZORPAY_WEBHOOK_SECRET
    from app.models import RecoveryCase

    if not verify_signature(raw_body, signature, RAZORPAY_WEBHOOK_SECRET):
        raise InvalidWebhookSignature("Webhook signature does not match")

    payload = json.loads(raw_body)
    outcome = parse_payment_outcome_event(payload, event)

    case = None
    if outcome["case_id"]:
        case = db.query(RecoveryCase).filter(RecoveryCase.id == outcome["case_id"]).first()

    if case is None and outcome["subscription_id"]:
        # Best-effort fallback for outcomes we can't trace via notes (e.g. a
        # Razorpay-native Smart Retry success rather than our payment link).
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.subscription_id == outcome["subscription_id"])
            .filter(RecoveryCase.status == "EXECUTING")
            .order_by(RecoveryCase.created_at.desc())
            .first()
        )

    if case is None:
        return None  # no case to resolve — logged by the caller if desired

    case.status = "RESOLVED"
    db.commit()

    log_stage(
        db,
        case_id=case.id,
        stage="RESOLVED",
        input_snapshot={"event": event, "source_payment_id": outcome["source_payment_id"]},
        output={"amount_paise": outcome["amount_paise"], "final_status": "RESOLVED"},
    )

    return case


def handle_payment_failed_event(raw_body: bytes, signature: str, db) -> Any:
    """
    Full handler used by the API route: verify -> parse -> dedupe -> persist.

    Returns the RecoveryCase (existing one if this was a duplicate delivery,
    a freshly created one otherwise). Imports models/config/db lazily so the
    pure functions above stay testable without the app's DB stack installed.
    """
    import json
    import uuid

    from app.audit.logger import log_stage
    from app.config import RAZORPAY_WEBHOOK_SECRET
    from app.models import RecoveryCase

    if not verify_signature(raw_body, signature, RAZORPAY_WEBHOOK_SECRET):
        raise InvalidWebhookSignature("Webhook signature does not match")

    payload = json.loads(raw_body)
    case_input = parse_subscription_charge_failed(payload)

    if case_input["source_payment_id"]:
        existing = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.source_payment_id == case_input["source_payment_id"])
            .first()
        )
        if existing is not None:
            return existing  # duplicate webhook delivery — NFR-idempotency, no double-execution

    case = RecoveryCase(
        id=str(uuid.uuid4()),
        subscription_id=case_input["subscription_id"],
        customer_id=case_input["customer_id"],
        source_payment_id=case_input["source_payment_id"],
        amount=case_input["amount_paise"],
        error_code=case_input["error_code"],
        error_reason=case_input["error_reason"],
        mandate_status=case_input["mandate_status"],
        status="DETECTED",
    )
    db.add(case)
    db.commit()

    log_stage(
        db,
        case_id=case.id,
        stage="DETECTED",
        input_snapshot=payload,
        output={"subscription_id": case.subscription_id, "amount_paise": case.amount},
    )

    return case
