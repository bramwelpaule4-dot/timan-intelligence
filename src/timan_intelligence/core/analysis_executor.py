"""Controlled execution of explicitly approved analysis-plan recommendations.

Only methods with a validated implementation are executable here. A plan
recommendation is not an execution instruction: callers must obtain explicit
user approval and resolve outstanding clarification questions first.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from timan_intelligence.registry.method_catalogue import get_statistical_methods

from timan_intelligence.core.contracts import AnalysisResult
from timan_intelligence.core.statistical_engine import (
    run_descriptive_statistics,
    run_independent_samples_t_test,
    run_mean_confidence_interval,
    run_one_sample_t_test,
    run_proportion_confidence_interval,
    run_welch_mean_difference_confidence_interval,
    run_paired_mean_difference_confidence_interval,
    run_one_way_anova,
)


class AnalysisExecutionError(ValueError):
    """A recommendation cannot safely be executed."""


_EXECUTOR_BY_METHOD_ID = {
    "method.descriptive.numeric.summary": "descriptive",
    "method.inference.confidence_interval.mean": "mean_ci",
    "method.inference.comparison.t_test.one_sample": "one_sample_t",
    "method.inference.confidence_interval.proportion": "proportion_ci",
    "method.inference.confidence_interval.mean_difference.welch": "welch_mean_difference_ci",
    "method.inference.confidence_interval.mean_difference.paired": "paired_mean_difference_ci",
    "method.inference.comparison.t_test.independent.welch": "welch_t",
    "method.inference.comparison.anova.one_way": "anova",
}


def _resolve_registered_method(label: str):
    """Resolve a method label or alias using the authoritative catalogue."""
    normalised = " ".join(label.casefold().split())
    for record in get_statistical_methods():
        labels = [record.name, *record.aliases]
        if any(" ".join(item.casefold().split()) == normalised for item in labels):
            return record
    return None


def _validate_design_compatibility(
    recommendation: dict[str, Any],
    *,
    executor: str,
    sampling_design_aware: bool,
) -> dict[str, Any]:
    """Fail closed when the declared design is unsupported by an executor."""
    context = recommendation.get("design_context") or {}
    if not isinstance(context, dict):
        raise AnalysisExecutionError(
            "The recommendation contains an invalid study-design context."
        )

    study_design = str(
        context.get("study_design", recommendation.get("study_design")) or ""
    ).strip().casefold().replace("-", "_").replace(" ", "_")
    sampling_design = str(
        context.get("sampling_design", recommendation.get("sampling_design")) or ""
    ).strip().casefold().replace("-", "_").replace(" ", "_")

    complex_sampling = (
        study_design in {"clustered", "complex_survey"}
        or sampling_design in {"cluster", "stratified", "multistage"}
        or bool(context.get("sampling_weight"))
    )
    if executor != "descriptive" and complex_sampling and not sampling_design_aware:
        raise AnalysisExecutionError(
            "Execution blocked: this method is not validated for the declared "
            "clustered or complex sampling design. A design-aware estimator "
            "and variance procedure are required."
        )

    repeated_designs = {
        "paired", "repeated_measure", "repeated_measures",
        "longitudinal", "time_series",
    }
    if executor in {"welch_t", "anova", "welch_mean_difference_ci"} and study_design in repeated_designs:
        raise AnalysisExecutionError(
            "Execution blocked: this executor assumes independent groups and "
            "is not validated for paired, repeated-measures, longitudinal or "
            "time-series designs."
        )

    return context


def available_execution_methods() -> tuple[str, ...]:
    """Return labels only for catalogue methods with validated executors."""
    labels = []
    for record in get_statistical_methods(implementation_status="implemented"):
        if (
            record.entity_id in _EXECUTOR_BY_METHOD_ID
            and record.execution_eligibility in {"eligible", "conditional"}
        ):
            labels.extend([record.name, *record.aliases])
    return tuple(dict.fromkeys(labels))


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
    if not isinstance(method, str):
        raise AnalysisExecutionError("The recommendation does not identify a valid method.")

    registry_record = _resolve_registered_method(method)
    executor = (
        _EXECUTOR_BY_METHOD_ID.get(registry_record.entity_id)
        if registry_record is not None
        and registry_record.implementation_status == "implemented"
        and registry_record.execution_eligibility in {"eligible", "conditional"}
        else None
    )
    if executor is None:
        raise AnalysisExecutionError(
            f"The recommended method '{method}' does not yet have a validated execution implementation."
        )

    supplied_method_id = recommendation.get("method_id")
    if supplied_method_id and supplied_method_id != registry_record.entity_id:
        raise AnalysisExecutionError(
            "The recommendation method identifier does not match the statistical catalogue."
        )

    status = recommendation.get("status")
    if status in {"ineligible", "insufficient_information"}:
        raise AnalysisExecutionError(
            f"The recommended method cannot be executed while its status is '{status}'."
        )

    design_context = _validate_design_compatibility(
        recommendation,
        executor=executor,
        sampling_design_aware=bool(
            (registry_record.statistical_specification or {}).get(
                "sampling_design_aware", False
            )
        ),
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
        result.metadata.update({
            "estimate_scope": "observed_dataset",
            "population_representative": False,
        })
        result.limitations.append(
            "This is an unweighted summary of the observed dataset; it is not "
            "a population estimate. Use a validated weighting and "
            "sampling-design procedure when population inference is intended."
        )
    elif executor == "mean_ci":
        if len(variables) != 1:
            raise AnalysisExecutionError(
                "A mean confidence interval requires exactly one numeric variable."
            )
        confidence_level = (recommendation.get("options") or {}).get(
            "confidence_level", 0.95
        )
        result = run_mean_confidence_interval(
            df, variables[0], confidence_level=confidence_level
        )
    elif executor == "one_sample_t":
        if len(variables) != 1:
            raise AnalysisExecutionError(
                "A one-sample t-test requires exactly one numeric outcome variable."
            )
        options = recommendation.get("options") or {}
        if "reference_value" not in options:
            raise AnalysisExecutionError(
                "A one-sample t-test requires a user-specified reference_value."
            )
        result = run_one_sample_t_test(
            df,
            variables[0],
            reference_value=options["reference_value"],
            alternative=options.get("alternative", "two-sided"),
        )
    elif executor == "proportion_ci":
        if len(variables) != 1:
            raise AnalysisExecutionError(
                "A proportion confidence interval requires exactly one binary variable."
            )
        confidence_level = (recommendation.get("options") or {}).get(
            "confidence_level", 0.95
        )
        result = run_proportion_confidence_interval(
            df, variables[0], confidence_level=confidence_level
        )
    elif executor == "paired_mean_difference_ci":
        if len(variables) != 2:
            raise AnalysisExecutionError(
                "A paired mean-change interval requires before and after measurement variables."
            )
        confidence_level = (recommendation.get("options") or {}).get(
            "confidence_level", 0.95
        )
        result = run_paired_mean_difference_confidence_interval(
            df, variables[0], variables[1], confidence_level=confidence_level
        )
    elif executor == "welch_mean_difference_ci":
        if len(variables) != 2:
            raise AnalysisExecutionError(
                "A Welch mean-difference interval requires an outcome and a grouping variable."
            )
        confidence_level = (recommendation.get("options") or {}).get(
            "confidence_level", 0.95
        )
        result = run_welch_mean_difference_confidence_interval(
            df, variables[0], variables[1], confidence_level=confidence_level
        )
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
            "method_id": registry_record.entity_id,
            "catalogue_version": registry_record.metadata.get("catalogue_version"),
            "sampling_design_aware": bool(
                (registry_record.statistical_specification or {}).get(
                    "sampling_design_aware", False
                )
            ),
            "study_design": design_context.get("study_design"),
            "sampling_design": design_context.get("sampling_design"),
            "design_context": dict(design_context),
        }
    )
    return result
