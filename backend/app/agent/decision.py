"""
Calls Grok (via xAI's OpenAI-compatible API) with the fixed
RECOMMEND_ACTION_TOOL schema (agent/tools.py) and returns its recommended
action. This is the one place in the system where LLM judgment weighs
context (root cause, amount, attempt history) against each other to make a
call — see docs/ARCHITECTURE.md section 7.1 for why this is deliberately
NOT used in the classifier.

The returned action is advisory only: guardrails/gate.py always gets the
final say before anything executes (docs/ARCHITECTURE.md section 3.3).

Provider note: uses xAI's Grok models via their OpenAI-SDK-compatible
endpoint (base_url=https://api.x.ai/v1) rather than calling a provider's
native SDK directly. Because the interface is just the standard OpenAI
chat-completions shape, swapping to a different OpenAI-compatible provider
later is a one-line base_url/model change, not a rewrite.

`openai` is imported lazily inside _get_client() rather than at module
level, so this module — and its tests — don't require the SDK to be
installed unless you're actually making a live call.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from app.agent.tools import RECOMMEND_ACTION_TOOL

MODEL = "grok-4.6"
XAI_BASE_URL = "https://api.x.ai/v1"

SYSTEM_PROMPT = (
    "You are a payment-recovery decision assistant for Reflo. Given a failed "
    "subscription payment's root cause and history, recommend exactly one "
    "recovery action using the recommend_action tool. You may only choose "
    "from the tool's fixed action set. Your recommendation is advisory — a "
    "separate deterministic guardrail layer may override it, so explain your "
    "reasoning briefly rather than trying to out-think the guardrails "
    "yourself. Prefer retry_scheduled over retry_now for recoverable causes "
    "like insufficient_funds, since immediate retries rarely succeed. Prefer "
    "escalate_human when you are uncertain."
)


def build_case_summary(case_context: dict[str, Any]) -> str:
    """Human-readable summary handed to the model — only the fields the decision needs, no raw PII."""
    return (
        f"Root cause: {case_context.get('root_cause')}\n"
        f"Amount: {case_context.get('amount_paise')} paise\n"
        f"Attempt count so far: {case_context.get('attempt_count', 0)}\n"
        f"Hours since last attempt: {case_context.get('hours_since_last_attempt')}\n"
        f"Mandate status: {case_context.get('mandate_status')}\n"
        f"Prior unknown-classification count: {case_context.get('unknown_classification_count', 0)}\n"
    )


def _get_client():
    from openai import OpenAI
    from app.config import XAI_API_KEY
    return OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)


def decide(case_context: dict[str, Any], client: Optional[Any] = None) -> dict[str, Any]:
    """
    Returns {"action": ..., "scheduled_for": ..., "rationale": ...}.

    Raises ValueError if Grok doesn't return a recommend_action tool call —
    fail loud rather than silently guess an action, since this feeds
    straight into the guardrail gate and audit log.
    """
    client = client or _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_case_summary(case_context)},
        ],
        tools=[RECOMMEND_ACTION_TOOL],
        tool_choice={"type": "function", "function": {"name": "recommend_action"}},
    )

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None) or []
    for call in tool_calls:
        if call.function.name == "recommend_action":
            return json.loads(call.function.arguments)

    raise ValueError("Grok did not return a recommend_action tool call")
