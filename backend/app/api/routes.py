"""
FastAPI routes — docs/ARCHITECTURE.md section 3.6, updated to reflect a
single consolidated webhook endpoint rather than one route per event type,
since that's how Razorpay actually expects webhooks to be configured (one
URL in the dashboard, event type read from the payload's "event" field).

All webhook-adjacent routes return a 2xx for event types we don't act on
(rather than 4xx/5xx) — Razorpay retries endpoints that don't return 2xx,
and there's no reason to trigger retry storms for events we've deliberately
chosen to ignore.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.logger import log_stage
from app.audit.metrics import compute_batch_metrics
from app.db import get_db
from app.guardrails.gate import load_rules
from app.ingestion.webhooks import (
    InvalidWebhookSignature,
    handle_payment_failed_event,
    handle_payment_outcome_event,
)
from app.models import AuditLogEntry, BatchRun, RecoveryCase
from app.pipeline import build_case_context, process_case

router = APIRouter()

# Event types this webhook endpoint actually acts on; everything else is
# acknowledged with 200 and ignored, per the retry-storm note above.
FAILURE_EVENTS = {"subscription.charge.failed"}
OUTCOME_EVENTS = {"payment_link.paid", "payment.captured"}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    try:
        import json
        event = json.loads(raw_body).get("event", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        if event in FAILURE_EVENTS:
            case = handle_payment_failed_event(raw_body, signature, db)
            _run_pipeline_for_case(case, db)
            return {"status": "processed", "event": event, "case_id": case.id}

        if event in OUTCOME_EVENTS:
            case = handle_payment_outcome_event(raw_body, signature, event, db)
            return {"status": "processed" if case else "no_matching_case", "event": event}

        return {"status": "ignored", "event": event}

    except InvalidWebhookSignature:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _run_pipeline_for_case(case: RecoveryCase, db: Session) -> None:
    """
    Bridges the DB-agnostic pipeline.process_case() to real persistence:
    loads this subscription's case history, runs the pipeline, writes the
    audit trail, and updates the case's final status/root_cause.

    A duplicate webhook delivery returns the SAME existing case object from
    handle_payment_failed_event() (idempotency dedup) — re-running the
    pipeline against an already-processed case would double-execute a real
    Razorpay action, so we skip anything not still at DETECTED.
    """
    if case.status != "DETECTED":
        return

    prior = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.subscription_id == case.subscription_id)
        .filter(RecoveryCase.id != case.id)
        .all()
    )
    prior_cases = [
        {"subscription_id": p.subscription_id, "created_at": p.created_at.isoformat() if p.created_at else None,
         "root_cause": p.root_cause}
        for p in prior
    ]

    case_input = {
        "id": case.id,
        "subscription_id": case.subscription_id,
        "customer_id": case.customer_id,
        "amount_paise": case.amount,
        "mandate_status": case.mandate_status,
        "error_code": case.error_code,
        "error_reason": case.error_reason,
    }

    result = process_case(case_input, prior_cases)

    for entry in result["audit_trail"]:
        log_stage(db, case_id=case.id, stage=entry["stage"],
                   input_snapshot=entry["input"], output=entry["output"], rule_fired=entry["rule_fired"])

    case.root_cause = result["root_cause"]
    if result["decision"]:
        case.decision = result["decision"].get("action")
    if result["gate_result"]:
        case.gate_result = "approved" if result["gate_result"].approved else "blocked"
    case.status = result["status"]
    db.commit()


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "id": case.id, "subscription_id": case.subscription_id, "customer_id": case.customer_id,
        "amount_paise": case.amount, "root_cause": case.root_cause, "decision": case.decision,
        "gate_result": case.gate_result, "status": case.status,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


@router.get("/cases/{case_id}/audit")
def get_case_audit(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    entries = (
        db.query(AuditLogEntry)
        .filter(AuditLogEntry.case_id == case_id)
        .order_by(AuditLogEntry.timestamp.asc())
        .all()
    )
    return {
        "case_id": case_id,
        "audit_trail": [
            {"stage": e.stage, "input": e.input_snapshot, "output": e.output,
             "rule_fired": e.rule_fired, "timestamp": e.timestamp.isoformat() if e.timestamp else None}
            for e in entries
        ],
    }


@router.get("/batch/{batch_id}/metrics")
def get_batch_metrics(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(BatchRun).filter(BatchRun.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "batch_id": batch.id, "batch_size": batch.batch_size,
        "recovered_amount_paise": batch.recovered_amount, "recovery_rate": batch.recovery_rate,
        "baseline_recovery_rate": batch.baseline_rate, "guardrail_blocked_count": batch.blocked_count,
    }


@router.get("/rules")
def get_rules():
    return {"rules": load_rules()}


@router.post("/admin/run-batch")
def run_batch_endpoint(
    n: int = 50,
    x_admin_secret: str = Header(default="", alias="X-Admin-Secret"),
    db: Session = Depends(get_db),
):
    """
    Triggers scripts/run_batch.py over HTTP instead of a shell command.

    This exists specifically because Render's free web-service tier has no
    SSH/shell access and can't run one-off jobs — the only way to execute
    a script against the live deployment is through the running process
    itself, i.e. an API call. Protected by a shared-secret header
    (ADMIN_SECRET) rather than left open, since it makes real Razorpay API
    calls and writes to the database.
    """
    from app.config import ADMIN_SECRET

    if not ADMIN_SECRET or x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Secret header")

    from scripts.run_batch import run as run_batch
    batch_id = run_batch(n)
    return {"batch_id": batch_id}
