"""
Deterministic gate — every agent decision passes through here before execution.
Loads rules.yaml; first matching active rule wins and overrides the agent's
proposed action. No rule fired => agent's proposed action is approved as-is.
"""
import yaml
from pathlib import Path

RULES_PATH = Path(__file__).parent / "rules.yaml"

def load_rules() -> list[dict]:
    with open(RULES_PATH) as f:
        return yaml.safe_load(f)["rules"]

def gate(case_context: dict, proposed_action: str) -> dict:
    """Stub — evaluate rules against case_context, return {approved, action, rule_fired}."""
    raise NotImplementedError
