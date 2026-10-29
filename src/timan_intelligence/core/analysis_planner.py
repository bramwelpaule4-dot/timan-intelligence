
"""Rule-based planning for statistical analyses.

This module recommends candidate analyses; it does not execute tests.
Recommendations must be reviewed against the study design and assumptions.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from timan_intelligence.core.contracts import AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe


@dataclass
class AnalysisPlan:
    """A structured, reviewable recommendation for an analysis."""

    question: str
    status: str
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    information_needed: list[str] = field(default_factory=list)
    data_profile: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def plan_analysis(
    df: pd.DataFrame,
    request: AnalysisRequest,
) -> AnalysisPlan:
    """Recommend candidate analyses from the question and dataset structure."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if not isinstance(request, AnalysisRequest):
        raise TypeError("Expected an AnalysisRequest.")

    profile = profile_dataframe(df)
    question = request.question.strip()

    plan = AnalysisPlan(
        question=question,
        status="needs_input",
        data_profile={
            "rows": profile["rows"],
            "columns": profile["columns"],
            "missing_cells": profile["missing_cells"],
            "duplicate_rows": profile["duplicate_rows"],
        },
        warnings=list(profile["warnings"]),
    )

    if not question:
        plan.information_needed.append(
            "Provide a research question or analytical objective."
        )
        return plan

    if df.empty or len(df.columns) == 0:
        plan.information_needed.append(
            "Upload a dataset containing rows and columns."
        )
        return plan

    selected = request.selected_variables
    missing_selected = [name for name in selected if name not in df.columns]

    if missing_selected:
        plan.information_needed.append(
            "These selected variables were not found in the dataset: "
            + ", ".join(map(str, missing_selected))
        )
        return plan

    variables = selected if selected else list(df.columns)

    if not variables:
        plan.information_needed.append(
            "Select the variables relevant to your research question."
        )
        return plan

    for column in variables:
        series = df[column]
        non_missing = series.dropna()
        unique_count = int(non_missing.nunique())

        if pd.api.types.is_numeric_dtype(series):
            plan.recommendations.append({
                "method": "Descriptive statistics",
                "variables": [str(column)],
                "reason": (
                    f"'{column}' is numeric; its distribution and summary "
                    "statistics may help address the objective."
                ),
                "checks": [
                    "Check missingness and implausible values.",
                    "Consider skewness and outliers when interpreting summaries.",
                ],
            })
        elif unique_count > 0:
            plan.recommendations.append({
                "method": "Frequency distribution",
                "variables": [str(column)],
                "reason": (
                    f"'{column}' is non-numeric; counts and proportions "
                    "may describe its categories."
                ),
                "checks": [
                    "Review category labels for inconsistent spelling or coding.",
                    "Confirm whether survey weights are required.",
                ],
            })

    if len(variables) >= 2:
        plan.information_needed.append(
            "Specify the outcome variable and the explanatory or grouping "
            "variable if you want a comparison or association analysis."
        )

    plan.information_needed.append(
        "Confirm the study design, sampling approach, and intended interpretation "
        "before selecting an inferential test."
    )

    if plan.recommendations:
        plan.status = "review_required"
    else:
        plan.information_needed.append(
            "No candidate analysis could be suggested from the available variables."
        )

    return plan
