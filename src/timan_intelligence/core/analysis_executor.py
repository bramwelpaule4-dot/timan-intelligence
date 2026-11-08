"""Controlled execution of explicitly approved analysis-plan recommendations.

Only methods with a validated implementation are executable here. A plan
recommendation is not an execution instruction: callers must obtain explicit
user approval and resolve outstanding clarification questions first.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from timan_intelligence.core.contracts import AnalysisResult
from timan_intelligence.core.statistical_engine import (
    run_descriptive_statistics,
    run_independent_samples_t_test,
    run_one_way_anova,
)


class AnalysisExecutionError(ValueError):
    """A recommendation cannot safely be executed."""


_EXECUTORS = {
    "Descriptive statistics": "descriptive",
    "Welch's independent-samples t-test": "welch_t",
    "Independent-samples t-test": "welch_t",
    "One-way ANOVA": "anova",
}


def available_execution_methods() -> tuple[str, ...]:
    """Return the exact recommendation labels currently executable."""
    return tuple(_EXECUTORS)


def execute_recommendation(
    df: pd.DataFrame,
    recommendation: dict[str, Any],
    *,
    approved: bool = False,
    information_needed: list[str] | None = None,
) -> AnalysisResult:
    """Execute one approved recommendation using a controlled method registry.

    This function deliberately does not infer approval, resolve study-design
    questions, or execute arbitrary code. Assumptions listed by the planner
    remain review requirements and are not automatically certified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(recommendation, dict):
        raise TypeError("Expected one analysis-plan recommendation.")
    if approved is not True:
        raise AnalysisExecutionError(
            "Explicit user approval is required before executing an analysis."
        )
    if information_needed:
        raise AnalysisExecutionError(
            "Resolve the plan's outstanding clarification questions before execution."
        )

    method = recommendation.get("method")
    executor = _EXECUTORS.get(method)
    if executor is None:
        raise AnalysisExecutionError(
            f"The recommended method '{method}' does not yet have a validated execution implementation."
        )

    status = recommendation.get("status")
    if status in {"ineligible", "insufficient_information"}:
        raise AnalysisExecutionError(
            f"The recommended method cannot be executed while its status is '{status}'."
        )

    variables = recommendation.get("variables")
    if not isinstance(variables, list) or not all(
        isinstance(name, str) and name in df.columns for name in variables
    ):
        raise AnalysisExecutionError(
            "The recommendation contains missing or invalid dataset variables."
        )

    if executor == "descriptive":
        if len(variables) != 1:
            raise AnalysisExecutionError(
                "Descriptive statistics require exactly one numeric variable."
            )
        result = run_descriptive_statistics(df, variables[0])
    elif executor == "welch_t":
        if len(variables) != 2:
            raise AnalysisExecutionError(
                "Welch's t-test requires an outcome and a grouping variable."
            )
        result = run_independent_samples_t_test(
            df, outcome_variable=variables[0], group_variable=variables[1]
        )
    else:
        if len(variables) != 2:
            raise AnalysisExecutionError(
                "One-way ANOVA requires an outcome and a grouping variable."
            )
        result = run_one_way_anova(
            df, outcome_variable=variables[0], group_variable=variables[1]
        )

    review_checks = recommendation.get("checks") or []
    if review_checks:
        result.limitations.extend(
            f"Review required: {check}" for check in review_checks
        )
    result.metadata.update(
        {
            "planned_method": method,
            "recommendation_status": status or "unspecified",
            "user_approved": True,
            "execution_registry": "controlled",
        }
    )
    return result
