"""
Deterministic first pass: map Razorpay error_code/error_reason to a fixed
root-cause taxonomy. Only unmatched codes fall through to the LLM fallback.
Taxonomy: insufficient_funds | expired_instrument | mandate_revoked |
          bank_timeout | issuer_decline | unknown
"""

ERROR_CODE_MAP = {
    # "BAD_REQUEST_ERROR:payment_failed": "insufficient_funds",
}

def classify_by_rule(error_code: str, error_reason: str) -> str | None:
    """Stub — return a root cause string or None if no rule matches."""
    raise NotImplementedError
