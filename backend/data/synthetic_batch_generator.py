"""
Generates a synthetic batch of failed subscription-payment cases for driving
the pipeline end-to-end before any real merchant data exists.

Each record carries BOTH the raw failure signal (error_code, error_reason) —
the only thing the classifier is allowed to see — and a hidden
true_root_cause label, so classifier precision/recall can be measured
honestly against ground truth (docs/ARCHITECTURE.md section 6.3).
true_root_cause must never be passed into classify_by_rule() or the agent.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone

# Illustrative pairings shaped like Razorpay's public error taxonomy
# (error_code / error_description). Swap in exact values from real
# test-mode webhook payloads once integration testing starts.
#
# Each true_root_cause maps to SEVERAL possible reason-string phrasings,
# not one — including near-miss phrasings that deliberately do NOT contain
# the classifier's exact keyword. This is what makes precision/recall on
# this batch honest rather than circular: classify_by_rule() will legitimately
# miss some of these and fall through to "unknown", which is the correct,
# intended behavior (see classifier/rules.py + the escalation guardrail).
# Format: (true_root_cause, [reason_string_variants], error_code, sampling_weight)
ERROR_SIGNAL_GROUPS = [
    ("insufficient_funds", [
        "payment_failed_insufficient_funds",       # matches rule
        "insufficient balance in account",          # near-miss, no keyword match
        "insufficient_funds_at_bank",                # matches rule
    ], "BAD_REQUEST_ERROR", 25),
    ("expired_instrument", [
        "payment_failed_expired_card",               # matches rule
        "card has expired, please update",           # near-miss, no keyword match
    ], "BAD_REQUEST_ERROR", 15),
    ("mandate_revoked", [
        "payment_failed_mandate_cancelled",          # matches rule
        "upi mandate was revoked by customer",       # near-miss, no underscore keyword match
        "e-mandate no longer active",                # near-miss
    ], "GATEWAY_ERROR", 10),
    ("bank_timeout", [
        "payment_failed_bank_timeout",                # matches rule
        "no response from issuing bank",              # near-miss, no keyword match
    ], "GATEWAY_ERROR", 15),
    ("issuer_decline", [
        "payment_failed_issuer_declined",             # matches rule
        "card issuer declined the transaction",       # near-miss, no keyword match
    ], "BAD_REQUEST_ERROR", 15),
    ("unknown", [
        "payment_failed_unclassified",
        "risk_check_review_required",
        "generic_processing_error",
    ], "SERVER_ERROR", 10),
]


def _weighted_group_choice(groups: list[tuple]) -> tuple:
    """Pick a (true_root_cause, reason_variants, error_code) group by weight."""
    total = sum(w for *_, w in groups)
    r = random.uniform(0, total)
    upto = 0.0
    for *rest, w in groups:
        upto += w
        if upto >= r:
            return tuple(rest)
    return tuple(groups[-1][:-1])


def generate_batch(n: int = 50, seed: int = 42) -> list[dict]:
    """
    Returns n case dicts with:
      - raw failure signal: error_code, error_reason (classifier input)
      - true_root_cause: ground truth, evaluation-only, NOT classifier input
      - guardrail context: attempt_count, mandate_status,
        hours_since_last_attempt, unknown_classification_count, amount_paise
      - identifiers: id, subscription_id, customer_id, created_at

    Reason strings are sampled per-record from several real-ish phrasings
    per root cause (see ERROR_SIGNAL_GROUPS), some of which the deterministic
    classifier will correctly fail to match — that's intentional, and is
    what makes the resulting precision/recall numbers meaningful.
    """
    random.seed(seed)
    batch = []

    for i in range(n):
        true_root_cause, reason_variants, error_code = _weighted_group_choice(ERROR_SIGNAL_GROUPS)
        error_reason = random.choice(reason_variants)

        # Amounts: mostly typical subscription tiers, ~8% high-value outliers
        # so the high_value guardrail rule actually gets exercised.
        if random.random() < 0.08:
            amount_paise = random.randint(5_000_001, 15_000_000)
        else:
            amount_paise = random.randint(29_900, 499_900)

        mandate_status = (
            "revoked" if true_root_cause == "mandate_revoked"
            else random.choices(["active", "revoked"], weights=[95, 5])[0]
        )

        attempt_count = random.choices([0, 1, 2, 3, 4], weights=[40, 25, 15, 12, 8])[0]
        hours_since_last_attempt = None if attempt_count == 0 else round(random.uniform(0.5, 48), 1)
        unknown_classification_count = (
            2 if true_root_cause == "unknown" and random.random() < 0.3
            else random.choice([0, 0, 1])
        )

        batch.append({
            "id": str(uuid.uuid4()),
            "subscription_id": f"sub_{1000 + i}",
            "customer_id": f"cust_{2000 + i}",
            "error_code": error_code,
            "error_reason": error_reason,
            "true_root_cause": true_root_cause,
            "amount_paise": amount_paise,
            "mandate_status": mandate_status,
            "attempt_count": attempt_count,
            "hours_since_last_attempt": hours_since_last_attempt,
            "unknown_classification_count": unknown_classification_count,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 72))).isoformat(),
        })

    return batch


if __name__ == "__main__":
    import json
    records = generate_batch(50)
    print(json.dumps(records[:3], indent=2))
    print(f"\n...generated {len(records)} records total")
