"""
Tests for ingestion/webhooks.py. verify_signature() and
parse_subscription_charge_failed() are pure functions with zero
dependencies, so they're fully tested here without a DB or the razorpay SDK.

handle_payment_failed_event() (the DB-touching idempotency path) needs
sqlalchemy + a real/in-memory DB session to test properly — that's an
integration test, not a unit test; add it under tests/integration/ once
the local environment has sqlalchemy installed.
"""
import hashlib
import hmac

from app.ingestion.webhooks import parse_subscription_charge_failed, verify_signature

SAMPLE_PAYLOAD = {
    "entity": "event",
    "event": "subscription.charge.failed",
    "payload": {
        "subscription": {
            "entity": {
                "id": "sub_1000",
                "customer_id": "cust_2000",
                "status": "active",
            }
        },
        "payment": {
            "entity": {
                "id": "pay_abc123",
                "amount": 49900,
                "error_code": "BAD_REQUEST_ERROR",
                "error_reason": "payment_failed_insufficient_funds",
            }
        },
    },
}


def test_parse_extracts_all_fields():
    result = parse_subscription_charge_failed(SAMPLE_PAYLOAD)
    assert result == {
        "subscription_id": "sub_1000",
        "customer_id": "cust_2000",
        "amount_paise": 49900,
        "error_code": "BAD_REQUEST_ERROR",
        "error_reason": "payment_failed_insufficient_funds",
        "source_payment_id": "pay_abc123",
        "mandate_status": "active",
    }


def test_parse_maps_cancelled_subscription_to_revoked_mandate():
    payload = {
        "payload": {
            "subscription": {"entity": {"id": "sub_2", "customer_id": "cust_2", "status": "cancelled"}},
            "payment": {"entity": {"id": "pay_2", "amount": 1000}},
        }
    }
    result = parse_subscription_charge_failed(payload)
    assert result["mandate_status"] == "revoked"


def test_verify_signature_accepts_valid_signature():
    secret = "whsec_test"
    body = b'{"event": "subscription.charge.failed"}'
    valid_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, valid_sig, secret) is True


def test_verify_signature_rejects_tampered_body():
    secret = "whsec_test"
    original_body = b'{"event": "subscription.charge.failed"}'
    tampered_body = b'{"event": "subscription.charge.failed", "extra": "injected"}'
    sig_for_original = hmac.new(secret.encode(), original_body, hashlib.sha256).hexdigest()
    assert verify_signature(tampered_body, sig_for_original, secret) is False


def test_verify_signature_rejects_wrong_secret():
    body = b'{"event": "subscription.charge.failed"}'
    sig_with_wrong_secret = hmac.new(b"wrong_secret", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig_with_wrong_secret, "whsec_test") is False
