"""
Deterministic gate — every agent decision passes through here before execution.

Loads rules.yaml; the first active rule that fires overrides the agent's
proposed action. If no rule fires, the agent's proposed action is approved
as-is. Rule order in rules.yaml IS priority order — non-negotiable rules
(mandate_revoked) are listed first so they always win over softer ones.

Deliberately NOT using eval() on config strings: each rule has a typed
`type` field mapped to a small checker function below. This keeps the gate
auditable, unit-testable in isolation, and safe against malformed config.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import yaml

RULES_PATH = Path(__file__).parent / "rules.yaml"


@dataclass
class GateResult:
    approved: bool
    action: str
    rule_fired: Optional[str] = None


def load_rules() -> list[dict]:
    with open(RULES_PATH) as f:
        return yaml.safe_load(f)["rules"]


# --- individual rule checkers ----------------------------------------------
# Each checker takes (case_context, rule_config) and returns True if the
# rule's condition is met (i.e. the rule "fires" and overrides the action).

def _attempt_count_gte(ctx: dict, rule: dict) -> bool:
    return ctx.get("attempt_count", 0) >= rule["threshold"]


def _hours_since_last_attempt_lt(ctx: dict, rule: dict) -> bool:
    hours = ctx.get("hours_since_last_attempt")
    return hours is not None and hours < rule["threshold"]


def _mandate_status_eq(ctx: dict, rule: dict) -> bool:
    return ctx.get("mandate_status") == rule["value"]


def _amount_paise_gt(ctx: dict, rule: dict) -> bool:
    return ctx.get("amount_paise", 0) > rule["threshold"]


def _unknown_classification_count_gte(ctx: dict, rule: dict) -> bool:
    return ctx.get("unknown_classification_count", 0) >= rule["threshold"]


CHECKERS: dict[str, Callable[[dict, dict], bool]] = {
    "attempt_count_gte": _attempt_count_gte,
    "hours_since_last_attempt_lt": _hours_since_last_attempt_lt,
    "mandate_status_eq": _mandate_status_eq,
    "amount_paise_gt": _amount_paise_gt,
    "unknown_classification_count_gte": _unknown_classification_count_gte,
}


def gate(case_context: dict, proposed_action: str, rules: Optional[list[dict]] = None) -> GateResult:
    """
    Evaluate active rules in file order against case_context. The first
    rule that fires overrides proposed_action entirely — this is what makes
    the system "bounded" rather than advisory.

    Args:
        case_context: fields like attempt_count, mandate_status, amount_paise,
            hours_since_last_attempt, unknown_classification_count.
        proposed_action: the action the decision agent recommended.
        rules: injectable for tests; defaults to loading rules.yaml.

    Returns:
        GateResult — if approved, action == proposed_action and rule_fired
        is None. If blocked, action is the forced_action from the rule that
        fired, and rule_fired names it for the audit log.
    """
    rules = rules if rules is not None else load_rules()

    for rule in rules:
        if not rule.get("active", True):
            continue
        checker = CHECKERS.get(rule["type"])
        if checker is None:
            raise ValueError(f"Unknown guardrail rule type: {rule['type']!r} in rule {rule.get('name')!r}")
        if checker(case_context, rule):
            return GateResult(approved=False, action=rule["forced_action"], rule_fired=rule["name"])

    return GateResult(approved=True, action=proposed_action, rule_fired=None)
