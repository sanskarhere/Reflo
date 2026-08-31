"""
Thin wrapper around the Razorpay test-mode SDK — the execution layer for
whatever action the guardrail gate approved.

IMPORTANT — a real finding from checking Razorpay's actual API surface
(razorpay-python SDK docs), not an assumption baked in from day one:
Razorpay Subscriptions has its own built-in "Smart Retry" system that
retries failed charges automatically on Razorpay's own schedule. There is
NO public merchant-facing API to force an immediate retry of a specific
subscription charge. This changes what our action set actually does:

  - retry_now / retry_scheduled: NOT a Razorpay API call. These represent a
    decision to defer to Razorpay's own Smart Retry rather than reinvent
    retry scheduling Razorpay already does better. Still logged as a real,
    structured audit entry (acknowledge_automatic_retry) rather than
    silently doing nothing, which would look like a bug rather than a
    deliberate design choice.
  - send_payment_link: the actual proactive lever we control — creates a
    real Razorpay Payment Link the customer can pay directly.
  - stop: for a genuinely dead mandate, cancels the subscription via the
    API so it stops attempting to bill entirely, rather than just "doing
    nothing" and letting Razorpay keep trying against a dead mandate.
  - escalate_human: intentionally NOT handled here — it's a human workflow
    step, not an API call. The orchestration layer routes it straight to
    the ESCALATED terminal state.

See docs/ARCHITECTURE.md section 4.1 for how this feeds the design.
"""
from __future__ import annotations

from typing import Any, Optional


def _get_client():
    import razorpay
    from app.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_payment_link(
    amount_paise: int,
    customer_name: str,
    customer_email: str,
    customer_contact: str,
    case_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    description: str = "Subscription payment recovery",
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Creates a real Razorpay Payment Link in test mode. Returns the API
    response dict, which includes 'short_url' — the link to send the customer.

    case_id/subscription_id are stamped into the link's `notes` field so the
    payment_link.paid outcome webhook can match the payment back to the
    exact RecoveryCase reliably, instead of guessing via "most recent
    EXECUTING case for this subscription" (see ingestion/webhooks.py).
    """
    client = client or _get_client()
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "description": description,
        "customer": {
            "name": customer_name,
            "email": customer_email,
            "contact": customer_contact,
        },
        "notify": {"sms": True, "email": True},
        "reminder_enable": True,
        "notes": {
            "reflo_case_id": case_id or "",
            "reflo_subscription_id": subscription_id or "",
        },
    }
    return client.payment_link.create(data)


def cancel_subscription(
    subscription_id: str,
    cancel_at_cycle_end: bool = False,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Cancels a subscription via the Razorpay API — the real action behind
    'stop' on a dead mandate, so billing actually stops rather than the
    system silently doing nothing while Razorpay keeps trying regardless.
    """
    client = client or _get_client()
    return client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": cancel_at_cycle_end})


def acknowledge_automatic_retry(subscription_id: str, scheduled_for: Optional[str] = None) -> dict[str, Any]:
    """
    No Razorpay API call — see module docstring. Exists so retry_now /
    retry_scheduled still produce a real, structured audit-log entry.
    """
    return {
        "action": "acknowledge_automatic_retry",
        "subscription_id": subscription_id,
        "scheduled_for": scheduled_for,
        "note": "Deferred to Razorpay's built-in Smart Retry; no direct API call made.",
    }


def execute_action(action: str, case: dict[str, Any], client: Optional[Any] = None) -> dict[str, Any]:
    """
    Routes a gated action to the correct handler.

    `case` fields used per action:
      - retry_now / retry_scheduled: subscription_id, scheduled_for (optional)
      - send_payment_link: subscription_id, amount_paise, customer_name,
        customer_email, customer_contact
      - stop: subscription_id

    Raises ValueError for any action without an execution handler here
    (currently escalate_human, which is a human workflow step) — fail loud
    rather than silently no-op an action nobody implemented.
    """
    if action in ("retry_now", "retry_scheduled"):
        return acknowledge_automatic_retry(case["subscription_id"], case.get("scheduled_for"))

    if action == "send_payment_link":
        return create_payment_link(
            amount_paise=case["amount_paise"],
            customer_name=case.get("customer_name", "Customer"),
            customer_email=case.get("customer_email", ""),
            customer_contact=case.get("customer_contact", ""),
            case_id=case.get("id"),
            subscription_id=case.get("subscription_id"),
            client=client,
        )

    if action == "stop":
        return cancel_subscription(case["subscription_id"], client=client)

    raise ValueError(f"execute_action: no execution handler for action {action!r}")
