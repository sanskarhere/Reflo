"""
Fixed action-set tool schema for the decision agent (docs/ARCHITECTURE.md 4.4).
The model can only ever return one of these five actions — bounded by
construction, not by prompt discipline.

Uses OpenAI-style function-calling shape rather than Anthropic's tool_use
shape, since the decision agent calls xAI's Grok via its OpenAI-compatible
API (see agent/decision.py).
"""

RECOMMEND_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "recommend_action",
        "description": "Recommend one recovery action for a failed payment case.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["retry_now", "retry_scheduled", "send_payment_link",
                              "escalate_human", "stop"],
                },
                "scheduled_for": {
                    "type": ["string", "null"],
                    "description": "ISO8601 timestamp, or null if not applicable",
                },
                "rationale": {"type": "string"},
            },
            "required": ["action", "rationale"],
        },
    },
}
