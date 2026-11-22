
"""Safe, deterministic statistical calculations for TimanStat.

This execution engine provides descriptive statistics and selected
inferential statistical tests. It does not execute arbitrary code
or make automatic scientific decisions.
"""

from typing import Any

import pandas as pd
from scipy.stats import f_oneway, ttest_ind

from timan_intelligence.core.contracts import AnalysisResult



def run_chi_square_test_of_independence(df: pd.DataFrame, row_variable: str, column_variable: str) -> AnalysisResult:
    """Test association between two categorical variables using Pearson's chi-square test."""
    from scipy.stats import chi2_contingency
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    for variable, label in ((row_variable, "first"), (column_variable, "second")):
        if not isinstance(variable, str) or variable not in df.columns:
            raise ValueError(f"Select a valid {label} categorical variable.")
        if pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError("Both variables must be categorical. Recode numeric category codes as categorical variables before testing.")
    if row_variable == column_variable:
        raise ValueError("Choose two different categorical variables.")
    pair = df[[row_variable, column_variable]]
    complete = pair.dropna()
    excluded = int(len(pair) - len(complete))
    if complete.empty:
        raise ValueError("No complete observations remain for the contingency table.")
    observed = pd.crosstab(complete[row_variable], complete[column_variable])
    observed = observed.loc[observed.sum(axis=1) > 0, observed.sum(axis=0) > 0]
    if observed.shape[0] < 2 or observed.shape[1] < 2:
        raise ValueError("The chi-square test requires at least two observed categories in each variable.")
    statistic, p_value, dfree, expected_values = chi2_contingency(observed.to_numpy(), correction=False)
    expected = pd.DataFrame(expected_values, index=observed.index, columns=observed.columns)
    n = int(observed.to_numpy().sum())
    minimum_expected = float(expected_values.min())
    small = int((expected_values < 5).sum())
    cells = int(expected_values.size)
    r, k = observed.shape
    cramers_v = float((statistic / (n * min(r - 1, k - 1))) ** 0.5)
    residuals = (observed - expected) / expected.pow(0.5)
    summary = pd.DataFrame([{"Chi-square statistic": float(statistic), "Degrees of freedom": int(dfree),
        "p-value": float(p_value), "Cramer's V": cramers_v, "Complete observations": n,
        "Excluded missing pairs": excluded, "Minimum expected count": minimum_expected,
        "Expected cells below 5": small, "Expected cell count": cells}])
    findings = [f"Pearson chi-square statistic is {statistic:.4g} with {dfree} degrees of freedom (p = {p_value:.4g}).",
        f"Cramer's V is {cramers_v:.4g}; interpret its magnitude in the context of the table and subject matter.",
        f"The table contains {n:,} complete observations across {r} by {k} categories."]
    limitations = [
        "The ordinary Pearson chi-square test assumes independent observational units and is not adjusted for survey weights, clustering, stratification or finite-population corrections.",
        "The test identifies evidence of association, not causation or the direction of a relationship.",
        "Cramer's V is an uncorrected effect-size estimate; interpret it in context."]
    if small:
        limitations.append(f"{small} of {cells} expected cells ({small / cells:.1%}) are below 5; the asymptotic chi-square approximation may be unreliable.")
    if minimum_expected < 1:
        limitations.append("At least one expected cell count is below 1; do not rely on the asymptotic p-value. Consider an appropriate exact or Monte Carlo procedure.")
    if excluded:
        limitations.append(f"{excluded:,} rows with missing values in either variable were excluded using complete-case analysis.")
    return AnalysisResult(title=f"Chi-square test of independence: {row_variable} × {column_variable}",
        method="Pearson chi-square test of independence", status="success",
        tables={"contingency_table": observed.reset_index(), "expected_counts": expected.reset_index(),
            "pearson_residuals": residuals.reset_index(), "test_summary": summary},
        findings=findings, assumptions=["Both variables are categorical with mutually exclusive categories.",
            "Each observational unit contributes to exactly one cell.",
            "Observations are independent under the ordinary Pearson chi-square model.",
            "Expected cell counts are adequate for the asymptotic chi-square approximation."],
        limitations=limitations, metadata={"row_variable": row_variable, "column_variable": column_variable,
            "chi_square": float(statistic), "degrees_of_freedom": int(dfree), "p_value": float(p_value),
            "cramers_v": cramers_v, "n_observations": n, "missing_pairs_excluded": excluded,
            "minimum_expected_count": minimum_expected, "expected_cells_below_5": small,
            "expected_cell_count": cells, "sampling_design_aware": False,
            "study_design": "independent_observations", "continuity_correction": False})


def run_descriptive_statistics(
    df: pd.DataFrame,
    variable: str,
) -> AnalysisResult:
    """Calculate descriptive statistics for one numeric variable.

    Missing and infinite values are excluded from calculations and
    counted separately. The original DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("Provide a valid variable name.")

    if variable not in df.columns:
        raise ValueError(
            f"Variable '{variable}' was not found in the dataset."
        )

    series = df[variable]

    if series.isna().all():
        raise ValueError(
            f"Variable '{variable}' contains no usable numeric observations."
        )

    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError(
            f"Variable '{variable}' must be numeric."
        )

    missing_values = int(series.isna().sum())

    non_missing = series.dropna().astype(float)
    infinite_mask = non_missing.isin(
        [float("inf"), float("-inf")]
    )
    infinite_values = int(infinite_mask.sum())

    values = non_missing[~infinite_mask]

    if values.empty:
        raise ValueError(
            f"Variable '{variable}' contains no usable numeric observations."
        )

    observations = int(values.count())
    mean = float(values.mean())
    median = float(values.median())

    standard_deviation = (
        float(values.std(ddof=1))
        if observations > 1
        else None
    )

    summary: dict[str, Any] = {
        "variable": variable,
        "observations": observations,
        "missing_values": missing_values,
        "infinite_values": infinite_values,
        "mean": mean,
        "median": median,
        "standard_deviation": standard_deviation,
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "q1": float(values.quantile(0.25)),
        "q3": float(values.quantile(0.75)),
    }

    assumptions = [
        "Missing values were excluded from the calculations.",
        "Infinite values were excluded from the calculations.",
        "The standard deviation is the sample standard deviation.",
        "Descriptive statistics do not establish causation.",
    ]

    limitations = []

    if infinite_values > 0:
        limitations.append(
            f"{infinite_values} infinite value(s) were excluded "
            "from the calculations."
        )

    if observations == 1:
        limitations.append(
            "Only one usable observation is available; "
            "sample standard deviation cannot be calculated."
        )

    findings = [
        f"{variable} has {observations} usable numeric observations.",
        f"The mean is {mean:.4g} and the median is {median:.4g}.",
    ]

    if infinite_values > 0:
        findings.append(
            f"{infinite_values} infinite value(s) were excluded."
        )

    return AnalysisResult(
        title=f"Descriptive statistics: {variable}",
        method="Descriptive statistics",
        status="success",
        tables={"summary": summary},
        findings=findings,
        assumptions=assumptions,
        limitations=limitations,
        metadata={
            "variable": variable,
            "observations": observations,
            "missing_values": missing_values,
            "infinite_values": infinite_values,
        },
    )


def run_independent_samples_t_test(
    df: pd.DataFrame,
    outcome_variable: str,
    group_variable: str,
) -> AnalysisResult:
    """Run Welch's independent-samples t-test.

    Compares the means of a numeric outcome between exactly two
    independent groups without assuming equal population variances.

    Missing and infinite outcome values are excluded and counted.
    The original DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if outcome_variable not in df.columns:
        raise ValueError(
            f"Outcome variable '{outcome_variable}' was not found."
        )

    if group_variable not in df.columns:
        raise ValueError(
            f"Group variable '{group_variable}' was not found."
        )

    outcome = df[outcome_variable]
    groups = df[group_variable]

    if not pd.api.types.is_numeric_dtype(outcome):
        raise TypeError(
            f"Outcome variable '{outcome_variable}' must be numeric."
        )

    if groups.isna().any():
        raise ValueError(
            f"Group variable '{group_variable}' contains missing group labels."
        )

    unique_groups = list(pd.unique(groups))

    if len(unique_groups) != 2:
        raise ValueError(
            "Welch's t-test requires exactly two groups."
        )

    missing_outcomes = int(outcome.isna().sum())

    non_missing = outcome.dropna().astype(float)

    infinite_mask = non_missing.isin(
        [float("inf"), float("-inf")]
    )
    infinite_outcomes = int(infinite_mask.sum())

    finite_mask = outcome.notna() & ~outcome.isin(
        [float("inf"), float("-inf")]
    )

    valid_data = df.loc[finite_mask, [group_variable, outcome_variable]]

    group_1_label, group_2_label = unique_groups

    group_1 = valid_data.loc[
        valid_data[group_variable] == group_1_label,
        outcome_variable,
    ].astype(float)

    group_2 = valid_data.loc[
        valid_data[group_variable] == group_2_label,
        outcome_variable,
    ].astype(float)

    group_1_n = int(group_1.count())
    group_2_n = int(group_2.count())

    if group_1_n < 2 or group_2_n < 2:
        raise ValueError(
            "Welch's t-test requires at least two usable observations "
            "in each group."
        )

    group_1_mean = float(group_1.mean())
    group_2_mean = float(group_2.mean())

    group_1_variance = float(group_1.var(ddof=1))
    group_2_variance = float(group_2.var(ddof=1))

    group_1_component = group_1_variance / group_1_n
    group_2_component = group_2_variance / group_2_n

    standard_error_squared = (
        group_1_component + group_2_component
    )

    if standard_error_squared == 0:
        if group_1_mean == group_2_mean:
            t_statistic = 0.0
            p_value = 1.0
            degrees_of_freedom = float("inf")
        else:
            raise ValueError(
                "Welch's t-test cannot calculate a finite test statistic "
                "when both groups have zero variance and different means."
            )
    else:
        test_result = ttest_ind(
            group_1,
            group_2,
            equal_var=False,
            nan_policy="raise",
        )

        t_statistic = float(test_result.statistic)
        p_value = float(test_result.pvalue)

        denominator = (
            (group_1_component ** 2) / (group_1_n - 1)
            + (group_2_component ** 2) / (group_2_n - 1)
        )

        degrees_of_freedom = (
            float("inf")
            if denominator == 0
            else float((standard_error_squared ** 2) / denominator)
        )

    summary: dict[str, Any] = {
        "group_1_n": group_1_n,
        "group_2_n": group_2_n,
        "group_1_mean": group_1_mean,
        "group_2_mean": group_2_mean,
        "t_statistic": t_statistic,
        "p_value": p_value,
        "degrees_of_freedom": degrees_of_freedom,
        "missing_outcomes": missing_outcomes,
        "infinite_outcomes": infinite_outcomes,
    }

    assumptions = [
        "The two groups are independent.",
        "The outcome variable is numeric.",
        "Observations are independent within and between groups.",
        "Welch's t-test does not assume equal population variances.",
        "Missing outcome values were excluded.",
        "Infinite outcome values were excluded.",
        "The test evaluates a difference between group means.",
    ]

    limitations = []

    if missing_outcomes > 0:
        limitations.append(
            f"{missing_outcomes} missing outcome value(s) were excluded."
        )

    if infinite_outcomes > 0:
        limitations.append(
            f"{infinite_outcomes} infinite outcome value(s) were excluded."
        )

    findings = [
        (
            f"Group {group_1_label} has {group_1_n} usable observations "
            f"and a mean of {group_1_mean:.4g}."
        ),
        (
            f"Group {group_2_label} has {group_2_n} usable observations "
            f"and a mean of {group_2_mean:.4g}."
        ),
        (
            f"Welch's t-statistic is {t_statistic:.4g}, "
            f"with p-value {p_value:.4g}."
        ),
    ]

    if p_value < 0.05:
        findings.append(
            "The result is statistically significant at the 0.05 level."
        )
    else:
        findings.append(
            "The result is not statistically significant at the 0.05 level."
        )

    return AnalysisResult(
        title=(
            f"Welch's t-test: {outcome_variable} by {group_variable}"
        ),
        method="Welch's independent-samples t-test",
        status="success",
        tables={"summary": summary},
        findings=findings,
        assumptions=assumptions,
        limitations=limitations,
        metadata={
            "outcome_variable": outcome_variable,
            "group_variable": group_variable,
            "group_1_label": str(group_1_label),
            "group_2_label": str(group_2_label),
        },
    )


def run_one_way_anova(
    df: pd.DataFrame,
    outcome_variable: str,
    group_variable: str,
) -> AnalysisResult:
    """Run a one-way independent-groups ANOVA.

    Compares the means of a numeric outcome across two or more
    independent groups.

    Missing and infinite outcome values are excluded and counted.
    Each group must have at least two usable observations.
    The original DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if outcome_variable not in df.columns:
        raise ValueError(
            f"Outcome variable '{outcome_variable}' was not found."
        )

    if group_variable not in df.columns:
        raise ValueError(
            f"Group variable '{group_variable}' was not found."
        )

    outcome = df[outcome_variable]
    groups = df[group_variable]

    if not pd.api.types.is_numeric_dtype(outcome):
        raise TypeError(
            f"Outcome variable '{outcome_variable}' must be numeric."
        )

    if groups.isna().any():
        raise ValueError(
            f"Group variable '{group_variable}' contains missing group labels."
        )

    missing_outcomes = int(outcome.isna().sum())

    non_missing = outcome.dropna().astype(float)
    infinite_mask = non_missing.isin(
        [float("inf"), float("-inf")]
    )
    infinite_outcomes = int(infinite_mask.sum())

    finite_mask = outcome.notna() & ~outcome.isin(
        [float("inf"), float("-inf")]
    )

    valid_data = df.loc[
        finite_mask,
        [group_variable, outcome_variable],
    ].copy()

    unique_groups = list(pd.unique(valid_data[group_variable]))

    if len(unique_groups) < 2:
        raise ValueError(
            "One-way ANOVA requires at least two groups."
        )

    group_values = []

    for group_label in unique_groups:
        values = valid_data.loc[
            valid_data[group_variable] == group_label,
            outcome_variable,
        ].astype(float)

        if len(values) < 2:
            raise ValueError(
                "One-way ANOVA requires at least two usable observations "
                "in each group."
            )

        group_values.append(values)

    observations = int(sum(len(values) for values in group_values))
    number_of_groups = len(group_values)

    test_result = f_oneway(*group_values)

    f_statistic = float(test_result.statistic)
    p_value = float(test_result.pvalue)

    degrees_of_freedom_between = number_of_groups - 1
    degrees_of_freedom_within = observations - number_of_groups

    summary: dict[str, Any] = {
        "groups": number_of_groups,
        "observations": observations,
        "f_statistic": f_statistic,
        "p_value": p_value,
        "degrees_of_freedom_between": degrees_of_freedom_between,
        "degrees_of_freedom_within": degrees_of_freedom_within,
        "missing_outcomes": missing_outcomes,
        "infinite_outcomes": infinite_outcomes,
    }

    assumptions = [
        "The outcome variable is numeric.",
        "The groups are independent.",
        "Observations are independent within and between groups.",
        "The outcome is approximately normally distributed within each group.",
        "Population variances are assumed to be approximately equal.",
        "Missing outcome values were excluded.",
        "Infinite outcome values were excluded.",
        "The test evaluates whether all group population means are equal.",
    ]

    limitations = []

    if missing_outcomes > 0:
        limitations.append(
            f"{missing_outcomes} missing outcome value(s) were excluded."
        )

    if infinite_outcomes > 0:
        limitations.append(
            f"{infinite_outcomes} infinite outcome value(s) were excluded."
        )

    findings = [
        (
            f"One-way ANOVA compared {number_of_groups} groups "
            f"using {observations} usable observations."
        ),
        (
            f"The F-statistic is {f_statistic:.4g}, "
            f"with p-value {p_value:.4g}."
        ),
    ]

    if p_value < 0.05:
        findings.append(
            "There is evidence of a statistically significant difference "
            "among the group means at the 0.05 level."
        )
    else:
        findings.append(
            "There is insufficient evidence of a statistically significant "
            "difference among the group means at the 0.05 level."
        )

    findings.append(
        "A significant ANOVA result does not identify which specific "
        "groups differ; post-hoc comparisons are needed for that."
    )

    return AnalysisResult(
        title=(
            f"One-way ANOVA: {outcome_variable} by {group_variable}"
        ),
        method="One-way ANOVA",
        status="success",
        tables={"summary": summary},
        findings=findings,
        assumptions=assumptions,
        limitations=limitations,
        metadata={
            "outcome_variable": outcome_variable,
            "group_variable": group_variable,
            "group_labels": [str(label) for label in unique_groups],
        },
    )


def run_mean_confidence_interval(
    df: pd.DataFrame,
    variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate a mean and Student-t confidence interval for IID observations.

    This is a model-based interval for independent observations. It is not
    design-adjusted and must not be used as a substitute for survey estimation.
    """
    from scipy.stats import t

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("Provide a valid numeric variable name.")
    if variable not in df.columns:
        raise ValueError(f"Variable '{variable}' was not found in the dataset.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")
    series = df[variable]
    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError(f"Variable '{variable}' must be numeric.")

    values = series.dropna().astype(float)
    finite = values[pd.Series(values).map(lambda value: pd.notna(value) and abs(value) != float("inf")).to_numpy()]
    missing_count = int(series.isna().sum())
    infinite_count = int((values.abs() == float("inf")).sum())
    n = int(len(finite))
    if n < 2:
        raise ValueError("A mean confidence interval requires at least two finite observations.")
    mean = float(finite.mean())
    standard_deviation = float(finite.std(ddof=1))
    standard_error = standard_deviation / (n ** 0.5)
    degrees_of_freedom = n - 1
    critical_value = float(t.ppf(0.5 + float(confidence_level) / 2.0, degrees_of_freedom))
    margin = critical_value * standard_error
    lower, upper = mean - margin, mean + margin

    findings = [
        f"Estimated mean of {variable}: {mean:,.6g}.",
        f"Standard error: {standard_error:,.6g} based on {n:,} usable observations.",
        f"{float(confidence_level):.1%} Student-t confidence interval: [{lower:,.6g}, {upper:,.6g}].",
    ]
    limitations = [
        "This interval assumes independent observations from a common population; it does not account for clustering, stratification, unequal survey weights or finite-population corrections.",
        "The interval is model-based. For complex survey samples, use the relevant design-aware estimator in Survey Analysis.",
    ]
    if missing_count:
        limitations.append(f"{missing_count:,} missing observation(s) were excluded.")
    if infinite_count:
        limitations.append(f"{infinite_count:,} infinite observation(s) were excluded.")

    return AnalysisResult(
        title=f"Confidence interval for mean: {variable}",
        method="One-sample Student-t confidence interval",
        status="success",
        tables={
            "estimate": pd.DataFrame([{
                "Variable": variable,
                "Observations": n,
                "Mean": mean,
                "Standard deviation": standard_deviation,
                "Standard error": standard_error,
                "Degrees of freedom": degrees_of_freedom,
                "Confidence level": float(confidence_level),
                "Lower confidence limit": lower,
                "Upper confidence limit": upper,
            }])
        },
        findings=findings,
        assumptions=[
            "The outcome is numeric and measured on a meaningful scale.",
            "Observations are independent and arise from the target population under the stated model.",
            "The Student-t interval is appropriate; with small samples, the population distribution should not be severely non-normal or dominated by influential outliers.",
            "Missing and infinite observations are excluded and reported.",
        ],
        limitations=limitations,
        metadata={
            "variable": variable,
            "estimate": mean,
            "standard_deviation": standard_deviation,
            "standard_error": standard_error,
            "degrees_of_freedom": degrees_of_freedom,
            "confidence_level": float(confidence_level),
            "confidence_interval": (float(lower), float(upper)),
            "observations": n,
            "missing_values": missing_count,
            "infinite_values": infinite_count,
            "sampling_design_aware": False,
            "inference_framework": "iid_model_based",
        },
    )


def run_one_sample_t_test(
    df: pd.DataFrame,
    variable: str,
    reference_value: float,
    alternative: str = "two-sided",
) -> AnalysisResult:
    """Test a numeric population mean against a fixed reference under IID assumptions."""
    from scipy.stats import t

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("Provide a valid numeric variable name.")
    if variable not in df.columns:
        raise ValueError(f"Variable '{variable}' was not found in the dataset.")
    if isinstance(reference_value, bool) or not isinstance(reference_value, (int, float)):
        raise TypeError("Reference value must be numeric.")
    reference_value = float(reference_value)
    if not pd.notna(reference_value) or abs(reference_value) == float("inf"):
        raise ValueError("Reference value must be finite.")
    if alternative not in {"two-sided", "less", "greater"}:
        raise ValueError("Alternative must be 'two-sided', 'less' or 'greater'.")
    series = df[variable]
    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError(f"Variable '{variable}' must be numeric.")
    observed = series.dropna().astype(float)
    finite = observed[observed.map(lambda value: pd.notna(value) and abs(value) != float("inf"))]
    missing_count = int(series.isna().sum())
    infinite_count = int((observed.abs() == float("inf")).sum())
    n = int(len(finite))
    if n < 2:
        raise ValueError("A one-sample t-test requires at least two finite observations.")
    mean = float(finite.mean())
    sd = float(finite.std(ddof=1))
    if sd == 0:
        difference = mean - reference_value
        if difference == 0:
            raise ValueError("The t statistic is undefined when all observations equal the reference value.")
        statistic = float("inf") if difference > 0 else float("-inf")
        p_value = 0.0 if ((alternative == "greater" and difference > 0) or (alternative == "less" and difference < 0) or alternative == "two-sided") else 1.0
        standard_error = 0.0
    else:
        standard_error = sd / (n ** 0.5)
        statistic = (mean - reference_value) / standard_error
        if alternative == "two-sided":
            p_value = float(2.0 * t.sf(abs(statistic), n - 1))
        elif alternative == "greater":
            p_value = float(t.sf(statistic, n - 1))
        else:
            p_value = float(t.cdf(statistic, n - 1))
    degrees_of_freedom = n - 1
    confidence_level = 0.95
    critical = float(t.ppf(0.975, degrees_of_freedom))
    lower = mean - critical * standard_error
    upper = mean + critical * standard_error
    findings = [
        f"Sample mean of {variable}: {mean:,.6g}; reference value: {reference_value:,.6g}.",
        f"Mean difference (sample minus reference): {mean - reference_value:,.6g}.",
        f"t({degrees_of_freedom}) = {statistic:,.4g}; {alternative} p-value = {p_value:.6g}.",
        f"95% confidence interval for the population mean: [{lower:,.6g}, {upper:,.6g}].",
    ]
    limitations = [
        "Assumes independent observations from a population for which the one-sample Student-t model is appropriate.",
        "Does not adjust for survey weights, clustering, stratification, repeated measures or finite-population corrections; use Survey Analysis for complex samples.",
    ]
    if missing_count:
        limitations.append(f"{missing_count:,} missing observation(s) were excluded.")
    if infinite_count:
        limitations.append(f"{infinite_count:,} infinite observation(s) were excluded.")
    return AnalysisResult(
        title=f"One-sample t-test: {variable}",
        method="One-sample Student's t-test",
        status="success",
        tables={"test": pd.DataFrame([{
            "Variable": variable, "Observations": n, "Sample mean": mean,
            "Reference value": reference_value, "Mean difference": mean - reference_value,
            "Standard deviation": sd, "Standard error": standard_error,
            "t statistic": statistic, "Degrees of freedom": degrees_of_freedom,
            "Alternative": alternative, "p-value": p_value,
            "Confidence level": confidence_level, "Lower confidence limit": lower,
            "Upper confidence limit": upper,
        }])},
        findings=findings,
        assumptions=[
            "The outcome is numeric and the reference value is specified before interpreting the test.",
            "Observations are independent and representative under the stated model.",
            "For small samples, the outcome distribution should not be severely non-normal or dominated by influential outliers.",
        ],
        limitations=limitations,
        metadata={
            "variable": variable, "reference_value": reference_value,
            "estimate": mean, "mean_difference": mean - reference_value,
            "standard_error": standard_error, "t_statistic": statistic,
            "degrees_of_freedom": degrees_of_freedom, "p_value": p_value,
            "alternative": alternative, "confidence_level": confidence_level,
            "confidence_interval": (float(lower), float(upper)),
            "observations": n, "missing_values": missing_count,
            "infinite_values": infinite_count, "sampling_design_aware": False,
            "inference_framework": "iid_one_sample_t",
        },
    )


def run_proportion_confidence_interval(
    df: pd.DataFrame,
    variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate a binary population proportion using a Wilson score interval.

    Missing values are excluded. The procedure assumes independent,
    identically distributed Bernoulli observations and is not survey-design
    adjusted.
    """
    from scipy.stats import norm

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("Provide a valid binary variable name.")
    if variable not in df.columns:
        raise ValueError(f"Variable '{variable}' was not found in the dataset.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")
    series = df[variable]
    observed_raw = series.dropna()
    if observed_raw.empty:
        raise ValueError("A proportion confidence interval requires at least one observed value.")
    if not pd.api.types.is_numeric_dtype(observed_raw):
        raise TypeError(f"Variable '{variable}' must be numeric and coded 0/1.")
    observed = observed_raw.astype(float)
    if not observed.isin([0.0, 1.0]).all():
        raise ValueError(f"Variable '{variable}' must contain only 0 and 1 (and optional missing values).")

    n = int(len(observed))
    successes = int(observed.sum())
    estimate = successes / n
    z = float(norm.ppf(0.5 + float(confidence_level) / 2.0))
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = (estimate + z2 / (2.0 * n)) / denominator
    half_width = (
        z
        * ((estimate * (1.0 - estimate) / n) + z2 / (4.0 * n * n)) ** 0.5
        / denominator
    )
    lower = max(0.0, centre - half_width)
    upper = min(1.0, centre + half_width)
    standard_error = (estimate * (1.0 - estimate) / n) ** 0.5
    missing_count = int(series.isna().sum())

    findings = [
        f"Estimated proportion of {variable}=1: {estimate:.4f} ({estimate:.1%}).",
        f"{successes:,} positive observations among {n:,} usable observations.",
        f"{float(confidence_level):.1%} Wilson score confidence interval: [{lower:.4f}, {upper:.4f}].",
    ]
    limitations = [
        "The Wilson interval assumes independent Bernoulli observations and does not adjust for clustering, stratification, unequal survey weights or finite-population corrections.",
        "For complex probability samples, use the design-aware proportion estimator in Survey Analysis.",
    ]
    if missing_count:
        limitations.append(f"{missing_count:,} missing observation(s) were excluded.")

    return AnalysisResult(
        title=f"Confidence interval for proportion: {variable}",
        method="Wilson score confidence interval for a proportion",
        status="success",
        tables={
            "estimate": pd.DataFrame([{
                "Variable": variable,
                "Positive observations": successes,
                "Observations": n,
                "Estimated proportion": estimate,
                "Estimated percentage": estimate * 100.0,
                "Standard error": standard_error,
                "Confidence level": float(confidence_level),
                "Lower confidence limit": lower,
                "Upper confidence limit": upper,
            }])
        },
        findings=findings,
        assumptions=[
            "The outcome is binary and coded 1 for the event of interest and 0 otherwise.",
            "Observations are independent and arise from a common Bernoulli population.",
            "The denominator includes all eligible non-missing observations.",
            "Missing outcomes are excluded and reported.",
        ],
        limitations=limitations,
        metadata={
            "variable": variable,
            "estimate": estimate,
            "successes": successes,
            "observations": n,
            "standard_error": standard_error,
            "confidence_level": float(confidence_level),
            "confidence_interval": (float(lower), float(upper)),
            "missing_values": missing_count,
            "sampling_design_aware": False,
            "inference_framework": "iid_wilson_score",
        },
    )



def run_paired_mean_difference_confidence_interval(
    df: pd.DataFrame,
    before_variable: str,
    after_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate the mean after-minus-before change for matched rows.

    Each row must represent one correctly matched pair. Rows with either
    measurement missing or infinite are excluded as incomplete pairs.
    """
    from scipy.stats import t

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if before_variable not in df.columns or after_variable not in df.columns:
        raise ValueError("Both before and after measurement variables must exist.")
    if before_variable == after_variable:
        raise ValueError("Before and after measurements must use different variables.")
    for variable in (before_variable, after_variable):
        if not pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError(f"Measurement variable '{variable}' must be numeric.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")

    before = df[before_variable].astype(float)
    after = df[after_variable].astype(float)
    finite_pair = (
        before.notna() & after.notna()
        & before.map(lambda x: abs(x) != float("inf"))
        & after.map(lambda x: abs(x) != float("inf"))
    )
    differences = after[finite_pair] - before[finite_pair]
    pair_count = int(differences.size)
    if pair_count < 2:
        raise ValueError("At least two complete finite matched pairs are required.")
    mean_change = float(differences.mean())
    sd_change = float(differences.std(ddof=1))
    if sd_change == 0:
        raise ValueError("A finite paired confidence interval cannot be calculated when all paired differences are identical.")
    standard_error = sd_change / (pair_count ** 0.5)
    degrees_freedom = pair_count - 1
    critical = float(t.ppf(0.5 + float(confidence_level) / 2.0, degrees_freedom))
    margin = critical * standard_error
    lower, upper = mean_change - margin, mean_change + margin
    incomplete_pairs = int((~finite_pair).sum())
    missing_pairs = int((before.isna() | after.isna()).sum())
    infinite_pairs = incomplete_pairs - missing_pairs

    summary = pd.DataFrame([{
        "Before variable": before_variable,
        "After variable": after_variable,
        "Complete pairs": pair_count,
        "Mean before": float(before[finite_pair].mean()),
        "Mean after": float(after[finite_pair].mean()),
        "Mean change (after - before)": mean_change,
        "Standard error": standard_error,
        "Degrees of freedom": degrees_freedom,
        "Confidence level": float(confidence_level),
        "CI lower": lower,
        "CI upper": upper,
        "Incomplete pairs excluded": incomplete_pairs,
    }])
    findings = [
        f"Mean within-pair change (after minus before) is {mean_change:.4g}.",
        f"{pair_count:,} complete matched pairs were analysed.",
        f"{float(confidence_level):.1%} paired t confidence interval: [{lower:.4g}, {upper:.4g}].",
    ]
    limitations = [
        "Each row is assumed to contain correctly matched before-and-after measurements from the same unit.",
        "Pair-level differences are assumed independent across rows; the interval is not adjusted for complex survey sampling or clustering.",
        "The Student-t interval relies on the distribution of paired differences being reasonably compatible with the model, especially for small samples.",
    ]
    if incomplete_pairs:
        limitations.append(f"{incomplete_pairs:,} incomplete or non-finite pair(s) were excluded ({missing_pairs:,} with missing measurements and {infinite_pairs:,} with infinite measurements).")

    return AnalysisResult(
        title=f"Paired mean change: {before_variable} to {after_variable}",
        method="Paired-samples Student-t confidence interval",
        status="success",
        tables={"summary": summary},
        findings=findings,
        assumptions=[
            "Each row represents one correctly matched pair.",
            "The analysis uses after minus before as the change convention.",
            "Pair-level differences are independent across rows.",
            "The paired differences are numeric and their distribution is assessed.",
        ],
        limitations=limitations,
        metadata={
            "before_variable": before_variable,
            "after_variable": after_variable,
            "estimate": mean_change,
            "standard_error": standard_error,
            "degrees_of_freedom": degrees_freedom,
            "confidence_level": float(confidence_level),
            "confidence_interval": (float(lower), float(upper)),
            "complete_pairs": pair_count,
            "incomplete_pairs": incomplete_pairs,
            "missing_pairs": missing_pairs,
            "infinite_pairs": infinite_pairs,
            "sampling_design_aware": False,
            "study_design": "paired",
        },
    )


def run_paired_samples_t_test(
    df: pd.DataFrame, before_variable: str, after_variable: str,
    confidence_level: float = 0.95, alternative: str = "two-sided",
) -> AnalysisResult:
    """Test the mean after-minus-before difference for correctly matched rows."""
    from scipy.stats import t
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if before_variable not in df.columns or after_variable not in df.columns:
        raise ValueError("Both before and after measurement variables must exist.")
    if before_variable == after_variable:
        raise ValueError("Before and after measurements must use different variables.")
    for variable in (before_variable, after_variable):
        if not pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError(f"Measurement variable '{variable}' must be numeric.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")
    if alternative not in {"two-sided", "greater", "less"}:
        raise ValueError("Alternative must be 'two-sided', 'greater' or 'less'.")
    before, after = df[before_variable].astype(float), df[after_variable].astype(float)
    finite_pair = before.notna() & after.notna() & before.map(lambda v: abs(v) != float("inf")) & after.map(lambda v: abs(v) != float("inf"))
    differences = after[finite_pair] - before[finite_pair]
    n = int(differences.size)
    if n < 2:
        raise ValueError("A paired-samples t-test requires at least two complete finite matched pairs.")
    mean_change = float(differences.mean())
    sd_change = float(differences.std(ddof=1))
    dfree = n - 1
    se = sd_change / (n ** 0.5)
    if se == 0:
        if mean_change == 0:
            raise ValueError("The paired t statistic is undefined when all paired differences are zero.")
        statistic = float("inf") if mean_change > 0 else float("-inf")
    else:
        statistic = mean_change / se
    if alternative == "two-sided":
        p_value = float(2 * t.sf(abs(statistic), dfree))
    elif alternative == "greater":
        p_value = float(t.sf(statistic, dfree))
    else:
        p_value = float(t.cdf(statistic, dfree))
    critical = float(t.ppf(0.5 + float(confidence_level) / 2, dfree))
    lower, upper = mean_change - critical * se, mean_change + critical * se
    missing_pairs = int((before.isna() | after.isna()).sum())
    incomplete_pairs = int((~finite_pair).sum())
    infinite_pairs = incomplete_pairs - missing_pairs
    summary = pd.DataFrame([{
        "Before variable": before_variable, "After variable": after_variable,
        "Complete pairs": n, "Mean before": float(before[finite_pair].mean()),
        "Mean after": float(after[finite_pair].mean()), "Mean change (after - before)": mean_change,
        "Standard error": se, "t statistic": statistic, "Degrees of freedom": dfree,
        "Alternative": alternative, "p-value": p_value, "Confidence level": float(confidence_level),
        "CI lower": lower, "CI upper": upper, "Incomplete pairs excluded": incomplete_pairs,
    }])
    findings = [
        f"Mean within-pair change (after minus before) is {mean_change:.4g}.",
        f"{n:,} complete matched pairs were analysed.",
        f"Paired t statistic: {statistic:.4g} with {dfree} degrees of freedom; p-value: {p_value:.4g}.",
        f"{float(confidence_level):.1%} two-sided confidence interval for mean change: [{lower:.4g}, {upper:.4g}].",
        "The result is statistically significant at the 0.05 level." if p_value < 0.05 else "The result is not statistically significant at the 0.05 level.",
    ]
    limitations = [
        "Each row is assumed to contain correctly matched before-and-after measurements from the same unit.",
        "Pair-level differences are assumed independent across rows; this test is not adjusted for complex survey sampling or clustering.",
        "The Student-t model applies to paired differences; inspect outliers and distributional shape, especially for small samples.",
        "The confidence interval is two-sided even when a one-sided alternative is selected for the p-value.",
    ]
    if incomplete_pairs:
        limitations.append(f"{incomplete_pairs:,} incomplete or non-finite pair(s) were excluded ({missing_pairs:,} with missing measurements and {infinite_pairs:,} with infinite measurements).")
    return AnalysisResult(
        title=f"Paired-samples t-test: {before_variable} to {after_variable}",
        method="Paired-samples Student's t-test", status="success",
        tables={"test": summary}, findings=findings, assumptions=[
            "Each row represents one correctly matched pair.",
            "The tested difference is after minus before.",
            "Pair-level differences are independent across pairs.",
            "The paired differences are numeric and their distribution is assessed.",
        ], limitations=limitations, metadata={
            "before_variable": before_variable, "after_variable": after_variable,
            "estimate": mean_change, "standard_error": se, "t_statistic": statistic,
            "degrees_of_freedom": dfree, "p_value": p_value, "alternative": alternative,
            "confidence_level": float(confidence_level), "confidence_interval": (float(lower), float(upper)),
            "complete_pairs": n, "incomplete_pairs": incomplete_pairs, "missing_pairs": missing_pairs,
            "infinite_pairs": infinite_pairs, "sampling_design_aware": False, "study_design": "paired",
        },
    )


def run_welch_mean_difference_confidence_interval(
    df: pd.DataFrame,
    outcome_variable: str,
    group_variable: str,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Estimate the difference between two independent means using Welch's t interval.

    The reported difference is mean(group 1) minus mean(group 2), where
    group order follows first appearance in the data. Assumes independent
    observations and does not adjust for complex survey designs.
    """
    from scipy.stats import t

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Both outcome and grouping variables must exist.")
    if outcome_variable == group_variable:
        raise ValueError("Outcome and grouping variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome variable must be numeric.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")

    groups = df[group_variable]
    if groups.isna().any():
        raise ValueError("The grouping variable contains missing group labels.")
    labels = list(pd.unique(groups))
    if len(labels) != 2:
        raise ValueError("A Welch mean-difference interval requires exactly two groups.")

    values = df[outcome_variable]
    finite_mask = values.notna() & values.map(lambda value: pd.notna(value) and abs(float(value)) != float("inf"))
    clean = df.loc[finite_mask, [group_variable, outcome_variable]]
    samples = [
        clean.loc[clean[group_variable] == label, outcome_variable].astype(float)
        for label in labels
    ]
    n1, n2 = (int(sample.size) for sample in samples)
    if n1 < 2 or n2 < 2:
        raise ValueError("At least two finite observations are required in each group.")

    mean1, mean2 = (float(sample.mean()) for sample in samples)
    var1, var2 = (float(sample.var(ddof=1)) for sample in samples)
    component1, component2 = var1 / n1, var2 / n2
    se_squared = component1 + component2
    difference = mean1 - mean2
    if se_squared == 0:
        raise ValueError("A finite Welch interval cannot be calculated when both groups have zero variance.")
    standard_error = se_squared ** 0.5
    df_denominator = component1 ** 2 / (n1 - 1) + component2 ** 2 / (n2 - 1)
    degrees_freedom = se_squared ** 2 / df_denominator
    critical = float(t.ppf(0.5 + float(confidence_level) / 2.0, degrees_freedom))
    margin = critical * standard_error
    lower, upper = difference - margin, difference + margin
    missing_count = int(values.isna().sum())
    infinite_count = int((values.notna() & ~finite_mask).sum())

    summary = pd.DataFrame([{
        "Group 1": str(labels[0]),
        "Group 2": str(labels[1]),
        "Group 1 n": n1,
        "Group 2 n": n2,
        "Group 1 mean": mean1,
        "Group 2 mean": mean2,
        "Mean difference (group 1 - group 2)": difference,
        "Standard error": standard_error,
        "Welch degrees of freedom": degrees_freedom,
        "Confidence level": float(confidence_level),
        "Lower confidence limit": lower,
        "Upper confidence limit": upper,
    }])
    limitations = [
        "Assumes independent observations within and between the two groups.",
        "Uses Welch-Satterthwaite degrees of freedom and does not assume equal population variances.",
        "Not adjusted for survey weights, clustering, stratification, repeated measures or finite-population corrections.",
    ]
    if missing_count:
        limitations.append(f"{missing_count} missing outcome value(s) were excluded.")
    if infinite_count:
        limitations.append(f"{infinite_count} infinite outcome value(s) were excluded.")

    return AnalysisResult(
        title=f"Welch confidence interval for mean difference: {outcome_variable}",
        method="Welch-Satterthwaite confidence interval for difference between two independent means",
        status="success",
        tables={"summary": summary},
        findings=[
            f"Mean difference (group {labels[0]} minus group {labels[1]}): {difference:.6g}.",
            f"Standard error: {standard_error:.6g}; Welch degrees of freedom: {degrees_freedom:.4g}.",
            f"{float(confidence_level):.1%} confidence interval: [{lower:.6g}, {upper:.6g}].",
        ],
        assumptions=[
            "The grouping variable identifies exactly two independent groups.",
            "The outcome is numeric and observations are independent.",
            "Welch-Satterthwaite approximation is appropriate for the mean difference.",
        ],
        limitations=limitations,
        metadata={
            "outcome_variable": outcome_variable,
            "group_variable": group_variable,
            "group_1_label": str(labels[0]),
            "group_2_label": str(labels[1]),
            "estimate": difference,
            "standard_error": standard_error,
            "degrees_of_freedom": degrees_freedom,
            "confidence_level": float(confidence_level),
            "confidence_interval": (float(lower), float(upper)),
            "missing_values": missing_count,
            "infinite_values": infinite_count,
            "sampling_design_aware": False,
        },
    )
