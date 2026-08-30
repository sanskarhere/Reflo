"""Idempotency test — pending until backend/app/ingestion/webhooks.py is implemented."""
import pytest


def test_duplicate_webhook_no_double_execution():
    pytest.skip("implement once ingestion webhook handler is built")
