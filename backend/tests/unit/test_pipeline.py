"""
End-to-end pipeline tests using fake decision/execution clients — no
network, no keys. Each test exercises one real path through
process_case(): classify -> decide -> gate -> execute/escalate/stop.
"""
import json
from types import SimpleNamespace

import pytest

from app.pipeline import process_case, build_case_context


# --- fakes ------------------------------------------------------------------

class _FakeFunction:
    def __init__(self, name, arguments_dict):
        self.name = name
        self.arguments = json.dumps(arguments_dict)


class _FakeToolCall:
    def __init__(self, name, arguments_dict):
        self.function = _FakeFunction(name, arguments_dict)


class _FakeDecisionClient:
    """Always recommends the given action, regardless of context — the gate is what we're testing."""
    def __init__(self, action="retry_now", scheduled_for=None):
        self._action = action
        self._scheduled_for = scheduled_for
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        tool_call = _FakeToolCall("recommend_action", {
            "action": self._action, "scheduled_for": self._scheduled_for,
            "rationale": "fake rationale for testing",
        })
        message = SimpleNamespace(tool_calls=[tool_call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeExecutionClient:
    def __init__(self):
        self.payment_link = SimpleNamespace(create=lambda data: {"short_url": "https://rzp.io/i/fake"})
        self.subscription = SimpleNamespace(cancel=lambda sid, data: {"id": sid, "status": "cancelled"})


BASE_CASE = {
    "subscription_id": "sub_1", "customer_id": "cust_1", "amount_paise": 49900,
    "error_code": "BAD_REQUEST_ERROR", "error_reason": "payment_failed_insufficient_funds",
    "mandate_status": "active",
}


# --- tests -------------------------------------------------------------------

def test_mandate_revoked_forces_stop_and_cancels_subscription():
    case = {**BASE_CASE, "mandate_status": "revoked"}
    result = process_case(case, prior_cases=[],
                           decision_client=_FakeDecisionClient("retry_now"),
                           execution_client=_FakeExecutionClient())
    assert result["status"] == "STOPPED"
    assert result["gate_result"].rule_fired == "mandate_revoked"
    assert result["execution_result"]["status"] == "cancelled"


def test_high_value_forces_escalation_without_execution():
    case = {**BASE_CASE, "amount_paise": 6_000_000}
    result = process_case(case, prior_cases=[],
                           decision_client=_FakeDecisionClient("retry_now"))
    assert result["status"] == "ESCALATED"
    assert result["gate_result"].rule_fired == "high_value"
    assert result["execution_result"] is None  # no execution call for escalation


def test_clean_case_recoverable_cause_ends_in_executing():
    result = process_case(BASE_CASE, prior_cases=[],
                           decision_client=_FakeDecisionClient("retry_scheduled", "2026-09-02T10:00:00Z"),
                           execution_client=_FakeExecutionClient())
    assert result["status"] == "EXECUTING"
    assert result["root_cause"] == "insufficient_funds"
    assert result["gate_result"].rule_fired is None  # agent's own choice, nothing overrode it
    assert result["execution_result"]["scheduled_for"] == "2026-09-02T10:00:00Z"


def test_send_payment_link_action_calls_real_execution_path():
    result = process_case(BASE_CASE, prior_cases=[],
                           decision_client=_FakeDecisionClient("send_payment_link"),
                           execution_client=_FakeExecutionClient())
    assert result["status"] == "EXECUTING"
    assert result["execution_result"]["short_url"] == "https://rzp.io/i/fake"


def test_prior_cases_drive_max_attempts_guardrail():
    prior = [{"subscription_id": "sub_1", "created_at": "2026-08-29T10:00:00Z", "root_cause": "insufficient_funds"}] * 3
    result = process_case(BASE_CASE, prior_cases=prior,
                           decision_client=_FakeDecisionClient("retry_now"),
                           execution_client=_FakeExecutionClient())
    assert result["status"] == "STOPPED"
    assert result["gate_result"].rule_fired == "max_attempts"


def test_decision_agent_failure_produces_failed_status_not_a_crash():
    class _BrokenClient:
        chat = SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider down"))
        ))
    result = process_case(BASE_CASE, prior_cases=[], decision_client=_BrokenClient())
    assert result["status"] == "FAILED"
    assert result["decision"] is None
    assert any(entry["stage"] == "DECIDED" and "error" in entry["output"] for entry in result["audit_trail"])


def test_build_case_context_counts_only_same_subscription():
    prior = [
        {"subscription_id": "sub_1", "created_at": "2026-08-29T10:00:00Z", "root_cause": "unknown"},
        {"subscription_id": "sub_2", "created_at": "2026-08-29T10:00:00Z", "root_cause": "unknown"},
    ]
    ctx = build_case_context(BASE_CASE, prior)
    assert ctx["attempt_count"] == 1  # only sub_1's prior case counts
    assert ctx["unknown_classification_count"] == 1
