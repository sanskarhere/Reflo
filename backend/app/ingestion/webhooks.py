"""
Receives Razorpay test-mode webhooks (subscription.charge.failed etc),
normalizes them, and creates a RecoveryCase at status=DETECTED.
Idempotency key: subscription_id + attempt_number (FR-ingestion, NFR-idempotency).
"""

def handle_payment_failed_event(payload: dict) -> dict:
    """Stub — normalize Razorpay payload into internal event shape."""
    raise NotImplementedError
