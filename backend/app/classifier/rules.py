"""
Deterministic first pass: map a Razorpay-style error_code/error_reason to a
fixed root-cause taxonomy. Only unmatched signals fall through to the LLM
fallback (classifier/llm_fallback.py).

Taxonomy: insufficient_funds | expired_instrument | mandate_revoked |
          bank_timeout | issuer_decline | unknown

Substring matching on error_reason (not exact equality) so this stays
resilient if Razorpay appends extra detail to the reason string without
changing the underlying failure category.
"""

REASON_KEYWORD_MAP: dict[str, str] = {
    "insufficient_funds": "insufficient_funds",
    "expired_card": "expired_instrument",
    "mandate_cancelled": "mandate_revoked",
    "mandate_revoked": "mandate_revoked",
    "bank_timeout": "bank_timeout",
    "issuer_declined": "issuer_decline",
}


def classify_by_rule(error_code: str, error_reason: str) -> str | None:
    """
    Returns a root-cause string if a keyword rule matches, else None
    (signals the caller to fall through to the LLM classifier).
    error_code is accepted for future rules that key off it directly but is
    currently unused — kept in the signature so callers don't need to change
    when that's added.
    """
    reason = (error_reason or "").lower()
    for keyword, root_cause in REASON_KEYWORD_MAP.items():
        if keyword in reason:
            return root_cause
    return None
