"""
Tests agent/decision.py with a fake OpenAI-shaped client — no real API calls,
no network, no key required. Confirms the tool schema is wired correctly
for xAI's OpenAI-compatible API and that a missing tool call fails loud.
"""
import json
from types import SimpleNamespace

import pytest

from app.agent.decision import decide, build_case_summary


class _FakeFunction:
    def __init__(self, name, arguments_dict):
        self.name = name
        self.arguments = json.dumps(arguments_dict)


class _FakeToolCall:
    def __init__(self, name, arguments_dict):
        self.function = _FakeFunction(name, arguments_dict)


class _FakeCompletions:
    def __init__(self, tool_calls):
        self._tool_calls = tool_calls

    def create(self, **kwargs):
        # Confirm the agent is actually forced into the fixed action set —
        # this is what makes the system "bounded" at the model-call level.
        assert kwargs["tool_choice"] == {"type": "function", "function": {"name": "recommend_action"}}
        assert kwargs["tools"][0]["function"]["name"] == "recommend_action"
        message = SimpleNamespace(tool_calls=self._tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeChat:
    def __init__(self, tool_calls):
        self.completions = _FakeCompletions(tool_calls)


class _FakeClient:
    def __init__(self, tool_calls):
        self.chat = _FakeChat(tool_calls)


def test_decide_returns_tool_input():
    fake_action = {
        "action": "retry_scheduled",
        "scheduled_for": "2026-09-02T10:00:00Z",
        "rationale": "Insufficient funds; wait for likely payday.",
    }
    client = _FakeClient([_FakeToolCall("recommend_action", fake_action)])

    result = decide(
        {"root_cause": "insufficient_funds", "amount_paise": 49900, "attempt_count": 1},
        client=client,
    )

    assert result == fake_action


def test_decide_raises_if_no_tool_call_returned():
    client = _FakeClient([])  # no tool_calls at all

    with pytest.raises(ValueError):
        decide({"root_cause": "unknown"}, client=client)


def test_build_case_summary_includes_key_fields():
    summary = build_case_summary({
        "root_cause": "bank_timeout", "amount_paise": 10000,
        "attempt_count": 2, "mandate_status": "active",
    })
    assert "bank_timeout" in summary
    assert "10000" in summary
