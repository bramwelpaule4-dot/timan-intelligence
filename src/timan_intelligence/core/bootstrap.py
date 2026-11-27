"""Guarded IID nonparametric bootstrap confidence intervals."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from timan_intelligence.core.contracts import AnalysisResult


def run_bootstrap_confidence_interval(
    df: pd.DataFrame,
    analysis_variable: str,
    statistic: str = "mean",
    category_value: Any = None,
    confidence_level: float = 0.95,
    n_resamples: int = 2000,
    random_state: int | None = None,
) -> AnalysisResult:
    """Estimate a percentile bootstrap interval for an IID mean, median or proportion."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(analysis_variable, str) or analysis_variable not in df.columns:
        raise ValueError("Select a valid analysis variable.")
    if statistic not in {"mean", "median", "proportion"}:
        raise ValueError("Statistic must be mean, median or proportion.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    level = float(confidence_level)
    if not 0 < level < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, (int, np.integer)):
        raise TypeError("n_resamples must be an integer.")
    if not 1000 <= int(n_resamples) <= 50000:
        raise ValueError("n_resamples must be between 1000 and 50000.")
    if random_state is not None and (
        isinstance(random_state, bool) or not isinstance(random_state, (int, np.integer))
    ):
        raise TypeError("random_state must be an integer or None.")

    series = df[analysis_variable]
    excluded = 0
    if statistic in {"mean", "median"}:
        if not pd.api.types.is_numeric_dtype(series):
            raise TypeError(f"The {statistic} bootstrap requires a numeric analysis variable.")
        numeric = pd.to_numeric(series, errors="coerce")
        finite = numeric.notna() & np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
        values = numeric.loc[finite].to_numpy(dtype=float)
        excluded = int(len(series) - len(values))
        if statistic == "mean":
            estimate = float(np.mean(values)) if len(values) else float("nan")
            statistic_function = np.mean
        else:
            estimate = float(np.median(values)) if len(values) else float("nan")
            statistic_function = np.median
    else:
        if category_value is None or not np.isscalar(category_value):
            raise ValueError("A scalar category_value is required for a proportion bootstrap.")
        complete = series.notna()
        values = series.loc[complete].to_numpy()
        excluded = int(len(series) - len(values))
        if len(values) and not bool(pd.Series(values).eq(category_value).any()):
            raise ValueError("category_value does not occur in the observed data.")
        estimate = float(np.mean(pd.Series(values).eq(category_value).to_numpy(dtype=float))) if len(values) else float("nan")
        statistic_function = lambda sample: float(np.mean(pd.Series(sample).eq(category_value).to_numpy(dtype=float)))

    n = int(len(values))
    if n < 10:
        raise ValueError("At least 10 complete finite observations are required for bootstrap estimation.")

    rng = np.random.default_rng(None if random_state is None else int(random_state))
    bootstrap_estimates = np.empty(int(n_resamples), dtype=float)
    for index in range(int(n_resamples)):
        sample = rng.choice(values, size=n, replace=True)
        bootstrap_estimates[index] = float(statistic_function(sample))

    alpha = 1.0 - level
    lower, upper = np.quantile(
        bootstrap_estimates, [alpha / 2.0, 1.0 - alpha / 2.0]
    )
    bootstrap_se = float(np.std(bootstrap_estimates, ddof=1))
    bootstrap_bias = float(np.mean(bootstrap_estimates) - estimate)
    bootstrap_mean_mcse = float(bootstrap_se / np.sqrt(int(n_resamples)))
    summary = pd.DataFrame([{
        "statistic": statistic,
        "estimate": estimate,
        "confidence_level": level,
        "ci_lower": float(lower),
        "ci_upper": float(upper),
        "bootstrap_standard_error": bootstrap_se,
        "bootstrap_bias": bootstrap_bias,
        "bootstrap_resamples": int(n_resamples),
        "successful_resamples": int(n_resamples),
        "bootstrap_mean_mcse": bootstrap_mean_mcse,
        "complete_observations": n,
        "excluded_observations": excluded,
    }])
    findings = [
        f"Bootstrap {statistic} estimate: {estimate:.5g}.",
        f"{level:.1%} percentile bootstrap confidence interval: [{float(lower):.5g}, {float(upper):.5g}].",
        f"{int(n_resamples):,} IID row-level resamples completed; bootstrap standard error: {bootstrap_se:.5g}.",
    ]
    limitations = [
        "Uses an IID row-level nonparametric percentile bootstrap; each row is treated as an independent resampling unit.",
        "Not valid for clustered, stratified, multistage, paired, longitudinal or time-series designs without a design-specific resampling scheme.",
        "The Monte Carlo standard error is for the bootstrap replicate mean, not for the confidence-interval endpoints.",
        "Percentile intervals can have poor coverage for strongly biased or non-smooth statistics; assess whether a bootstrap interval is appropriate for the estimand.",
    ]
    if excluded:
        limitations.append(f"{excluded:,} rows with missing or non-finite analysis values were excluded before resampling.")
    return AnalysisResult(
        title=f"Bootstrap confidence interval: {statistic} of {analysis_variable}",
        method="IID nonparametric percentile bootstrap",
        status="success",
        tables={"bootstrap_summary": summary},
        findings=findings,
        assumptions=[
            "The observed rows are independent and identically distributed sampling units.",
            "The empirical distribution is a suitable approximation to the target population distribution.",
            "The selected statistic is defined for the observed sample and bootstrap resamples.",
        ],
        limitations=limitations,
        metadata={
            "analysis_variable": analysis_variable,
            "statistic": statistic,
            "category_value": str(category_value) if statistic == "proportion" else None,
            "confidence_level": level,
            "n_resamples": int(n_resamples),
            "random_state": None if random_state is None else int(random_state),
            "bootstrap_scheme": "IID row-level percentile",
            "resampling_unit": "observation_row",
            "sampling_design_aware": False,
            "complete_observations": n,
            "excluded_observations": excluded,
            "bootstrap_standard_error": bootstrap_se,
            "bootstrap_bias": bootstrap_bias,
            "bootstrap_mean_mcse": bootstrap_mean_mcse,
        },
    )
