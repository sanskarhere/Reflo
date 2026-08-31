"""
Tests for execution/razorpay_client.py using a fake Razorpay client — no
network, no real keys required. Covers execute_action() routing and the
no-op-but-logged acknowledgment path for retry actions (see module
docstring for why retry_now/retry_scheduled don't call a Razorpay API).
"""
import pytest

from app.execution.razorpay_client import execute_action


class _FakePaymentLink:
    def __init__(self):
        self.last_call = None

    def create(self, data):
        self.last_call = data
        return {"id": "plink_123", "short_url": "https://rzp.io/i/fake"}


class _FakeSubscription:
    def __init__(self):
        self.last_call = None

    def cancel(self, subscription_id, data):
        self.last_call = (subscription_id, data)
        return {"id": subscription_id, "status": "cancelled"}


class _FakeClient:
    def __init__(self):
        self.payment_link = _FakePaymentLink()
        self.subscription = _FakeSubscription()


def test_retry_now_acknowledges_without_api_call():
    result = execute_action("retry_now", {"subscription_id": "sub_1"})
    assert result["action"] == "acknowledge_automatic_retry"
    assert result["subscription_id"] == "sub_1"


def test_retry_scheduled_includes_scheduled_for():
    result = execute_action(
        "retry_scheduled",
        {"subscription_id": "sub_1", "scheduled_for": "2026-09-02T10:00:00Z"},
    )
    assert result["scheduled_for"] == "2026-09-02T10:00:00Z"


def test_send_payment_link_calls_payment_link_api():
    client = _FakeClient()
    case = {
        "subscription_id": "sub_1", "amount_paise": 49900, "customer_name": "Asha",
        "customer_email": "asha@example.com", "customer_contact": "9999999999",
    }
    result = execute_action("send_payment_link", case, client=client)
    assert result["short_url"] == "https://rzp.io/i/fake"
    assert client.payment_link.last_call["amount"] == 49900
    assert client.payment_link.last_call["customer"]["name"] == "Asha"


def test_stop_cancels_subscription():
    client = _FakeClient()
    result = execute_action("stop", {"subscription_id": "sub_9"}, client=client)
    assert result["status"] == "cancelled"
    assert client.subscription.last_call[0] == "sub_9"


def test_unhandled_action_raises():
    with pytest.raises(ValueError):
        execute_action("escalate_human", {"subscription_id": "sub_1"})
