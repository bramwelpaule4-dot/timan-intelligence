"""Tests for the provider-neutral billing ledger."""

from __future__ import annotations

import pytest

from timan_intelligence.billing.records import (
    BillingError,
    create_invoice,
    get_invoice,
    issue_invoice,
    list_invoices,
    record_payment_transaction,
)
from timan_intelligence.billing.settlement import finalize_payment_transaction
from timan_intelligence.billing.upgrades import create_upgrade_invoice
from timan_intelligence.entitlements.subscriptions import (
    get_effective_plan_code,
    request_plan_change,
    review_plan_change_request,
)
from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


@pytest.fixture
def billing_database(tmp_path, monkeypatch):
    path = tmp_path / "billing.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    initialise_database()
    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (id, username, email, full_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("bill-user", "billuser", "bill@example.com", "Billing User", "hash"),
        )
        connection.execute(
            "INSERT INTO organisations (id, name) VALUES (?, ?)",
            ("bill-org", "Billing Organisation"),
        )
    return path


def _invoice():
    return create_invoice(
        user_id="bill-user",
        currency="KES",
        tax_minor=1000,
        items=[
            {"description": "Professional subscription", "plan_code": "professional", "quantity": 1, "unit_amount_minor": 10000},
            {"description": "Additional service", "quantity": 2, "unit_amount_minor": 2000},
        ],
    )


def test_invoice_creation_calculates_totals_and_preserves_items(billing_database):
    invoice_id = _invoice()
    invoice = get_invoice(invoice_id)
    assert invoice is not None
    assert invoice["status"] == "draft"
    assert invoice["currency"] == "KES"
    assert invoice["subtotal_minor"] == 14000
    assert invoice["tax_minor"] == 1000
    assert invoice["total_minor"] == 15000
    assert invoice["amount_paid_minor"] == 0
    assert len(invoice["items"]) == 2
    assert invoice["items"][1]["line_total_minor"] == 4000
    assert invoice["events"][0]["event_type"] == "invoice.created"


def test_invoice_creation_validates_single_owner_and_item_values(billing_database):
    with pytest.raises(BillingError):
        create_invoice(
            user_id="bill-user",
            organisation_id="bill-org",
            items=[{"description": "Service", "unit_amount_minor": 100}],
        )
    with pytest.raises(BillingError):
        create_invoice(
            user_id="bill-user",
            items=[{"description": "Invalid quantity", "quantity": 0, "unit_amount_minor": 100}],
        )
    with database_connection() as connection:
        assert connection.execute("SELECT COUNT(*) AS n FROM billing_invoices").fetchone()["n"] == 0


def test_issue_and_partial_payment_finalization(billing_database):
    invoice_id = _invoice()
    assert issue_invoice(invoice_id) is True
    with pytest.raises(BillingError, match="Only a draft"):
        issue_invoice(invoice_id)

    first = record_payment_transaction(
        invoice_id,
        amount_minor=5000,
        currency="KES",
        provider_code="manual",
        status="pending",
        idempotency_key="attempt-00000001",
    )
    assert finalize_payment_transaction(first, status="succeeded") is True
    assert finalize_payment_transaction(first, status="succeeded") is True
    invoice = get_invoice(invoice_id)
    assert invoice["status"] == "open"
    assert invoice["amount_paid_minor"] == 5000

    second = record_payment_transaction(
        invoice_id,
        amount_minor=10000,
        currency="KES",
        provider_code="manual",
        status="succeeded",
        idempotency_key="attempt-00000002",
    )
    assert second
    invoice = get_invoice(invoice_id)
    assert invoice["status"] == "paid"
    assert invoice["amount_paid_minor"] == 15000
    assert invoice["paid_at"] is not None
    assert len(invoice["events"]) >= 4


def test_payment_idempotency_and_terminal_state(billing_database):
    invoice_id = _invoice()
    issue_invoice(invoice_id)
    payment_id = record_payment_transaction(
        invoice_id,
        amount_minor=15000,
        currency="KES",
        provider_code="manual",
        status="succeeded",
        idempotency_key="attempt-unique-0001",
    )
    assert record_payment_transaction(
        invoice_id,
        amount_minor=15000,
        currency="KES",
        provider_code="manual",
        status="succeeded",
        idempotency_key="attempt-unique-0001",
    ) == payment_id
    with pytest.raises(BillingError, match="another payment"):
        record_payment_transaction(
            invoice_id,
            amount_minor=14000,
            currency="KES",
            provider_code="manual",
            status="succeeded",
            idempotency_key="attempt-unique-0001",
        )
    with pytest.raises(BillingError, match="cannot be changed"):
        finalize_payment_transaction(payment_id, status="failed")


def test_payment_rejects_currency_mismatch_and_overpayment(billing_database):
    invoice_id = _invoice()
    issue_invoice(invoice_id)
    with pytest.raises(BillingError, match="currency"):
        record_payment_transaction(
            invoice_id, amount_minor=100, currency="USD",
            provider_code="manual", status="succeeded",
            idempotency_key="attempt-currency-0001",
        )
    with pytest.raises(BillingError, match="exceeds"):
        record_payment_transaction(
            invoice_id, amount_minor=15001, currency="KES",
            provider_code="manual", status="succeeded",
            idempotency_key="attempt-overpay-0001",
        )


def test_failed_payment_does_not_reduce_invoice_balance(billing_database):
    invoice_id = _invoice()
    issue_invoice(invoice_id)
    record_payment_transaction(
        invoice_id,
        amount_minor=15000,
        currency="KES",
        provider_code="manual",
        status="failed",
        idempotency_key="attempt-failed-0001",
        failure_code="DECLINED",
        failure_message="Payment was declined.",
    )
    invoice = get_invoice(invoice_id)
    assert invoice["status"] == "open"
    assert invoice["amount_paid_minor"] == 0
    assert invoice["payments"][0]["status"] == "failed"


def test_owner_scoped_invoice_listing(billing_database):
    personal = _invoice()
    organisation = create_invoice(
        organisation_id="bill-org",
        items=[{"description": "Organisation service", "unit_amount_minor": 500}],
    )
    assert [row["id"] for row in list_invoices(user_id="bill-user")] == [personal]
    assert [row["id"] for row in list_invoices(organisation_id="bill-org")] == [organisation]


def _approved_upgrade_request():
    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (id, username, email, full_name, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("bill-admin", "billadmin", "admin@example.com", "Billing Admin", "hash", "admin"),
        )
    request_id = request_plan_change(
        requested_by="bill-user",
        user_id="bill-user",
        requested_plan_code="professional",
    )
    assert review_plan_change_request(
        request_id,
        reviewer_id="bill-admin",
        decision="approve",
        notes="Approved for upgrade payment.",
    ) == "approved_pending_payment"
    return request_id


def test_upgrade_entitlement_changes_only_after_full_payment(billing_database):
    request_id = _approved_upgrade_request()
    invoice_id = create_upgrade_invoice(
        request_id,
        amount_minor=15000,
        currency="KES",
        period_start="2026-11-08T00:00:00Z",
        period_end="2026-12-08T00:00:00Z",
    )
    assert get_effective_plan_code(user_id="bill-user") == "free"
    invoice = get_invoice(invoice_id)
    assert invoice["subscription_change_request_id"] == request_id
    assert invoice["status"] == "open"

    partial = record_payment_transaction(
        invoice_id,
        amount_minor=5000,
        currency="KES",
        provider_code="manual",
        status="pending",
        idempotency_key="upgrade-partial-0001",
    )
    finalize_payment_transaction(partial, status="succeeded")
    assert get_effective_plan_code(user_id="bill-user") == "free"

    balance = get_invoice(invoice_id)
    remaining = int(balance["total_minor"]) - int(balance["amount_paid_minor"])
    final = record_payment_transaction(
        invoice_id,
        amount_minor=remaining,
        currency="KES",
        provider_code="manual",
        status="pending",
        idempotency_key="upgrade-final-0001",
    )
    finalize_payment_transaction(final, status="succeeded")
    assert get_effective_plan_code(user_id="bill-user") == "professional"
    assert get_invoice(invoice_id)["status"] == "paid"
    with database_connection() as connection:
        request = connection.execute(
            "SELECT status FROM subscription_change_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        assert request["status"] == "completed"
        events = connection.execute(
            "SELECT COUNT(*) AS n FROM billing_events WHERE invoice_id = ? AND event_type = 'subscription.upgrade_activated'",
            (invoice_id,),
        ).fetchone()
        assert events["n"] == 1


def test_upgrade_invoice_requires_approved_request_and_explicit_period(billing_database):
    request_id = request_plan_change(
        requested_by="bill-user",
        user_id="bill-user",
        requested_plan_code="professional",
    )
    with pytest.raises(BillingError, match="approved upgrade"):
        create_upgrade_invoice(
            request_id,
            amount_minor=10000,
            currency="KES",
            period_start="2026-11-08T00:00:00Z",
            period_end="2026-12-08T00:00:00Z",
        )
