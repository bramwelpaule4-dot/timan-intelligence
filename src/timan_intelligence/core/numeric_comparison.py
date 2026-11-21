"""Reusable comparisons of a numeric outcome across independent groups."""

import numpy as np
import pandas as pd
from scipy import stats


def run_numeric_group_comparison(
    df: pd.DataFrame,
    group_variable: str,
    outcome_variable: str,
) -> dict:
    """Compare a numeric outcome across independent groups using Welch methods.

    Two groups use Welch's independent-samples t-test. Three or more groups
    use Welch's one-way ANOVA. Descriptive summaries remain available when
    inferential assumptions or minimum sample sizes are not met.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if group_variable == outcome_variable:
        raise ValueError("Select two different variables for this comparison.")
    missing_columns = [
        name for name in (group_variable, outcome_variable)
        if name not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"Variable(s) not found: {', '.join(missing_columns)}.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable].dtype):
        raise ValueError(
            "The outcome variable must be numeric. Confirm and convert text-coded "
            "numbers in data preparation before analysis."
        )

    group = df[group_variable].copy()
    if (
        pd.api.types.is_object_dtype(group.dtype)
        or pd.api.types.is_string_dtype(group.dtype)
    ):
        group = group.replace(r"^\\s*$", np.nan, regex=True)

    outcome = pd.to_numeric(df[outcome_variable], errors="coerce")
    outcome = outcome.where(np.isfinite(outcome), np.nan)
    valid = group.notna() & outcome.notna()
    analysis = pd.DataFrame({
        "group": group[valid],
        "outcome": outcome[valid],
    })
    total_records = int(len(df))
    valid_n = int(len(analysis))
    excluded_n = total_records - valid_n

    group_count = int(analysis["group"].nunique(dropna=True))
    if group_count > 50:
        raise ValueError(
            "The grouping variable has more than 50 observed categories. "
            "It may be an identifier or free-text field."
        )
    if group_count < 2:
        raise ValueError(
            "At least two groups with valid numeric observations are required."
        )

    summaries = []
    group_values = []
    for label, values in analysis.groupby("group", sort=False, observed=True)["outcome"]:
        values = values.astype(float)
        group_values.append((label, values))
        summaries.append({
            "Group": str(label),
            "Valid n": int(values.count()),
            "Mean": float(values.mean()),
            "Standard deviation": (
                float(values.std(ddof=1)) if values.count() > 1 else np.nan
            ),
            "Median": float(values.median()),
            "Q1": float(values.quantile(0.25)),
            "Q3": float(values.quantile(0.75)),
            "Minimum": float(values.min()),
            "Maximum": float(values.max()),
        })
    summary_table = pd.DataFrame(summaries)

    warnings = [
        "Welch procedures compare independent groups. Repeated measurements, "
        "matched observations, clustering and complex survey designs require "
        "a different analysis.",
        "The analysis uses unweighted complete records; it does not account "
        "for survey weights or complex sample design.",
        "Statistical significance does not establish causation or practical importance.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because the group or numeric "
            "outcome was missing, blank or non-finite."
        )

    test_name = "Not calculated"
    test_status = "descriptive_only"
    statistic = None
    p_value = None
    degrees_freedom = None
    confidence_interval = None
    mean_difference = None
    group_sizes_sufficient = all(len(values) >= 2 for _, values in group_values)

    if not group_sizes_sufficient:
        warnings.append(
            "At least one group has fewer than two valid observations. "
            "Descriptive summaries are shown, but inferential testing is withheld."
        )
    elif len(group_values) == 2:
        (label_a, values_a), (label_b, values_b) = group_values
        variance_a = float(values_a.var(ddof=1))
        variance_b = float(values_b.var(ddof=1))
        n_a, n_b = len(values_a), len(values_b)
        mean_difference = float(values_b.mean() - values_a.mean())
        component_a = variance_a / n_a
        component_b = variance_b / n_b
        standard_error = float(np.sqrt(component_a + component_b))

        if standard_error == 0:
            warnings.append(
                "Both groups have zero within-group variation. "
                "A Welch t-test cannot be calculated."
            )
        else:
            denominator = (
                (component_a ** 2) / (n_a - 1)
                + (component_b ** 2) / (n_b - 1)
            )
            degrees_freedom = float(
                ((component_a + component_b) ** 2) / denominator
            )
            statistic = float(mean_difference / standard_error)
            p_value = float(2 * stats.t.sf(abs(statistic), degrees_freedom))
            critical_value = float(
                stats.t.ppf(0.975, degrees_freedom)
            )
            confidence_interval = [
                float(mean_difference - critical_value * standard_error),
                float(mean_difference + critical_value * standard_error),
            ]
            test_name = "Welch's independent-samples t-test"
            test_status = "tested"
            warnings.append(
                f"The mean difference is calculated as {label_b} minus {label_a}; "
                "the 95% confidence interval uses Welch-Satterthwaite degrees of freedom."
            )
    else:
        sample_sizes = np.array([len(values) for _, values in group_values], dtype=float)
        means = np.array([values.mean() for _, values in group_values], dtype=float)
        variances = np.array([values.var(ddof=1) for _, values in group_values], dtype=float)

        if np.any(variances <= 0) or not np.all(np.isfinite(variances)):
            warnings.append(
                "Welch's ANOVA requires estimable, positive within-group variances "
                "in every group. Inferential testing is withheld."
            )
        else:
            weights = sample_sizes / variances
            weighted_mean = float(np.sum(weights * means) / np.sum(weights))
            numerator = float(
                np.sum(weights * (means - weighted_mean) ** 2)
                / (len(group_values) - 1)
            )
            correction_component = float(
                np.sum(
                    ((1 - weights / np.sum(weights)) ** 2)
                    / (sample_sizes - 1)
                )
            )
            correction = 1 + (
                2 * (len(group_values) - 2)
                / (len(group_values) ** 2 - 1)
            ) * correction_component
            denominator_df = float(
                (len(group_values) ** 2 - 1)
                / (3 * correction_component)
            ) if correction_component > 0 else np.inf
            statistic = float(numerator / correction)
            degrees_freedom = {
                "numerator": float(len(group_values) - 1),
                "denominator": denominator_df,
            }
            p_value = float(
                stats.f.sf(
                    statistic,
                    degrees_freedom["numerator"],
                    degrees_freedom["denominator"],
                )
            )
            test_name = "Welch's one-way ANOVA"
            test_status = "tested"
            warnings.append(
                "A significant omnibus result indicates that not all group means "
                "are equal. It does not identify which pairs differ; adjusted "
                "post-hoc comparisons are not included in this release."
            )

    findings = [
        f"Compared {len(group_values)} groups using {valid_n:,} complete records.",
        "Group summaries report the mean, standard deviation, median and interquartile range.",
    ]
    if test_status == "tested":
        findings.append(
            f"{test_name} returned p={p_value:.4g}."
        )

    return {
        "group_summaries": summary_table,
        "findings": findings,
        "warnings": warnings,
        "metadata": {
            "group_variable": group_variable,
            "outcome_variable": outcome_variable,
            "total_records": total_records,
            "valid_n": valid_n,
            "excluded_n": excluded_n,
            "group_count": len(group_values),
            "test": test_name,
            "test_status": test_status,
            "statistic": statistic,
            "p_value": p_value,
            "degrees_freedom": degrees_freedom,
            "mean_difference": mean_difference,
            "confidence_interval_95": confidence_interval,
            "group_labels": [str(label) for label, _ in group_values],
        },
    }
