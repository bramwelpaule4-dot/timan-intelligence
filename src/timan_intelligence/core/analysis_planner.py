
"""Rule-based planning for statistical analyses.

This module recommends candidate analyses; it does not execute tests.
Recommendations must be reviewed against the study design and assumptions.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from timan_intelligence.core.contracts import AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe
from timan_intelligence.core.method_selector import select_methods
from timan_intelligence.core.objective_classifier import classify_objective


@dataclass
class AnalysisPlan:
    """A structured, reviewable recommendation for an analysis."""

    question: str
    status: str
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    information_needed: list[str] = field(default_factory=list)
    data_profile: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    objective_type: str = "unknown"
    objective_confidence: str = "low"
    objective_explanation: str = ""


def _infer_variable_type(series: pd.Series) -> str:
    """Infer a provisional variable type from pandas data."""
    non_missing = series.dropna()

    if non_missing.empty:
        return "unknown"

    if pd.api.types.is_bool_dtype(series):
        return "binary"

    if isinstance(series.dtype, pd.CategoricalDtype):
        if series.dtype.ordered:
            return "ordinal"

        if non_missing.nunique() == 2:
            return "binary"

        return "categorical"

    if pd.api.types.is_numeric_dtype(series):
        unique_values = set(non_missing.unique().tolist())

        if len(unique_values) == 2 and unique_values.issubset({0, 1}):
            return "binary"

        return "numeric"

    if non_missing.nunique() == 2:
        return "binary"

    return "categorical"


def _add_method_recommendations(
    plan: AnalysisPlan,
    df: pd.DataFrame,
    request: AnalysisRequest,
    selected: list[str],
) -> None:
    """Add candidate methods when the objective and variable roles are clear."""
    objective_type = plan.objective_type

    if objective_type == "description":
        # Existing descriptive recommendations already cover this objective.
        return

    if objective_type not in {"comparison", "association", "prediction"}:
        return

    options = request.options

    # Explicit variable roles take priority over the selected-variable order.
    outcome = options.get("outcome_variable")
    group = options.get("group_variable")
    predictor = options.get("predictor_variable")

    if outcome is None and selected:
        outcome = selected[0]

    if group is None and len(selected) >= 2:
        group = selected[1]

    if predictor is None and len(selected) >= 2:
        predictor = selected[1]

    if objective_type == "comparison":
        if outcome not in df.columns or group not in df.columns:
            plan.information_needed.append(
                "Select the outcome variable and the grouping variable "
                "for the comparison."
            )
            return

        group_count = int(df[group].dropna().nunique())
        independent_groups = options.get("independent_groups")

        if group_count != 2:
            plan.information_needed.append(
                "The initial comparison selector supports two groups. "
                "Confirm the grouping variable and study design."
            )
            return

        if independent_groups is not True:
            plan.information_needed.append(
                "Confirm whether the two groups contain independent "
                "observations. Paired or repeated measurements require "
                "different methods."
            )
            return

        candidates = select_methods(
            objective_type="comparison",
            outcome_type=_infer_variable_type(df[outcome]),
            group_count=group_count,
            independent_groups=True,
        )

    elif objective_type == "association":
        if outcome not in df.columns or predictor not in df.columns:
            plan.information_needed.append(
                "Select the two variables whose association you want to assess."
            )
            return

        candidates = select_methods(
            objective_type="association",
            outcome_type=_infer_variable_type(df[outcome]),
            predictor_type=_infer_variable_type(df[predictor]),
        )

    else:  # prediction
        if outcome not in df.columns:
            plan.information_needed.append(
                "Select the outcome variable to predict."
            )
            return

        outcome_type = _infer_variable_type(df[outcome])

        candidates = select_methods(
            objective_type="prediction",
            outcome_type=outcome_type,
        )

        if candidates and len(selected) < 2:
            plan.information_needed.append(
                "Select at least one predictor variable in addition "
                "to the outcome."
            )
            return

    if not candidates:
        plan.information_needed.append(
            "The current selector cannot recommend a method for these "
            "variable types and settings. Additional information or "
            "method-selection rules may be needed."
        )
        return

    for candidate in candidates:
        plan.recommendations.append({
            "method": candidate.method,
            "variables": [
                str(value)
                for value in (
                    [outcome, group]
                    if objective_type == "comparison"
                    else [outcome, predictor]
                    if objective_type == "association"
                    else [outcome] + [
                        name for name in selected if name != outcome
                    ]
                )
            ],
            "reason": candidate.rationale,
            "checks": candidate.checks,
            "status": candidate.status,
        })

    plan.warnings.append(
        "Candidate methods are provisional. Review variable coding, "
        "sampling design, missing data, sample size and method assumptions "
        "before conducting an analysis."
    )


def plan_analysis(
    df: pd.DataFrame,
    request: AnalysisRequest,
) -> AnalysisPlan:
    """Recommend candidate analyses using the objective and dataset structure."""
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

    objective = classify_objective(question)
    plan.objective_type = objective.objective_type
    plan.objective_confidence = objective.confidence
    plan.objective_explanation = objective.explanation

    if objective.objective_type in {"unknown", "ambiguous"}:
        plan.information_needed.append(
            "Clarify the primary research objective before selecting an analysis."
        )
        plan.warnings.append(
            "The objective classification is tentative and uses keyword rules."
        )

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

    _add_method_recommendations(plan, df, request, selected)

    if objective.objective_type == "comparison":
        plan.information_needed.append(
            "Confirm the outcome variable, grouping variable and study design."
        )
    elif objective.objective_type == "association":
        plan.information_needed.append(
            "Confirm the two variables and whether potential confounding "
            "needs to be considered."
        )
    elif objective.objective_type == "prediction":
        plan.information_needed.append(
            "Confirm the outcome, candidate predictors and validation approach."
        )
    elif objective.objective_type == "description":
        plan.information_needed.append(
            "Confirm the indicator and desired summary, such as a count, "
            "proportion, mean or median."
        )
    elif len(variables) >= 2:
        plan.information_needed.append(
            "Specify the outcome variable and the explanatory or grouping "
            "variable if you want a comparison or association analysis."
        )

    plan.information_needed.append(
        "Confirm the study design, sampling approach, and intended interpretation "
        "before selecting an inferential test."
    )

    if objective.objective_type in {"unknown", "ambiguous"}:
        plan.status = "needs_input"
    elif plan.recommendations:
        plan.status = "review_required"
    else:
        plan.status = "needs_input"
        plan.information_needed.append(
            "No candidate analysis could be suggested from the available variables."
        )

    return plan
