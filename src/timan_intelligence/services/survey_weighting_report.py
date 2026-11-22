"""PDF reporting for validated survey weighting results."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#173B67")
BLUE = colors.HexColor("#2586C7")
PALE_BLUE = colors.HexColor("#EAF2F9")
PALE_GREY = colors.HexColor("#F3F6FA")
MID_GREY = colors.HexColor("#64758B")
DARK = colors.HexColor("#24364B")


def _safe(value: Any) -> str:
    if value is None:
        return "Not applied"
    if isinstance(value, float):
        if pd.isna(value):
            return "Not available"
        return f"{value:,.4f}"
    return escape(str(value))


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_safe(text), style)


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _safe(value)
    if not pd.notna(number):
        return "—"
    return f"{number:,.4f}"


def generate_survey_weighting_pdf_report(
    result: Any,
    report_title: str = "Survey Weighting and Adjustment Report",
    project_name: str | None = None,
    prepared_by: str | None = None,
) -> bytes:
    """Create an audit-focused PDF from a completed weighting AnalysisResult.

    The report consumes validated result tables and metadata only; it does not
    recompute weights, calibration factors, or survey estimates.
    """
    if not hasattr(result, "tables") or not hasattr(result, "metadata"):
        raise TypeError("A completed TimanStat survey weighting AnalysisResult is required.")
    weighted = result.tables.get("weighted_dataset")
    diagnostics = result.tables.get("weight_diagnostics")
    stage_diagnostics = result.tables.get("weight_stage_diagnostics")
    if not isinstance(weighted, pd.DataFrame) or weighted.empty:
        raise ValueError("The weighting result does not contain a non-empty weighted dataset.")
    if not isinstance(diagnostics, pd.DataFrame) or diagnostics.empty:
        raise ValueError("The weighting result does not contain weight diagnostics.")

    metadata = result.metadata or {}
    spec = metadata.get("weighting_specification", {})
    diag = metadata.get("diagnostics", {})
    raking = metadata.get("raking") or {}
    generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=19 * mm, bottomMargin=18 * mm,
        title=report_title, author="TimanStat | Timan Analytics",
        subject="Survey weight construction, adjustment and quality diagnostics",
    )

    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle(
            "TimanBrand", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=BLUE, spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "TimanTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=21, leading=25, alignment=TA_LEFT, textColor=NAVY,
            spaceAfter=7,
        ),
        "subtitle": ParagraphStyle(
            "TimanSubtitle", parent=base["Normal"], fontSize=9, leading=13,
            textColor=MID_GREY, spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "TimanH1", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=17, textColor=NAVY, spaceBefore=12, spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "TimanH2", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=BLUE, spaceBefore=7, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "TimanBody", parent=base["BodyText"], fontSize=8.5,
            leading=12, textColor=DARK, spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "TimanSmall", parent=base["BodyText"], fontSize=7.3,
            leading=10, textColor=MID_GREY, spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "TimanBullet", parent=base["BodyText"], fontSize=8.2,
            leading=11, leftIndent=11, firstLineIndent=-7,
            textColor=DARK, spaceAfter=3,
        ),
        "callout": ParagraphStyle(
            "TimanCallout", parent=base["BodyText"], fontSize=8.3,
            leading=12, textColor=NAVY, spaceAfter=0,
        ),
        "table": ParagraphStyle(
            "TimanTable", parent=base["BodyText"], fontSize=7.2,
            leading=9, textColor=DARK,
        ),
    }
    story: list[Any] = []
    story.append(Paragraph("TIMAN ANALYTICS  /  TIMANSTAT", styles["brand"]))
    story.append(Paragraph(escape(report_title), styles["title"]))
    subtitle_parts = []
    if project_name:
        subtitle_parts.append(f"Project: {escape(project_name)}")
    if prepared_by:
        subtitle_parts.append(f"Prepared by: {escape(prepared_by)}")
    subtitle_parts.extend([f"Generated: {generated}", "Status: Completed weighting workflow"])
    story.append(Paragraph("  |  ".join(subtitle_parts), styles["subtitle"]))

    story.append(Paragraph("1. Executive summary", styles["h1"]))
    summary_rows = [
        ["Input records", f"{int(spec.get('records_in_input', len(weighted))):,}",
         "Records in weighted analysis", f"{int(spec.get('records_in_weighted_analysis', diag.get('n', 0))):,}"],
        ["Records with zero analysis weight", f"{int(spec.get('records_with_zero_analysis_weight', 0)):,}",
         "Sum of final weights", _format_number(diag.get("sum_weights"))],
        ["Kish effective sample size", _format_number(diag.get("kish_effective_sample_size")),
         "Weight coefficient of variation", _format_number(diag.get("coefficient_of_variation"))],
        ["Approx. unequal-weight DEFF", _format_number(diag.get("kish_deff_approximation")),
         "Final weight column", "analysis_weight"],
        ["Minimum final weight", _format_number(diag.get("minimum")),
         "Maximum final weight", _format_number(diag.get("maximum"))],
    ]
    summary_table = Table(summary_rows, colWidths=[42 * mm, 35 * mm, 48 * mm, 42 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
        ("BACKGROUND", (2, 0), (2, -1), PALE_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE5EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "Interpretation: Kish effective sample size and the unequal-weighting DEFF "
        "are approximations that describe weight variability. They are not substitutes "
        "for design-based variance estimation accounting for clustering, stratification, "
        "finite population corrections or calibration.",
        styles["callout"],
    ))
    callout = Table([[story.pop()]], colWidths=[167 * mm])
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(callout)

    story.append(Paragraph("2. Weighting specification", styles["h1"]))
    specification_rows = [
        ["Specification", "Selected value"],
        [Paragraph("Base-weight probability field", styles["table"]), Paragraph(_safe(spec.get("inclusion_probability_column")), styles["table"])],
        [Paragraph("Base-weight formula", styles["table"]), Paragraph("wᵢ = 1 / πᵢ, using exact first-order inclusion probabilities", styles["table"])],
        [Paragraph("Response indicator", styles["table"]), Paragraph(_safe(spec.get("response_column")), styles["table"])],
        [Paragraph("Nonresponse adjustment cells", styles["table"]), Paragraph(_safe(", ".join(map(str, spec.get("adjustment_cells", []))) if spec.get("adjustment_cells") else None), styles["table"])],
        [Paragraph("Post-stratification variable", styles["table"]), Paragraph(_safe(spec.get("poststratification_variable")), styles["table"])],
        [Paragraph("Population control totals", styles["table"]), Paragraph(_safe(spec.get("population_totals") or None), styles["table"])],
        [Paragraph("Raking margins", styles["table"]), Paragraph(_safe(spec.get("raking_margins") or None), styles["table"])],
        [Paragraph("Trimming quantiles", styles["table"]), Paragraph(_safe(spec.get("trimming_quantiles")), styles["table"])],
    ]
    spec_table = Table(specification_rows, colWidths=[54 * mm, 113 * mm], repeatRows=1)
    spec_table.setStyle(_standard_table_style())
    story.append(spec_table)

    story.append(Paragraph("3. Methodology and processing sequence", styles["h1"]))
    descriptions = {
        "Inverse-probability base weights":
            "Each sampled unit receives the Horvitz–Thompson base weight wᵢ = 1/πᵢ. "
            "The supplied πᵢ must be the exact first-order unit inclusion probability.",
        "Weighted response-rate adjustment within cells":
            "Base weights are adjusted within the declared cells by the inverse of the "
            "base-weighted response rate. Nonrespondents remain in the exported file "
            "with analysis_weight = 0 and are excluded from respondent-level diagnostics.",
        "Post-stratification to known population totals":
            "Respondent weights are multiplied within post-strata so their weighted "
            "category totals match the supplied population controls.",
        "Iterative proportional fitting (raking)":
            "Iterative proportional fitting adjusts weights to match the supplied "
            "one-way population margins. Convergence is assessed using the maximum "
            "relative margin discrepancy and the configured tolerance.",
        "Winsorised weight trimming with total-weight preservation":
            "Weights are winsorised at the selected sample quantiles and rescaled "
            "to preserve the pre-trimming sum of weights.",
    }
    stages = metadata.get("stages", [])
    if not stages:
        stages = ["Inverse-probability base weights"]
    for number, stage in enumerate(stages, start=1):
        description = descriptions.get(stage, stage)
        story.append(Paragraph(f"{number}. {escape(str(stage))}", styles["h2"]))
        story.append(Paragraph(description, styles["body"]))

    if isinstance(stage_diagnostics, pd.DataFrame) and not stage_diagnostics.empty:
        story.append(Paragraph("4. Diagnostics by weighting stage", styles["h1"]))
        columns = [
            ("stage", "Stage"), ("n", "n"), ("sum_weights", "Sum"),
            ("minimum", "Minimum"), ("maximum", "Maximum"),
            ("mean", "Mean"), ("coefficient_of_variation", "CV"),
            ("kish_effective_sample_size", "Kish n"),
            ("kish_deff_approximation", "Approx. DEFF"),
        ]
        rows = [[label for _, label in columns]]
        for _, row in stage_diagnostics.iterrows():
            rows.append([
                str(row.get(key, "")) if key == "stage"
                else (f"{int(row.get(key, 0)):,}" if key == "n" else _format_number(row.get(key)))
                for key, _ in columns
            ])
        stage_table = Table(
            rows,
            colWidths=[34 * mm, 9 * mm, 18 * mm, 15 * mm, 15 * mm, 15 * mm, 13 * mm, 19 * mm, 17 * mm],
            repeatRows=1,
        )
        stage_table.setStyle(_standard_table_style(font_size=6.2))
        story.append(stage_table)
    else:
        story.append(Paragraph("4. Weight diagnostics", styles["h1"]))
        story.append(Paragraph("A stage-by-stage diagnostics table was not included in this result.", styles["body"]))

    story.append(Paragraph("5. Calibration and raking checks", styles["h1"]))
    if raking:
        rake_text = (
            f"Converged: {'Yes' if raking.get('converged') else 'No'}; "
            f"iterations: {raking.get('iterations', 'Not available')}; "
            f"maximum relative margin error: {_format_number(raking.get('maximum_relative_margin_error'))}; "
            f"tolerance: {_format_number(raking.get('tolerance'))}."
        )
        story.append(Paragraph(rake_text, styles["body"]))
        if not raking.get("converged"):
            story.append(Paragraph(
                "Warning: raking did not meet the convergence tolerance. Treat the calibrated "
                "weights as provisional and review sparse cells, inconsistent control totals "
                "and structural zeros before analysis.",
                styles["callout"],
            ))
    else:
        story.append(Paragraph(
            "Raking was not applied. Review the selected post-stratification and population "
            "controls in the specification table, if any.",
            styles["body"],
        ))

    story.append(Paragraph("6. Findings", styles["h1"]))
    for finding in getattr(result, "findings", []):
        story.append(Paragraph(f"• {escape(str(finding))}", styles["bullet"]))

    story.append(Paragraph("7. Assumptions and limitations", styles["h1"]))
    for assumption in getattr(result, "assumptions", []):
        story.append(Paragraph(f"Assumption: {escape(str(assumption))}", styles["bullet"]))
    for limitation in getattr(result, "limitations", []):
        story.append(Paragraph(f"Limitation: {escape(str(limitation))}", styles["bullet"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Audit note: This document reports the weighting result supplied to the report "
        "generator. It does not independently reconstruct the sampling design, verify "
        "external population controls, or recalculate estimates. Retain the source frame, "
        "probability documentation, control-total source and exported weighted dataset "
        "alongside this report.",
        styles["small"],
    ))

    def draw_page(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1.2)
        canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, 10 * mm, "TIMANSTAT  |  STATISTICAL SUPPORT PLATFORM")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MID_GREY)
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()


def _standard_table_style(font_size: float = 7.2) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE5EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
