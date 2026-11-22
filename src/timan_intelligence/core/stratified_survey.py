"""Stratified descriptive estimators for stratified simple random samples.

This first stratification release supports one-stage stratified sampling where
weights are constant within each stratum (expansion weights). It estimates
stratified means and proportions with Taylor-style variance under independent
simple random sampling within strata. It does not support PSU clustering,
multistage designs, unequal-probability sampling within strata, or FPCs.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t


def _prepare_stratified_data(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    strata_variable: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    for name in (outcome_variable, weight_variable, strata_variable):
        if name not in df.columns:
            raise KeyError(f"Variable '{name}' was not found.")
    if len({outcome_variable, weight_variable, strata_variable}) != 3:
        raise ValueError("Outcome, weight and stratum variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[weight_variable]):
        raise TypeError("The survey weight variable must be numeric.")

    weights = pd.to_numeric(df[weight_variable], errors="coerce")
    observed_weights = weights.dropna().to_numpy(dtype=float)
    if observed_weights.size == 0 or not np.isfinite(observed_weights).all():
        raise ValueError("Observed survey weights must be finite numeric values.")
    if (observed_weights <= 0).any():
        raise ValueError("All observed survey weights must be strictly positive.")

    strata = df[strata_variable].astype("object").map(
        lambda value: value.strip() if isinstance(value, str) else value
    ).replace("", pd.NA)
    if strata.isna().any():
        raise ValueError("Stratum identifiers cannot be missing.")

    outcome = df[outcome_variable]
    if pd.api.types.is_numeric_dtype(outcome):
        outcome = pd.to_numeric(outcome, errors="coerce")
        observed = outcome.dropna().to_numpy(dtype=float)
        if not np.isfinite(observed).all():
            raise ValueError("Observed numeric outcomes must be finite.")
    else:
        outcome = outcome.astype("object").map(
            lambda value: value.strip() if isinstance(value, str) else value
        ).replace("", pd.NA)

    work = pd.DataFrame({
        "outcome": outcome,
        "weight": weights,
        "stratum": strata,
    })
    valid = work["weight"].notna() & work["outcome"].notna()
    work = work.loc[valid].copy()
    if work.empty:
        raise ValueError("No complete records with valid outcomes, weights and strata remain.")

    weight_counts = work.groupby("stratum", sort=False)["weight"].nunique()
    if (weight_counts > 1).any():
        affected = ", ".join(map(str, weight_counts[weight_counts > 1].index.tolist()))
        raise ValueError(
            "This release requires a constant expansion weight within each stratum. "
            f"Variable weights were detected in: {affected}. Use a design-specific "
            "survey estimator for unequal-probability sampling within strata."
        )

    grouped = work.groupby("stratum", sort=False)
    small = grouped.size()
    if (small < 2).any():
        affected = ", ".join(map(str, small[small < 2].index.tolist()))
        raise ValueError(
            "At least two valid observations are required in every stratum to "
            f"estimate within-stratum variance. Insufficient strata: {affected}."
        )

    strata_rows = []
    for label, group in grouped:
        n_h = len(group)
        w_h = float(group["weight"].iloc[0] * n_h)
        strata_rows.append({
            "stratum": str(label),
            "sample_n": int(n_h),
            "expansion_weight_per_record": float(group["weight"].iloc[0]),
            "estimated_population_total": w_h,
        })
    total_weight = float(work["weight"].sum())
    df_resid = int(sum(len(g) - 1 for _, g in grouped))
    metadata = {
        "records_in_dataset": int(len(df)),
        "records_used": int(len(work)),
        "records_excluded": int(len(df) - len(work)),
        "number_of_strata": int(work["stratum"].nunique()),
        "sum_of_weights": total_weight,
        "residual_degrees_of_freedom": df_resid,
        "weight_structure": "constant expansion weight within each stratum",
        "variance_method": "stratified SRS Taylor linearization; no finite population correction",
        "strata_summary": pd.DataFrame(strata_rows),
    }
    return work, metadata


def _estimate_stratified(
    work: pd.DataFrame,
    value: pd.Series,
    confidence_level: float,
) -> dict[str, float]:
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    total_weight = float(work["weight"].sum())
    estimate = 0.0
    variance = 0.0
    for _, group in work.assign(_value=value).groupby("stratum", sort=False):
        x = group["_value"].to_numpy(dtype=float)
        n_h = len(x)
        stratum_weight = float(group["weight"].sum())
        mean_h = float(np.mean(x))
        sample_variance_h = float(np.var(x, ddof=1))
        share_h = stratum_weight / total_weight
        estimate += share_h * mean_h
        variance += (share_h**2) * sample_variance_h / n_h

    standard_error = float(np.sqrt(max(variance, 0.0)))
    degrees_freedom = int(
        sum(len(group) - 1 for _, group in work.groupby("stratum", sort=False))
    )
    critical = float(t.ppf(1 - (1 - confidence_level) / 2, degrees_freedom))
    lower = estimate - critical * standard_error
    upper = estimate + critical * standard_error
    return {
        "estimate": float(estimate),
        "standard_error": standard_error,
        "confidence_level": float(confidence_level),
        "confidence_interval_lower": float(lower),
        "confidence_interval_upper": float(upper),
        "degrees_of_freedom": degrees_freedom,
    }


def stratified_weighted_mean(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    strata_variable: str,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a stratified weighted mean and design-based standard error."""
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome variable must be numeric for a stratified mean.")
    work, metadata = _prepare_stratified_data(
        df, outcome_variable, weight_variable, strata_variable
    )
    estimate = _estimate_stratified(work, work["outcome"], confidence_level)
    x = work["outcome"].astype(float)
    weighted_total = float(np.sum(work["weight"].to_numpy() * x.to_numpy()))
    metadata.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "strata_variable": strata_variable,
        "weighted_total": weighted_total,
        "estimate_type": "stratified weighted mean",
    })
    table = pd.DataFrame([{
        "outcome": outcome_variable,
        "stratified_weighted_mean": estimate["estimate"],
        "standard_error": estimate["standard_error"],
        "confidence_level": estimate["confidence_level"],
        "ci_lower": estimate["confidence_interval_lower"],
        "ci_upper": estimate["confidence_interval_upper"],
        "weighted_total": weighted_total,
        "records_used": metadata["records_used"],
        "number_of_strata": metadata["number_of_strata"],
    }])
    warnings = [
        "Inference assumes independent simple random sampling within each stratum and constant expansion weights within strata.",
        "No finite population correction is applied; standard errors may be conservative when sampling fractions are substantial.",
        "This release does not adjust for PSU clustering, multistage sampling, unequal-probability selection within strata or replicate weights.",
        "The supplied expansion weights must represent stratum population expansion factors for the weighted mean to target the intended population.",
    ]
    return {
        "table": table,
        "strata_summary": metadata.pop("strata_summary"),
        "metadata": metadata | estimate,
        "findings": [
            f"Stratified weighted mean of {outcome_variable}: {estimate['estimate']:.4g}.",
            f"Design-based standard error: {estimate['standard_error']:.4g}.",
            f"{metadata['number_of_strata']} strata and {metadata['records_used']:,} records contributed.",
        ],
        "warnings": warnings,
    }


def stratified_weighted_frequencies(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    strata_variable: str,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate weighted category proportions and stratified confidence intervals."""
    work, metadata = _prepare_stratified_data(
        df, outcome_variable, weight_variable, strata_variable
    )
    categories = list(pd.unique(work["outcome"]))
    rows = []
    for category in categories:
        indicator = work["outcome"].eq(category).astype(float)
        estimate = _estimate_stratified(work, indicator, confidence_level)
        rows.append({
            "response": str(category),
            "weighted_percent": estimate["estimate"] * 100,
            "standard_error_percentage_points": estimate["standard_error"] * 100,
            "ci_lower_percent": estimate["confidence_interval_lower"] * 100,
            "ci_upper_percent": estimate["confidence_interval_upper"] * 100,
            "unweighted_n": int((work["outcome"] == category).sum()),
            "weighted_count": float(work.loc[work["outcome"] == category, "weight"].sum()),
        })
    table = pd.DataFrame(rows).sort_values(
        "weighted_percent", ascending=False
    ).reset_index(drop=True)
    metadata.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "strata_variable": strata_variable,
        "estimate_type": "stratified weighted category proportions",
        "confidence_level": float(confidence_level),
    })
    warnings = [
        "Inference assumes independent simple random sampling within each stratum and constant expansion weights within strata.",
        "No finite population correction is applied; standard errors may be conservative when sampling fractions are substantial.",
        "This release does not adjust for PSU clustering, multistage sampling, unequal-probability selection within strata or replicate weights.",
        "The supplied expansion weights must represent stratum population expansion factors for estimates to target the intended population.",
    ]
    return {
        "table": table,
        "strata_summary": metadata.pop("strata_summary"),
        "metadata": metadata,
        "findings": [
            f"Stratified weighted proportions were estimated for {len(categories)} response categories.",
            f"{metadata['number_of_strata']} strata and {metadata['records_used']:,} records contributed.",
        ],
        "warnings": warnings,
    }
