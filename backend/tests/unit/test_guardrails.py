"""
Adversarial guardrail cases — docs/ARCHITECTURE.md section 6.2.
All must pass before the demo; these are what turn "bounded" from a claim
into a proven property.
"""
from app.guardrails.gate import gate


def test_mandate_revoked_forces_stop():
    ctx = {"mandate_status": "revoked", "attempt_count": 0, "amount_paise": 100_000}
    result = gate(ctx, proposed_action="retry_now")
    assert result.approved is False
    assert result.action == "stop"
    assert result.rule_fired == "mandate_revoked"


def test_max_attempts_forces_stop():
    ctx = {"attempt_count": 3, "mandate_status": "active", "amount_paise": 100_000}
    result = gate(ctx, proposed_action="retry_now")
    assert result.approved is False
    assert result.action == "stop"
    assert result.rule_fired == "max_attempts"


def test_high_value_forces_escalation():
    ctx = {"amount_paise": 6_000_000, "attempt_count": 0, "mandate_status": "active"}
    result = gate(ctx, proposed_action="retry_now")
    assert result.approved is False
    assert result.action == "escalate_human"
    assert result.rule_fired == "high_value"


def test_cooldown_blocks_immediate_retry():
    ctx = {"hours_since_last_attempt": 2, "attempt_count": 1,
           "mandate_status": "active", "amount_paise": 100_000}
    result = gate(ctx, proposed_action="retry_now")
    assert result.approved is False
    assert result.action == "retry_scheduled"
    assert result.rule_fired == "cooldown"


def test_repeat_unknown_cause_forces_escalation():
    ctx = {"unknown_classification_count": 2, "attempt_count": 0,
           "mandate_status": "active", "amount_paise": 100_000}
    result = gate(ctx, proposed_action="retry_now")
    assert result.approved is False
    assert result.action == "escalate_human"
    assert result.rule_fired == "repeat_unknown_cause"


def test_clean_case_approves_agent_action():
    """No rule fires -> the agent's proposed action passes through untouched."""
    ctx = {"attempt_count": 0, "mandate_status": "active", "amount_paise": 100_000}
    result = gate(ctx, proposed_action="send_payment_link")
    assert result.approved is True
    assert result.action == "send_payment_link"
    assert result.rule_fired is None


def test_rule_priority_mandate_revoked_beats_max_attempts():
    """Both conditions true; mandate_revoked must win — it's listed first as non-negotiable."""
    ctx = {"mandate_status": "revoked", "attempt_count": 5, "amount_paise": 100_000}
    result = gate(ctx, proposed_action="retry_now")
    assert result.rule_fired == "mandate_revoked"
