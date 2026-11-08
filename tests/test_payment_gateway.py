"""Tests for provider-neutral payment gateway orchestration."""
from dataclasses import dataclass

import pytest

from timan_intelligence.billing.gateway import (
    CheckoutRequest, CheckoutResponse, PaymentNotification,
    get_gateway, initiate_checkout, process_webhook, register_gateway,
)
from timan_intelligence.billing.records import BillingError, create_invoice, get_invoice
from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


@pytest.fixture
def billing_database(tmp_path, monkeypatch):
    path = tmp_path / "gateway.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    initialise_database()
    with database_connection() as connection:
        connection.execute(
            """INSERT INTO users (id, username, email, full_name, password_hash)
               VALUES (?, ?, ?, ?, ?)""",
            ("gateway-user", "gatewayuser", "gateway@example.com", "Gateway User", "hash"),
        )
    return path


class FakeGateway:
    provider_code = "fakepay"

    def __init__(self):
        self.notification = None
        self.checkout_requests = []

    def create_checkout(self, request: CheckoutRequest) -> CheckoutResponse:
        self.checkout_requests.append(request)
        return CheckoutResponse("checkout-123", "https://payments.example/checkout/123")

    def verify_webhook(self, raw_body: bytes, headers):
        if headers.get("X-Test-Signature") != "valid":
            raise BillingError("Invalid webhook signature.")
        return self.notification


def _invoice():
    return create_invoice(
        user_id="gateway-user", currency="KES",
        items=[{"description": "Professional plan", "unit_amount_minor": 12000}],
    )


def test_checkout_is_owner_scoped_and_persists_hosted_session(billing_database):
    invoice_id = _invoice()
    from timan_intelligence.billing.records import issue_invoice
    issue_invoice(invoice_id)
    gateway = FakeGateway()
    register_gateway(gateway)
    result = initiate_checkout(
        invoice_id, user_id="gateway-user", provider_code="fakepay",
        return_url="https://timanstat.example/billing/return",
    )
    assert result["checkout_url"] == "https://payments.example/checkout/123"
    assert gateway.checkout_requests[0].amount_minor == 12000
    with database_connection() as connection:
        session = connection.execute(
            "SELECT * FROM payment_checkout_sessions"
        ).fetchone()
        assert session["provider_checkout_id"] == "checkout-123"
        assert session["status"] == "created"
    assert get_invoice(invoice_id, user_id="gateway-user")["payments"][0]["status"] == "pending"


def test_checkout_rejects_wrong_owner_and_non_https_return_url(billing_database):
    invoice_id = _invoice()
    from timan_intelligence.billing.records import issue_invoice
    issue_invoice(invoice_id)
    register_gateway(FakeGateway())
    with pytest.raises(BillingError, match="not found"):
        initiate_checkout(
            invoice_id, user_id="someone-else", provider_code="fakepay",
            return_url="https://timanstat.example/return",
        )
    with pytest.raises(BillingError, match="HTTPS"):
        initiate_checkout(
            invoice_id, user_id="gateway-user", provider_code="fakepay",
            return_url="http://timanstat.example/return",
        )


def test_webhook_requires_signature_and_settles_once(billing_database):
    invoice_id = _invoice()
    from timan_intelligence.billing.records import issue_invoice
    issue_invoice(invoice_id)
    gateway = FakeGateway()
    register_gateway(gateway)
    checkout = initiate_checkout(
        invoice_id, user_id="gateway-user", provider_code="fakepay",
        return_url="https://timanstat.example/return",
    )
    payment_id = checkout["payment_transaction_id"]
    gateway.notification = PaymentNotification(
        provider_event_id="evt-001", payment_transaction_id=payment_id,
        status="succeeded", amount_minor=12000, currency="KES",
        provider_reference="provider-ref-001",
    )
    with pytest.raises(BillingError, match="signature"):
        process_webhook("fakepay", raw_body=b'{"event":"evt-001"}', headers={})
    first = process_webhook(
        "fakepay", raw_body=b'{"event":"evt-001"}',
        headers={"X-Test-Signature": "valid"},
    )
    second = process_webhook(
        "fakepay", raw_body=b'{"event":"evt-001"}',
        headers={"X-Test-Signature": "valid"},
    )
    assert first == {"processed": True, "duplicate": False}
    assert second == {"processed": True, "duplicate": True}
    invoice = get_invoice(invoice_id, user_id="gateway-user")
    assert invoice["status"] == "paid"
    assert invoice["amount_paid_minor"] == 12000
    with database_connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM payment_webhook_events"
        ).fetchone()["n"] == 1
