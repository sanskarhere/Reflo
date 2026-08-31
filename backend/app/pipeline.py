"""
Orchestration — chains classify -> decide -> gate -> execute for one case
and produces a complete audit trail. Deliberately DB-agnostic: takes plain
dicts in, returns a plain dict out, so the entire pipeline is unit-testable
without a real database. api/routes.py owns the thin adapter that loads
case history from SQLAlchemy and persists the result.

State machine (docs/ARCHITECTURE.md section 3.2):
  DETECTED -> CLASSIFIED -> DECIDED -> GATED -> EXECUTING -> terminal

Honesty note: only 'stop' and 'escalate_human' are immediately terminal
here (STOPPED / ESCALATED). send_payment_link and the retry_* actions leave
the case in EXECUTING, pending a future outcome webhook (payment succeeded/
failed) that isn't built yet in v1 — see docs/ARCHITECTURE.md open
questions. Marking those cases RESOLVED without that real signal would be
exactly the kind of invented number the "honest metrics" bar exists to catch.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.agent.decision import decide
from app.classifier.rules import classify_by_rule
from app.execution.razorpay_client import execute_action
from app.guardrails.gate import gate


def _hours_since(iso_timestamp: Optional[str]) -> Optional[float]:
    if not iso_timestamp:
        return None
    then = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return round((now - then).total_seconds() / 3600, 1)


def build_case_context(case_input: dict[str, Any], prior_cases: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Derives guardrail/agent context from case_input plus this subscription's
    prior recovery cases — a single source of truth instead of a separately
    maintained counter that can drift from what actually happened.
    """
    same_sub = [c for c in prior_cases if c.get("subscription_id") == case_input["subscription_id"]]
    same_sub_sorted = sorted(same_sub, key=lambda c: c.get("created_at") or "")

    last_attempt_at = same_sub_sorted[-1]["created_at"] if same_sub_sorted else None
    unknown_count = sum(1 for c in same_sub if c.get("root_cause") == "unknown")

    return {
        "subscription_id": case_input["subscription_id"],
        "amount_paise": case_input["amount_paise"],
        "mandate_status": case_input.get("mandate_status", "active"),
        "attempt_count": len(same_sub),
        "hours_since_last_attempt": _hours_since(last_attempt_at),
        "unknown_classification_count": unknown_count,
    }


def process_case(
    case_input: dict[str, Any],
    prior_cases: list[dict[str, Any]],
    decision_client: Optional[Any] = None,
    execution_client: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Runs one case through the full pipeline.

    Returns: {status, root_cause, decision, gate_result, execution_result, audit_trail}
    audit_trail is a list of {stage, input, output, rule_fired} dicts —
    the same shape audit/logger.py persists as AuditLogEntry rows.
    """
    audit_trail: list[dict[str, Any]] = []

    def log(stage: str, input_snapshot: Any, output: Any, rule_fired: Optional[str] = None) -> None:
        audit_trail.append({"stage": stage, "input": input_snapshot, "output": output, "rule_fired": rule_fired})

    log("DETECTED", case_input, {"received": True})

    # --- classify ---
    root_cause = classify_by_rule(case_input.get("error_code"), case_input.get("error_reason")) or "unknown"
    log("CLASSIFIED",
        {"error_code": case_input.get("error_code"), "error_reason": case_input.get("error_reason")},
        {"root_cause": root_cause})

    case_context = build_case_context(case_input, prior_cases)
    case_context["root_cause"] = root_cause

    # --- decide ---
    try:
        decision = decide(case_context, client=decision_client)
    except Exception as exc:
        log("DECIDED", case_context, {"error": str(exc)})
        return {"status": "FAILED", "root_cause": root_cause, "decision": None,
                "gate_result": None, "execution_result": None, "audit_trail": audit_trail}
    log("DECIDED", case_context, decision)

    # --- gate ---
    gate_result = gate(case_context, proposed_action=decision["action"])
    log("GATED", {"proposed_action": decision["action"]},
        {"approved": gate_result.approved, "action": gate_result.action},
        rule_fired=gate_result.rule_fired)

    # --- terminal shortcut: escalation is a human workflow step, not an API call ---
    if gate_result.action == "escalate_human":
        log("ESCALATED", {"action": gate_result.action}, {"final_status": "ESCALATED"})
        return {"status": "ESCALATED", "root_cause": root_cause, "decision": decision,
                "gate_result": gate_result, "execution_result": None, "audit_trail": audit_trail}

    # --- execute ---
    exec_case = {**case_input, "scheduled_for": decision.get("scheduled_for")}
    try:
        execution_result = execute_action(gate_result.action, exec_case, client=execution_client)
    except Exception as exc:
        log("EXECUTING", {"action": gate_result.action}, {"error": str(exc)})
        return {"status": "FAILED", "root_cause": root_cause, "decision": decision,
                "gate_result": gate_result, "execution_result": None, "audit_trail": audit_trail}

    log("EXECUTING", {"action": gate_result.action}, execution_result)

    # 'stop' is genuinely terminal (subscription cancelled); everything else
    # is pending a real outcome signal we don't have yet — see module docstring.
    final_status = "STOPPED" if gate_result.action == "stop" else "EXECUTING"
    log(final_status, {}, {"final_status": final_status})

    return {"status": final_status, "root_cause": root_cause, "decision": decision,
            "gate_result": gate_result, "execution_result": execution_result, "audit_trail": audit_trail}
