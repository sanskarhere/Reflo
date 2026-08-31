"""
Integration test: POST /webhooks/razorpay -> full pipeline -> DB, using
FastAPI's TestClient against an in-memory SQLite DB. The decision agent and
execution layer are monkeypatched (no live Grok/Razorpay calls), so this
test needs no API keys — it's testing the wiring, not the providers.

Unlike the unit tests elsewhere in this repo (which were manually verified
with plain assertion scripts since this sandbox has no network to install
fastapi/sqlalchemy), this file genuinely needs those packages installed to
run. Execute for real with:
    cd backend && pip install -r requirements-dev.txt && pytest tests/integration/
"""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import pipeline as pipeline_module
from app.db import Base, get_db
from app.main import app

WEBHOOK_SECRET = "whsec_test_integration"

SAMPLE_FAILURE_PAYLOAD = {
    "event": "subscription.charge.failed",
    "payload": {
        "subscription": {"entity": {"id": "sub_int_1", "customer_id": "cust_int_1", "status": "active"}},
        "payment": {"entity": {"id": "pay_int_1", "amount": 49900,
                                 "error_code": "BAD_REQUEST_ERROR",
                                 "error_reason": "payment_failed_insufficient_funds"}},
    },
}


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture()
def client(monkeypatch):
    # Fresh in-memory DB per test, so tests don't leak state into each other.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.config.RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    # Stub the decision agent and execution layer — same idea as the fake
    # clients used in the unit tests, applied here at the module-function
    # level since routes.py calls process_case() without client injection.
    monkeypatch.setattr(
        pipeline_module, "decide",
        lambda case_context, client=None: {"action": "retry_scheduled", "scheduled_for": None, "rationale": "test"},
    )
    monkeypatch.setattr(
        pipeline_module, "execute_action",
        lambda action, case, client=None: {"action": action, "note": "stubbed for integration test"},
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_failed_payment_webhook_creates_and_processes_case(client):
    body = json.dumps(SAMPLE_FAILURE_PAYLOAD).encode()
    response = client.post(
        "/webhooks/razorpay", content=body,
        headers={"X-Razorpay-Signature": _sign(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    case_id = data["case_id"]

    case_response = client.get(f"/cases/{case_id}")
    assert case_response.status_code == 200
    case = case_response.json()
    assert case["root_cause"] == "insufficient_funds"
    assert case["status"] == "EXECUTING"  # retry_scheduled, no guardrail override for a clean case

    audit_response = client.get(f"/cases/{case_id}/audit")
    stages = [e["stage"] for e in audit_response.json()["audit_trail"]]
    assert "DETECTED" in stages
    assert "CLASSIFIED" in stages
    assert "GATED" in stages


def test_duplicate_webhook_delivery_does_not_create_a_second_case(client):
    body = json.dumps(SAMPLE_FAILURE_PAYLOAD).encode()
    headers = {"X-Razorpay-Signature": _sign(body), "Content-Type": "application/json"}

    first = client.post("/webhooks/razorpay", content=body, headers=headers)
    second = client.post("/webhooks/razorpay", content=body, headers=headers)

    assert first.json()["case_id"] == second.json()["case_id"]


def test_invalid_signature_rejected(client):
    body = json.dumps(SAMPLE_FAILURE_PAYLOAD).encode()
    response = client.post(
        "/webhooks/razorpay", content=body,
        headers={"X-Razorpay-Signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


def test_unrecognized_event_type_is_acknowledged_not_errored(client):
    payload = {"event": "some.unrelated.event", "payload": {}}
    body = json.dumps(payload).encode()
    response = client.post(
        "/webhooks/razorpay", content=body,
        headers={"X-Razorpay-Signature": _sign(body), "Content-Type": "application/json"},
    )
    # Must be 200, not 4xx/5xx — Razorpay retries endpoints that don't
    # return 2xx, and we deliberately ignore event types we don't act on.
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
