"""Unit tests for the Daraja STK Push adapter."""
import base64
import json

import pytest

from timan_intelligence.billing.daraja import DarajaAdapter, DarajaError
from timan_intelligence.billing.mpesa_reconciliation import (
    ReconciliationError, attach_originator, create_attempt, verify_result,
)
from timan_intelligence.billing.records import create_invoice, issue_invoice, record_payment_transaction
from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


def test_normalize_kenyan_phone_numbers():
    assert DarajaAdapter.normalize_phone("0712345678") == "254712345678"
    assert DarajaAdapter.normalize_phone("+254712345678") == "254712345678"
    assert DarajaAdapter.normalize_phone("0712 345 678") == "254712345678"
    assert DarajaAdapter.normalize_phone("+254 (712) 345-678") == "254712345678"
    assert DarajaAdapter.normalize_phone("0112345678") == "254112345678"
    with pytest.raises(DarajaError):
        DarajaAdapter.normalize_phone("12345")


def test_production_mode_is_blocked_until_independent_reconciliation_exists():
    env = {
        "DARAJA_ENVIRONMENT": "production",
        "DARAJA_CONSUMER_KEY": "key",
        "DARAJA_CONSUMER_SECRET": "secret",
        "DARAJA_BUSINESS_SHORTCODE": "123456",
        "DARAJA_PASSKEY": "pass",
        "DARAJA_CALLBACK_URL": "https://example.org/api/v1/payments/mpesa/callback",
    }
    with pytest.raises(DarajaError, match="independent Safaricom"):
        DarajaAdapter(environ=env)._config()


def test_daraja_requires_complete_credentials_and_https_callback():
    with pytest.raises(DarajaError, match="must be configured"):
        DarajaAdapter(environ={})._config()
    env = {
        "DARAJA_CONSUMER_KEY": "key", "DARAJA_CONSUMER_SECRET": "secret",
        "DARAJA_BUSINESS_SHORTCODE": "123456", "DARAJA_PASSKEY": "pass",
        "DARAJA_CALLBACK_URL": "http://localhost/callback",
    }
    with pytest.raises(DarajaError, match="HTTPS"):
        DarajaAdapter(environ=env)._config()


def test_stk_password_is_generated_from_shortcode_passkey_timestamp():
    shortcode, passkey, timestamp = "174379", "test-passkey", "20261108123000"
    actual = base64.b64decode(
        base64.b64encode((shortcode + passkey + timestamp).encode())
    ).decode()
    assert actual == shortcode + passkey + timestamp


def test_callback_rejects_malformed_json_without_network_call():
    adapter = DarajaAdapter(environ={})
    with pytest.raises(DarajaError, match="Malformed"):
        adapter.verify_webhook(b"not-json", {})



@pytest.fixture
def reconciliation_database(tmp_path, monkeypatch):
    path = tmp_path / "mpesa-reconciliation.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    initialise_database()
    with database_connection() as connection:
        connection.execute(
            "INSERT INTO users (id, username, email, full_name, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("mpesa-user", "mpesauser", "mpesa@example.com", "M-Pesa User", "hash"),
        )
    invoice_id = create_invoice(
        user_id="mpesa-user",
        currency="KES",
        items=[{"description": "Professional plan", "unit_amount_minor": 150000}],
    )
    issue_invoice(invoice_id)
    payment_id = record_payment_transaction(
        invoice_id, amount_minor=150000, currency="KES", provider_code="mpesa",
        status="pending", idempotency_key="mpesa-reconcile-test-001",
    )
    create_attempt(payment_id, "ws_CO_test_001", "QHT7ABC123", 150000)
    attach_originator("ws_CO_test_001", "1234-567890-1")
    return payment_id


def _transaction_status_result(*, amount=1500, receipt="QHT7ABC123", status="Completed"):
    return {
        "Result": {
            "ResultType": 0,
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "OriginatorConversationID": "1234-567890-1",
            "ConversationID": "AG_20261108_123456",
            "TransactionID": receipt,
            "ResultParameters": {
                "ResultParameter": [
                    {"Key": "ReceiptNo", "Value": receipt},
                    {"Key": "Amount", "Value": amount},
                    {"Key": "TransactionStatus", "Value": status},
                ]
            },
        }
    }


def test_transaction_status_reconciliation_requires_matching_receipt_amount_and_completed_status(reconciliation_database):
    verified = verify_result(json.dumps(_transaction_status_result()).encode())
    assert verified == {
        "payment_transaction_id": reconciliation_database,
        "checkout_request_id": "ws_CO_test_001",
        "receipt": "QHT7ABC123",
        "amount_minor": 150000,
    }


@pytest.mark.parametrize(
    "result",
    [
        _transaction_status_result(amount=1499),
        _transaction_status_result(receipt="OTHER12345"),
        _transaction_status_result(status="Cancelled"),
    ],
)
def test_transaction_status_mismatch_is_rejected(reconciliation_database, result):
    with pytest.raises(ReconciliationError, match="does not match"):
        verify_result(json.dumps(result).encode())


def test_transaction_status_rejects_unknown_originator(reconciliation_database):
    payload = _transaction_status_result()
    payload["Result"]["OriginatorConversationID"] = "unknown-originator"
    with pytest.raises(ReconciliationError, match="Unknown"):
        verify_result(json.dumps(payload).encode())



def test_verified_transaction_status_callback_settles_invoice(reconciliation_database, monkeypatch):
    monkeypatch.setattr(
        DarajaAdapter,
        "_query",
        lambda self, checkout_id: {
            "ResponseCode": "0",
            "ResultCode": "0",
            "CheckoutRequestID": checkout_id,
        },
    )
    adapter = DarajaAdapter(environ={})
    result = adapter.handle_transaction_status_result(
        json.dumps(_transaction_status_result()).encode()
    )
    assert result == {"processed": True, "duplicate": False}
    with database_connection() as connection:
        payment = connection.execute(
            "SELECT status, provider_reference FROM payment_transactions WHERE id = ?",
            (reconciliation_database,),
        ).fetchone()
        reconciliation = connection.execute(
            "SELECT status, verified_receipt, verified_amount_minor "
            "FROM mpesa_transaction_reconciliations WHERE checkout_request_id = ?",
            ("ws_CO_test_001",),
        ).fetchone()
    assert payment["status"] == "succeeded"
    assert payment["provider_reference"] == "QHT7ABC123"
    assert reconciliation["status"] == "verified"
    assert reconciliation["verified_receipt"] == "QHT7ABC123"
    assert reconciliation["verified_amount_minor"] == 150000


def test_transaction_status_request_requires_https_callbacks(reconciliation_database, monkeypatch):
    adapter = DarajaAdapter(environ={
        "DARAJA_INITIATOR_NAME": "api-user",
        "DARAJA_SECURITY_CREDENTIAL": "encrypted-credential",
        "DARAJA_TRANSACTION_STATUS_RESULT_URL": "http://example.org/result",
        "DARAJA_TRANSACTION_STATUS_TIMEOUT_URL": "https://example.org/timeout",
    })
    monkeypatch.setattr(
        adapter, "_token",
        lambda: ("https://sandbox.safaricom.co.ke", {"shortcode": "174379"}, "token"),
    )
    with pytest.raises(DarajaError, match="public HTTPS"):
        adapter._request_transaction_status(
            {"id": reconciliation_database}, "ws_CO_test_001",
            "QHT7ABC123", 150000, create_record=False,
        )
