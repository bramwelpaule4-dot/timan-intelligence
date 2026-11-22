"""Additional estimands for the two-stage PPSWOR design.

These wrappers deliberately build on the validated total estimator so that
stage-specific variance calculations and inclusion-probability requirements
remain identical across estimands.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from timan_intelligence.core.two_stage_ppswor import estimate_two_stage_ppswor_total


def _scale_total_result(
    output: dict[str, Any],
    denominator: float,
    estimand: str,
    denominator_label: str,
) -> dict[str, Any]:
    """Convert a total and its design variance to a fixed-denominator estimand."""
    estimate = float(output["estimate"] / denominator)
    variance_stage_1 = float(output["variance_stage_1"] / denominator**2)
    variance_stage_2 = float(output["variance_stage_2"] / denominator**2)
    variance = float(variance_stage_1 + variance_stage_2)
    standard_error = float(np.sqrt(variance))
    lower, upper = output["confidence_interval"]
    # Scale the total interval directly; this preserves the total estimator's
    # t critical value and does not impose artificial [0, 1] clipping.
    interval = (float(lower / denominator), float(upper / denominator))
    result = dict(output)
    result.update({
        "estimate": estimate,
        "variance": variance,
        "variance_stage_1": variance_stage_1,
        "variance_stage_2": variance_stage_2,
        "standard_error": standard_error,
        "confidence_interval": interval,
        "findings": [
            f"Two-stage PPSWOR {estimand}: {estimate:,.6g}.",
            f"Design-based standard error: {standard_error:,.6g}.",
            f"{output['confidence_level']:.0%} confidence interval: [{interval[0]:,.6g}, {interval[1]:,.6g}].",
            f"Denominator: {denominator:,.6g} ({denominator_label}).",
        ],
        "metadata": {
            **output["metadata"],
            "estimand": estimand,
            "fixed_denominator": denominator,
            "denominator_definition": denominator_label,
            "variance_method": "Two-stage PPSWOR total variance divided by the square of a known fixed denominator",
        },
    })
    return result


def estimate_two_stage_ppswor_mean(
    df: pd.DataFrame,
    outcome_variable: str,
    population_ssu_total: float,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Estimate an SSU population mean when total population SSUs are known."""
    denominator = float(population_ssu_total)
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("Known population SSU total must be a positive finite number.")
    output = estimate_two_stage_ppswor_total(
        df, outcome_variable, *args, **kwargs
    )
    return _scale_total_result(
        output, denominator, "population mean",
        "known total number of SSUs in the target population",
    )


def estimate_two_stage_ppswor_proportion(
    df: pd.DataFrame,
    outcome_variable: str,
    population_ssu_total: float,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Estimate a population proportion from a binary 0/1 SSU outcome."""
    if outcome_variable not in df.columns:
        raise KeyError(f"Variable not found: {outcome_variable}.")
    values = pd.to_numeric(df[outcome_variable], errors="coerce")
    if values.isna().any() or not values.isin([0, 1]).all():
        raise ValueError("Proportion outcomes must be complete binary values coded 0 and 1.")
    output = estimate_two_stage_ppswor_total(
        df, outcome_variable, *args, **kwargs
    )
    result = _scale_total_result(
        output, float(population_ssu_total), "population proportion",
        "known total number of SSUs in the target population",
    )
    result["warnings"] = list(result["warnings"]) + [
        "The proportion is estimated as a binary-outcome total divided by the known target-population SSU count; the confidence interval is not clipped to [0, 1]."
    ]
    return result


def estimate_two_stage_ppswor_domain_total(
    df: pd.DataFrame,
    outcome_variable: str,
    domain_variable: str,
    domain_value: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Estimate an outcome total for a domain, retaining out-of-domain SSUs as zeros."""
    if domain_variable not in df.columns:
        raise KeyError(f"Variable not found: {domain_variable}.")
    if df[domain_variable].isna().any():
        raise ValueError("Domain identifiers cannot be missing.")
    domain_mask = df[domain_variable].eq(domain_value)
    if not domain_mask.any():
        raise ValueError("The selected domain has no sampled SSUs.")
    outcome = pd.to_numeric(df[outcome_variable], errors="coerce")
    if outcome.loc[domain_mask].isna().any() or not np.isfinite(
        outcome.loc[domain_mask].to_numpy(dtype=float)
    ).all():
        raise ValueError("Outcome values within the selected domain must be complete, numeric and finite.")
    working = df.copy()
    working[outcome_variable] = outcome.where(domain_mask, 0.0)
    output = estimate_two_stage_ppswor_total(
        working, outcome_variable, *args, **kwargs
    )
    result = dict(output)
    result["findings"] = [
        f"Two-stage PPSWOR domain total for {domain_variable}={domain_value}: {output['estimate']:,.6g}.",
        *output["findings"][1:],
    ]
    result["warnings"] = list(output["warnings"]) + [
        "Out-of-domain SSUs are retained in the original sample design and contribute zero to the domain total; they are not dropped before variance estimation."
    ]
    result["metadata"] = {
        **output["metadata"],
        "estimand": "domain total",
        "domain_variable": domain_variable,
        "domain_value": str(domain_value),
        "variance_method": "Two-stage PPSWOR total variance with zero contributions for out-of-domain SSUs",
    }
    return result
