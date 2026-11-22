"""Survey-weighted descriptive statistics for probability-sample data.

This module applies positive case weights to descriptive estimates. It does not
estimate design-based variances and must not be used to claim cluster- or
stratum-adjusted inference.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _validated_weights(df: pd.DataFrame, weight_variable: str) -> pd.Series:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if weight_variable not in df.columns:
        raise KeyError(f"Weight variable '{weight_variable}' was not found.")
    if not pd.api.types.is_numeric_dtype(df[weight_variable]):
        raise TypeError("The weight variable must be numeric.")
    weights = pd.to_numeric(df[weight_variable], errors="coerce")
    observed = weights.dropna()
    if observed.empty:
        raise ValueError("The weight variable has no observed numeric values.")
    if not np.isfinite(observed.to_numpy(dtype=float)).all():
        raise ValueError("Observed weights must be finite.")
    if (observed <= 0).any():
        raise ValueError("All observed survey weights must be strictly positive.")
    return weights.astype(float)


def _weight_diagnostics(weights: pd.Series, valid_mask: pd.Series) -> dict[str, Any]:
    used = weights.loc[valid_mask].astype(float)
    if used.empty or float(used.sum()) <= 0:
        raise ValueError("No records with valid outcomes and positive weights remain.")
    sum_weights = float(used.sum())
    sum_squared = float(np.square(used.to_numpy()).sum())
    effective_n = sum_weights**2 / sum_squared if sum_squared else 0.0
    mean_weight = float(used.mean())
    weight_cv = float(used.std(ddof=0) / mean_weight) if mean_weight else 0.0
    return {
        "records_in_dataset": int(len(weights)),
        "records_with_observed_weights": int(weights.notna().sum()),
        "records_used": int(len(used)),
        "records_excluded_missing_weight": int(weights.isna().sum()),
        "sum_of_weights": sum_weights,
        "effective_sample_size_kish": effective_n,
        "minimum_weight": float(used.min()),
        "maximum_weight": float(used.max()),
        "weight_coefficient_of_variation": weight_cv,
    }


def weighted_frequency_table(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    include_missing: bool = False,
) -> dict[str, Any]:
    """Return weighted category totals and percentages for one response variable.

    Percentages use the sum of weights among included response categories. When
    include_missing=True, nonresponse is retained as an explicit category.
    """
    if outcome_variable not in df.columns:
        raise KeyError(f"Outcome variable '{outcome_variable}' was not found.")
    if outcome_variable == weight_variable:
        raise ValueError("The outcome and weight variables must be different.")

    weights = _validated_weights(df, weight_variable)
    values = df[outcome_variable].astype("object").map(
        lambda value: value.strip() if isinstance(value, str) else value
    )
    values = values.replace("", pd.NA)
    valid_weight = weights.notna()
    response_valid = values.notna()
    include_mask = valid_weight & (response_valid | include_missing)
    if not include_mask.any():
        raise ValueError("No records with usable weights and responses remain.")

    rows = []
    if include_missing:
        display_values = values.astype("object").where(values.notna(), "No response")
    else:
        display_values = values
    selected = pd.DataFrame({
        "response": display_values.loc[include_mask].map(str),
        "weight": weights.loc[include_mask],
    })
    grouped = selected.groupby("response", dropna=False, sort=False)["weight"].agg(
        weighted_count="sum", unweighted_n="size"
    ).reset_index()
    denominator = float(grouped["weighted_count"].sum())
    grouped["weighted_percent"] = (
        grouped["weighted_count"] / denominator * 100
    ).round(2)
    grouped["weighted_count"] = grouped["weighted_count"].astype(float)
    grouped["unweighted_n"] = grouped["unweighted_n"].astype(int)
    grouped = grouped.sort_values("weighted_count", ascending=False).reset_index(drop=True)

    diagnostics = _weight_diagnostics(weights, include_mask)
    diagnostics.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "weighted_denominator": denominator,
        "records_excluded_missing_outcome": int((valid_weight & ~response_valid).sum())
            if not include_missing else 0,
        "missing_outcomes_included": bool(include_missing),
        "estimate_type": "weighted descriptive population estimate",
    })
    warnings = [
        "Interpret weighted totals as population estimates only when the supplied weights are valid expansion or inverse-probability weights for the target population.",
        "Weights alone do not account for stratification, clustering, finite population corrections or nonresponse adjustments not already reflected in the supplied weights.",
        "No design-based standard errors, confidence intervals or hypothesis tests are calculated.",
        "The Kish effective sample size is a weight-variability diagnostic, not a substitute for a full complex-survey design effect.",
    ]
    if diagnostics["effective_sample_size_kish"] < diagnostics["records_used"] * 0.5:
        warnings.append("Weight variability substantially reduces the Kish effective sample size relative to the number of analysed records.")
    return {
        "table": grouped,
        "metadata": diagnostics,
        "findings": [
            f"{diagnostics['records_used']:,} records contributed to the weighted frequency estimate.",
            f"Sum of included weights: {denominator:,.3f}.",
            f"Kish effective sample size: {diagnostics['effective_sample_size_kish']:.1f}.",
        ],
        "warnings": warnings,
    }


def weighted_numeric_summary(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
) -> dict[str, Any]:
    """Return weighted mean, population-form weighted SD and weighted total."""
    if outcome_variable not in df.columns:
        raise KeyError(f"Outcome variable '{outcome_variable}' was not found.")
    if outcome_variable == weight_variable:
        raise ValueError("The outcome and weight variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The numeric outcome variable must have a numeric data type.")

    weights = _validated_weights(df, weight_variable)
    values = pd.to_numeric(df[outcome_variable], errors="coerce")
    observed_values = values.dropna()
    if not np.isfinite(observed_values.to_numpy(dtype=float)).all():
        raise ValueError("Observed numeric outcomes must be finite.")
    valid = weights.notna() & values.notna()
    if not valid.any():
        raise ValueError("No records with both a valid numeric outcome and weight remain.")

    x = values.loc[valid].astype(float).to_numpy()
    w = weights.loc[valid].astype(float).to_numpy()
    sum_w = float(w.sum())
    mean = float(np.sum(w * x) / sum_w)
    variance = float(np.sum(w * np.square(x - mean)) / sum_w)
    weighted_sd = float(np.sqrt(max(variance, 0.0)))
    weighted_total = float(np.sum(w * x))
    diagnostics = _weight_diagnostics(weights, valid)
    diagnostics.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "weighted_mean": mean,
        "weighted_standard_deviation": weighted_sd,
        "weighted_total": weighted_total,
        "records_excluded_missing_outcome": int((weights.notna() & values.isna()).sum()),
        "estimate_type": "weighted descriptive population estimate",
    })
    summary = pd.DataFrame([{
        "outcome": outcome_variable,
        "unweighted_n": int(valid.sum()),
        "weighted_total": weighted_total,
        "weighted_mean": mean,
        "weighted_standard_deviation": weighted_sd,
        "unweighted_minimum": float(np.min(x)),
        "unweighted_maximum": float(np.max(x)),
        "sum_of_weights": sum_w,
        "kish_effective_sample_size": diagnostics["effective_sample_size_kish"],
    }])
    warnings = [
        "The weighted standard deviation uses the population-form denominator (sum of weights); it is descriptive, not a design-based variance estimator.",
        "Interpret weighted totals as population totals only when the supplied weights are valid expansion or inverse-probability weights for the target population.",
        "Weights alone do not account for stratification, clustering, finite population corrections or nonresponse adjustments not already reflected in the supplied weights.",
        "No design-based standard errors, confidence intervals or hypothesis tests are calculated.",
        "The Kish effective sample size is a weight-variability diagnostic, not a substitute for a full complex-survey design effect.",
    ]
    if diagnostics["effective_sample_size_kish"] < diagnostics["records_used"] * 0.5:
        warnings.append("Weight variability substantially reduces the Kish effective sample size relative to the number of analysed records.")
    return {
        "table": summary,
        "metadata": diagnostics,
        "findings": [
            f"Weighted mean of {outcome_variable}: {mean:,.4g}.",
            f"Weighted total of {outcome_variable}: {weighted_total:,.4g}.",
            f"Kish effective sample size: {diagnostics['effective_sample_size_kish']:.1f}.",
        ],
        "warnings": warnings,
    }
