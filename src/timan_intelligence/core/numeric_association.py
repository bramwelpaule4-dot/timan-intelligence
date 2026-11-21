"""Pairwise association analysis for two numeric variables."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def run_numeric_association(
    df: pd.DataFrame,
    first_variable: str,
    second_variable: str,
) -> dict:
    """Calculate Pearson and Spearman associations on complete finite pairs.

    Both coefficients are reported so users do not have to choose a test
    without understanding the data. Pearson describes linear association;
    Spearman describes monotonic rank association. Neither establishes causality.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    for variable in (first_variable, second_variable):
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("Provide valid variable names.")
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype):
            raise ValueError(
                f"Variable '{variable}' must be numeric. Confirm and convert "
                "text-coded numbers during data preparation."
            )
    if first_variable == second_variable:
        raise ValueError("Select two different numeric variables.")

    first = pd.to_numeric(df[first_variable], errors="coerce")
    second = pd.to_numeric(df[second_variable], errors="coerce")
    finite = np.isfinite(first) & np.isfinite(second)
    paired = pd.DataFrame({
        "first": first.loc[finite].astype(float),
        "second": second.loc[finite].astype(float),
    })
    n = int(len(paired))
    excluded_n = int(len(df) - n)
    if n < 3:
        raise ValueError(
            "At least three complete finite pairs are required to calculate "
            "numeric correlations."
        )
    if paired["first"].nunique() < 2 or paired["second"].nunique() < 2:
        raise ValueError(
            "Both selected variables must vary. A constant variable has no "
            "defined correlation."
        )

    pearson = stats.pearsonr(paired["first"], paired["second"])
    spearman = stats.spearmanr(paired["first"], paired["second"])
    pearson_r = float(pearson.statistic)
    pearson_p = float(pearson.pvalue)
    spearman_rho = float(spearman.statistic)
    spearman_p = float(spearman.pvalue)

    pearson_ci = None
    if n > 3:
        if abs(pearson_r) >= 1:
            pearson_ci = [pearson_r, pearson_r]
        else:
            z = float(np.arctanh(pearson_r))
            standard_error = 1 / np.sqrt(n - 3)
            pearson_ci = [
                float(np.tanh(z - stats.norm.ppf(0.975) * standard_error)),
                float(np.tanh(z + stats.norm.ppf(0.975) * standard_error)),
            ]

    warnings = [
        "Pearson's r measures linear association; Spearman's rho measures monotonic association using ranks.",
        "Correlation does not establish causation, direction of influence or absence of confounding.",
        "The calculations use unweighted complete pairs and assume independent observational units. They do not adjust for survey weights, clustering, repeated measures or complex sample designs.",
        "Inspect the scatterplot and data quality for outliers, non-linear patterns, restricted ranges and influential observations before interpreting either coefficient.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because one or both values "
            "were missing or non-finite."
        )
    if n < 30:
        warnings.append(
            "The paired sample is relatively small; p-values and confidence "
            "intervals may be imprecise. Interpret them cautiously."
        )
    if abs(pearson_r) >= 0.999999 and abs(spearman_rho) >= 0.999999:
        warnings.append(
            "The observed values have an almost perfectly monotonic relationship. "
            "Check for derived variables, duplicated information or data-entry artefacts."
        )
    if np.sign(pearson_r) != np.sign(spearman_rho) and pearson_r != 0 and spearman_rho != 0:
        warnings.append(
            "Pearson and Spearman coefficients have different directions. "
            "Inspect the scatterplot for non-linear structure, influential values or data issues."
        )

    return {
        "paired_data": paired,
        "descriptive_summary": {
            first_variable: {
                "mean": float(paired["first"].mean()),
                "standard_deviation": float(paired["first"].std(ddof=1)),
                "median": float(paired["first"].median()),
                "minimum": float(paired["first"].min()),
                "maximum": float(paired["first"].max()),
            },
            second_variable: {
                "mean": float(paired["second"].mean()),
                "standard_deviation": float(paired["second"].std(ddof=1)),
                "median": float(paired["second"].median()),
                "minimum": float(paired["second"].min()),
                "maximum": float(paired["second"].max()),
            },
        },
        "findings": [
            f"{n:,} complete pairs were analysed; {excluded_n:,} records were excluded.",
            f"Pearson's r = {pearson_r:.4g}; Spearman's rho = {spearman_rho:.4g}.",
        ],
        "warnings": warnings,
        "metadata": {
            "first_variable": first_variable,
            "second_variable": second_variable,
            "total_records": int(len(df)),
            "valid_n": n,
            "excluded_n": excluded_n,
            "pearson_r": pearson_r,
            "pearson_p_value": pearson_p,
            "pearson_confidence_interval_95": pearson_ci,
            "spearman_rho": spearman_rho,
            "spearman_p_value": spearman_p,
            "test_status": "tested",
        },
    }
