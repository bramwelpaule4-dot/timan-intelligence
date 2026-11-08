"""Tests for invoice PDF rendering and owner-scoped retrieval."""

from timan_intelligence.billing.invoice_pdf import build_invoice_pdf
from timan_intelligence.billing.records import create_invoice, get_invoice


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
