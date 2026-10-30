
"""Safe, deterministic statistical calculations for TimanStat.

This execution engine provides descriptive statistics and selected
inferential statistical tests. It does not execute arbitrary code
or make automatic scientific decisions.
"""

from typing import Any

import pandas as pd
from scipy.stats import ttest_ind

from timan_intelligence.core.contracts import AnalysisResult


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
