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
    run_categorical_frequency_distribution,
    run_categorical_cross_tabulation,
    run_independent_samples_t_test,
    run_mean_confidence_interval,
    run_one_sample_t_test,
    run_one_sample_binomial_test,
    run_two_independent_proportions_test,
    run_two_proportions_confidence_interval,
    run_proportion_confidence_interval,
    run_welch_mean_difference_confidence_interval,
    run_paired_mean_difference_confidence_interval,
    run_paired_samples_t_test,
    run_chi_square_test_of_independence,
    run_fisher_exact_test,
    run_one_way_anova,
    run_mann_whitney_u_test,
    run_kruskal_wallis_test,
    run_dunn_posthoc_test,
    run_wilcoxon_signed_rank_test,
    run_friedman_test,
    run_friedman_pairwise_posthoc,
    run_repeated_measures_anova,
    run_linear_mixed_effects_model,
)
from timan_intelligence.core.numeric_association import run_numeric_association
from timan_intelligence.services.analysis_service import (
    run_multiple_linear_regression_service,
    run_binary_logistic_regression_service,
    run_simple_linear_regression_service,
    run_ordinal_logistic_regression_service,
    run_multinomial_logistic_regression_service,
    run_poisson_regression_service,
    run_negative_binomial_regression_service,
    run_kaplan_meier_service,
    run_cox_survival_service,
)


class AnalysisExecutionError(ValueError):
    """A recommendation cannot safely be executed."""


_EXECUTOR_BY_METHOD_ID = {
    "method.descriptive.numeric.summary": "descriptive",
    "method.descriptive.categorical.frequency": "categorical_frequency",
    "method.descriptive.categorical.cross_tabulation": "cross_tabulation",
    "method.inference.confidence_interval.mean": "mean_ci",
    "method.inference.comparison.t_test.one_sample": "one_sample_t",
    "method.inference.comparison.binomial.one_sample": "one_sample_binomial",
    "method.inference.comparison.proportions.independent": "two_proportions",
    "method.inference.confidence_interval.proportions.independent": "two_proportions_ci",
    "method.inference.confidence_interval.proportion": "proportion_ci",
    "method.inference.confidence_interval.mean_difference.welch": "welch_mean_difference_ci",
    "method.inference.confidence_interval.mean_difference.paired": "paired_mean_difference_ci",
    "method.inference.comparison.t_test.paired": "paired_t",
    "method.inference.association.chi_square.independence": "chi_square_independence",
    "method.inference.association.fisher_exact": "fisher_exact",
    "method.inference.association.correlation.pearson": "numeric_correlation",
    "method.inference.association.correlation.spearman": "numeric_correlation",
    "method.inference.comparison.t_test.independent.welch": "welch_t",
    "method.inference.comparison.anova.one_way": "anova",
    "method.inference.comparison.mann_whitney": "mann_whitney",
    "method.inference.comparison.kruskal_wallis": "kruskal_wallis",
    "method.inference.comparison.posthoc.dunn_holm": "dunn_holm",
    "method.inference.comparison.wilcoxon_signed_rank": "wilcoxon_signed_rank",
    "method.inference.comparison.friedman": "friedman",
    "method.inference.comparison.posthoc.friedman_wilcoxon_holm": "friedman_wilcoxon_holm",
    "method.inference.comparison.anova.repeated_measures": "repeated_measures_anova",
    "method.inference.regression.linear_mixed_effects": "linear_mixed_effects",
    "method.inference.regression.linear.multiple": "multiple_linear_regression",
    "method.inference.regression.logistic.binary": "binary_logistic_regression",
    "method.inference.regression.linear.simple": "simple_linear_regression",
    "method.inference.regression.logistic.ordinal": "ordinal_logistic_regression",
    "method.inference.regression.logistic.multinomial": "multinomial_logistic_regression",
    "method.inference.regression.count.poisson": "poisson_regression",
    "method.inference.regression.count.negative_binomial": "negative_binomial_regression",
    "method.inference.survival.kaplan_meier": "kaplan_meier",
    "method.inference.survival.cox": "cox_survival",
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
    if executor not in {"descriptive", "cross_tabulation"} and complex_sampling and not sampling_design_aware:
        raise AnalysisExecutionError(
            "Execution blocked: this method is not validated for the declared "
            "clustered or complex sampling design. A design-aware estimator "
            "and variance procedure are required."
        )

    repeated_designs = {
        "paired", "repeated_measure", "repeated_measures",
        "longitudinal", "time_series",
    }
    if executor in {"welch_t", "anova", "mann_whitney", "kruskal_wallis", "dunn_holm", "welch_mean_difference_ci", "chi_square_independence", "fisher_exact", "two_proportions", "two_proportions_ci", "numeric_correlation", "multiple_linear_regression", "binary_logistic_regression", "simple_linear_regression", "ordinal_logistic_regression", "multinomial_logistic_regression", "poisson_regression", "negative_binomial_regression", "kaplan_meier", "cox_survival"} and study_design in repeated_designs:
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

    options = recommendation.get("options") or {}

    if executor == "cross_tabulation":
        if len(variables) != 2:
            raise AnalysisExecutionError(
                "Cross-tabulation requires exactly two categorical variables."
            )
        result = run_categorical_cross_tabulation(df, variables[0], variables[1])
        result.limitations.append(
            "The displayed cross-tabulation is unweighted even if the dataset has a complex sampling design; use a design-adjusted procedure for population inference."
        )
    elif executor == "categorical_frequency":
        if len(variables) != 1:
            raise AnalysisExecutionError("A frequency distribution requires exactly one categorical variable.")
        result = run_categorical_frequency_distribution(df, variables[0])
    elif executor == "descriptive":
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
    elif executor == "one_sample_binomial":
        if len(variables) != 1:
            raise AnalysisExecutionError("An exact binomial test requires exactly one binary outcome variable.")
        options = recommendation.get("options") or {}
        if "reference_proportion" not in options:
            raise AnalysisExecutionError("An exact binomial test requires a user-specified reference_proportion.")
        result = run_one_sample_binomial_test(df, variables[0], options["reference_proportion"],
            alternative=options.get("alternative", "two-sided"), confidence_level=options.get("confidence_level", 0.95))
    elif executor == "two_proportions_ci":
        if len(variables) != 2:
            raise AnalysisExecutionError("A two-proportion confidence interval requires a binary outcome and a two-group variable.")
        confidence_level = (recommendation.get("options") or {}).get("confidence_level", 0.95)
        result = run_two_proportions_confidence_interval(df, variables[0], variables[1], confidence_level)
    elif executor == "two_proportions":
        if len(variables) != 2:
            raise AnalysisExecutionError("A two-proportion comparison requires a binary outcome and a two-group variable.")
        options = recommendation.get("options") or {}
        result = run_two_independent_proportions_test(
            df, variables[0], variables[1],
            confidence_level=options.get("confidence_level", 0.95),
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
    elif executor == "numeric_correlation":
        if len(variables) != 2:
            raise AnalysisExecutionError("Correlation requires exactly two numeric variables.")
        association = run_numeric_association(df, variables[0], variables[1])
        result = AnalysisResult(
            title=f"Numeric association: {variables[0]} and {variables[1]}",
            method="Pearson product-moment and Spearman rank correlation",
            status="success",
            tables={
                "descriptive_summary": pd.DataFrame(association["descriptive_summary"]).T,
                "paired_observations": association["paired_data"].rename(
                    columns={"first": variables[0], "second": variables[1]}
                ),
            },
            findings=list(association["findings"]),
            assumptions=[
                "Each complete pair represents one independent observational unit.",
                "Pearson correlation describes linear association; Spearman correlation describes monotonic rank association.",
            ],
            limitations=list(association["warnings"]),
            metadata=dict(association["metadata"]),
        )
    elif executor == "fisher_exact":
        if len(variables) != 2:
            raise AnalysisExecutionError("Fisher exact test requires exactly two categorical variables.")
        options = recommendation.get("options") or {}
        result = run_fisher_exact_test(df, variables[0], variables[1], alternative=options.get("alternative", "two-sided"))
    elif executor == "chi_square_independence":
        if len(variables) != 2:
            raise AnalysisExecutionError("A chi-square test of independence requires exactly two categorical variables.")
        result = run_chi_square_test_of_independence(df, variables[0], variables[1])
    elif executor == "paired_t":
        if len(variables) != 2:
            raise AnalysisExecutionError("A paired-samples t-test requires before and after measurement variables.")
        options = recommendation.get("options") or {}
        result = run_paired_samples_t_test(
            df, variables[0], variables[1],
            confidence_level=options.get("confidence_level", 0.95),
            alternative=options.get("alternative", "two-sided"),
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
    elif executor == "mann_whitney":
        if len(variables) != 2:
            raise AnalysisExecutionError("The Mann–Whitney U test requires an outcome and a two-group variable.")
        options = recommendation.get("options") or {}
        result = run_mann_whitney_u_test(df, variables[0], variables[1], alternative=options.get("alternative", "two-sided"))
    elif executor == "kruskal_wallis":
        if len(variables) != 2:
            raise AnalysisExecutionError("The Kruskal–Wallis test requires an outcome and a grouping variable.")
        result = run_kruskal_wallis_test(df, variables[0], variables[1])
    elif executor == "dunn_holm":
        if len(variables) != 2:
            raise AnalysisExecutionError("Dunn post-hoc testing requires an outcome and a grouping variable.")
        result = run_dunn_posthoc_test(df, variables[0], variables[1])
    elif executor == "wilcoxon_signed_rank":
        if len(variables) != 2:
            raise AnalysisExecutionError("Wilcoxon signed-rank testing requires before and after measurement variables.")
        result = run_wilcoxon_signed_rank_test(df, variables[0], variables[1], options.get("alternative", "two-sided"))
    elif executor == "multiple_linear_regression":
        if len(variables) < 3:
            raise AnalysisExecutionError(
                "Multiple linear regression requires one numeric outcome and at least two numeric predictors."
            )
        result = run_multiple_linear_regression_service(
            df, variables[1:], variables[0]
        )
    elif executor == "binary_logistic_regression":
        if len(variables) < 2:
            raise AnalysisExecutionError(
                "Binary logistic regression requires one binary outcome and at least one numeric predictor."
            )
        result = run_binary_logistic_regression_service(
            df, variables[1:], variables[0],
            positive_class=options.get("positive_class"),
        )
    elif executor == "simple_linear_regression":
        if len(variables) != 2:
            raise AnalysisExecutionError("Simple linear regression requires an outcome and exactly one predictor.")
        result = run_simple_linear_regression_service(df, variables[1], variables[0])
    elif executor == "ordinal_logistic_regression":
        ordered = options.get("ordered_categories")
        if len(variables) < 2:
            raise AnalysisExecutionError("Ordinal logistic regression requires an outcome and at least one predictor.")
        if not isinstance(ordered, list) or len(ordered) < 2:
            raise AnalysisExecutionError("Ordinal logistic regression requires ordered_categories in the options.")
        result = run_ordinal_logistic_regression_service(df, variables[1:], variables[0], ordered)
    elif executor == "multinomial_logistic_regression":
        if len(variables) < 2:
            raise AnalysisExecutionError("Multinomial logistic regression requires an outcome and at least one predictor.")
        result = run_multinomial_logistic_regression_service(
            df, variables[1:], variables[0], options.get("reference_category")
        )
    elif executor in {"poisson_regression", "negative_binomial_regression"}:
        if len(variables) < 2:
            raise AnalysisExecutionError("Count regression requires a count outcome and at least one predictor.")
        exposure = options.get("exposure_variable")
        if exposure is not None and (not isinstance(exposure, str) or exposure not in df.columns):
            raise AnalysisExecutionError("The selected exposure_variable is not a valid dataset column.")
        service = (
            run_poisson_regression_service
            if executor == "poisson_regression"
            else run_negative_binomial_regression_service
        )
        result = service(df, variables[1:], variables[0], exposure_variable=exposure)
    elif executor == "kaplan_meier":
        if len(variables) not in {2, 3}:
            raise AnalysisExecutionError("Kaplan-Meier analysis requires time and event variables, plus an optional grouping variable.")
        if "event_value" not in options:
            raise AnalysisExecutionError("Kaplan-Meier analysis requires an explicit event_value.")
        result = run_kaplan_meier_service(
            df, variables[0], variables[1], options["event_value"],
            variables[2] if len(variables) == 3 else options.get("group_variable"),
        )
    elif executor == "cox_survival":
        if len(variables) < 3:
            raise AnalysisExecutionError("Cox regression requires time, event and at least one predictor variable.")
        if "event_value" not in options:
            raise AnalysisExecutionError("Cox regression requires an explicit event_value.")
        result = run_cox_survival_service(
            df, variables[2:], variables[0], variables[1], options["event_value"]
        )
    elif executor == "linear_mixed_effects":
        if len(variables) < 3:
            raise AnalysisExecutionError("A linear mixed-effects model requires an outcome, group identifier and at least one fixed-effect predictor.")
        result = run_linear_mixed_effects_model(df, variables[0], variables[1], variables[2:], options.get("confidence_level", 0.95), options.get("random_slope_variable"))
    elif executor == "repeated_measures_anova":
        if len(variables) < 3:
            raise AnalysisExecutionError("Repeated-measures ANOVA requires at least three repeated-measurement variables.")
        result = run_repeated_measures_anova(df, variables, options.get("confidence_level", 0.95))
    elif executor == "friedman_wilcoxon_holm":
        if len(variables) < 3:
            raise AnalysisExecutionError("Friedman pairwise post-hoc testing requires at least three repeated-measurement variables.")
        result = run_friedman_pairwise_posthoc(df, variables)
    elif executor == "friedman":
        if len(variables) < 3:
            raise AnalysisExecutionError("The Friedman test requires at least three repeated-measurement variables.")
        result = run_friedman_test(df, variables)
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
