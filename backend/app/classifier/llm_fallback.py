"""
Deliberately not implemented in v1 — see docs/ARCHITECTURE.md section 7.1
for the reasoning: classification is a closed-world problem where a
deterministic miss should safely escalate to a human (existing
repeat_unknown_cause guardrail), not trigger an LLM guess on an outcome
that costs real money if wrong. LLM judgment is reserved for
agent/decision.py, where it's actually needed.

This file is kept as an explicit placeholder — rather than deleted — so the
design decision is visible in the codebase, not just the docs.
"""


def classify_with_llm(event_context: dict) -> tuple[str, float]:
    raise NotImplementedError(
        "Deliberately unimplemented in v1 — see docs/ARCHITECTURE.md section 7.1. "
        "Unmatched cases should fall through to 'unknown' and the escalation "
        "guardrail, not call this function."
    )
