
"""Rule-based planning for statistical analyses.

This module recommends candidate analyses and assesses preferred methods.
It does not execute statistical tests or verify statistical assumptions.
Recommendations must be reviewed against the study design and data.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from timan_intelligence.core.contracts import AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe
from timan_intelligence.core.method_selector import (
    INELIGIBLE,
    INSUFFICIENT_INFORMATION,
    assess_preferred_method,
    select_methods,
)
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


def _add_information_needed(plan: AnalysisPlan, message: str) -> None:
    """Add a clarification request only once."""
    if message not in plan.information_needed:
        plan.information_needed.append(message)


def _add_warning(plan: AnalysisPlan, message: str) -> None:
    """Add a warning only once."""
    if message not in plan.warnings:
        plan.warnings.append(message)


def _add_candidate(
    plan: AnalysisPlan,
    method: str,
    variables: list[str],
    reason: str,
    checks: list[str] | None = None,
    status: str = "review_required",
) -> None:
    """Add a structured method recommendation without duplicating it."""
    if any(
        item.get("method") == method
        and item.get("variables") == variables
        for item in plan.recommendations
    ):
        return

    plan.recommendations.append(
        {
            "method": method,
            "variables": variables,
            "reason": reason,
            "checks": list(checks or []),
            "status": status,
        }
    )


def _resolve_variable(
    plan: AnalysisPlan,
    df: pd.DataFrame,
    options: dict[str, Any],
    option_name: str,
    selected: list[str],
    fallback_index: int | None = None,
) -> str | None:
    """Resolve a variable role and validate explicitly supplied names."""
    value = options.get(option_name)

    if value is not None:
        if not isinstance(value, str) or value not in df.columns:
            _add_information_needed(
                plan,
                f"The configured {option_name.replace('_', ' ')} "
                f"{value!r} was not found in the dataset. "
                "Select a valid column name."
            )
            return None

        return value

    if fallback_index is not None and len(selected) > fallback_index:
        return selected[fallback_index]

    return None


def _add_descriptive_recommendations(
    plan: AnalysisPlan,
    df: pd.DataFrame,
    variables: list[str],
) -> None:
    """Recommend basic summaries only after the objective is understood."""
    for column in variables:
        series = df[column]
        non_missing = series.dropna()

        if non_missing.empty:
            _add_information_needed(
                plan,
                f"Variable '{column}' contains no non-missing values. "
                "Review it before analysis."
            )
            continue

        if pd.api.types.is_numeric_dtype(series):
            _add_candidate(
                plan,
                method="Descriptive statistics",
                variables=[str(column)],
                reason=(
                    f"'{column}' is numeric; summaries of its centre, "
                    "spread and distribution may help describe the data."
                ),
                checks=[
                    "Review missing values and implausible observations.",
                    "Inspect the distribution and potential outliers.",
                    "Consider whether the numeric coding represents a "
                    "quantity or a categorical code.",
                ],
            )
        else:
            _add_candidate(
                plan,
                method="Frequency distribution",
                variables=[str(column)],
                reason=(
                    f"'{column}' is non-numeric; counts and proportions "
                    "may describe its observed categories."
                ),
                checks=[
                    "Review category labels for inconsistent spelling or coding.",
                    "Confirm whether survey weights are required.",
                    "Review missing and invalid category values.",
                ],
            )


def _candidate_variables(
    objective_type: str,
    outcome: str,
    group: str | None,
    predictor: str | None,
    selected: list[str],
) -> list[str]:
    """Return the variables associated with a candidate method."""
    if objective_type == "comparison":
        return [outcome, group] if group is not None else [outcome]

    if objective_type == "association":
        return [outcome, predictor] if predictor is not None else [outcome]

    if objective_type == "prediction":
        return [outcome] + [
            name for name in selected if name != outcome
        ]

    return [outcome]


def _add_method_recommendations(
    plan: AnalysisPlan,
    df: pd.DataFrame,
    request: AnalysisRequest,
    selected: list[str],
) -> None:
    """Assess a preferred method or recommend suitable candidate methods."""
    objective_type = plan.objective_type

    if objective_type not in {"comparison", "association", "prediction"}:
        return

    options = request.options or {}

    outcome = _resolve_variable(
        plan, df, options, "outcome_variable", selected, 0
    )

    if outcome is None:
        _add_information_needed(
            plan,
            "Select the outcome variable for the intended analysis."
        )
        return

    group = None
    predictor = None

    if objective_type == "comparison":
        group = _resolve_variable(
            plan, df, options, "group_variable", selected, 1
        )
        if group is None:
            _add_information_needed(
                plan,
                "Select the grouping variable for the comparison."
            )
            return

    elif objective_type == "association":
        predictor = _resolve_variable(
            plan, df, options, "predictor_variable", selected, 1
        )
        if predictor is None:
            _add_information_needed(
                plan,
                "Select the second variable whose association with the "
                "outcome you want to assess."
            )
            return

    else:
        configured_predictor = options.get("predictor_variable")

        if configured_predictor is not None:
            predictor = _resolve_variable(
                plan, df, options, "predictor_variable", selected
            )
            if predictor is None:
                return

        predictors = [
            name for name in selected if name != outcome
        ]

        if predictor is not None and predictor not in predictors:
            predictors.append(predictor)

        if not predictors:
            _add_information_needed(
                plan,
                "Select at least one predictor variable in addition "
                "to the outcome."
            )
            return

    if objective_type in {"comparison", "association"}:
        if group == outcome or predictor == outcome:
            _add_information_needed(
                plan,
                "The outcome and explanatory/grouping variables must be "
                "distinct columns for this workflow."
            )
            return

    outcome_type = _infer_variable_type(df[outcome])
    predictor_type = (
        _infer_variable_type(df[predictor])
        if predictor is not None
        else None
    )
    group_count = (
        int(df[group].dropna().nunique())
        if group is not None
        else None
    )
    independent_groups = options.get("independent_groups")

    if objective_type == "comparison":
        if group_count is None or group_count < 2:
            _add_information_needed(
                plan,
                "The grouping variable must contain at least two "
                "observed groups. Check its values and missingness."
            )
            return

        if independent_groups is not True and independent_groups is not False:
            _add_information_needed(
                plan,
                "Confirm whether the groups contain independent "
                "observations or paired/repeated measurements."
            )

    preferred_method = options.get("preferred_method")

    if preferred_method:
        assessment = assess_preferred_method(
            preferred_method=preferred_method,
            objective_type=objective_type,
            outcome_type=outcome_type,
            predictor_type=predictor_type,
            group_count=group_count,
            independent_groups=independent_groups,
        )

        plan.recommendations.append(
            {
                "method": assessment.preferred_method,
                "variables": _candidate_variables(
                    objective_type, outcome, group, predictor, selected
                ),
                "reason": assessment.rationale,
                "checks": assessment.checks,
                "status": assessment.eligibility,
                "clarification_questions": (
                    assessment.clarification_questions
                ),
                "is_preferred": True,
            }
        )

        for candidate in assessment.alternatives:
            _add_candidate(
                plan,
                method=candidate.method,
                variables=_candidate_variables(
                    objective_type, outcome, group, predictor, selected
                ),
                reason=candidate.rationale,
                checks=candidate.checks,
                status=candidate.status,
            )

        for question in assessment.clarification_questions:
            _add_information_needed(plan, question)

        if assessment.eligibility == INELIGIBLE:
            _add_warning(
                plan,
                "The preferred method is incompatible with the "
                "information supplied. Review the explanation and "
                "consider the alternative candidates."
            )
        elif assessment.eligibility == INSUFFICIENT_INFORMATION:
            _add_warning(
                plan,
                "The preferred method cannot yet be fully assessed "
                "because essential information is missing."
            )
        else:
            _add_warning(
                plan,
                "The preferred method's compatibility is preliminary. "
                "Its assumptions have not been verified."
            )

    else:
        if objective_type == "comparison":
            if independent_groups is not True:
                if independent_groups is False:
                    _add_information_needed(
                        plan,
                        "The observations are not independent. The current "
                        "selector does not yet generate paired/repeated-measures "
                        "candidates automatically."
                    )
                return

            candidates = select_methods(
                objective_type=objective_type,
                outcome_type=outcome_type,
                group_count=group_count,
                independent_groups=True,
            )

        elif objective_type == "association":
            candidates = select_methods(
                objective_type=objective_type,
                outcome_type=outcome_type,
                predictor_type=predictor_type,
            )

        else:
            candidates = select_methods(
                objective_type=objective_type,
                outcome_type=outcome_type,
            )

        if not candidates:
            _add_information_needed(
                plan,
                "The current method selector has no candidate for these "
                "variable types and study settings. More information or "
                "additional selection rules may be required."
            )
            return

        for candidate in candidates:
            _add_candidate(
                plan,
                method=candidate.method,
                variables=_candidate_variables(
                    objective_type, outcome, group, predictor, selected
                ),
                reason=candidate.rationale,
                checks=candidate.checks,
                status=candidate.status,
            )

    _add_warning(
        plan,
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
        _add_information_needed(
            plan,
            "Provide a research question or analytical objective."
        )
        return plan

    objective = classify_objective(question)
    plan.objective_type = objective.objective_type
    plan.objective_confidence = objective.confidence
    plan.objective_explanation = objective.explanation

    if objective.objective_type in {"unknown", "ambiguous"}:
        _add_information_needed(
            plan,
            "Clarify the primary research objective before selecting an analysis."
        )
        _add_warning(
            plan,
            "The objective classification is tentative and uses keyword rules."
        )
        plan.status = "needs_input"
        return plan

    if df.empty or len(df.columns) == 0:
        _add_information_needed(
            plan,
            "Upload a dataset containing rows and columns."
        )
        return plan

    selected = list(request.selected_variables or [])
    missing_selected = [
        name for name in selected if name not in df.columns
    ]

    if missing_selected:
        _add_information_needed(
            plan,
            "These selected variables were not found in the dataset: "
            + ", ".join(map(str, missing_selected))
        )
        return plan

    variables = selected if selected else list(df.columns)

    if not variables:
        _add_information_needed(
            plan,
            "Select the variables relevant to your research question."
        )
        return plan

    # Descriptive objectives get descriptive recommendations only.
    # For other objectives, summaries are supplemental rather than
    # substitutes for the research-question-driven method.
    if objective.objective_type == "description":
        _add_descriptive_recommendations(plan, df, variables)
        _add_information_needed(
            plan,
            "Confirm the indicator and desired summary, such as a count, "
            "proportion, mean or median."
        )
    else:
        _add_method_recommendations(plan, df, request, selected)

        if objective.objective_type == "comparison":
            _add_information_needed(
                plan,
                "Confirm the outcome variable, grouping variable and study design."
            )
        elif objective.objective_type == "association":
            _add_information_needed(
                plan,
                "Confirm the two variables and whether potential confounding "
                "needs to be considered."
            )
        elif objective.objective_type == "prediction":
            _add_information_needed(
                plan,
                "Confirm the outcome, candidate predictors and validation approach."
            )

    _add_information_needed(
        plan,
        "Confirm the study design, sampling approach and intended "
        "interpretation before conducting an inferential analysis."
    )

    if plan.recommendations:
        plan.status = "review_required"
    else:
        plan.status = "needs_input"
        _add_information_needed(
            plan,
            "No candidate analysis could be suggested from the available "
            "variables and supplied information."
        )

    return plan
