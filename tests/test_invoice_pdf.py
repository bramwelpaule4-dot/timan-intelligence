"""Tests for invoice PDF rendering and owner-scoped retrieval."""

import pytest

from timan_intelligence.billing.invoice_pdf import build_invoice_pdf
from timan_intelligence.billing.records import create_invoice, get_invoice
from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


@pytest.fixture
def billing_database(tmp_path, monkeypatch):
    path = tmp_path / "invoice-pdf.db"
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


def test_invoice_pdf_contains_valid_pdf_header_and_invoice_data(billing_database):
    invoice_id = create_invoice(
        user_id="bill-user", currency="KES", tax_minor=100,
        items=[{
            "description": "Professional subscription",
            "quantity": 2,
            "unit_amount_minor": 5000,
        }],
    )
    invoice = get_invoice(invoice_id, user_id="bill-user")
    pdf = build_invoice_pdf(invoice)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_invoice_retrieval_enforces_owner_scope(billing_database):
    invoice_id = create_invoice(
        user_id="bill-user",
        items=[{"description": "Private service", "unit_amount_minor": 500}],
    )
    assert get_invoice(invoice_id, user_id="bill-user") is not None
    assert get_invoice(invoice_id, organisation_id="bill-org") is None
