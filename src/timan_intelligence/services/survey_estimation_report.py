"""PDF reporting for completed survey estimation and domain inference results."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

NAVY = colors.HexColor("#173B67")
BLUE = colors.HexColor("#2586C7")
PALE_BLUE = colors.HexColor("#EAF2F9")
PALE_GREY = colors.HexColor("#F3F6FA")
MID_GREY = colors.HexColor("#64758B")
DARK = colors.HexColor("#24364B")


def _display(value: Any) -> str:
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:,.4f}" if isinstance(value, float) else f"{value:,}"
    return str(value)


def _table(data: list[list[Any]], widths: list[float], font_size: float = 7.0) -> Table:
    rendered = []
    for row_index, row in enumerate(data):
        rendered.append([
            Paragraph(escape(_display(value)), ParagraphStyle(
                f"ReportCell{row_index}", fontName="Helvetica-Bold" if row_index == 0 else "Helvetica",
                fontSize=font_size, leading=font_size + 2,
                textColor=colors.white if row_index == 0 else DARK,
            ))
            for value in row
        ])
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE5EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def generate_survey_estimation_pdf_report(
    result: Any,
    report_title: str = "Survey Estimation and Inference Report",
    project_name: str | None = None,
    prepared_by: str | None = None,
) -> bytes:
    """Render a completed estimation AnalysisResult without recalculating statistics."""
    if not hasattr(result, "tables") or not hasattr(result, "metadata"):
        raise TypeError("A completed TimanStat survey estimation AnalysisResult is required.")
    estimates = result.tables.get("estimates")
    details = result.tables.get("design_details")
    if not isinstance(estimates, pd.DataFrame) or estimates.empty:
        raise ValueError("The estimation result does not contain an estimates table.")
    metadata = result.metadata or {}
    generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=19 * mm, bottomMargin=18 * mm,
        title=report_title, author="TimanStat | Timan Analytics",
        subject="Survey estimates, design-based inference and diagnostics",
    )
    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle("EstBrand", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=BLUE, spaceAfter=5),
        "title": ParagraphStyle("EstTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, alignment=TA_LEFT, textColor=NAVY, spaceAfter=7),
        "subtitle": ParagraphStyle("EstSubtitle", parent=base["Normal"], fontSize=8,
            leading=12, textColor=MID_GREY, spaceAfter=12),
        "heading": ParagraphStyle("EstHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=NAVY, spaceBefore=11, spaceAfter=5),
        "body": ParagraphStyle("EstBody", parent=base["BodyText"], fontSize=8.3,
            leading=11.5, textColor=DARK, spaceAfter=5),
        "bullet": ParagraphStyle("EstBullet", parent=base["BodyText"], fontSize=8,
            leading=11, leftIndent=10, firstLineIndent=-7, textColor=DARK, spaceAfter=3),
        "callout": ParagraphStyle("EstCallout", parent=base["BodyText"], fontSize=8,
            leading=11, textColor=NAVY),
    }
    story: list[Any] = [
        Paragraph("TIMAN ANALYTICS  /  TIMANSTAT", styles["brand"]),
        Paragraph(escape(report_title), styles["title"]),
    ]
    subtitle = []
    if project_name:
        subtitle.append(f"Project: {escape(project_name)}")
    if prepared_by:
        subtitle.append(f"Prepared by: {escape(prepared_by)}")
    subtitle.extend([f"Generated: {generated}", "Status: Completed estimation"])
    story.append(Paragraph("  |  ".join(subtitle), styles["subtitle"]))

    story.append(Paragraph("1. Executive summary", styles["heading"]))
    summary = [
        ["Analysis item", "Result"],
        ["Estimand", _display(metadata.get("estimand"))],
        ["Sampling design", _display(metadata.get("design"))],
        ["Outcome variable", _display(metadata.get("outcome_variable"))],
        ["Analysis weight", _display(metadata.get("weight_variable"))],
        ["Domain", (
            f"{metadata.get('domain_variable')} = {metadata.get('domain_value')}"
            if metadata.get("domain_variable") else "Full analysis population"
        )],
        ["Records used / in domain", _display(metadata.get("records_used", metadata.get("domain_unweighted_n", "See estimates table")))],
        ["Variance method", _display(metadata.get("variance_method", "Not estimated"))],
        ["Degrees of freedom", _display(metadata.get("degrees_of_freedom", "Not applicable"))],
    ]
    story.append(_table(summary, [57 * mm, 113 * mm], 7.2))

    story.append(Paragraph("2. Estimates and precision", styles["heading"]))
    columns = list(estimates.columns)
    max_columns = 10
    if len(columns) > max_columns:
        columns = columns[:max_columns]
    estimate_rows = [columns]
    for _, row in estimates.iterrows():
        estimate_rows.append([_display(row.get(column)) for column in columns])
    widths = [170 * mm / len(columns)] * len(columns)
    story.append(_table(estimate_rows, widths, 6.2))

    if isinstance(details, pd.DataFrame) and not details.empty:
        story.append(Paragraph("3. Stratum / PSU variance diagnostics", styles["heading"]))
        detail_columns = list(details.columns)[:8]
        detail_rows = [detail_columns]
        for _, row in details.iterrows():
            detail_rows.append([_display(row.get(column)) for column in detail_columns])
        story.append(_table(detail_rows, [170 * mm / len(detail_columns)] * len(detail_columns), 6.1))
    else:
        story.append(Paragraph("3. Design diagnostics", styles["heading"]))
        story.append(Paragraph(
            "No stratum- or PSU-level variance diagnostics were included in this result.",
            styles["body"],
        ))

    story.append(Paragraph("4. Findings", styles["heading"]))
    for finding in getattr(result, "findings", []):
        story.append(Paragraph(f"• {escape(str(finding))}", styles["bullet"]))
    if not getattr(result, "findings", []):
        story.append(Paragraph("No narrative findings were supplied.", styles["body"]))

    story.append(Paragraph("5. Assumptions and limitations", styles["heading"]))
    for assumption in getattr(result, "assumptions", []):
        story.append(Paragraph(f"Assumption: {escape(str(assumption))}", styles["bullet"]))
    for limitation in getattr(result, "limitations", []):
        story.append(Paragraph(f"Limitation: {escape(str(limitation))}", styles["bullet"]))

    story.append(Paragraph("6. Interpretation and use", styles["heading"]))
    if metadata.get("design") == "weighted_descriptive":
        interpretation = (
            "The reported point estimates are weighted descriptive estimates. "
            "Weights alone do not identify design-based standard errors or confidence intervals; "
            "do not interpret missing precision measures as zero uncertainty."
        )
    else:
        interpretation = (
            "Confidence intervals and standard errors are conditional on the sampling design "
            "declaration and variance method shown in this report. Review the stated assumptions, "
            "especially the absence of finite population corrections and any restrictions on "
            "expansion weights, before generalising to the target population."
        )
    story.append(Paragraph(interpretation, styles["callout"]))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "Audit note: This report presents the completed TimanStat analysis result. "
        "It does not reconstruct the sample design, validate external population controls, "
        "or independently recalculate estimates and variances. Preserve the source dataset, "
        "weight documentation and sampling-design records with this report.",
        styles["body"],
    ))

    def draw_page(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1.2)
        canvas.line(17 * mm, height - 13 * mm, width - 17 * mm, height - 13 * mm)
        canvas.setFont("Helvetica-Bold", 7.3)
        canvas.setFillColor(NAVY)
        canvas.drawString(17 * mm, 10 * mm, "TIMANSTAT  |  STATISTICAL SUPPORT PLATFORM")
        canvas.setFont("Helvetica", 7.3)
        canvas.setFillColor(MID_GREY)
        canvas.drawRightString(width - 17 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()
