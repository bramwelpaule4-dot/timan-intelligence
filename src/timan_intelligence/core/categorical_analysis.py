"""Categorical cross-tabulation and association analysis shared across domains."""

from __future__ import annotations

from typing import Any

import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact


def run_categorical_association(
    df: pd.DataFrame,
    row_variable: str,
    column_variable: str,
) -> dict[str, Any]:
    """Build a complete-case cross-tabulation and select a defensible test.

    Descriptive counts and row/column percentages are always returned when
    there are at least two observed categories on each variable. Inferential
    testing is withheld for sparse tables larger than 2x2.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    for variable in (row_variable, column_variable):
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("Provide valid variable names.")
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' was not found.")
    if row_variable == column_variable:
        raise ValueError("Select two different variables for a cross-tabulation.")

    def clean(series: pd.Series) -> pd.Series:
        values = series.astype("object").where(series.notna(), pd.NA)
        values = values.map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        return values.replace("", pd.NA)

    rows = clean(df[row_variable])
    columns = clean(df[column_variable])
    valid = rows.notna() & columns.notna()
    excluded = int((~valid).sum())
    if not bool(valid.any()):
        raise ValueError("No complete records are available for the selected variables.")

    row_values = rows.loc[valid]
    column_values = columns.loc[valid]
    row_categories = list(pd.unique(row_values))
    column_categories = list(pd.unique(column_values))
    if len(row_categories) < 2 or len(column_categories) < 2:
        raise ValueError("A cross-tabulation requires at least two observed categories in each variable.")
    if len(row_categories) > 50 or len(column_categories) > 50:
        raise ValueError("The selected variable has more than 50 observed categories. Review whether it is an identifier or free-text field before comparing groups.")

    counts = pd.crosstab(row_values, column_values, dropna=False)
    counts.index.name = row_variable
    counts.columns.name = column_variable
    row_pct = counts.div(counts.sum(axis=1).replace(0, pd.NA), axis=0).mul(100).round(2)
    col_pct = counts.div(counts.sum(axis=0).replace(0, pd.NA), axis=1).mul(100).round(2)

    count_table = counts.copy()
    count_table.insert(0, "Total", counts.sum(axis=1))
    row_table = row_pct.copy()
    row_table.insert(0, "Total", 100.0)
    column_totals = pd.DataFrame(
        [[int(counts.sum().sum()), *[round(float(v), 2) for v in col_pct.sum(axis=0)]]],
        index=["Total"],
        columns=["Total", *list(counts.columns)],
    )
    expected = None
    test_name = "Not performed"
    statistic = p_value = degrees_freedom = cramers_v = None
    warnings: list[str] = []
    test_status = "descriptive_only"

    if counts.shape[0] >= 2 and counts.shape[1] >= 2:
        try:
            chi2, p_chi, dof, expected = chi2_contingency(counts.to_numpy(), correction=False)
            expected_frame = pd.DataFrame(expected, index=counts.index, columns=counts.columns)
            low_expected = int((expected < 5).sum())
            minimum_expected = float(expected.min())
            sparse = minimum_expected < 1 or low_expected / expected.size > 0.20
            if counts.shape == (2, 2) and minimum_expected < 5:
                odds_ratio, p_fisher = fisher_exact(counts.to_numpy(), alternative="two-sided")
                test_name = "Fisher's exact test (two-sided)"
                statistic = float(odds_ratio)
                p_value = float(p_fisher)
                test_status = "tested"
                warnings.append("Fisher's exact test was selected because the 2×2 table contains small expected cell counts.")
            elif sparse:
                warnings.append(
                    "Inferential testing was withheld: expected cell counts are too sparse for the chi-square approximation, and an exact procedure for this table size is not enabled."
                )
            else:
                test_name = "Pearson chi-square test"
                statistic = float(chi2)
                p_value = float(p_chi)
                degrees_freedom = int(dof)
                test_status = "tested"
            if test_status == "tested":
                denominator = int(counts.to_numpy().sum())
                dimension = min(counts.shape[0] - 1, counts.shape[1] - 1)
                cramers_v = float((chi2 / (denominator * dimension)) ** 0.5) if denominator and dimension else 0.0
                if test_name.startswith("Fisher"):
                    warnings.append("Cramér's V is calculated from the Pearson chi-square statistic as a descriptive effect-size estimate; interpret cautiously with sparse cells.")
                if p_value < 0.05:
                    conclusion = "Evidence of an association was detected at the 0.05 significance level."
                else:
                    conclusion = "The data do not provide sufficient evidence of an association at the 0.05 significance level."
            else:
                conclusion = "The cross-tabulation is descriptive only; no inferential conclusion is reported."
        except (ValueError, ZeroDivisionError) as exc:
            warnings.append(f"Inferential test could not be calculated: {exc}")
            conclusion = "The cross-tabulation is descriptive only; no inferential conclusion is reported."
    else:
        conclusion = "At least two categories in each variable are required for an association test."

    if excluded:
        warnings.append(f"{excluded} record(s) with a missing or blank value in either selected variable were excluded from the cross-tabulation and test.")
    warnings.extend([
        "Percentages are unweighted and describe the observed complete cases.",
        "An association does not establish causation.",
        "The test assumes independent observations; clustered, paired, repeated, weighted or otherwise complex survey designs require design-adjusted methods.",
    ])
    return {
        "counts": count_table,
        "row_percentages": row_table,
        "column_percentages": col_pct,
        "column_totals": column_totals,
        "metadata": {
            "row_variable": row_variable,
            "column_variable": column_variable,
            "total_records": int(len(df)),
            "valid_n": int(valid.sum()),
            "excluded_n": excluded,
            "table_shape": tuple(counts.shape),
            "test": test_name,
            "test_status": test_status,
            "statistic": statistic,
            "degrees_of_freedom": degrees_freedom,
            "p_value": p_value,
            "cramers_v": cramers_v,
            "minimum_expected_count": float(expected.min()) if expected is not None else None,
            "expected_cells_below_5": int((expected < 5).sum()) if expected is not None else None,
        },
        "findings": [
            f"{int(valid.sum()):,} complete records were included; {excluded:,} were excluded.",
            f"The table compares {counts.shape[0]} categories of '{row_variable}' with {counts.shape[1]} categories of '{column_variable}'.",
            conclusion,
        ],
        "warnings": warnings,
    }
