"""Shared orchestration entry points used by the web and desktop interfaces."""

import pandas as pd
from timan_intelligence.core.poisson_regression import run_poisson_regression
from timan_intelligence.core.negative_binomial_regression import run_negative_binomial_regression

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
