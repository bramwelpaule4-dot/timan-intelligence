
"""Safe, deterministic statistical calculations for TimanStat.

This execution engine provides descriptive statistics and selected
inferential statistical tests. It does not execute arbitrary code
or make automatic scientific decisions.
"""

from typing import Any

import numpy as np
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



def run_fisher_exact_test(df: pd.DataFrame, row_variable: str, column_variable: str, alternative: str = "two-sided") -> AnalysisResult:
    """Run Fisher's exact test for association in a 2 by 2 table."""
    from scipy.stats import fisher_exact
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    for variable, label in ((row_variable, "first"), (column_variable, "second")):
        if not isinstance(variable, str) or variable not in df.columns:
            raise ValueError(f"Select a valid {label} categorical variable.")
        if pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError("Both variables must be categorical. Recode numeric category codes as categorical variables before testing.")
    if row_variable == column_variable:
        raise ValueError("Choose two different categorical variables.")
    if alternative not in {"two-sided", "less", "greater"}:
        raise ValueError("Alternative must be 'two-sided', 'less' or 'greater'.")
    pair = df[[row_variable, column_variable]]
    complete = pair.dropna()
    excluded = int(len(pair) - len(complete))
    if complete.empty:
        raise ValueError("No complete observations remain for the contingency table.")
    observed = pd.crosstab(complete[row_variable], complete[column_variable])
    observed = observed.loc[observed.sum(axis=1) > 0, observed.sum(axis=0) > 0]
    if observed.shape != (2, 2):
        raise ValueError("Fisher's exact test requires exactly two observed categories in each variable (a 2 by 2 table).")
    odds_ratio, p_value = fisher_exact(observed.to_numpy(), alternative=alternative)
    n = int(observed.to_numpy().sum())
    summary = pd.DataFrame([{"Odds ratio": float(odds_ratio), "Exact p-value": float(p_value),
        "Alternative hypothesis": alternative, "Complete observations": n, "Excluded missing pairs": excluded}])
    findings = [f"Fisher's exact test p-value is {p_value:.4g} ({alternative} alternative).",
        f"The sample odds ratio is {odds_ratio:.4g}; interpret it using the row and column category order shown in the table.",
        f"The 2 by 2 table contains {n:,} complete observations."]
    limitations = ["The standard Fisher exact test assumes independent observational units and does not adjust for survey weights, clustering, stratification or finite-population corrections.",
        "The odds ratio is a sample effect estimate; this implementation does not provide a confidence interval.",
        "The alternative hypothesis is interpreted relative to the row and column category ordering shown in the contingency table."]
    if excluded:
        limitations.append(f"{excluded:,} rows with missing values in either variable were excluded using complete-case analysis.")
    return AnalysisResult(title=f"Fisher's exact test: {row_variable} × {column_variable}", method="Fisher's exact test", status="success",
        tables={"contingency_table": observed.reset_index(), "test_summary": summary}, findings=findings,
        assumptions=["Both variables are categorical and each has exactly two observed categories.", "Each observational unit contributes to exactly one cell.", "Observations are independent under the applicable sampling model."],
        limitations=limitations, metadata={"row_variable": row_variable, "column_variable": column_variable,
        "odds_ratio": float(odds_ratio), "p_value": float(p_value), "alternative": alternative,
        "n_observations": n, "missing_pairs_excluded": excluded, "sampling_design_aware": False,
        "study_design": "independent_observations"})


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


def run_mann_whitney_u_test(
    df: pd.DataFrame,
    outcome_variable: str,
    group_variable: str,
    alternative: str = "two-sided",
) -> AnalysisResult:
    """Compare two independent groups using the Mann–Whitney U rank test."""
    from scipy.stats import mannwhitneyu

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Both outcome and grouping variables must exist.")
    if outcome_variable == group_variable:
        raise ValueError("Choose different outcome and grouping variables.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome must be numeric or ordinal values encoded numerically.")
    if df[group_variable].isna().any():
        raise ValueError("The grouping variable contains missing group labels.")
    if alternative not in {"two-sided", "less", "greater"}:
        raise ValueError("Alternative must be 'two-sided', 'less' or 'greater'.")
    group_labels = list(pd.unique(df[group_variable]))
    if len(group_labels) != 2:
        raise ValueError("The Mann–Whitney U test requires exactly two independent groups.")
    outcome = df[outcome_variable]
    missing_count = int(outcome.isna().sum())
    numeric = outcome.astype(float)
    finite_mask = outcome.notna() & numeric.map(lambda value: bool(pd.notna(value) and abs(value) != float("inf")))
    infinite_count = int((outcome.notna() & ~finite_mask).sum())
    valid = df.loc[finite_mask, [group_variable, outcome_variable]]
    group_1 = valid.loc[valid[group_variable] == group_labels[0], outcome_variable].astype(float).to_numpy()
    group_2 = valid.loc[valid[group_variable] == group_labels[1], outcome_variable].astype(float).to_numpy()
    if len(group_1) < 2 or len(group_2) < 2:
        raise ValueError("The Mann–Whitney U test requires at least two finite observations in each group.")
    test = mannwhitneyu(group_1, group_2, alternative=alternative, method="auto", use_continuity=True)
    u_statistic, p_value = float(test.statistic), float(test.pvalue)
    rank_biserial = float((2.0 * u_statistic / (len(group_1) * len(group_2))) - 1.0)
    has_ties = len(set(group_1.tolist() + group_2.tolist())) < (len(group_1) + len(group_2))
    selected_method = "exact" if min(len(group_1), len(group_2)) <= 8 and not has_ties else "asymptotic"
    summary = pd.DataFrame([{
        "Group 1": str(group_labels[0]), "Group 2": str(group_labels[1]),
        "Group 1 n": int(len(group_1)), "Group 2 n": int(len(group_2)),
        "Group 1 median": float(pd.Series(group_1).median()), "Group 2 median": float(pd.Series(group_2).median()),
        "U statistic (Group 1)": u_statistic, "Rank-biserial correlation": rank_biserial,
        "Alternative": alternative, "P-value": p_value, "P-value method": selected_method,
        "Missing outcomes excluded": missing_count, "Infinite outcomes excluded": infinite_count,
    }])
    assumptions = [
        "The two groups are independent, and observations are independent within each group.",
        "The outcome is at least ordinal; numeric values preserve the intended ordering.",
        "The test compares rank distributions. A median/location-shift interpretation additionally requires similarly shaped group distributions.",
        "The exact p-value is used automatically for small samples without ties; otherwise an asymptotic approximation is used.",
    ]
    limitations = [
        "This is not automatically a test of medians; differing distribution shapes or spreads can produce a significant result without a pure median shift.",
        "The rank-biserial correlation is a directional effect-size summary, not a causal effect.",
        "The ordinary test is not adjusted for survey weights, clustering, stratification, finite population corrections or repeated-measures designs.",
        "Missing and infinite outcome values are excluded; missing group labels are rejected.",
    ]
    findings = [
        f"Group 1 ({group_labels[0]}) has {len(group_1)} usable observations; group 2 ({group_labels[1]}) has {len(group_2)}.",
        f"Mann–Whitney U statistic for group 1 is {u_statistic:.4g}; p-value is {p_value:.4g}.",
        f"Directional rank-biserial correlation is {rank_biserial:.3f}; positive values indicate higher ranks in group 1.",
    ]
    return AnalysisResult(
        title=f"Mann–Whitney U test: {outcome_variable} by {group_variable}",
        status="success", method="Mann–Whitney U test", tables={"test": summary},
        findings=findings, assumptions=assumptions, limitations=limitations,
        metadata={
            "outcome_variable": outcome_variable, "group_variable": group_variable,
            "group_1_label": str(group_labels[0]), "group_2_label": str(group_labels[1]),
            "group_1_n": int(len(group_1)), "group_2_n": int(len(group_2)),
            "u_statistic": u_statistic, "rank_biserial_correlation": rank_biserial,
            "p_value": p_value, "alternative": alternative, "p_value_method": selected_method,
            "missing_outcomes": missing_count, "infinite_outcomes": infinite_count,
            "sampling_design_aware": False, "study_design": "independent_groups",
        },
    )



def run_kruskal_wallis_test(df: pd.DataFrame, outcome_variable: str, group_variable: str) -> AnalysisResult:
    """Compare three or more independent groups using the Kruskal–Wallis H test."""
    from scipy.stats import kruskal, rankdata
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Both outcome and grouping variables must exist.")
    if outcome_variable == group_variable:
        raise ValueError("Choose different outcome and grouping variables.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome must be numeric or ordinal values encoded numerically.")
    if df[group_variable].isna().any():
        raise ValueError("The grouping variable contains missing group labels.")
    labels = list(pd.unique(df[group_variable]))
    if len(labels) < 3:
        raise ValueError("The Kruskal–Wallis test requires at least three independent groups.")
    outcome = df[outcome_variable]
    missing = int(outcome.isna().sum())
    numeric = pd.to_numeric(outcome, errors="coerce")
    finite = outcome.notna() & numeric.map(lambda x: bool(pd.notna(x) and abs(float(x)) != float("inf")))
    infinite = int((outcome.notna() & ~finite).sum())
    valid = df.loc[finite, [group_variable, outcome_variable]].copy()
    valid[outcome_variable] = pd.to_numeric(valid[outcome_variable], errors="coerce").astype(float)
    samples = [valid.loc[valid[group_variable] == label, outcome_variable].to_numpy(float) for label in labels]
    if any(len(x) < 2 for x in samples):
        raise ValueError("The Kruskal–Wallis test requires at least two finite observations in each group.")
    if valid[outcome_variable].nunique(dropna=True) < 2:
        raise ValueError("The Kruskal–Wallis statistic is undefined when all observations are identical.")
    try:
        test = kruskal(*samples, nan_policy="raise")
    except ValueError as exc:
        if "identical" in str(exc).casefold():
            raise ValueError("The Kruskal–Wallis statistic is undefined when all observations are identical.") from exc
        raise
    h, p = float(test.statistic), float(test.pvalue)
    k, n = len(samples), int(sum(map(len, samples)))
    valid["_rank"] = rankdata(valid[outcome_variable].to_numpy(float), method="average")
    group_summary = pd.DataFrame([{
        "Group": str(label), "Valid n": int(len(sample)),
        "Median": float(pd.Series(sample).median()),
        "Mean rank": float(valid.loc[valid[group_variable] == label, "_rank"].mean()),
    } for label, sample in zip(labels, samples)])
    eps2 = max(0.0, float((h - k + 1) / (n - k)))
    findings = [
        f"The Kruskal–Wallis H statistic is {h:.4g} with {k-1} degrees of freedom (p = {p:.4g}).",
        f"The analysis includes {n:,} observations across {k} independent groups.",
        f"Epsilon-squared effect-size estimate is {eps2:.3f}; interpret its magnitude in context.",
    ]
    if p < 0.05:
        findings.append("There is evidence that at least one group rank distribution differs; this omnibus test does not identify which groups differ.")
    else:
        findings.append("The omnibus test does not provide sufficient evidence of a difference in rank distributions at the 0.05 level.")
    limitations = [
        "This is an omnibus comparison of rank distributions, not automatically a test of medians. A location-shift interpretation requires similarly shaped group distributions.",
        "A significant result does not identify which pairs differ; use a justified post-hoc procedure with multiplicity control.",
        "The ordinary test is not adjusted for survey weights, clustering, stratification, finite-population corrections or repeated-measures designs.",
        "The chi-square approximation for H may be unreliable with very small group samples.",
        "Missing and infinite outcome values are excluded; missing group labels are rejected.",
    ]
    if missing: limitations.append(f"{missing:,} missing outcome value(s) were excluded.")
    if infinite: limitations.append(f"{infinite:,} infinite outcome value(s) were excluded.")
    return AnalysisResult(
        title=f"Kruskal–Wallis test: {outcome_variable} by {group_variable}",
        status="success", method="Kruskal–Wallis test",
        tables={"group_summary": group_summary, "test": pd.DataFrame([{
            "H statistic": h, "Degrees of freedom": k-1, "P-value": p,
            "Epsilon-squared": eps2, "Total observations": n, "Groups": k,
            "Missing outcomes excluded": missing, "Infinite outcomes excluded": infinite,
        }])},
        findings=findings,
        assumptions=[
            "Groups and observations within groups are independent.",
            "The outcome is at least ordinal and numeric coding preserves its ordering.",
            "The test compares rank distributions; a location-shift interpretation requires similarly shaped distributions.",
            "The H statistic uses its large-sample chi-square approximation.",
        ],
        limitations=limitations,
        metadata={
            "outcome_variable": outcome_variable, "group_variable": group_variable,
            "group_labels": [str(x) for x in labels], "group_count": k,
            "group_sizes": [int(len(x)) for x in samples], "h_statistic": h,
            "degrees_of_freedom": k-1, "p_value": p, "epsilon_squared": eps2,
            "n_observations": n, "missing_outcomes": missing, "infinite_outcomes": infinite,
            "sampling_design_aware": False, "study_design": "independent_groups",
        },
    )



def run_dunn_posthoc_test(df: pd.DataFrame, outcome_variable: str, group_variable: str) -> AnalysisResult:
    """Run Dunn pairwise rank comparisons with Holm family-wise adjustment."""
    from itertools import combinations
    import numpy as np
    from scipy.stats import norm, rankdata
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Both outcome and grouping variables must exist.")
    if outcome_variable == group_variable:
        raise ValueError("Choose different outcome and grouping variables.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome must be numeric or ordinal values encoded numerically.")
    if df[group_variable].isna().any():
        raise ValueError("The grouping variable contains missing group labels.")
    labels = list(pd.unique(df[group_variable]))
    if len(labels) < 3:
        raise ValueError("Dunn's post-hoc test requires at least three independent groups.")
    outcome = df[outcome_variable]
    missing = int(outcome.isna().sum())
    numeric = pd.to_numeric(outcome, errors="coerce")
    finite = outcome.notna() & numeric.map(lambda x: bool(pd.notna(x) and abs(float(x)) != float("inf")))
    infinite = int((outcome.notna() & ~finite).sum())
    valid = df.loc[finite, [group_variable, outcome_variable]].copy()
    valid[outcome_variable] = pd.to_numeric(valid[outcome_variable], errors="coerce").astype(float)
    if valid.empty:
        raise ValueError("At least one finite outcome value is required.")
    samples = [valid.loc[valid[group_variable] == label, outcome_variable].to_numpy(float) for label in labels]
    if any(len(sample) < 2 for sample in samples):
        raise ValueError("Dunn's post-hoc test requires at least two finite observations in each group.")
    values = valid[outcome_variable].to_numpy(float)
    valid["_rank"] = rankdata(values, method="average")
    n_total = len(values)
    _, tie_counts = np.unique(values, return_counts=True)
    tie_sum = float(np.sum(tie_counts ** 3 - tie_counts))
    variance_factor = n_total * (n_total + 1) / 12.0 - tie_sum / (12.0 * (n_total - 1))
    if not np.isfinite(variance_factor) or variance_factor <= 0:
        raise ValueError("Dunn's test is undefined when all observations are tied.")
    rows, raw_p = [], []
    for first, second in combinations(labels, 2):
        r1 = valid.loc[valid[group_variable] == first, "_rank"]
        r2 = valid.loc[valid[group_variable] == second, "_rank"]
        difference = float(r1.mean() - r2.mean())
        se = float(np.sqrt(variance_factor * (1.0 / len(r1) + 1.0 / len(r2))))
        z = difference / se
        p = float(2.0 * norm.sf(abs(z)))
        raw_p.append(p)
        rows.append({"Group 1": str(first), "Group 2": str(second), "Group 1 n": int(len(r1)), "Group 2 n": int(len(r2)), "Mean rank difference (1 - 2)": difference, "Standard error": se, "Z statistic": float(z), "Unadjusted p-value": p})
    order = np.argsort(raw_p)
    adjusted = np.empty(len(raw_p), dtype=float)
    running = 0.0
    for i, original in enumerate(order):
        running = max(running, min(1.0, (len(raw_p) - i) * raw_p[original]))
        adjusted[original] = running
    for row, p_adj in zip(rows, adjusted):
        row["Holm-adjusted p-value"] = float(p_adj)
        row["Significant at 0.05"] = bool(p_adj < 0.05)
    pairwise = pd.DataFrame(rows)
    summary = pd.DataFrame([{"Group": str(label), "Valid n": int(len(sample)), "Median": float(pd.Series(sample).median()), "Mean rank": float(valid.loc[valid[group_variable] == label, "_rank"].mean())} for label, sample in zip(labels, samples)])
    significant = int(pairwise["Significant at 0.05"].sum())
    findings = [
        f"Dunn's procedure compared {len(rows)} group pairs using tie-corrected rank variance.",
        f"Holm adjustment identified {significant} pairwise difference(s) at the 0.05 family-wise level.",
        "Direction is shown by the mean rank difference (Group 1 minus Group 2).",
    ]
    limitations = [
        "This independent-groups post-hoc procedure is commonly used after a significant Kruskal–Wallis omnibus test.",
        "The normal approximation may be less reliable with very small samples.",
        "The test compares rank distributions, not automatically medians; a location-shift interpretation requires similarly shaped distributions.",
        "Not adjusted for survey weights, clustering, stratification, finite-population corrections or repeated-measures designs.",
        "Missing and infinite outcomes are excluded; missing group labels are rejected.",
    ]
    if missing: limitations.append(f"{missing:,} missing outcome value(s) were excluded.")
    if infinite: limitations.append(f"{infinite:,} infinite outcome value(s) were excluded.")
    return AnalysisResult(
        title=f"Dunn post-hoc comparisons: {outcome_variable} by {group_variable}",
        status="success", method="Dunn's post-hoc test (Holm-adjusted)",
        tables={"pairwise_comparisons": pairwise, "group_summary": summary},
        findings=findings,
        assumptions=["Groups and observations within groups are independent.", "The outcome is at least ordinal and numeric coding preserves its ordering.", "The pooled rank variance is appropriate for this independent-groups design.", "Holm adjustment controls family-wise error across all pairwise comparisons."],
        limitations=limitations,
        metadata={"outcome_variable": outcome_variable, "group_variable": group_variable, "group_labels": [str(x) for x in labels], "group_count": len(labels), "pairwise_comparisons": len(rows), "significant_comparisons": significant, "adjustment": "Holm", "familywise_alpha": 0.05, "n_observations": n_total, "missing_outcomes": missing, "infinite_outcomes": infinite, "sampling_design_aware": False, "study_design": "independent_groups"},
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






def run_two_proportions_confidence_interval(df: pd.DataFrame, outcome_variable: str, group_variable: str, confidence_level: float = 0.95) -> AnalysisResult:
    """Estimate group 1 minus group 2 with a Newcombe-Wilson interval; no test p-value."""
    from scipy.stats import norm
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns or outcome_variable == group_variable:
        raise ValueError("Select distinct, existing outcome and grouping variables.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome must be numeric and coded strictly as 1 and 0.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)) or not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be numeric and between 0 and 1.")
    level = float(confidence_level)
    pair = df[[outcome_variable, group_variable]]
    clean = pair.dropna()
    excluded = int(len(pair) - len(clean))
    if clean.empty:
        raise ValueError("No complete outcome and group observations remain.")
    if not set(clean[outcome_variable].unique()).issubset({0, 1}):
        raise ValueError("The outcome must contain only 0 and 1 values.")
    labels = list(pd.unique(clean[group_variable]))
    if len(labels) != 2:
        raise ValueError("A two-proportion interval requires exactly two observed independent groups.")
    samples = [clean.loc[clean[group_variable] == label, outcome_variable].astype(int) for label in labels]
    n1, n2 = (int(x.size) for x in samples)
    x1, x2 = (int(x.sum()) for x in samples)
    p1, p2 = x1 / n1, x2 / n2
    difference = p1 - p2
    zc = float(norm.ppf(0.5 + level / 2))
    def wilson(x, n):
        p = x / n
        den = 1 + zc ** 2 / n
        centre = (p + zc ** 2 / (2 * n)) / den
        half = zc * (p * (1 - p) / n + zc ** 2 / (4 * n ** 2)) ** 0.5 / den
        return max(0.0, centre - half), min(1.0, centre + half)
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    lower = max(-1.0, difference - ((p1-l1)**2 + (u2-p2)**2)**0.5)
    upper = min(1.0, difference + ((u1-p1)**2 + (p2-l2)**2)**0.5)
    se = (p1*(1-p1)/n1 + p2*(1-p2)/n2)**0.5
    summary = pd.DataFrame([{"Group 1": str(labels[0]), "Group 1 successes": x1, "Group 1 observations": n1, "Group 1 proportion": p1, "Group 2": str(labels[1]), "Group 2 successes": x2, "Group 2 observations": n2, "Group 2 proportion": p2, "Difference (group 1 - group 2)": difference, "Unpooled standard error": se, "Confidence level": level, "Newcombe CI lower": lower, "Newcombe CI upper": upper, "Incomplete pairs excluded": excluded}])
    findings = [f"Group {labels[0]}: {x1}/{n1} events ({p1:.1%}); group {labels[1]}: {x2}/{n2} events ({p2:.1%}).", f"Estimated difference (group 1 minus group 2): {difference:.1%}.", f"{level:.0%} Newcombe-Wilson confidence interval: [{lower:.1%}, {upper:.1%}]."]
    limitations = ["Assumes two independent groups and independent Bernoulli observations within each group.", "Uses Newcombe's method combining two Wilson score intervals.", "Estimation only: no hypothesis-test p-value is calculated.", "Not adjusted for survey weights, clustering, stratification, repeated measures or finite-population corrections."]
    if excluded:
        limitations.append(f"{excluded:,} rows with a missing outcome or group label were excluded.")
    return AnalysisResult(title=f"Confidence interval for difference in proportions: {outcome_variable} by {group_variable}", method="Newcombe-Wilson confidence interval for two independent proportions", status="success", tables={"interval_summary": summary}, findings=findings, assumptions=["Outcome is binary (1=event, 0=non-event).", "Exactly two independent groups are observed.", "Observations are independent within each group."], limitations=limitations, metadata={"outcome_variable": outcome_variable, "group_variable": group_variable, "group_1_label": str(labels[0]), "group_2_label": str(labels[1]), "group_1_successes": x1, "group_1_n": n1, "group_1_proportion": p1, "group_2_successes": x2, "group_2_n": n2, "group_2_proportion": p2, "estimate": difference, "standard_error": se, "confidence_level": level, "confidence_interval": (float(lower), float(upper)), "incomplete_pairs_excluded": excluded, "sampling_design_aware": False, "study_design": "independent_groups", "inference_framework": "newcombe_wilson_two_proportion_interval"})

def run_two_independent_proportions_test(df: pd.DataFrame, outcome_variable: str, group_variable: str, confidence_level: float = 0.95, alternative: str = "two-sided") -> AnalysisResult:
    """Compare two independent binary proportions using a pooled score test and Newcombe-Wilson interval."""
    from scipy.stats import norm
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Both binary outcome and grouping variables must exist.")
    if outcome_variable == group_variable:
        raise ValueError("Outcome and grouping variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome must be numeric and coded strictly as 1 and 0.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    level = float(confidence_level)
    if not 0 < level < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")
    if alternative not in {"two-sided", "greater", "less"}:
        raise ValueError("Alternative must be 'two-sided', 'greater' or 'less'.")
    pair = df[[outcome_variable, group_variable]]
    clean = pair.dropna()
    excluded = int(len(pair) - len(clean))
    if clean.empty:
        raise ValueError("No complete outcome and group observations remain.")
    if not set(clean[outcome_variable].unique()).issubset({0, 1}):
        raise ValueError("The outcome must contain only 0 and 1 values.")
    labels = list(pd.unique(clean[group_variable]))
    if len(labels) != 2:
        raise ValueError("A two-proportion comparison requires exactly two observed independent groups.")
    samples = [clean.loc[clean[group_variable] == label, outcome_variable].astype(int) for label in labels]
    n1, n2 = (int(x.size) for x in samples)
    x1, x2 = (int(x.sum()) for x in samples)
    p1, p2 = x1 / n1, x2 / n2
    difference = p1 - p2
    pooled = (x1 + x2) / (n1 + n2)
    pooled_se = (pooled * (1 - pooled) * (1 / n1 + 1 / n2)) ** 0.5
    z = difference / pooled_se if pooled_se else (0.0 if difference == 0 else (float("inf") if difference > 0 else float("-inf")))
    p_value = float(2 * norm.sf(abs(z))) if alternative == "two-sided" else float(norm.sf(z) if alternative == "greater" else norm.cdf(z))
    zc = float(norm.ppf(0.5 + level / 2))
    def wilson(x, n):
        p = x / n
        den = 1 + zc ** 2 / n
        centre = (p + zc ** 2 / (2 * n)) / den
        half = zc * (p * (1 - p) / n + zc ** 2 / (4 * n ** 2)) ** 0.5 / den
        return max(0.0, centre - half), min(1.0, centre + half)
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    lower = max(-1.0, difference - ((p1-l1)**2 + (u2-p2)**2)**0.5)
    upper = min(1.0, difference + ((u1-p1)**2 + (p2-l2)**2)**0.5)
    se = (p1*(1-p1)/n1 + p2*(1-p2)/n2)**0.5
    summary = pd.DataFrame([{"Group 1": str(labels[0]), "Group 2": str(labels[1]), "Group 1 successes": x1, "Group 1 n": n1, "Group 1 proportion": p1, "Group 2 successes": x2, "Group 2 n": n2, "Group 2 proportion": p2, "Difference (group 1 - group 2)": difference, "Standard error": se, "Pooled z statistic": z, "p-value": p_value, "Alternative": alternative, "Confidence level": level, "CI lower": lower, "CI upper": upper, "Incomplete pairs excluded": excluded}])
    findings = [f"Group {labels[0]}: {x1}/{n1} events ({p1:.1%}); group {labels[1]}: {x2}/{n2} events ({p2:.1%}).", f"Estimated difference (group 1 minus group 2): {difference:.1%}.", f"Pooled score z = {z:.4g}; p = {p_value:.4g} ({alternative}).", f"{level:.0%} Newcombe-Wilson confidence interval: [{lower:.1%}, {upper:.1%}]."]
    limitations = ["Assumes two independent groups and independent Bernoulli observations within each group.", "The hypothesis test uses the pooled two-proportion score z statistic without continuity correction.", "The confidence interval uses Newcombe's method combining two Wilson score intervals.", "Not adjusted for survey weights, clustering, stratification, repeated measures or finite-population corrections."]
    if excluded:
        limitations.append(f"{excluded:,} rows with a missing outcome or group label were excluded.")
    return AnalysisResult(title=f"Two independent proportions: {outcome_variable} by {group_variable}", method="Two-independent-proportions score test", status="success", tables={"test_summary": summary}, findings=findings, assumptions=["Outcome is binary (1=event, 0=non-event).", "The grouping variable defines exactly two independent groups.", "Observations are independent within each group."], limitations=limitations, metadata={"outcome_variable": outcome_variable, "group_variable": group_variable, "group_1_label": str(labels[0]), "group_2_label": str(labels[1]), "group_1_successes": x1, "group_1_n": n1, "group_1_proportion": p1, "group_2_successes": x2, "group_2_n": n2, "group_2_proportion": p2, "estimate": difference, "standard_error": se, "z_statistic": float(z), "p_value": p_value, "alternative": alternative, "confidence_level": level, "confidence_interval": (float(lower), float(upper)), "incomplete_pairs_excluded": excluded, "sampling_design_aware": False, "study_design": "independent_groups", "inference_framework": "pooled_two_proportion_score_newcombe_wilson"})

def run_one_sample_binomial_test(df: pd.DataFrame, variable: str, reference_proportion: float,
                                alternative: str = "two-sided", confidence_level: float = 0.95) -> AnalysisResult:
    """Test a binary population proportion against a reference using an exact binomial test."""
    from scipy.stats import binomtest
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(variable, str) or variable not in df.columns:
        raise ValueError("Select a valid binary outcome variable.")
    if not pd.api.types.is_numeric_dtype(df[variable]):
        raise TypeError("The outcome must be numeric and coded strictly as 1 (event) and 0 (non-event).")
    try:
        p0 = float(reference_proportion)
        level = float(confidence_level)
    except (TypeError, ValueError):
        raise ValueError("Reference proportion and confidence level must be numeric.") from None
    if not pd.notna(p0) or not 0 <= p0 <= 1:
        raise ValueError("Reference proportion must be finite and between 0 and 1.")
    if not pd.notna(level) or not 0 < level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    if alternative not in {"two-sided", "less", "greater"}:
        raise ValueError("Alternative must be 'two-sided', 'less' or 'greater'.")
    raw = df[variable].dropna()
    if raw.empty:
        raise ValueError("A binomial test requires at least one observed value.")
    if not set(raw.unique()).issubset({0, 1}):
        raise ValueError("The outcome must contain only 0 and 1 values.")
    values = raw.astype(int)
    n = int(len(values))
    successes = int(values.sum())
    estimate = successes / n
    test = binomtest(successes, n, p=p0, alternative=alternative)
    interval = test.proportion_ci(confidence_level=level, method="exact")
    lower, upper = float(interval.low), float(interval.high)
    excluded = int(len(df) - n)
    summary = pd.DataFrame([{"Successes": successes, "Observations": n,
        "Observed proportion": estimate, "Reference proportion": p0,
        "Alternative hypothesis": alternative, "Exact p-value": float(test.pvalue),
        "Confidence level": level, "Exact lower confidence limit": lower,
        "Exact upper confidence limit": upper, "Missing values excluded": excluded}])
    findings = [f"Observed proportion is {estimate:.4f} ({successes} of {n}).",
        f"The exact binomial test p-value is {test.pvalue:.4g} against reference proportion {p0:.4f} ({alternative} alternative).",
        f"The {level:.0%} exact Clopper-Pearson interval is [{lower:.4f}, {upper:.4f}]."]
    limitations = ["The exact binomial test assumes independent Bernoulli observations with a common event probability.",
        "This procedure is not adjusted for survey weights, clustering, stratification or finite-population corrections.",
        "The exact interval is the conservative Clopper-Pearson interval."]
    if excluded:
        limitations.append(f"{excluded:,} rows with missing outcomes were excluded.")
    return AnalysisResult(title=f"Exact one-sample binomial test: {variable}",
        method="Exact one-sample binomial test", status="success",
        tables={"test_summary": summary}, findings=findings,
        assumptions=["Outcome is binary: 1 denotes an event and 0 denotes a non-event.",
            "Observations are independent and share a common event probability."],
        limitations=limitations, metadata={"variable": variable, "successes": successes,
            "observations": n, "estimate": estimate, "reference_proportion": p0,
            "alternative": alternative, "p_value": float(test.pvalue),
            "confidence_level": level, "confidence_interval": (lower, upper),
            "missing_values_excluded": excluded, "sampling_design_aware": False,
            "inference_framework": "exact_binomial"})


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





def run_repeated_measures_anova(df: pd.DataFrame, measurement_variables: list[str], confidence_level: float = 0.95) -> AnalysisResult:
    """One-way repeated-measures ANOVA with sphericity diagnostics and Holm follow-ups."""
    from itertools import combinations
    from scipy.linalg import helmert
    from scipy.stats import chi2, f as f_dist, t as t_dist, ttest_rel
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    variables = list(measurement_variables or [])
    if len(variables) < 3 or len(set(variables)) != len(variables):
        raise ValueError("Repeated-measures ANOVA requires at least three distinct measurement variables.")
    if not 0 < float(confidence_level) < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    missing = [v for v in variables if not isinstance(v, str) or v not in df.columns]
    if missing:
        raise ValueError(f"Measurement variables not found: {missing}.")
    for v in variables:
        if not pd.api.types.is_numeric_dtype(df[v]):
            raise TypeError(f"Measurement variable '{v}' must be numeric.")
    values = df[variables].apply(pd.to_numeric, errors="coerce")
    mask = values.notna().all(axis=1)
    for v in variables:
        mask &= values[v].map(lambda z: abs(float(z)) != float("inf"))
    complete = values.loc[mask].astype(float)
    n, k = len(complete), len(variables)
    if n < 3:
        raise ValueError("Repeated-measures ANOVA requires at least three complete matched units.")
    x = complete.to_numpy(dtype=float)
    grand, means, subjects = float(x.mean()), x.mean(axis=0), x.mean(axis=1)
    ss_condition = float(n * ((means - grand) ** 2).sum())
    ss_subject = float(k * ((subjects - grand) ** 2).sum())
    ss_total = float(((x - grand) ** 2).sum())
    ss_error = ss_total - ss_condition - ss_subject
    if ss_error <= 1e-12 * max(1.0, ss_total):
        raise ValueError("Repeated-measures ANOVA is undefined because residual within-subject error variance is zero.")
    df1, df2 = k - 1, (n - 1) * (k - 1)
    f_stat = float((ss_condition / df1) / (ss_error / df2))
    p_unc = float(f_dist.sf(f_stat, df1, df2))
    eta_p = float(ss_condition / (ss_condition + ss_error))
    p = k - 1
    contrast = x @ helmert(k, full=False).T
    cov = np.cov(contrast, rowvar=False, ddof=1)
    tr, tr2 = float(np.trace(cov)), float(np.trace(cov @ cov))
    eps_gg = float(np.clip(tr * tr / (p * tr2), 1 / p, 1.0)) if tr2 > 0 else 1.0
    hf_den = p * (n - 1 - p * eps_gg)
    eps_hf = float(np.clip((n * p * eps_gg - 2) / hf_den, eps_gg, 1.0)) if hf_den > 0 else 1.0
    sign, logdet = np.linalg.slogdet(cov)
    if sign > 0 and tr > 0:
        mauchly_w = float(np.clip(np.exp(min(0.0, logdet - p * np.log(tr / p))), 0.0, 1.0))
        correction = 1.0 - (2 * p * p + p + 2) / (6 * p * (n - 1))
        mauchly_chi = float(-(n - 1) * correction * np.log(max(mauchly_w, np.finfo(float).tiny)))
        mauchly_df = int(p * (p + 1) / 2 - 1)
        mauchly_p = float(chi2.sf(mauchly_chi, mauchly_df)) if mauchly_df > 0 else 1.0
    else:
        mauchly_w, mauchly_chi, mauchly_p = 0.0, float("inf"), 0.0
        mauchly_df = int(p * (p + 1) / 2 - 1)
    gg1, gg2, hf1, hf2 = eps_gg * df1, eps_gg * df2, eps_hf * df1, eps_hf * df2
    p_gg, p_hf = float(f_dist.sf(f_stat, gg1, gg2)), float(f_dist.sf(f_stat, hf1, hf2))
    alpha = 1 - float(confidence_level)
    pairs, raw_p = [], []
    for first, second in combinations(variables, 2):
        diff = complete[second].to_numpy() - complete[first].to_numpy()
        test = ttest_rel(complete[second].to_numpy(), complete[first].to_numpy(), nan_policy="raise")
        mean_diff, se, pv = float(diff.mean()), float(diff.std(ddof=1) / np.sqrt(n)), float(test.pvalue)
        crit = float(t_dist.ppf(1 - alpha / 2, n - 1))
        pairs.append({"Measurement 1": first, "Measurement 2": second, "Complete pairs": n,
            "Mean difference (2 - 1)": mean_diff, "Standard error": se, "t statistic": float(test.statistic),
            "Degrees of freedom": n - 1, "P-value": pv, f"{confidence_level:.0%} CI lower": mean_diff-crit*se,
            f"{confidence_level:.0%} CI upper": mean_diff+crit*se})
        raw_p.append(pv)
    order = sorted(range(len(raw_p)), key=lambda i: raw_p[i])
    adjusted, running = [0.0] * len(raw_p), 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (len(raw_p)-rank) * raw_p[idx]))
        adjusted[idx] = running
    for row, adj in zip(pairs, adjusted):
        row["Holm-adjusted p-value"], row["Significant at alpha"] = float(adj), bool(adj < alpha)
    summary = pd.DataFrame([{"F statistic":f_stat,"Numerator df (uncorrected)":df1,"Denominator df (uncorrected)":df2,
        "Uncorrected p-value":p_unc,"Greenhouse-Geisser epsilon":eps_gg,"GG numerator df":gg1,"GG denominator df":gg2,
        "Greenhouse-Geisser p-value":p_gg,"Huynh-Feldt epsilon":eps_hf,"HF numerator df":hf1,"HF denominator df":hf2,
        "Huynh-Feldt p-value":p_hf,"Partial eta-squared":eta_p,"Complete units":n,"Excluded incomplete/non-finite units":len(df)-n}])
    sphericity = pd.DataFrame([{"Mauchly's W":mauchly_w,"Chi-square approximation":mauchly_chi,
        "Degrees of freedom":mauchly_df,"P-value":mauchly_p,"Sphericity at 0.05":bool(mauchly_p >= .05)}])
    descriptive = pd.DataFrame([{"Measurement":v,"N":n,"Mean":float(complete[v].mean()),
        "Standard deviation":float(complete[v].std(ddof=1))} for v in variables])
    findings = [f"Repeated-measures ANOVA: F({gg1:.3g}, {gg2:.3g}) = {f_stat:.4g}, Greenhouse-Geisser corrected p = {p_gg:.4g}.",
        f"Partial eta-squared is {eta_p:.4g}.",
        f"Mauchly's test: W = {mauchly_w:.4g}, p = {mauchly_p:.4g}; epsilon GG = {eps_gg:.4g}, epsilon HF = {eps_hf:.4g}.",
        f"{len(pairs)} paired t-test follow-ups use Holm-adjusted p-values."]
    if mauchly_p < .05:
        findings.append("Mauchly's test indicates departure from sphericity; interpret corrected degrees of freedom and p-values.")
    limitations = ["One-factor univariate repeated-measures ANOVA for complete matched observations; not a mixed-effects model.",
        "Assumes independent subjects and approximately multivariate-normal within-subject contrasts/residuals.",
        "Mauchly's test may have low power in small samples and can be unstable with singular contrast covariance.",
        "Pairwise follow-ups are paired t-tests; confidence intervals are unadjusted while p-values are Holm-adjusted.",
        "Not adjusted for survey weights, clustering, stratification, finite-population corrections or missing-data models."]
    if len(df) > n:
        limitations.append(f"{len(df)-n} rows with missing or non-finite selected measurements were excluded using complete-case analysis.")
    return AnalysisResult(title="One-way repeated-measures ANOVA", method="One-way repeated-measures ANOVA", status="success",
        tables={"test_summary":summary,"sphericity_test":sphericity,"descriptive_statistics":descriptive,"pairwise_comparisons":pd.DataFrame(pairs)},
        findings=findings, assumptions=["At least three numeric repeated measurements in wide format, one row per matched unit.",
            "The same units are observed under each condition/time point.","Different units are independent.",
            "Within-subject contrasts/residuals are approximately multivariate normal.","Sphericity is assessed and corrected degrees of freedom are reported.",
            "Complete-case analysis is used."], limitations=limitations,
        metadata={"measurement_variables":variables,"n_complete":n,"n_incomplete":len(df)-n,"k_measurements":k,
            "f_statistic":f_stat,"p_value":p_gg,"p_value_uncorrected":p_unc,"p_value_greenhouse_geisser":p_gg,
            "p_value_huynh_feldt":p_hf,"epsilon_greenhouse_geisser":eps_gg,"epsilon_huynh_feldt":eps_hf,
            "mauchly_w":mauchly_w,"mauchly_p_value":mauchly_p,"partial_eta_squared":eta_p,
            "number_of_pairwise_comparisons":len(pairs),"adjustment":"Holm","confidence_level":float(confidence_level),
            "study_design":"repeated_measures","sampling_design_aware":False})


def run_friedman_test(
    df: pd.DataFrame,
    measurement_variables: list[str],
) -> AnalysisResult:
    """Compare three or more related measurements using the Friedman test.

    Data are supplied in wide form: each row is one subject/unit and each
    selected column is one repeated condition or time point.
    """
    from scipy.stats import friedmanchisquare
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not isinstance(measurement_variables, (list, tuple)) or len(measurement_variables) < 3:
        raise ValueError("The Friedman test requires at least three repeated-measurement variables.")
    if len(set(measurement_variables)) != len(measurement_variables):
        raise ValueError("Select each repeated-measurement variable only once.")
    missing_columns = [name for name in measurement_variables if not isinstance(name, str) or name not in df.columns]
    if missing_columns:
        raise ValueError(f"Measurement variables not found: {missing_columns}.")
    for variable in measurement_variables:
        if not pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError(f"Measurement variable '{variable}' must be numeric or ordinal-coded.")
    raw = df[list(measurement_variables)]
    numeric = raw.astype(float)
    finite_mask = numeric.notna().all(axis=1) & numeric.apply(lambda col: col.map(lambda value: abs(value) != float("inf"))).all(axis=1)
    complete = numeric.loc[finite_mask]
    incomplete = int(len(df) - len(complete))
    if len(complete) < 2:
        raise ValueError("The Friedman test requires at least two complete matched units across all selected measurements.")
    if (complete.nunique(axis=1) == 1).all():
        raise ValueError("The Friedman test is undefined when all repeated measurements are identical within every unit.")
    arrays = [complete[column].to_numpy() for column in measurement_variables]
    try:
        statistic, p_value = friedmanchisquare(*arrays)
    except ValueError as exc:
        raise ValueError(f"The Friedman test could not be calculated: {exc}") from exc
    if not pd.notna(statistic) or not pd.notna(p_value):
        raise ValueError("The Friedman test is undefined for these repeated measurements (check for all-tied data).")
    n, k = int(len(complete)), int(len(measurement_variables))
    degrees_freedom = k - 1
    kendall_w = float(statistic / (n * (k - 1)))
    rank_rows = []
    rank_matrix = complete.rank(axis=1, method="average")
    for variable in measurement_variables:
        rank_rows.append({
            "Measurement": variable,
            "Complete units": n,
            "Mean within-unit rank": float(rank_matrix[variable].mean()),
            "Median": float(complete[variable].median()),
            "Mean": float(complete[variable].mean()),
        })
    summary = pd.DataFrame([{
        "Friedman chi-square statistic": float(statistic),
        "Degrees of freedom": degrees_freedom,
        "p-value": float(p_value),
        "Complete matched units": n,
        "Repeated measurements": k,
        "Kendall's W": kendall_w,
        "Incomplete units excluded": incomplete,
    }])
    findings = [
        f"Friedman statistic is {statistic:.4g} with {degrees_freedom} degrees of freedom (p = {p_value:.4g}).",
        f"{n:,} complete matched units were analysed across {k} repeated measurements.",
        f"Kendall's W is {kendall_w:.4g}; interpret the magnitude in the study context.",
        "The result is statistically significant at the 0.05 level." if p_value < 0.05 else "The result is not statistically significant at the 0.05 level.",
    ]
    limitations = [
        "Each row must represent the same correctly matched participant, household, facility or other unit across all selected measurement columns.",
        "Units are assumed independent of one another; within-unit repeated measurements are handled by the Friedman procedure.",
        "The test is an omnibus rank-based comparison; it does not identify which time points or conditions differ. Use a justified paired post-hoc procedure with multiplicity adjustment.",
        "The ordinary Friedman test is not adjusted for survey weights, clustering, stratification or finite-population corrections.",
        "Complete-case analysis excludes a unit if any selected repeated measurement is missing or infinite.",
    ]
    if incomplete:
        limitations.append(f"{incomplete:,} unit(s) with incomplete or non-finite repeated measurements were excluded.")
    return AnalysisResult(
        title="Friedman test for related measurements",
        method="Friedman test",
        status="success",
        tables={"test_summary": summary, "measurement_ranks": pd.DataFrame(rank_rows)},
        findings=findings,
        assumptions=[
            "The selected columns represent at least three conditions or time points measured on the same units.",
            "Each unit's repeated measurements are correctly aligned within one row.",
            "Different units are independent.",
            "The outcome is at least ordinal and numeric coding preserves its ordering.",
        ],
        limitations=limitations,
        metadata={
            "measurement_variables": list(measurement_variables),
            "n_complete": n,
            "n_incomplete": incomplete,
            "k_measurements": k,
            "statistic": float(statistic),
            "degrees_of_freedom": degrees_freedom,
            "p_value": float(p_value),
            "kendall_w": kendall_w,
            "sampling_design_aware": False,
            "study_design": "repeated_measures",
        },
    )


def run_friedman_pairwise_posthoc(df: pd.DataFrame, measurement_variables: list[str]) -> AnalysisResult:
    """Run paired Wilcoxon comparisons across repeated measures with Holm adjustment."""
    from itertools import combinations
    from scipy.stats import rankdata, wilcoxon
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    variables = list(measurement_variables or [])
    if len(variables) < 3 or len(set(variables)) != len(variables):
        raise ValueError("Friedman post-hoc comparisons require at least three distinct measurement variables.")
    missing = [v for v in variables if v not in df.columns]
    if missing:
        raise ValueError(f"Measurement variables not found: {missing}.")
    for variable in variables:
        if not pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError(f"Measurement variable '{variable}' must be numeric or ordinal-coded.")
    values = df[variables].apply(pd.to_numeric, errors="coerce")
    complete_mask = values.notna().all(axis=1)
    for variable in variables:
        complete_mask &= values[variable].map(lambda value: abs(float(value)) != float("inf"))
    complete = values.loc[complete_mask]
    if len(complete) < 2:
        raise ValueError("Pairwise repeated-measurement comparisons require at least two complete matched units.")
    rows, raw_p = [], []
    for first, second in combinations(variables, 2):
        differences = (complete[second] - complete[first]).to_numpy(dtype=float)
        nonzero = differences[differences != 0]
        if len(nonzero) < 2:
            raise ValueError(f"Comparison '{second}' versus '{first}' has fewer than two non-zero paired differences.")
        test = wilcoxon(differences, alternative="two-sided", zero_method="wilcox", correction=False, method="auto")
        ranks = rankdata(abs(nonzero), method="average")
        positive, negative = float(ranks[nonzero > 0].sum()), float(ranks[nonzero < 0].sum())
        raw_p.append(float(test.pvalue))
        rows.append({"Measurement 1": first, "Measurement 2": second, "Complete pairs": int(len(differences)),
            "Non-zero differences": int(len(nonzero)), "Median change (2 - 1)": float(pd.Series(differences).median()),
            "Wilcoxon statistic": float(test.statistic),
            "Rank-biserial correlation (2 - 1)": float((positive-negative)/(positive+negative)),
            "P-value": float(test.pvalue)})
    order = sorted(range(len(raw_p)), key=lambda index: raw_p[index])
    adjusted, running = [0.0] * len(raw_p), 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(raw_p)-rank)*raw_p[index]))
        adjusted[index] = running
    for row, value in zip(rows, adjusted):
        row["Holm-adjusted p-value"] = float(value)
        row["Significant at 0.05"] = bool(value < 0.05)
    table = pd.DataFrame(rows).sort_values("Holm-adjusted p-value").reset_index(drop=True)
    return AnalysisResult(title="Pairwise Wilcoxon post-hoc comparisons for repeated measurements",
        method="Pairwise Wilcoxon signed-rank post-hoc test with Holm adjustment", status="success",
        tables={"pairwise_comparisons": table},
        findings=[f"Performed {len(rows)} pairwise comparisons across {len(variables)} repeated measurements.",
            f"Used {len(complete)} complete matched units; {len(df)-len(complete)} rows were excluded.",
            "Holm-adjusted p-values control the family-wise error rate across all comparisons."],
        assumptions=["Measurements are correctly matched within each row.", "Different units are independent.",
            "The outcome is at least ordinal and paired differences are suitable for signed-rank inference."],
        limitations=["Use as a follow-up to the omnibus Friedman test; it does not replace that test.",
            "Complete-case analysis across all selected measurements is used for a consistent comparison set.",
            "Not adjusted for complex survey weights, clustering, stratification or finite-population corrections."],
        metadata={"measurement_variables": variables, "n_complete": int(len(complete)),
            "n_incomplete": int(len(df)-len(complete)), "number_of_comparisons": len(rows),
            "adjustment": "Holm", "study_design": "repeated_measures", "sampling_design_aware": False})



def run_wilcoxon_signed_rank_test(
    df: pd.DataFrame, before_variable: str, after_variable: str,
    alternative: str = "two-sided",
) -> AnalysisResult:
    """Compare matched before/after measurements using Wilcoxon signed ranks."""
    from scipy.stats import rankdata, wilcoxon
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if before_variable not in df.columns or after_variable not in df.columns:
        raise ValueError("Both before and after measurement variables must exist.")
    if before_variable == after_variable:
        raise ValueError("Before and after measurements must use different variables.")
    for variable in (before_variable, after_variable):
        if not pd.api.types.is_numeric_dtype(df[variable]):
            raise TypeError(f"Measurement variable '{variable}' must be numeric or ordinal-coded.")
    if alternative not in {"two-sided", "greater", "less"}:
        raise ValueError("Alternative must be 'two-sided', 'greater' or 'less'.")
    before, after = df[before_variable].astype(float), df[after_variable].astype(float)
    finite_pair = before.notna() & after.notna() & before.map(lambda v: abs(v) != float("inf")) & after.map(lambda v: abs(v) != float("inf"))
    differences = (after[finite_pair] - before[finite_pair]).astype(float)
    complete_pairs = int(len(differences))
    if complete_pairs < 2:
        raise ValueError("Wilcoxon signed-rank test requires at least two complete finite matched pairs.")
    zero_count = int((differences == 0).sum())
    nonzero = differences[differences != 0]
    if nonzero.empty:
        raise ValueError("Wilcoxon signed-rank test is undefined when all paired differences are zero.")
    test = wilcoxon(differences.to_numpy(), alternative=alternative, zero_method="wilcox", correction=False, method="auto")
    ranks = rankdata(abs(nonzero.to_numpy()), method="average")
    positive_rank_sum = float(ranks[nonzero.to_numpy() > 0].sum())
    negative_rank_sum = float(ranks[nonzero.to_numpy() < 0].sum())
    rank_total = positive_rank_sum + negative_rank_sum
    rank_biserial = (positive_rank_sum - negative_rank_sum) / rank_total if rank_total else 0.0
    missing_pairs = int((before.isna() | after.isna()).sum())
    incomplete_pairs = int((~finite_pair).sum())
    infinite_pairs = incomplete_pairs - missing_pairs
    statistic, p_value = float(test.statistic), float(test.pvalue)
    summary = pd.DataFrame([{
        "Before variable": before_variable, "After variable": after_variable,
        "Complete matched pairs": complete_pairs, "Non-zero differences ranked": int(len(nonzero)),
        "Zero differences excluded": zero_count, "Median change (after - before)": float(differences.median()),
        "Mean change (after - before)": float(differences.mean()), "Positive rank sum": positive_rank_sum,
        "Negative rank sum": negative_rank_sum, "Wilcoxon statistic": statistic,
        "Alternative": alternative, "p-value": p_value, "Matched pairs excluded": incomplete_pairs,
    }])
    findings = [
        f"Median within-pair change (after minus before) is {float(differences.median()):.4g}.",
        f"{complete_pairs:,} complete matched pairs were assessed; {zero_count:,} zero differences were excluded from signed ranking.",
        f"Wilcoxon signed-rank statistic: {statistic:.4g}; p-value: {p_value:.4g}.",
        f"Matched-pairs rank-biserial correlation: {rank_biserial:.4g}.",
        "The result is statistically significant at the 0.05 level." if p_value < 0.05 else "The result is not statistically significant at the 0.05 level.",
    ]
    limitations = [
        "Each row must contain correctly matched before-and-after measurements from the same unit.",
        "Pair-level differences are assumed independent across units.",
        "The procedure evaluates the distribution of paired differences; interpreting it as a median-change test requires a suitably symmetric difference distribution.",
        "Zero differences are excluded using the Wilcox convention; ties in absolute differences receive average ranks.",
        "Not adjusted for complex survey weights, clustering, stratification or finite-population corrections.",
        "Missing and infinite pairs are excluded.",
    ]
    if missing_pairs: limitations.append(f"{missing_pairs:,} pair(s) with missing values were excluded.")
    if infinite_pairs: limitations.append(f"{infinite_pairs:,} pair(s) with infinite values were excluded.")
    return AnalysisResult(
        title=f"Wilcoxon signed-rank test: {after_variable} versus {before_variable}",
        status="success", method="Wilcoxon signed-rank test", tables={"test": summary},
        findings=findings,
        assumptions=["Before-and-after values are correctly paired by row.", "Pairs are independent of other pairs.", "The outcome is at least ordinal and numeric coding preserves ordering.", "The distribution of paired differences is reasonably symmetric for a location-shift interpretation."],
        limitations=limitations,
        metadata={
            "before_variable": before_variable, "after_variable": after_variable,
            "complete_pairs": complete_pairs, "nonzero_differences": int(len(nonzero)),
            "zero_differences": zero_count, "statistic": statistic, "p_value": p_value,
            "alternative": alternative, "rank_biserial_correlation": float(rank_biserial),
            "positive_rank_sum": positive_rank_sum, "negative_rank_sum": negative_rank_sum,
            "missing_pairs": missing_pairs, "infinite_pairs": infinite_pairs,
            "sampling_design_aware": False, "study_design": "paired",
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


def run_linear_mixed_effects_model(df: pd.DataFrame, outcome_variable: str, group_variable: str, fixed_effect_variables: list[str], confidence_level: float = 0.95) -> AnalysisResult:
    """Fit a Gaussian random-intercept model to long-format repeated observations."""
    import warnings
    from statsmodels.regression.mixed_linear_model import MixedLM
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if not 0.5 < float(confidence_level) < 1.0:
        raise ValueError("Confidence level must be greater than 0.50 and less than 1.00.")
    if outcome_variable not in df.columns or group_variable not in df.columns:
        raise ValueError("Select valid outcome and subject/group variables.")
    if outcome_variable == group_variable:
        raise ValueError("Outcome and group identifier must be different.")
    if not isinstance(fixed_effect_variables, list) or not fixed_effect_variables:
        raise ValueError("Select at least one fixed-effect predictor.")
    if len(set(fixed_effect_variables)) != len(fixed_effect_variables) or any(v not in df.columns for v in fixed_effect_variables):
        raise ValueError("Fixed-effect predictors must be valid and unique.")
    if outcome_variable in fixed_effect_variables or group_variable in fixed_effect_variables:
        raise ValueError("Outcome and group identifier cannot also be fixed-effect predictors.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome variable must be numeric.")
    if df[group_variable].isna().any():
        raise ValueError("Subject/group identifiers cannot be missing.")
    if df[group_variable].nunique() < 3:
        raise ValueError("A random-intercept model requires at least three independent groups.")
    selected = df[[outcome_variable, group_variable, *fixed_effect_variables]].copy()
    selected[outcome_variable] = pd.to_numeric(selected[outcome_variable], errors="coerce")
    selected = selected.replace([np.inf, -np.inf], np.nan)
    complete = selected.dropna()
    excluded = len(df) - len(complete)
    for variable in fixed_effect_variables:
        if complete[variable].nunique(dropna=True) < 2:
            raise ValueError(f"Fixed-effect predictor '{variable}' must contain at least two observed values.")
    if len(complete) < 10:
        raise ValueError("At least 10 complete observations are required.")
    counts = complete[group_variable].value_counts()
    if counts.size < 3 or int(counts.min()) < 2:
        raise ValueError("At least three groups with two or more observations each are required.")
    parts = []
    for i, variable in enumerate(fixed_effect_variables):
        series = complete[variable]
        if series.nunique(dropna=True) < 2:
            raise ValueError(f"Fixed-effect predictor '{variable}' must contain at least two observed values.")
        name = f"x{i + 1}"
        if pd.api.types.is_numeric_dtype(series):
            part = pd.DataFrame({name: series.astype(float)}, index=complete.index)
        else:
            part = pd.get_dummies(series.astype("category"), prefix=name, drop_first=True, dtype=float)
        if part.empty:
            raise ValueError(f"Predictor '{variable}' has no estimable contrast.")
        parts.append(part)
    exog = pd.concat(parts, axis=1).astype(float)
    exog.insert(0, "Intercept", 1.0)
    if np.linalg.matrix_rank(exog.to_numpy()) < exog.shape[1]:
        raise ValueError("Fixed-effect design matrix is rank deficient; remove redundant or collinear predictors.")
    endog = complete[outcome_variable].astype(float)
    groups = complete[group_variable].astype(str)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            fitted = MixedLM(endog, exog, groups=groups, exog_re=np.ones((len(complete), 1))).fit(reml=True, method="lbfgs", maxiter=500, disp=False)
        except Exception as exc:
            raise ValueError(f"The linear mixed-effects model could not be fitted: {exc}") from exc
    if not fitted.converged:
        raise ValueError("The linear mixed-effects model did not converge. Review the data and model specification.")
    ci = fitted.conf_int(alpha=1.0 - float(confidence_level))
    rows = []
    for name in exog.columns:
        lo, hi = map(float, ci.loc[name].tolist())
        rows.append({"Term": name, "Coefficient": float(fitted.fe_params[name]), "Standard error": float(fitted.bse_fe[name]), "z statistic": float(fitted.tvalues[name]), "p-value": float(fitted.pvalues[name]), f"{confidence_level:.0%} CI lower": lo, f"{confidence_level:.0%} CI upper": hi})
    random_var = float(np.asarray(fitted.cov_re)[0, 0])
    residual_var = float(fitted.scale)
    icc = random_var / (random_var + residual_var) if random_var + residual_var > 0 else None
    summary = pd.DataFrame([{"Observations": len(complete), "Groups": groups.nunique(), "Minimum observations per group": int(counts.min()), "Maximum observations per group": int(counts.max()), "Random-intercept variance": random_var, "Residual variance": residual_var, "Intraclass correlation (ICC)": icc, "Log-likelihood": float(fitted.llf), "AIC": float(fitted.aic) if np.isfinite(fitted.aic) else None, "BIC": float(fitted.bic) if np.isfinite(fitted.bic) else None, "Converged": bool(fitted.converged), "Rows excluded": excluded}])
    limits = ["Random-intercept structure only; random slopes and non-Gaussian outcomes are not implemented.", "REML is used for variance estimation; do not compare REML likelihoods across models with different fixed effects.", "Not adjusted for complex survey weights, stratification, sampling clusters or finite-population corrections.", "Wald z p-values use large-sample approximations; small-sample degrees-of-freedom corrections are not provided."]
    if excluded: limits.append(f"{excluded} incomplete or non-finite rows were excluded.")
    if random_var <= 1e-8: limits.append("The random-intercept variance is near zero; assess whether a mixed model is warranted.")
    warning_text = [str(w.message) for w in caught if issubclass(w.category, (ConvergenceWarning, RuntimeWarning))]
    if warning_text: limits.append("Model fitting warnings: " + " | ".join(warning_text[:3]))
    return AnalysisResult(title=f"Linear mixed-effects model: {outcome_variable}", method="Linear mixed-effects model (random intercept)", status="success", tables={"fixed_effects": pd.DataFrame(rows), "model_summary": summary}, findings=[f"Model fitted {len(complete):,} observations across {groups.nunique():,} groups.", f"Estimated random-intercept variance: {random_var:.4g}; residual variance: {residual_var:.4g}."] + ([f"Estimated intraclass correlation: {icc:.3f}."] if icc is not None else []), assumptions=["The outcome is continuous and the conditional mean is adequately represented by the fixed effects.", "Random intercepts are approximately normally distributed and independent across groups.", "Conditional residuals are approximately normal with constant variance.", "Observations are conditionally independent given random effects and fixed effects."], limitations=limits, metadata={"outcome_variable": outcome_variable, "group_variable": group_variable, "fixed_effect_variables": list(fixed_effect_variables), "n_observations": len(complete), "n_groups": int(groups.nunique()), "missing_rows_excluded": excluded, "random_intercept_variance": random_var, "residual_variance": residual_var, "intraclass_correlation": icc, "converged": bool(fitted.converged), "estimation": "REML", "confidence_level": float(confidence_level), "random_effect_structure": "random_intercept", "sampling_design_aware": False, "study_design": "longitudinal"})
