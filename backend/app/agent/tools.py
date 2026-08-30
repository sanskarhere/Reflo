"""
Fixed action-set tool schema for the decision agent (docs/ARCHITECTURE.md 4.4).
The model can only ever return one of these five actions — bounded by
construction, not by prompt discipline.
"""

RECOMMEND_ACTION_TOOL = {
    "name": "recommend_action",
    "description": "Recommend one recovery action for a failed payment case.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["retry_now", "retry_scheduled", "send_payment_link",
                          "escalate_human", "stop"],
            },
            "scheduled_for": {"type": ["string", "null"], "description": "ISO8601 or null"},
            "rationale": {"type": "string"},
        },
        "required": ["action", "rationale"],
    },
}
