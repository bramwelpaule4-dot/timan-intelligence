"""Shared orchestration entry points used by the web and desktop interfaces."""

from typing import Any

import pandas as pd
from timan_intelligence.core.poisson_regression import run_poisson_regression
from timan_intelligence.core.negative_binomial_regression import run_negative_binomial_regression
from timan_intelligence.core.survival_analysis import run_kaplan_meier, run_cox_proportional_hazards

from timan_intelligence.core.contracts import AnalysisResult, AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe
from timan_intelligence.core.categorical_analysis import run_categorical_association
from timan_intelligence.core.numeric_comparison import run_numeric_group_comparison
from timan_intelligence.core.numeric_association import run_numeric_association
from timan_intelligence.core.simple_regression import run_simple_linear_regression
from timan_intelligence.core.multiple_regression import run_multiple_linear_regression
from timan_intelligence.core.binary_logistic_regression import run_binary_logistic_regression
from timan_intelligence.core.ordinal_logistic_regression import run_ordinal_logistic_regression
from timan_intelligence.core.multinomial_logistic_regression import run_multinomial_logistic_regression
from timan_intelligence.core.categorical_model_recommender import recommend_categorical_outcome_model
from timan_intelligence.core.regression_diagnostics import run_regression_diagnostics
from timan_intelligence.core.survey_profiler import (
    profile_survey_dataframe,
    question_frequency_table,
    multiple_response_table,
    likert_item_table,
)
from timan_intelligence.modules.descriptive import numeric_summary, frequency_table


def run_data_quality(df: pd.DataFrame) -> AnalysisResult:
    profile = profile_dataframe(df)
    return AnalysisResult(
        title="Data quality profile",
        method="Deterministic data profiling",
        tables={"column_profiles": pd.DataFrame(profile["column_profiles"])},
        findings=[
            f"Dataset contains {profile['rows']:,} rows and {profile['columns']:,} columns.",
            f"{profile['missing_cells']:,} missing cells ({profile['missing_percent']}% of all cells).",
            f"{profile['duplicate_rows']:,} fully duplicated rows detected; none were removed.",
        ],
        limitations=profile["warnings"],
        metadata={"rows": profile["rows"], "columns": profile["columns"]},
    )


def run_survey_profile(df: pd.DataFrame) -> AnalysisResult:
    """Recognise and profile questionnaire-style data without modifying it."""
    profile = profile_survey_dataframe(df)
    status = "success" if profile["is_survey_like"] else "needs_input"
    findings = [
        (
            "Questionnaire-style response structure detected "
            f"({profile['confidence']} confidence)."
            if profile["is_survey_like"]
            else "The dataset does not yet show enough evidence of questionnaire-style structure."
        ),
        f"{profile['respondents']:,} records and {profile.get('variable_count', 0):,} variables inspected.",
        f"{profile['question_count']:,} response-like variables identified.",
    ]
    if profile.get("identifier_candidates"):
        findings.append(
            "Possible respondent or record identifiers: "
            + ", ".join(profile["identifier_candidates"])
            + ". Confirm these against the data dictionary."
        )
    tables = {"response_variable_profile": pd.DataFrame(profile["columns"])}
    frequency_columns = [
        item["column"] for item in profile["columns"]
        if item["type"] in {
            "categorical", "binary", "likert_item", "possible_likert_numeric"
        } and not item["identifier_name_hint"]
    ]
    multiple_response_columns = [
        item["column"] for item in profile["columns"]
        if item["type"] == "multiple_response"
    ]
    for column in frequency_columns:
        tables[f"frequency::{column}"] = question_frequency_table(df, column)
    for column in multiple_response_columns:
        tables[f"multiple_response::{column}"] = multiple_response_table(df, column)
    likert_columns = [
        item["column"] for item in profile["columns"]
        if item["type"] == "likert_item" and not item["identifier_name_hint"]
    ]
    for column in likert_columns:
        tables[f"likert::{column}"] = likert_item_table(df, column)

    return AnalysisResult(
        title="Survey data recognition and profile",
        method="Heuristic questionnaire recognition and deterministic response profiling",
        status=status,
        tables=tables,
        findings=findings,
        limitations=profile["warnings"],
        metadata={
            "is_survey_like": profile["is_survey_like"],
            "confidence": profile["confidence"],
            "recognition_score": profile.get("recognition_score", 0),
            "respondents": profile["respondents"],
            "variable_count": profile.get("variable_count", 0),
            "question_count": profile["question_count"],
            "identifier_candidates": profile.get("identifier_candidates", []),
            "response_type_counts": profile.get("response_type_counts", {}),
            "frequency_columns": frequency_columns,
            "multiple_response_columns": multiple_response_columns,
            "likert_columns": likert_columns,
        },
    )


def run_categorical_comparison(
    df: pd.DataFrame,
    row_variable: str,
    column_variable: str,
) -> AnalysisResult:
    """Run reusable categorical cross-tabulation and guarded association testing."""
    output = run_categorical_association(df, row_variable, column_variable)
    metadata = output["metadata"]
    findings = list(output["findings"])
    if metadata["test_status"] == "tested":
        findings.append(
            f"{metadata['test']} returned p={metadata['p_value']:.4g}."
        )
    return AnalysisResult(
        title=f"Categorical comparison: {row_variable} by {column_variable}",
        method=metadata["test"],
        status="success" if metadata["test_status"] == "tested" else "descriptive_only",
        tables={
            "observed_counts": output["counts"],
            "row_percentages": output["row_percentages"],
            "column_percentages": output["column_percentages"],
        },
        findings=findings,
        assumptions=[
            "Each row is treated as one independent observational unit.",
            "Only records with non-missing values for both selected variables are included.",
        ],
        limitations=output["warnings"],
        metadata=metadata,
    )



def run_numeric_group_comparison_service(
    df: pd.DataFrame,
    group_variable: str,
    outcome_variable: str,
) -> AnalysisResult:
    """Run a shared numeric-outcome comparison across independent groups."""
    output = run_numeric_group_comparison(
        df,
        group_variable,
        outcome_variable,
    )
    metadata = output["metadata"]
    findings = list(output["findings"])
    if metadata["test_status"] == "tested":
        if metadata["mean_difference"] is not None:
            ci = metadata["confidence_interval_95"]
            findings.append(
                f"Mean difference ({metadata['group_labels'][1]} minus "
                f"{metadata['group_labels'][0]}) = "
                f"{metadata['mean_difference']:.3g}; 95% CI "
                f"[{ci[0]:.3g}, {ci[1]:.3g}]."
            )
    return AnalysisResult(
        title=f"Numeric comparison: {outcome_variable} by {group_variable}",
        method=metadata["test"],
        status="success" if metadata["test_status"] == "tested" else "descriptive_only",
        tables={"group_summaries": output["group_summaries"]},
        findings=findings,
        assumptions=[
            "Groups are independent and each record represents one observational unit.",
            "The outcome is measured on a numeric scale with meaningful differences.",
            "Welch procedures do not require equal population variances, but observations must be independent.",
        ],
        limitations=output["warnings"],
        metadata=metadata,
    )


def run_numeric_association_service(
    df: pd.DataFrame,
    first_variable: str,
    second_variable: str,
) -> AnalysisResult:
    """Run shared Pearson and Spearman association analysis."""
    output = run_numeric_association(df, first_variable, second_variable)
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Numeric association: {first_variable} and {second_variable}",
        method="Pearson product-moment and Spearman rank correlation",
        status="success",
        tables={
            "descriptive_summary": pd.DataFrame(output["descriptive_summary"]).T,
            "paired_observations": output["paired_data"].rename(
                columns={"first": first_variable, "second": second_variable}
            ),
        },
        findings=list(output["findings"]),
        assumptions=[
            "Each complete pair represents one independent observational unit.",
            "Pearson correlation describes linear association; Spearman correlation describes monotonic rank association.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_simple_linear_regression_service(
    df: pd.DataFrame,
    predictor_variable: str,
    outcome_variable: str,
) -> AnalysisResult:
    """Run a shared one-predictor ordinary least-squares regression."""
    output = run_simple_linear_regression(
        df,
        predictor_variable,
        outcome_variable,
    )
    metadata = output["metadata"]
    coefficients = pd.DataFrame(
        [
            {
                "Coefficient": "Intercept",
                "Estimate": metadata["intercept"],
                "Standard error": metadata["intercept_standard_error"],
                "95% CI lower": metadata["intercept_confidence_interval_95"][0],
                "95% CI upper": metadata["intercept_confidence_interval_95"][1],
            },
            {
                "Coefficient": predictor_variable,
                "Estimate": metadata["slope"],
                "Standard error": metadata["slope_standard_error"],
                "95% CI lower": metadata["slope_confidence_interval_95"][0],
                "95% CI upper": metadata["slope_confidence_interval_95"][1],
            },
        ]
    )
    return AnalysisResult(
        title=f"Simple linear regression: {outcome_variable} by {predictor_variable}",
        method="Ordinary least squares (one numeric predictor)",
        status="success",
        tables={
            "coefficients": coefficients,
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The expected relationship between predictor and outcome is linear.",
            "Errors are independent and have constant variance; residual normality supports conventional small-sample inference.",
            "The model includes one predictor and does not adjust for confounders or other explanatory variables.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_multiple_linear_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
) -> AnalysisResult:
    """Run a shared multiple-predictor ordinary least-squares regression."""
    output = run_multiple_linear_regression(
        df,
        predictor_variables,
        outcome_variable,
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Multiple linear regression: {outcome_variable}",
        method="Ordinary least squares (multiple numeric predictors)",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The expected relationship between the outcome and included predictors is linear and additive.",
            "Errors are independent and have constant variance; residual normality supports conventional small-sample inference.",
            "Predictors are not perfectly or near-perfectly collinear.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )




def run_binary_logistic_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    positive_class=None,
) -> AnalysisResult:
    """Run a shared binary logistic regression model."""
    output = run_binary_logistic_regression(
        df,
        predictor_variables,
        outcome_variable,
        positive_class,
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Binary logistic regression: {outcome_variable}",
        method="Maximum-likelihood binary logistic regression",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The outcome has exactly two categories and the selected positive event is correctly identified.",
            "Observations are independent and continuous predictors have an approximately linear relationship with the log-odds of the outcome.",
            "The model is correctly specified and does not contain perfect or quasi-perfect separation.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )


def run_ordinal_logistic_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    ordered_categories: list,
) -> AnalysisResult:
    """Run a shared proportional-odds ordinal logistic regression model."""
    output = run_ordinal_logistic_regression(
        df, predictor_variables, outcome_variable, ordered_categories
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Ordinal logistic regression: {outcome_variable}",
        method="Cumulative-logit proportional-odds ordinal logistic regression",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
            "category_probabilities": output["category_probabilities"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The outcome categories have a meaningful order supplied by the analyst.",
            "The proportional-odds assumption holds: predictor effects are common across cumulative category splits.",
            "Observations are independent; predictors are appropriately specified and do not exhibit perfect multicollinearity.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_multinomial_logistic_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    reference_category=None,
) -> AnalysisResult:
    """Run a shared baseline-category multinomial logistic regression model."""
    output = run_multinomial_logistic_regression(
        df, predictor_variables, outcome_variable, reference_category
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Multinomial logistic regression: {outcome_variable}",
        method="Baseline-category multinomial logistic regression",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
            "category_probabilities": output["category_probabilities"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The outcome has three or more mutually exclusive nominal categories.",
            "One category is selected as the reference; coefficients compare each other category against it.",
            "Observations are independent and the selected numeric predictors are appropriately specified.",
            "The multinomial-logit model assumes independence of irrelevant alternatives; assess whether this is reasonable for the application.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_poisson_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    exposure_variable: str | None = None,
) -> AnalysisResult:
    """Run a shared Poisson count regression with an optional log exposure offset."""
    output = run_poisson_regression(
        df, predictor_variables, outcome_variable, exposure_variable
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Poisson regression: {outcome_variable}",
        method="Log-link Poisson regression by maximum likelihood",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The outcome is a non-negative integer count.",
            "Conditional on the predictors and any offset, the Poisson model assumes the count mean equals its variance.",
            "Observations are independent and the log expected count is correctly specified.",
            "An exposure offset, when supplied, is assumed to have a coefficient fixed at one.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_negative_binomial_regression_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    exposure_variable: str | None = None,
) -> AnalysisResult:
    """Run a shared NB2 count regression with optional log exposure offset."""
    output = run_negative_binomial_regression(
        df, predictor_variables, outcome_variable, exposure_variable
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title=f"Negative binomial regression: {outcome_variable}",
        method="NB2 log-link negative binomial regression by maximum likelihood",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The outcome is a non-negative integer count.",
            "The conditional variance follows the NB2 form: Var(Y|X) = mu + alpha × mu².",
            "Observations are independent and the log expected count is correctly specified.",
            "An exposure offset, when supplied, is assumed to have a coefficient fixed at one.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )



def run_kaplan_meier_service(
    df: pd.DataFrame,
    time_variable: str,
    event_variable: str,
    event_value,
    group_variable: str | None = None,
) -> AnalysisResult:
    """Run Kaplan-Meier survival estimation and optional log-rank comparison."""
    output = run_kaplan_meier(
        df, time_variable, event_variable, event_value, group_variable
    )
    metadata = output["metadata"]
    return AnalysisResult(
        title="Kaplan-Meier survival analysis",
        method="Non-parametric Kaplan-Meier estimator",
        status="success",
        tables=output["tables"],
        findings=list(output["findings"]),
        assumptions=[
            "The event category is explicitly selected; other observed event-status categories are treated as censored.",
            "Censoring is non-informative conditional on the analysis.",
            "Each record represents an independent observational unit.",
        ],
        limitations=list(output["warnings"]),
        metadata=metadata,
    )


def run_cox_survival_service(
    df: pd.DataFrame,
    predictor_variables: list[str],
    time_variable: str,
    event_variable: str,
    event_value,
) -> AnalysisResult:
    """Run Cox proportional hazards regression through the shared service."""
    output = run_cox_proportional_hazards(
        df, predictor_variables, time_variable, event_variable, event_value
    )
    return AnalysisResult(
        title="Cox proportional hazards regression",
        method="Cox semi-parametric proportional hazards model (Breslow ties)",
        status="success",
        tables={
            "coefficients": output["coefficients"],
            "baseline_survival": output["baseline_survival"],
            "fitted_data": output["fitted_data"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "The hazard ratios are constant over follow-up time (proportional hazards).",
            "Censoring is non-informative conditional on included predictors.",
            "The log hazard is linear in each numeric predictor.",
            "Observations are independent.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_regression_diagnostics_service(
    fitted_data: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
) -> AnalysisResult:
    """Assess residual and influence diagnostics for a fitted OLS model."""
    output = run_regression_diagnostics(
        fitted_data,
        predictor_variables,
        outcome_variable,
    )
    return AnalysisResult(
        title="Linear regression diagnostics",
        method="Residual, heteroscedasticity, collinearity and influence diagnostics",
        status="success",
        tables={
            "diagnostics": output["diagnostics"],
            "influential_observations": output["influential_observations"],
            "residual_plot_data": output["residual_plot_data"],
        },
        findings=[
            f"Diagnostics assessed {output['metadata']['valid_n']:,} complete fitted records.",
            f"Maximum Cook's distance was {output['metadata']['maximum_cooks_distance']:.4g}.",
            f"Maximum leverage was {output['metadata']['maximum_leverage']:.4g}.",
        ],
        assumptions=[
            "The supplied fitted values and residuals come from the intended ordinary least-squares model.",
            "The row order and record positions correspond to the fitted dataset supplied to this diagnostic routine.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_numeric_summary(df: pd.DataFrame, request: AnalysisRequest | None = None) -> AnalysisResult:
    summary = numeric_summary(df)
    if summary.empty:
        return AnalysisResult(
            title="Numeric summary",
            method="Descriptive statistics",
            status="needs_input",
            findings=["No numeric columns were detected. Check variable types or select a different analysis."],
        )
    return AnalysisResult(
        title="Numeric summary",
        method="Descriptive statistics",
        tables={"numeric_summary": summary},
        findings=[f"Summary statistics were calculated for {len(summary)} numeric variables."],
        limitations=["These are descriptive summaries; they do not account for survey weights or complex sampling design."],
    )


def run_frequency(df: pd.DataFrame, column: str) -> AnalysisResult:
    table = frequency_table(df, column)
    return AnalysisResult(
        title=f"Frequency distribution: {column}",
        method="Unweighted frequency distribution",
        tables={"frequency_table": table},
        findings=[f"Frequency distribution calculated for '{column}'."],
        limitations=["Percentages are unweighted unless a future survey-design module is explicitly used."],
    )


def recommend_categorical_outcome_model_service(
    df: pd.DataFrame,
    outcome_variable: str,
    category_structure: str | None = None,
) -> AnalysisResult:
    """Return a transparent recommendation for a categorical outcome model."""
    output = recommend_categorical_outcome_model(
        df, outcome_variable, category_structure
    )
    return AnalysisResult(
        title=f"Categorical outcome model recommendation: {outcome_variable}",
        method="Rule-based categorical outcome classification",
        status="success" if output["status"] in ("ready", "needs_classification") else "warning",
        findings=list(output["rationale"]),
        limitations=list(output["warnings"]),
        metadata=output,
    )


def run_weighted_frequency_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    include_missing: bool = False,
) -> AnalysisResult:
    """Run weighted categorical frequencies with explicit design limitations."""
    from timan_intelligence.core.survey_weights import weighted_frequency_table

    output = weighted_frequency_table(
        df, outcome_variable, weight_variable, include_missing
    )
    return AnalysisResult(
        title=f"Weighted frequencies: {outcome_variable}",
        method="Survey-weighted descriptive frequency estimation",
        status="success",
        tables={"weighted_frequencies": output["table"]},
        findings=list(output["findings"]),
        assumptions=[
            "The supplied weight is appropriate for the target population and analysis unit.",
            "Observed positive weights are numeric and finite.",
            "The weighted percentage denominator includes only records with usable weights and the selected response inclusion rule.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_weighted_numeric_summary_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
) -> AnalysisResult:
    """Run weighted numeric summaries with explicit design limitations."""
    from timan_intelligence.core.survey_weights import weighted_numeric_summary

    output = weighted_numeric_summary(df, outcome_variable, weight_variable)
    return AnalysisResult(
        title=f"Weighted numeric summary: {outcome_variable}",
        method="Survey-weighted descriptive estimation",
        status="success",
        tables={"weighted_summary": output["table"]},
        findings=list(output["findings"]),
        assumptions=[
            "The supplied weight is appropriate for the target population and analysis unit.",
            "Observed positive weights are numeric and finite.",
            "The weighted standard deviation is a population-form descriptive spread measure, not a design-based variance estimate.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )

def run_stratified_weighted_mean_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    strata_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run stratified weighted mean estimation through the shared service."""
    from timan_intelligence.core.stratified_survey import stratified_weighted_mean

    output = stratified_weighted_mean(
        df, outcome_variable, weight_variable, strata_variable, confidence_level
    )
    return AnalysisResult(
        title=f"Stratified weighted mean: {outcome_variable}",
        method="Stratified simple-random-sample weighted mean with Taylor linearization",
        status="success",
        tables={
            "stratified_estimate": output["table"],
            "strata_summary": output["strata_summary"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Sampling is independent simple random sampling within each stratum.",
            "Expansion weights are constant within each stratum.",
            "Each stratum has at least two complete observations.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_stratified_weighted_frequency_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    strata_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run stratified weighted category proportions through the shared service."""
    from timan_intelligence.core.stratified_survey import stratified_weighted_frequencies

    output = stratified_weighted_frequencies(
        df, outcome_variable, weight_variable, strata_variable, confidence_level
    )
    return AnalysisResult(
        title=f"Stratified weighted frequencies: {outcome_variable}",
        method="Stratified simple-random-sample proportions with Taylor linearization",
        status="success",
        tables={
            "stratified_frequencies": output["table"],
            "strata_summary": output["strata_summary"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Sampling is independent simple random sampling within each stratum.",
            "Expansion weights are constant within each stratum.",
            "Each stratum has at least two complete observations.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )

def run_cluster_weighted_mean_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    cluster_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run PSU-cluster-adjusted weighted mean estimation."""
    from timan_intelligence.core.cluster_survey import cluster_weighted_mean

    output = cluster_weighted_mean(
        df, outcome_variable, weight_variable, cluster_variable,
        strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Cluster-adjusted weighted mean: {outcome_variable}",
        method="Weighted ratio mean with PSU-level Taylor linearization",
        status="success",
        tables={"cluster_estimate": output["table"]},
        findings=list(output["findings"]),
        assumptions=[
            "Sampled primary sampling units are independent within strata.",
            "At least two sampled PSUs are present in every stratum.",
            "The supplied weights correctly represent selection probabilities and target-population expansion.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_cluster_weighted_frequency_service(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    cluster_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run PSU-cluster-adjusted weighted category proportions."""
    from timan_intelligence.core.cluster_survey import cluster_weighted_frequencies

    output = cluster_weighted_frequencies(
        df, outcome_variable, weight_variable, cluster_variable,
        strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Cluster-adjusted weighted frequencies: {outcome_variable}",
        method="Weighted proportions with PSU-level Taylor linearization",
        status="success",
        tables={"cluster_frequencies": output["table"]},
        findings=list(output["findings"]),
        assumptions=[
            "Sampled primary sampling units are independent within strata.",
            "At least two sampled PSUs are present in every stratum.",
            "The supplied weights correctly represent selection probabilities and target-population expansion.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_two_stage_survey_design_inspection_service(
    df: pd.DataFrame,
    psu_variable: str,
    ssu_variable: str,
    weight_variable: str,
    strata_variable: str | None = None,
    psu_population_count_variable: str | None = None,
    ssu_population_count_variable: str | None = None,
) -> AnalysisResult:
    """Validate and describe a two-stage survey design without inferential claims."""
    from timan_intelligence.core.multistage_survey import inspect_two_stage_design

    output = inspect_two_stage_design(
        df,
        psu_variable,
        ssu_variable,
        weight_variable,
        strata_variable,
        psu_population_count_variable,
        ssu_population_count_variable,
    )
    return AnalysisResult(
        title="Two-stage survey design inspection",
        method="Two-stage sample hierarchy and sampling-fraction validation",
        status="success",
        tables={
            "psu_summary": output["psu_summary"],
            "ssu_summary": output["ssu_summary"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Each sampled SSU identifier is unique within its stratum and belongs to one PSU.",
            "Population-count fields, when supplied, describe the relevant stage-specific sampling frame.",
            "The supplied positive weights are final analysis weights; this inspection does not reconstruct them.",
        ],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_two_stage_survey_total_service(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Estimate a total under stratified two-stage SRSWOR with stage FPCs."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_total

    output = estimate_two_stage_total(
        df,
        outcome_variable,
        psu_variable,
        ssu_variable,
        psu_population_count_variable,
        ssu_population_count_variable,
        strata_variable,
        confidence_level,
        certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage survey total: {outcome_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "psu_details": output["psu_details"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Non-certainty PSUs are selected by independent SRSWOR within each stratum; any flagged certainty PSUs are take-all units.",
            "SSUs are selected by simple random sampling without replacement within each sampled PSU.",
            "Each row represents one sampled SSU and contains its fully enumerated outcome total.",
            "Population PSU counts are constant within strata and population SSU counts are constant within PSUs.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"],
            "estimate": output["estimate"],
            "variance": output["variance"],
            "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_two_stage_survey_mean_service(
    df: pd.DataFrame,
    outcome_total_variable: str,
    element_count_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Estimate a two-stage design-based population element mean."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_mean

    output = estimate_two_stage_mean(
        df, outcome_total_variable, element_count_variable, psu_variable,
        ssu_variable, psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage survey mean: {outcome_total_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={"stratum_estimates": output["strata"], "psu_details": output["psu_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "Each sampled SSU supplies a fully enumerated outcome total and eligible-element count.",
            "Non-certainty PSUs are selected by SRSWOR within strata; flagged certainty PSUs are take-all units. SSUs are selected by SRSWOR within PSUs.",
            "Population frame counts are constant within the relevant sampling units.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "numerator_total": output["numerator_total"],
            "denominator_total": output["denominator_total"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_two_stage_survey_proportion_service(
    df: pd.DataFrame,
    successes_variable: str,
    eligible_count_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Estimate a two-stage design-based population proportion."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_proportion

    output = estimate_two_stage_proportion(
        df, successes_variable, eligible_count_variable, psu_variable,
        ssu_variable, psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage survey proportion: {successes_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={"stratum_estimates": output["strata"], "psu_details": output["psu_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "The numerator is the number of successes and the denominator is the number of eligible elements enumerated in each sampled SSU.",
            "Successes are between zero and eligible counts in every SSU.",
            "PSUs and SSUs are independently selected by SRSWOR at their respective stages.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "numerator_total": output["numerator_total"],
            "denominator_total": output["denominator_total"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_two_stage_survey_domain_total_service(
    df: pd.DataFrame, outcome_variable: str, domain_variable: str,
    domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_population_count_variable: str, ssu_population_count_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Return a two-stage design-based domain total."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_domain_total
    output = estimate_two_stage_domain_total(
        df, outcome_variable, domain_variable, domain_value, psu_variable,
        ssu_variable, psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage domain total: {outcome_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"], "psu_details": output["psu_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "Domain membership is constant within each SSU.",
            "PSUs and SSUs are independently selected by SRSWOR at their respective stages.",
            "All sampled SSUs are retained when estimating domain variance.",
        ],
        limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"]},
    )


def run_two_stage_survey_domain_mean_service(
    df: pd.DataFrame, outcome_total_variable: str, element_count_variable: str,
    domain_variable: str, domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_population_count_variable: str, ssu_population_count_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Return a two-stage design-based domain mean."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_domain_mean
    output = estimate_two_stage_domain_mean(
        df, outcome_total_variable, element_count_variable, domain_variable,
        domain_value, psu_variable, ssu_variable, psu_population_count_variable,
        ssu_population_count_variable, strata_variable, confidence_level, certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage domain mean: {outcome_total_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"], "psu_details": output["psu_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "Domain membership is constant within each SSU.",
            "Each sampled SSU supplies fully enumerated outcome totals and element counts.",
            "All sampled SSUs are retained in domain variance estimation.",
        ],
        limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"]},
    )


def run_two_stage_survey_domain_proportion_service(
    df: pd.DataFrame, successes_variable: str, eligible_count_variable: str,
    domain_variable: str, domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_population_count_variable: str, ssu_population_count_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
    certainty_psu_variable: str | None = None,
) -> AnalysisResult:
    """Return a two-stage design-based domain proportion."""
    from timan_intelligence.core.multistage_survey import estimate_two_stage_domain_proportion
    output = estimate_two_stage_domain_proportion(
        df, successes_variable, eligible_count_variable, domain_variable,
        domain_value, psu_variable, ssu_variable, psu_population_count_variable,
        ssu_population_count_variable, strata_variable, confidence_level, certainty_psu_variable,
    )
    return AnalysisResult(
        title=f"Two-stage domain proportion: {successes_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"], "psu_details": output["psu_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "Domain membership is constant within each SSU.",
            "Successes are whole numbers between zero and eligible counts.",
            "All sampled SSUs are retained in domain variance estimation.",
        ],
        limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"]},
    )


def run_two_stage_ppswr_total_service(
    df: pd.DataFrame, outcome_variable: str, psu_variable: str,
    draw_variable: str, ssu_variable: str, ssu_population_count_variable: str,
    selection_probability_variable: str, strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate a total using PPSWR PSU draws and SRSWOR SSUs."""
    from timan_intelligence.core.pps_survey import estimate_two_stage_ppswr_total
    output = estimate_two_stage_ppswr_total(
        df, outcome_variable, psu_variable, draw_variable, ssu_variable,
        ssu_population_count_variable, selection_probability_variable,
        strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Two-stage PPSWR survey total: {outcome_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"], "psu_draw_details": output["psu_draw_details"]},
        findings=list(output["findings"]),
        assumptions=[
            "PSUs are selected independently with replacement within strata using known per-draw selection probabilities.",
            "SSUs are selected by SRSWOR within each selected PSU draw.",
            "Each PSU draw has a unique draw identifier, including repeat selections of the same physical PSU.",
        ],
        limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"]},
    )


def run_two_stage_ppswr_mean_service(
    df: pd.DataFrame, outcome_total_variable: str, element_count_variable: str,
    psu_variable: str, draw_variable: str, ssu_variable: str,
    ssu_population_count_variable: str, selection_probability_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate an element mean using two-stage PPSWR sampling."""
    from timan_intelligence.core.pps_survey import estimate_two_stage_ppswr_mean
    output = estimate_two_stage_ppswr_mean(
        df, outcome_total_variable, element_count_variable, psu_variable,
        draw_variable, ssu_variable, ssu_population_count_variable,
        selection_probability_variable, strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Two-stage PPSWR survey mean: {outcome_total_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"]},
        findings=list(output["findings"]), assumptions=[
            "PSUs are selected independently with replacement using known selection probabilities.",
            "SSUs are selected by SRSWOR within each PSU draw; each row contains SSU-level outcome totals and element counts.",
        ], limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"],
                  "numerator_total": output["numerator_total"],
                  "denominator_total": output["denominator_total"]},
    )


def run_two_stage_ppswr_proportion_service(
    df: pd.DataFrame, successes_variable: str, eligible_count_variable: str,
    psu_variable: str, draw_variable: str, ssu_variable: str,
    ssu_population_count_variable: str, selection_probability_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate a proportion using two-stage PPSWR sampling."""
    from timan_intelligence.core.pps_survey import estimate_two_stage_ppswr_proportion
    output = estimate_two_stage_ppswr_proportion(
        df, successes_variable, eligible_count_variable, psu_variable,
        draw_variable, ssu_variable, ssu_population_count_variable,
        selection_probability_variable, strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Two-stage PPSWR survey proportion: {successes_variable}",
        method=output["metadata"]["estimator"], status="success",
        tables={"stratum_estimates": output["strata"]},
        findings=list(output["findings"]), assumptions=[
            "PSUs are selected independently with replacement using known selection probabilities.",
            "SSUs are selected by SRSWOR within each PSU draw; successes and eligible counts are SSU-level totals.",
        ], limitations=list(output["warnings"]),
        metadata={**output["metadata"], "estimate": output["estimate"],
                  "variance": output["variance"], "standard_error": output["standard_error"],
                  "confidence_interval": output["confidence_interval"],
                  "confidence_level": output["confidence_level"],
                  "numerator_total": output["numerator_total"],
                  "denominator_total": output["denominator_total"]},
    )


def run_ppswor_total_service(
    df: pd.DataFrame,
    outcome_total_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a PSU-level PPSWOR Horvitz-Thompson total with SYG variance."""
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_total

    output = estimate_ppswor_total(
        df, outcome_total_variable, psu_variable,
        inclusion_probability_variable, joint_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"PPSWOR survey total: {outcome_total_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "pairwise_variance": output["pairwise_variance"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Each row represents one sampled PSU with a fully observed PSU outcome total.",
            "The design is fixed-size PPS without replacement within each stratum.",
            "First- and second-order inclusion probabilities are supplied from the actual sampling design.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_ppswor_ratio_service(
    df: pd.DataFrame,
    numerator_variable: str,
    denominator_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    parameter: str = "mean",
) -> AnalysisResult:
    """Run a PSU-level PPSWOR ratio mean/proportion with Taylor-SYG variance."""
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_ratio

    output = estimate_ppswor_ratio(
        df, numerator_variable, denominator_variable, psu_variable,
        inclusion_probability_variable, joint_inclusion_probabilities,
        strata_variable, confidence_level, parameter,
    )
    return AnalysisResult(
        title=f"PPSWOR survey {parameter}: {numerator_variable} / {denominator_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "pairwise_variance": output["pairwise_variance"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Each row represents one sampled PSU with fully observed numerator and denominator totals.",
            "The design is fixed-size PPS without replacement within each stratum.",
            "First- and second-order inclusion probabilities are supplied from the actual sampling design.",
            "Variance is estimated by first-order Taylor linearisation and the Sen-Yates-Grundy estimator.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_ppswor_domain_ratio_service(
    df: pd.DataFrame,
    domain_name: str,
    domain_numerator_variable: str,
    domain_denominator_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    parameter: str = "mean",
) -> AnalysisResult:
    """Run a design-based PPSWOR domain mean or proportion analysis."""
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio

    output = estimate_ppswor_domain_ratio(
        df, domain_name, domain_numerator_variable, domain_denominator_variable,
        psu_variable, inclusion_probability_variable,
        joint_inclusion_probabilities, strata_variable, confidence_level,
        parameter,
    )
    return AnalysisResult(
        title=f"PPSWOR domain {parameter}: {domain_name}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "pairwise_variance": output["pairwise_variance"],
            "diagnostics": output["diagnostics"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Every sampled PSU is retained, including PSUs with zero domain totals.",
            "Each row represents one sampled PSU with fully observed domain-specific numerator and denominator totals.",
            "The original fixed-size PPSWOR design and its actual first- and second-order inclusion probabilities are preserved.",
            "Variance uses first-order Taylor linearisation with the Sen-Yates-Grundy estimator.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_ppswor_domain_total_service(
    df: pd.DataFrame,
    domain_name: str,
    domain_total_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a design-based PPSWOR Horvitz-Thompson domain total analysis."""
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    output = estimate_ppswor_domain_total(
        df, domain_name, domain_total_variable, psu_variable,
        inclusion_probability_variable, joint_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"PPSWOR domain total: {domain_name}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "pairwise_variance": output["pairwise_variance"],
            "diagnostics": output["diagnostics"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "Every sampled PSU is retained, including PSUs with zero domain totals.",
            "Each row represents one sampled PSU with a fully observed domain-specific total.",
            "The original fixed-size PPSWOR design and its actual first- and second-order inclusion probabilities are preserved.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"], "estimate": output["estimate"],
            "variance": output["variance"], "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_sample_size_service(**kwargs: Any) -> AnalysisResult:
    """Run a validated proportion or mean sample-size calculation."""
    from timan_intelligence.core.sample_size import calculate_sample_size

    output = calculate_sample_size(**kwargs)
    return AnalysisResult(
        title="Survey sample-size determination",
        method=f"Normal-approximation {output['parameter']} sample-size formula",
        status="success",
        tables={"calculation": pd.DataFrame([{
            key: value for key, value in output.items()
            if not isinstance(value, (list, dict))
        }])},
        findings=[
            f"Recommended sample size to approach: {output['recommended_sample_size']:,}.",
            f"Sample size before design-effect and nonresponse adjustments: {output['sample_size_after_fpc']:,}.",
        ],
        assumptions=list(output["assumptions"]),
        limitations=list(output["warnings"]),
        metadata=output,
    )


def run_stratified_allocation_service(
    strata: pd.DataFrame, total_sample_size: int, **kwargs: Any
) -> AnalysisResult:
    """Allocate a fixed total sample across supplied strata."""
    from timan_intelligence.core.sample_size import allocate_stratified_sample

    output = allocate_stratified_sample(strata, total_sample_size, **kwargs)
    return AnalysisResult(
        title="Stratified sample allocation",
        method=f"{output['allocation_method'].title()} allocation with largest-remainder rounding",
        status="success",
        tables={"stratum_allocation": output["allocation"]},
        findings=[
            f"Allocated {output['total_sample_size']:,} respondents across {len(output['allocation']):,} strata.",
        ],
        assumptions=list(output["assumptions"]),
        limitations=list(output["warnings"]),
        metadata={"allocation_method": output["allocation_method"], "total_sample_size": output["total_sample_size"]},
    )


def run_cluster_sample_plan_service(**kwargs: Any) -> AnalysisResult:
    """Create a cluster count and respondent approach plan."""
    from timan_intelligence.core.sample_size import plan_cluster_sample

    output = plan_cluster_sample(**kwargs)
    return AnalysisResult(
        title="Cluster sample planning",
        method="One-stage cluster design-effect approximation",
        status="success",
        tables={"cluster_plan": pd.DataFrame([{
            key: value for key, value in output.items()
            if not isinstance(value, (list, dict))
        }])},
        findings=[
            f"Plan for {output['number_of_clusters']:,} clusters.",
            f"Approach {output['respondents_to_approach']:,} respondents in total.",
            f"Approximate design effect: {output['design_effect']:.3f}.",
        ],
        assumptions=list(output["assumptions"]),
        limitations=list(output["warnings"]),
        metadata=output,
    )


def run_sample_selection_service(
    frame: pd.DataFrame,
    id_column: str,
    sample_size: int,
    method: str = "srswor",
    seed: int = 2026,
    size_column: str | None = None,
    reserve_size: int = 0,
) -> AnalysisResult:
    """Select a reproducible probability sample from a frame."""
    from timan_intelligence.core.sampling_selection import select_sample

    output = select_sample(
        frame, id_column, sample_size, method, seed, size_column, reserve_size
    )
    return AnalysisResult(
        title="Sampling-frame selection",
        method=output["method"],
        status="success",
        tables={"selected_sample": output["selected"], "reserve_sample": output["reserve"]},
        findings=[
            f"Selected {output['sample_size']:,} main-sample units from a frame of {output['population_size']:,}.",
            f"Selected {output['reserve_size']:,} reserve units separately.",
            f"Random seed: {output['seed']}.",
        ],
        assumptions=["The uploaded frame is the complete eligible sampling frame.", "Identifiers are unique and represent eligible sampling units."],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_stratified_sample_selection_service(
    frame: pd.DataFrame,
    id_column: str,
    strata_column: str,
    allocations: dict[Any, int],
    method: str = "srswor",
    seed: int = 2026,
    size_column: str | None = None,
    reserve_allocations: dict[Any, int] | None = None,
) -> AnalysisResult:
    """Select independently within strata using supplied integer allocations."""
    from timan_intelligence.core.sampling_selection import select_stratified_sample

    output = select_stratified_sample(
        frame, id_column, strata_column, allocations, method, seed,
        size_column, reserve_allocations,
    )
    return AnalysisResult(
        title="Stratified sampling-frame selection",
        method=f"Stratified {output['method']}",
        status="success",
        tables={"selected_sample": output["selected"], "reserve_sample": output["reserve"]},
        findings=[
            f"Selected {output['sample_size']:,} main-sample units across strata.",
            f"Selected {output['reserve_size']:,} reserve units separately.",
            f"Random seed: {output['seed']}.",
        ],
        assumptions=["Each stratum is sampled independently.", "Supplied allocations match every observed stratum exactly."],
        limitations=list(output["warnings"]),
        metadata=output["metadata"],
    )


def run_survey_weighting_service(
    frame: pd.DataFrame,
    inclusion_probability_column: str,
    response_column: str | None = None,
    adjustment_cells: list[str] | None = None,
    poststrata_column: str | None = None,
    population_totals: dict[Any, float] | None = None,
    raking_margins: dict[str, dict[Any, float]] | None = None,
    trim_quantiles: tuple[float, float] | None = None,
) -> AnalysisResult:
    """Construct weights; nonrespondents are retained with zero analysis weight."""
    from timan_intelligence.core.survey_weighting import (
        calculate_base_weights, adjust_nonresponse,
        calibrate_poststratification, rake_weights, trim_weights,
        weight_diagnostics,
    )

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("A non-empty sampled-unit dataset is required.")
    output = frame.copy()
    output["base_weight"] = calculate_base_weights(output, inclusion_probability_column)
    stages = ["Inverse-probability base weights"]
    analysis = output.copy()
    if response_column:
        if not adjustment_cells:
            raise ValueError("Specify at least one adjustment-cell variable for nonresponse adjustment.")
        adjusted = adjust_nonresponse(output, "base_weight", response_column, adjustment_cells)
        output["nonresponse_adjusted_weight"] = adjusted
        response = pd.to_numeric(output[response_column], errors="coerce")
        analysis = output.loc[response == 1].copy()
        if analysis.empty:
            raise ValueError("No respondent records are available for weighted analysis.")
        stages.append("Weighted response-rate adjustment within cells")
    current_column = "nonresponse_adjusted_weight" if response_column else "base_weight"
    if population_totals is not None:
        if not poststrata_column:
            raise ValueError("Select a post-stratification variable.")
        analysis["poststratified_weight"] = calibrate_poststratification(
            analysis, current_column, poststrata_column, population_totals
        )
        current_column = "poststratified_weight"
        stages.append("Post-stratification to known population totals")
    raking_info = None
    if raking_margins:
        analysis["raked_weight"], raking_info = rake_weights(
            analysis, current_column, raking_margins
        )
        current_column = "raked_weight"
        stages.append("Iterative proportional fitting (raking)")
    if trim_quantiles is not None:
        analysis["trimmed_weight"] = trim_weights(
            analysis, current_column, trim_quantiles[0], trim_quantiles[1],
            preserve_total=True,
        )
        current_column = "trimmed_weight"
        stages.append("Winsorised weight trimming with total-weight preservation")
    final_weights = analysis[current_column]
    # Preserve intermediate stages in the fieldwork dataset for auditability.
    for stage_column in ("poststratified_weight", "raked_weight", "trimmed_weight"):
        if stage_column in analysis.columns:
            output[stage_column] = float("nan")
            output.loc[analysis.index, stage_column] = analysis[stage_column]
    output["analysis_weight"] = 0.0
    output.loc[analysis.index, "analysis_weight"] = final_weights
    analysis_diagnostics = weight_diagnostics(final_weights)
    stage_weight_columns = [("base_weight", output["base_weight"].loc[analysis.index])]
    for stage_column in (
        "nonresponse_adjusted_weight", "poststratified_weight",
        "raked_weight", "trimmed_weight",
    ):
        if stage_column in analysis.columns:
            stage_weight_columns.append((stage_column, analysis[stage_column]))
    stage_diagnostics = pd.DataFrame([
        {"stage": stage_name, **weight_diagnostics(stage_values)}
        for stage_name, stage_values in stage_weight_columns
    ])
    diagnostics = pd.DataFrame([{"stage": "final", **analysis_diagnostics}])
    findings = [
        f"Constructed final weights for {len(analysis):,} analysis-eligible records.",
        f"Final analysis weight column: analysis_weight.",
        f"Effective sample size (Kish): {analysis_diagnostics['kish_effective_sample_size']:.2f}.",
    ]
    limitations = [
        "Kish effective sample size and DEFF are unequal-weighting approximations; they do not capture clustering, stratification or all calibration effects.",
        "Base weights require exact first-order unit inclusion probabilities. Conditional PPSWOR draw probabilities are not accepted as substitutes.",
    ]
    if response_column:
        limitations.append("Nonrespondents are retained in the exported dataset with analysis_weight = 0; exclude them from respondent-level analyses.")
    if raking_info and not raking_info["converged"]:
        limitations.append(
            f"Raking did not converge within {raking_info['iterations']} iterations; maximum relative margin error was {raking_info['maximum_relative_margin_error']:.6g}."
        )
    return AnalysisResult(
        title="Survey weighting and adjustment",
        method=" -> ".join(stages),
        tables={"weighted_dataset": output, "weight_diagnostics": diagnostics, "weight_stage_diagnostics": stage_diagnostics},
        findings=findings,
        assumptions=[
            "The supplied inclusion probabilities are exact first-order inclusion probabilities for the sampled units.",
            "Nonresponse adjustment cells are substantively defensible and contain at least one respondent each, where used.",
            "Population control totals are accurate and refer to the same target population and reference period.",
        ],
        limitations=limitations,
        metadata={
            "final_weight_column": "analysis_weight",
            "stages": stages,
            "raking": raking_info,
            "diagnostics": analysis_diagnostics,
            "stage_diagnostics": stage_diagnostics.to_dict(orient="records"),
            "weighting_specification": {
                "inclusion_probability_column": inclusion_probability_column,
                "response_column": response_column,
                "adjustment_cells": list(adjustment_cells or []),
                "poststratification_variable": (
                    poststrata_column.removeprefix("_timan_post_")
                    if poststrata_column else None
                ),
                "population_totals": dict(population_totals or {}),
                "raking_margins": {
                    column.removeprefix("_timan_rake_"): dict(targets)
                    for column, targets in (raking_margins or {}).items()
                },
                "trimming_quantiles": list(trim_quantiles) if trim_quantiles is not None else None,
                "records_in_input": int(len(output)),
                "records_in_weighted_analysis": int(len(analysis)),
                "records_with_zero_analysis_weight": int(len(output) - len(analysis)),
            },
        },
    )


def run_survey_estimation_service(
    frame: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    estimand: str = "mean",
    design: str = "weighted_descriptive",
    strata_variable: str | None = None,
    cluster_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run guarded weighted totals, means or category proportions."""
    from timan_intelligence.core.survey_estimation import estimate_survey

    output = estimate_survey(
        frame,
        outcome_variable,
        weight_variable,
        estimand,
        design,
        strata_variable,
        cluster_variable,
        confidence_level,
    )
    variance_method = output["metadata"].get("variance_method", "Design-based variance not estimated")
    return AnalysisResult(
        title=f"Survey {estimand}: {outcome_variable}",
        method=variance_method,
        status="success",
        tables={
            "estimates": output["table"],
            "design_details": output.get("details", pd.DataFrame()),
        },
        findings=list(output["findings"]),
        assumptions=[
            "The supplied analysis weights are valid for the target population and analysis unit.",
            "The selected design declaration matches the actual sample selection procedure.",
            "Missing outcome records are not silently imputed; complete records are required by the selected estimator.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"],
            "estimand": estimand,
            "design": design,
            "outcome_variable": outcome_variable,
            "weight_variable": weight_variable,
            "strata_variable": strata_variable,
            "cluster_variable": cluster_variable,
        },
    )


def run_domain_survey_estimation_service(
    frame: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    domain_variable: str,
    domain_value: Any,
    estimand: str = "mean",
    design: str = "weighted_descriptive",
    strata_variable: str | None = None,
    cluster_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a domain estimate while retaining the complete sample design."""
    from timan_intelligence.core.survey_estimation import estimate_domain_survey

    output = estimate_domain_survey(
        frame, outcome_variable, weight_variable, domain_variable,
        domain_value, estimand, design, strata_variable,
        cluster_variable, confidence_level,
    )
    return AnalysisResult(
        title=f"Survey domain {estimand}: {domain_variable}={domain_value}",
        method=output["metadata"].get("variance_method", "Design-based variance not estimated"),
        status="success",
        tables={
            "estimates": output["table"],
            "design_details": output.get("details", pd.DataFrame()),
        },
        findings=list(output["findings"]),
        assumptions=[
            "The domain variable and selected category correctly identify the target subpopulation.",
            "The supplied weights and declared sampling design are valid for the full original sample.",
            "Out-of-domain records are retained as zero contributors for domain variance estimation.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"],
            "estimand": estimand,
            "design": design,
            "outcome_variable": outcome_variable,
            "weight_variable": weight_variable,
            "domain_variable": domain_variable,
            "domain_value": str(domain_value),
            "strata_variable": strata_variable,
            "cluster_variable": cluster_variable,
        },
    )



def run_two_stage_ppswor_total_service(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_inclusion_probability_variable: str,
    ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a two-stage PPSWOR total with explicit stage-specific design inputs."""
    from timan_intelligence.core.two_stage_ppswor import (
        estimate_two_stage_ppswor_total,
    )

    output = estimate_two_stage_ppswor_total(
        df,
        outcome_variable,
        psu_variable,
        ssu_variable,
        psu_inclusion_probability_variable,
        ssu_population_count_variable,
        joint_psu_inclusion_probabilities,
        strata_variable,
        confidence_level,
    )
    return AnalysisResult(
        title=f"Two-stage PPSWOR total: {outcome_variable}",
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "psu_details": output["psu_details"],
            "pairwise_variance": output["pairwise_variance"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "PSUs are selected by fixed-size PPS without replacement within each stratum.",
            "Actual first- and second-order PSU inclusion probabilities are supplied from the sampling design.",
            "SSUs are selected by SRSWOR within each sampled PSU.",
            "Each row represents one sampled SSU with its fully observed outcome total.",
            "The declared SSU population count is correct and constant within each PSU.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"],
            "estimate": output["estimate"],
            "variance": output["variance"],
            "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )



def _two_stage_ppswor_estimand_result(output: dict[str, Any], title: str) -> AnalysisResult:
    """Wrap a two-stage PPSWOR estimand in the shared result contract."""
    return AnalysisResult(
        title=title,
        method=output["metadata"]["estimator"],
        status="success",
        tables={
            "stratum_estimates": output["strata"],
            "psu_details": output["psu_details"],
            "pairwise_variance": output["pairwise_variance"],
        },
        findings=list(output["findings"]),
        assumptions=[
            "PSUs are selected by fixed-size PPS without replacement within each stratum.",
            "Actual first- and second-order PSU inclusion probabilities are supplied from the sampling design.",
            "SSUs are selected by SRSWOR within each sampled PSU.",
            "Known population SSU denominators, where required, refer to the same target population and reference period.",
        ],
        limitations=list(output["warnings"]),
        metadata={
            **output["metadata"],
            "estimate": output["estimate"],
            "variance": output["variance"],
            "standard_error": output["standard_error"],
            "confidence_interval": output["confidence_interval"],
            "confidence_level": output["confidence_level"],
        },
    )


def run_two_stage_ppswor_mean_service(
    df: pd.DataFrame,
    outcome_variable: str,
    population_ssu_total: float,
    psu_variable: str,
    ssu_variable: str,
    psu_inclusion_probability_variable: str,
    ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a two-stage PPSWOR population mean with a known SSU denominator."""
    from timan_intelligence.core.two_stage_ppswor_estimands import (
        estimate_two_stage_ppswor_mean,
    )

    output = estimate_two_stage_ppswor_mean(
        df, outcome_variable, population_ssu_total, psu_variable,
        ssu_variable, psu_inclusion_probability_variable,
        ssu_population_count_variable, joint_psu_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    return _two_stage_ppswor_estimand_result(
        output, f"Two-stage PPSWOR mean: {outcome_variable}"
    )


def run_two_stage_ppswor_proportion_service(
    df: pd.DataFrame,
    outcome_variable: str,
    population_ssu_total: float,
    psu_variable: str,
    ssu_variable: str,
    psu_inclusion_probability_variable: str,
    ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a two-stage PPSWOR population proportion from a binary SSU outcome."""
    from timan_intelligence.core.two_stage_ppswor_estimands import (
        estimate_two_stage_ppswor_proportion,
    )

    output = estimate_two_stage_ppswor_proportion(
        df, outcome_variable, population_ssu_total, psu_variable,
        ssu_variable, psu_inclusion_probability_variable,
        ssu_population_count_variable, joint_psu_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    return _two_stage_ppswor_estimand_result(
        output, f"Two-stage PPSWOR proportion: {outcome_variable}"
    )


def run_two_stage_ppswor_domain_total_service(
    df: pd.DataFrame,
    outcome_variable: str,
    domain_variable: str,
    domain_value: Any,
    psu_variable: str,
    ssu_variable: str,
    psu_inclusion_probability_variable: str,
    ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a two-stage PPSWOR domain total without dropping out-of-domain units."""
    from timan_intelligence.core.two_stage_ppswor_estimands import (
        estimate_two_stage_ppswor_domain_total,
    )

    output = estimate_two_stage_ppswor_domain_total(
        df, outcome_variable, domain_variable, domain_value, psu_variable,
        ssu_variable, psu_inclusion_probability_variable,
        ssu_population_count_variable, joint_psu_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    return _two_stage_ppswor_estimand_result(
        output, f"Two-stage PPSWOR domain total: {domain_variable}={domain_value}"
    )


def run_two_stage_ppswor_domain_mean_service(
    df: pd.DataFrame, outcome_variable: str, domain_variable: str,
    domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_inclusion_probability_variable: str, ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a Taylor-linearised two-stage PPSWOR domain mean."""
    from timan_intelligence.core.two_stage_ppswor_estimands import estimate_two_stage_ppswor_domain_mean
    output = estimate_two_stage_ppswor_domain_mean(
        df, outcome_variable, domain_variable, domain_value, psu_variable,
        ssu_variable, psu_inclusion_probability_variable, ssu_population_count_variable,
        joint_psu_inclusion_probabilities, strata_variable, confidence_level,
    )
    return _two_stage_ppswor_estimand_result(
        output, f"Two-stage PPSWOR domain mean: {domain_variable}={domain_value}"
    )


def run_two_stage_ppswor_domain_proportion_service(
    df: pd.DataFrame, outcome_variable: str, domain_variable: str,
    domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_inclusion_probability_variable: str, ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a Taylor-linearised two-stage PPSWOR domain proportion."""
    from timan_intelligence.core.two_stage_ppswor_estimands import estimate_two_stage_ppswor_domain_proportion
    output = estimate_two_stage_ppswor_domain_proportion(
        df, outcome_variable, domain_variable, domain_value, psu_variable,
        ssu_variable, psu_inclusion_probability_variable, ssu_population_count_variable,
        joint_psu_inclusion_probabilities, strata_variable, confidence_level,
    )
    return _two_stage_ppswor_estimand_result(
        output, f"Two-stage PPSWOR domain proportion: {domain_variable}={domain_value}"
    )



def run_one_sample_t_test_service(
    df: pd.DataFrame,
    variable: str,
    reference_value: float,
    alternative: str = "two-sided",
) -> AnalysisResult:
    """Run a one-sample Student's t-test through the shared analysis service."""
    from timan_intelligence.core.statistical_engine import run_one_sample_t_test

    return run_one_sample_t_test(df, variable, reference_value, alternative)

def run_mean_confidence_interval_service(
    df: pd.DataFrame,
    variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a shared model-based confidence interval for a numeric mean."""
    from timan_intelligence.core.statistical_engine import run_mean_confidence_interval

    return run_mean_confidence_interval(df, variable, confidence_level)


def run_proportion_confidence_interval_service(
    df: pd.DataFrame,
    variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a Wilson score confidence interval for a binary proportion."""
    from timan_intelligence.core.statistical_engine import run_proportion_confidence_interval

    return run_proportion_confidence_interval(df, variable, confidence_level)



def run_paired_mean_difference_confidence_interval_service(
    df: pd.DataFrame,
    before_variable: str,
    after_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a paired Student-t confidence interval for mean change."""
    from timan_intelligence.core.statistical_engine import run_paired_mean_difference_confidence_interval

    return run_paired_mean_difference_confidence_interval(
        df, before_variable, after_variable, confidence_level
    )

def run_welch_mean_difference_confidence_interval_service(
    df: pd.DataFrame,
    outcome_variable: str,
    group_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Run a Welch-Satterthwaite interval for two independent group means."""
    from timan_intelligence.core.statistical_engine import run_welch_mean_difference_confidence_interval

    return run_welch_mean_difference_confidence_interval(
        df, outcome_variable, group_variable, confidence_level
    )


def run_paired_samples_t_test_service(
    df: pd.DataFrame, before_variable: str, after_variable: str,
    confidence_level: float = 0.95, alternative: str = "two-sided",
) -> AnalysisResult:
    """Run a paired-samples Student-t test through the shared analysis service."""
    from timan_intelligence.core.statistical_engine import run_paired_samples_t_test
    return run_paired_samples_t_test(df, before_variable, after_variable, confidence_level, alternative)


def run_chi_square_test_of_independence_service(df: pd.DataFrame, row_variable: str, column_variable: str) -> AnalysisResult:
    """Run Pearson's chi-square test through the shared analysis service."""
    from timan_intelligence.core.statistical_engine import run_chi_square_test_of_independence
    return run_chi_square_test_of_independence(df, row_variable, column_variable)


def run_fisher_exact_test_service(df: pd.DataFrame, row_variable: str, column_variable: str, alternative: str = "two-sided") -> AnalysisResult:
    """Run Fisher's exact test through the shared analysis service."""
    from timan_intelligence.core.statistical_engine import run_fisher_exact_test
    return run_fisher_exact_test(df, row_variable, column_variable, alternative)



def run_two_independent_proportions_test_service(df: pd.DataFrame, outcome_variable: str, group_variable: str, confidence_level: float = 0.95, alternative: str = "two-sided") -> AnalysisResult:
    """Compare two independent proportions through the shared analysis service."""
    from timan_intelligence.core.statistical_engine import run_two_independent_proportions_test
    return run_two_independent_proportions_test(df, outcome_variable, group_variable, confidence_level, alternative)

def run_one_sample_binomial_test_service(df: pd.DataFrame, variable: str, reference_proportion: float, alternative: str = "two-sided", confidence_level: float = 0.95) -> AnalysisResult:
    """Run an exact one-sample binomial test through the shared service."""
    from timan_intelligence.core.statistical_engine import run_one_sample_binomial_test
    return run_one_sample_binomial_test(df, variable, reference_proportion, alternative, confidence_level)
