"""PDF rendering for persisted TimanStat invoices."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)


def _text(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def _minor(value: Any) -> str:
    """Render the stored integer minor-unit amount without assuming an exponent."""
    return f"{int(value):,}"


def build_invoice_pdf(invoice: dict[str, Any]) -> bytes:
    """Build a downloadable invoice PDF from an already owner-scoped invoice."""
    required = {"id", "invoice_number", "currency", "total_minor", "amount_paid_minor", "status"}
    if not isinstance(invoice, dict) or not required.issubset(invoice):
        raise ValueError("A complete invoice record is required.")
    if not isinstance(invoice.get("items"), list):
        raise ValueError("Invoice line items are required.")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm,
        title=f"Invoice {invoice['invoice_number']}",
        author="TimanStat | Timan Analytics",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="InvoiceTitle", parent=styles["Title"], fontSize=21,
        leading=25, alignment=TA_RIGHT, textColor=colors.HexColor("#17365D"),
    ))
    styles.add(ParagraphStyle(
        name="SmallRight", parent=styles["Normal"], alignment=TA_RIGHT,
        fontSize=8, leading=11,
    ))
    story = [
        Paragraph("TIMANSTAT", styles["Heading1"]),
        Paragraph("Turning Data into Insights for Informed Decisions", styles["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph("INVOICE", styles["InvoiceTitle"]),
        Paragraph(f"<b>{_text(invoice['invoice_number'])}</b>", styles["SmallRight"]),
        Spacer(1, 5 * mm),
    ]
    owner_name = invoice.get("owner_name") or (
        "Organisation account" if invoice.get("organisation_id") else "Personal account"
    )
    owner_lines = [f"<b>Bill to</b><br/>{_text(owner_name)}"]
    if invoice.get("owner_email"):
        owner_lines.append(_text(invoice["owner_email"]))
    left = Paragraph("<br/>".join(owner_lines), styles["Normal"])
    right = Paragraph(
        "<b>Invoice date:</b> " + _text(invoice.get("issued_at"))
        + "<br/><b>Due date:</b> " + _text(invoice.get("due_at"))
        + "<br/><b>Status:</b> " + _text(str(invoice["status"]).replace("_", " ").title()),
        styles["SmallRight"],
    )
    meta = Table([[left, right]], colWidths=[88 * mm, 88 * mm])
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([meta, Spacer(1, 6 * mm)])

    currency = _text(invoice["currency"])
    item_data = [[
        "Description", "Qty", f"Unit ({currency}, minor)",
        f"Line total ({currency}, minor)",
    ]]
    for item in invoice["items"]:
        item_data.append([
            Paragraph(_text(item.get("description")), styles["BodyText"]),
            str(int(item.get("quantity", 1))),
            _minor(item.get("unit_amount_minor", 0)),
            _minor(item.get("line_total_minor", 0)),
        ])
    items_table = Table(item_data, colWidths=[75 * mm, 15 * mm, 39 * mm, 47 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DEE8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([items_table, Spacer(1, 7 * mm)])

    subtotal = int(invoice.get("subtotal_minor", sum(int(x.get("line_total_minor", 0)) for x in invoice["items"])))
    tax = int(invoice.get("tax_minor", 0))
    paid = int(invoice["amount_paid_minor"])
    total = int(invoice["total_minor"])
    balance = max(0, total - paid)
    totals = [
        ["Subtotal", f"{currency} {_minor(subtotal)}"],
        ["Tax", f"{currency} {_minor(tax)}"],
        ["Invoice total", f"{currency} {_minor(total)}"],
        ["Amount paid", f"{currency} {_minor(paid)}"],
        ["Outstanding balance", f"{currency} {_minor(balance)}"],
    ]
    totals_table = Table(totals, colWidths=[125 * mm, 51 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.7, colors.HexColor("#17365D")),
        ("LINEABOVE", (0, 4), (-1, 4), 0.7, colors.HexColor("#17365D")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([
        totals_table, Spacer(1, 8 * mm),
        Paragraph(
            "Amounts are displayed in the currency's stored minor units. "
            "No decimal-place assumption or currency conversion has been applied.",
            styles["Italic"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Generated by TimanStat billing records.", styles["SmallRight"]),
    ])
    document.build(story)
    return buffer.getvalue()
