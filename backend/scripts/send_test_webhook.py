"""
Sends a correctly-signed test webhook to a running Reflo backend — for
testing/debugging /webhooks/razorpay directly, which Swagger UI's /docs
page can't do (it has no way to compute the HMAC-SHA256 signature that
route requires).

Usage:
    cd backend
    python -m scripts.send_test_webhook \
        --url https://<your-render-url>/webhooks/razorpay \
        --secret <your RAZORPAY_WEBHOOK_SECRET> \
        --event subscription.charge.failed

    # or against local dev:
    python -m scripts.send_test_webhook --url http://localhost:8000/webhooks/razorpay --secret whsec_dev

Supported --event values: subscription.charge.failed, payment_link.paid,
payment.captured. Each sends a payload shaped like the real thing (same
shape used in tests/integration/test_webhook_flow.py) so this exercises
the actual parsing logic, not a simplified stand-in.
"""
import argparse
import hashlib
import hmac
import json
import uuid

import httpx

PAYLOADS = {
    "subscription.charge.failed": {
        "event": "subscription.charge.failed",
        "payload": {
            "subscription": {"entity": {"id": "sub_test_1", "customer_id": "cust_test_1", "status": "active"}},
            "payment": {"entity": {
                "id": f"pay_test_{uuid.uuid4().hex[:8]}", "amount": 49900,
                "error_code": "BAD_REQUEST_ERROR", "error_reason": "payment_failed_insufficient_funds",
            }},
        },
    },
    "payment_link.paid": {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_test_1", "amount_paid": 49900,
                                          "notes": {"reflo_case_id": "", "reflo_subscription_id": "sub_test_1"}}},
            "payment": {"entity": {"id": f"pay_test_{uuid.uuid4().hex[:8]}", "amount": 49900}},
        },
    },
    "payment.captured": {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": f"pay_test_{uuid.uuid4().hex[:8]}", "amount": 49900,
            "subscription_id": "sub_test_1", "notes": {},
        }}},
    },
}


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Full webhook URL, e.g. https://your-app.onrender.com/webhooks/razorpay")
    parser.add_argument("--secret", required=True, help="Your RAZORPAY_WEBHOOK_SECRET")
    parser.add_argument("--event", default="subscription.charge.failed", choices=PAYLOADS.keys())
    parser.add_argument("--case-id", default=None, help="For payment_link.paid: the real case_id to resolve (optional)")
    args = parser.parse_args()

    payload = PAYLOADS[args.event]
    if args.event == "payment_link.paid" and args.case_id:
        payload["payload"]["payment_link"]["entity"]["notes"]["reflo_case_id"] = args.case_id

    body = json.dumps(payload).encode()
    signature = sign(body, args.secret)

    print(f"POST {args.url}")
    print(f"Event: {args.event}")
    print(f"Body: {body.decode()}\n")

    response = httpx.post(
        args.url, content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")


if __name__ == "__main__":
    main()
