"""PDF reporting for PSU-level PPSWOR analyses.

The report is generated from the validated AnalysisResult and never re-runs
or modifies the estimator. It includes the result, precision diagnostics,
variance allocation tables, assumptions, and limitations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    LongTable, PageBreak, KeepTogether,
)

from timan_intelligence.core.contracts import AnalysisResult


def _display_value(value: Any) -> str:
    if value is None:
        return "Not defined"
    if isinstance(value, float):
        if pd.isna(value):
            return "Not available"
        return f"{value:,.5g}"
    if isinstance(value, (int,)):
        return f"{value:,}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_display_value(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_display_value(item)}" for key, item in value.items())
    return str(value)


def _safe_paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_display_value(value)).replace("\n", "<br/>"), style)


def _table_flowable(frame: pd.DataFrame, styles, max_rows: int = 250):
    if frame is None or frame.empty:
        return Paragraph("No rows were returned for this table.", styles["BodyText"])
    display = frame.copy()
    if len(display) > max_rows:
        display = display.head(max_rows)
    headers = [str(column) for column in display.columns]
    data = [[_safe_paragraph(column, styles["TableHeader"]) for column in headers]]
    for row in display.itertuples(index=False, name=None):
        data.append([
            _safe_paragraph(
                str(value) if not isinstance(value, (float, int)) else _display_value(value),
                styles["TableCell"],
            )
            for value in row
        ])
    page_width = landscape(A4)[0] - 30 * mm
    col_width = page_width / max(1, len(headers))
    table = LongTable(
        data, repeatRows=1, hAlign="LEFT",
        colWidths=[col_width] * len(headers),
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C9D6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F9")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build_ppswor_report(
    result: AnalysisResult,
    report_title: str | None = None,
    organisation: str = "Timan Analytics",
) -> bytes:
    """Create a downloadable PDF report from a successful PPSWOR result.

    Args:
        result: PPSWOR AnalysisResult returned by the shared analysis service.
        report_title: Optional display title; defaults to the analysis title.
        organisation: Report owner shown in the document.

    Returns:
        Complete PDF document as bytes.
    """
    if not isinstance(result, AnalysisResult):
        raise TypeError("A validated AnalysisResult is required to build a PPSWOR report.")
    if result.status != "success":
        raise ValueError("Only successful PPSWOR analyses can be exported.")
    metadata = result.metadata or {}
    required = ("estimate", "standard_error", "confidence_interval", "confidence_level")
    missing = [key for key in required if key not in metadata]
    if missing:
        raise ValueError(f"The analysis result is missing report fields: {', '.join(missing)}.")
    estimate = float(metadata["estimate"])
    standard_error = float(metadata["standard_error"])
    ci = metadata["confidence_interval"]
    if len(ci) != 2:
        raise ValueError("The confidence interval must contain lower and upper limits.")

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=colors.HexColor("#17365D"),
        alignment=TA_CENTER, spaceAfter=5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        textColor=colors.HexColor("#17365D"), spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="TableCell", parent=styles["BodyText"], fontSize=7,
        leading=9, wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7, leading=9, textColor=colors.white, wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="SmallNote", parent=styles["BodyText"], fontSize=8,
        leading=10, textColor=colors.HexColor("#555555"),
    ))

    page_size = landscape(A4)
    left = right = 15 * mm
    top = 18 * mm
    bottom = 16 * mm

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(left, 10 * mm, organisation)
        canvas.drawRightString(page_size[0] - right, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        buffer, pagesize=page_size, title=report_title or result.title,
        author=organisation, subject="PPSWOR statistical analysis report",
        leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
    )
    frame = Frame(left, bottom, page_size[0] - left - right,
                  page_size[1] - top - bottom, id="normal")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=draw_page)])

    story = [
        Paragraph(escape(report_title or result.title), styles["ReportTitle"]),
        Paragraph(escape(organisation) + " | Statistical analysis report", styles["Heading3"]),
        Paragraph(
            "Generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            styles["SmallNote"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Executive results", styles["SectionHeading"]),
    ]
    parameter = metadata.get("parameter") or metadata.get("domain_parameter") or "total"
    estimate_label = "Estimated " + str(parameter)
    summary_rows = [
        ["Measure", "Result"],
        [estimate_label, _display_value(estimate)],
        ["Design-based variance", _display_value(metadata.get("variance"))],
        ["Standard error", _display_value(standard_error)],
        [f"{float(metadata['confidence_level']):.1%} confidence interval",
         f"[{_display_value(ci[0])}, {_display_value(ci[1])}]"],
        ["Degrees of freedom", _display_value(metadata.get("degrees_of_freedom"))],
        ["Sampled PSUs", _display_value(metadata.get("number_of_sampled_psus"))],
        ["Strata", _display_value(metadata.get("number_of_strata"))],
    ]
    summary = Table(summary_rows, colWidths=[65 * mm, 95 * mm], hAlign="LEFT")
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C9D6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F9")]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary)

    story.append(Paragraph("Interpretation", styles["SectionHeading"]))
    direction = (
        "The point estimate is the design-weighted estimate for the target population. "
        "The confidence interval describes sampling uncertainty under the supplied "
        "PPSWOR design and variance estimator."
    )
    story.append(Paragraph(escape(direction), styles["BodyText"]))
    cv = metadata.get("precision_diagnostics", {}).get("coefficient_of_variation_percent")
    if cv is not None:
        story.append(Paragraph(
            f"Descriptive coefficient of variation: {float(cv):.2f}%. "
            "This is a precision diagnostic, not a universal acceptance threshold.",
            styles["BodyText"],
        ))
    if metadata.get("domain_estimation"):
        story.append(Paragraph(
            "This is a domain estimate. All sampled PSUs, including zero-domain PSUs, "
            "must remain in the design variance calculation.",
            styles["BodyText"],
        ))

    story.append(Paragraph("Method and design", styles["SectionHeading"]))
    story.append(Paragraph(escape(result.method), styles["BodyText"]))
    for key in ("sampling_design", "estimator", "parameter", "domain_name"):
        if metadata.get(key) is not None:
            story.append(Paragraph(
                f"<b>{escape(key.replace('_', ' ').title())}:</b> "
                f"{escape(_display_value(metadata[key]))}",
                styles["BodyText"],
            ))

    for heading, items in (
        ("Key findings", result.findings),
        ("Assumptions", result.assumptions),
        ("Limitations and cautions", result.limitations),
    ):
        story.append(Paragraph(heading, styles["SectionHeading"]))
        if items:
            for item in items:
                story.append(Paragraph("• " + escape(str(item)), styles["BodyText"]))
        else:
            story.append(Paragraph("None recorded.", styles["BodyText"]))

    table_labels = {
        "diagnostics": "Precision diagnostics",
        "stratum_estimates": "Stratum estimates and variance allocation",
        "pairwise_variance": "Pairwise Sen–Yates–Grundy variance contributions",
    }
    for key in ("diagnostics", "stratum_estimates", "pairwise_variance"):
        frame_data = result.tables.get(key)
        if isinstance(frame_data, pd.DataFrame):
            story.append(Paragraph(table_labels[key], styles["SectionHeading"]))
            story.append(_table_flowable(frame_data, styles))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Statistical note: this report documents the result returned by TimanStat. "
        "The validity of the estimates depends on the accuracy of the supplied "
        "first- and second-order inclusion probabilities and on the sampling design "
        "being correctly implemented. The PSU-level PPSWOR procedures reported here "
        "do not account for within-PSU SSU subsampling.",
        styles["SmallNote"],
    ))
    doc.build(story)
    return buffer.getvalue()
