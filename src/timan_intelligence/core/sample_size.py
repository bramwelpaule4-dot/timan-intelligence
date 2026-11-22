"""Survey sample-size determination and sampling allocation utilities.

Calculations are planning approximations. Users must supply defensible design
inputs; the engine never infers variability, prevalence, ICC or response rate.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


def _positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be finite and {qualifier}.")
    return result


def calculate_sample_size(
    parameter: str = "proportion",
    confidence_level: float = 0.95,
    margin_of_error: float = 0.05,
    population_size: int | None = None,
    prevalence: float = 0.5,
    standard_deviation: float | None = None,
    design_effect: float = 1.0,
    nonresponse_rate: float = 0.0,
) -> dict[str, Any]:
    """Calculate respondent sample size for a proportion or mean.

    Formula: z² p(1-p)/e² for proportions, or z² s²/e² for means.
    Apply finite population correction, design effect, then nonresponse
    inflation. The result is rounded upward at each operational stage.
    """
    if parameter not in {"proportion", "mean"}:
        raise ValueError("parameter must be 'proportion' or 'mean'.")
    confidence = _positive("confidence_level", confidence_level)
    if confidence >= 1:
        raise ValueError("confidence_level must be less than 1.")
    error = _positive("margin_of_error", margin_of_error)
    if error >= 1 and parameter == "proportion":
        raise ValueError("For a proportion, margin_of_error must be less than 1.")
    deff = _positive("design_effect", design_effect)
    nr = _positive("nonresponse_rate", nonresponse_rate, allow_zero=True)
    if nr >= 1:
        raise ValueError("nonresponse_rate must be less than 1.")
    if population_size is not None:
        if isinstance(population_size, bool) or int(population_size) != population_size or population_size <= 0:
            raise ValueError("population_size must be a positive integer.")
        population_size = int(population_size)

    z = float(norm.ppf(1 - (1 - confidence) / 2))
    if parameter == "proportion":
        p = _positive("prevalence", prevalence, allow_zero=True)
        if p > 1:
            raise ValueError("prevalence must be between 0 and 1.")
        base = z * z * p * (1 - p) / (error * error)
        assumption = f"Planning prevalence p={p:g}."
    else:
        if standard_deviation is None:
            raise ValueError("standard_deviation is required for a mean.")
        sd = _positive("standard_deviation", standard_deviation)
        base = z * z * sd * sd / (error * error)
        assumption = f"Supplied planning standard deviation={sd:g}."

    infinite_population_n = int(math.ceil(base))
    if population_size is None:
        fpc_n = infinite_population_n
        fpc_applied = False
    else:
        fpc_n = int(math.ceil((population_size * base) / (population_size + base - 1)))
        fpc_n = min(population_size, fpc_n)
        fpc_applied = True
    design_adjusted = int(math.ceil(fpc_n * deff))
    final_n = int(math.ceil(design_adjusted / (1 - nr)))
    if population_size is not None:
        final_n = min(population_size, final_n)
    return {
        "parameter": parameter,
        "confidence_level": confidence,
        "z_value": z,
        "margin_of_error": error,
        "population_size": population_size,
        "base_sample_size": infinite_population_n,
        "sample_size_after_fpc": fpc_n,
        "finite_population_correction_applied": fpc_applied,
        "design_effect": deff,
        "sample_size_after_design_effect": design_adjusted,
        "nonresponse_rate": nr,
        "recommended_sample_size": final_n,
        "assumptions": [assumption, "Normal-approximation planning formula.", "Design effect is applied after finite population correction."],
        "warnings": [
            "The requested precision is nominal; clustering, weighting, stratification and analysis-specific variance may require a more detailed design calculation."
        ],
    }


def allocate_stratified_sample(
    strata: pd.DataFrame,
    total_sample_size: int,
    allocation: str = "proportional",
    population_column: str = "population",
    standard_deviation_column: str | None = None,
    cost_column: str | None = None,
) -> dict[str, Any]:
    """Allocate integer sample across strata using largest-remainder rounding."""
    if not isinstance(strata, pd.DataFrame) or strata.empty:
        raise ValueError("A non-empty strata DataFrame is required.")
    if isinstance(total_sample_size, bool) or int(total_sample_size) != total_sample_size or total_sample_size <= 0:
        raise ValueError("total_sample_size must be a positive integer.")
    if population_column not in strata or strata[population_column].isna().any():
        raise ValueError("A complete stratum population column is required.")
    pop = pd.to_numeric(strata[population_column], errors="coerce").to_numpy(float)
    if not np.isfinite(pop).all() or (pop <= 0).any():
        raise ValueError("Stratum populations must be positive and finite.")
    if len(pop) < 1:
        raise ValueError("At least one stratum is required.")
    if allocation not in {"proportional", "equal", "neyman"}:
        raise ValueError("allocation must be proportional, equal or neyman.")
    if total_sample_size < len(pop):
        raise ValueError("The total sample must allow at least one respondent per stratum.")
    if allocation == "proportional":
        weights = pop.copy()
    elif allocation == "equal":
        weights = np.ones(len(pop))
    else:
        if not standard_deviation_column or standard_deviation_column not in strata:
            raise ValueError("Neyman allocation requires a standard deviation column.")
        sd = pd.to_numeric(strata[standard_deviation_column], errors="coerce").to_numpy(float)
        if not np.isfinite(sd).all() or (sd <= 0).any():
            raise ValueError("Stratum standard deviations must be positive and finite.")
        weights = pop * sd
        if cost_column:
            if cost_column not in strata:
                raise ValueError("The supplied cost column was not found.")
            costs = pd.to_numeric(strata[cost_column], errors="coerce").to_numpy(float)
            if not np.isfinite(costs).all() or (costs <= 0).any():
                raise ValueError("Stratum costs must be positive and finite.")
            weights = weights / np.sqrt(costs)
    raw = total_sample_size * weights / weights.sum()
    allocation_values = np.floor(raw).astype(int)
    allocation_values = np.maximum(allocation_values, 1)
    # Reconcile minimum-one constraints while preserving the requested total.
    while allocation_values.sum() > total_sample_size:
        candidates = np.where(allocation_values > 1)[0]
        if not len(candidates):
            raise ValueError("Cannot satisfy minimum allocation at the requested total.")
        idx = candidates[np.argmin(raw[candidates] - allocation_values[candidates])]
        allocation_values[idx] -= 1
    remainder = total_sample_size - int(allocation_values.sum())
    order = np.argsort(-(raw - np.floor(raw)))
    for idx in order[:remainder]:
        allocation_values[idx] += 1
    output = strata.copy()
    output["allocated_sample"] = allocation_values
    output["sampling_fraction"] = allocation_values / pop
    return {
        "allocation": output,
        "total_sample_size": int(total_sample_size),
        "allocation_method": allocation,
        "assumptions": ["At least one respondent is allocated to every stratum.", "Largest-remainder integer rounding is used."],
        "warnings": ["Neyman allocation is variance-efficient for a single outcome under its supplied variability and cost assumptions; it may not be optimal for multiple outcomes." ] if allocation == "neyman" else [],
    }


def plan_cluster_sample(
    total_respondents: int,
    average_cluster_size: int,
    intraclass_correlation: float,
    nonresponse_rate: float = 0.0,
    target_clusters: int | None = None,
) -> dict[str, Any]:
    """Plan a clustered sample using DEFF=1+(m-1)*ICC."""
    for name, value in (("total_respondents", total_respondents), ("average_cluster_size", average_cluster_size)):
        if isinstance(value, bool) or int(value) != value or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    icc = _positive("intraclass_correlation", intraclass_correlation, allow_zero=True)
    if icc > 1:
        raise ValueError("intraclass_correlation must be between 0 and 1.")
    nr = _positive("nonresponse_rate", nonresponse_rate, allow_zero=True)
    if nr >= 1:
        raise ValueError("nonresponse_rate must be less than 1.")
    deff = 1 + (int(average_cluster_size) - 1) * icc
    adjusted = int(math.ceil(int(total_respondents) / (1 - nr)))
    clusters = int(math.ceil(adjusted / int(average_cluster_size)))
    if target_clusters is not None:
        if isinstance(target_clusters, bool) or int(target_clusters) != target_clusters or target_clusters <= 0:
            raise ValueError("target_clusters must be a positive integer.")
        clusters = int(target_clusters)
        adjusted = clusters * int(average_cluster_size)
    return {
        "design_effect": deff,
        "average_cluster_size": int(average_cluster_size),
        "intraclass_correlation": icc,
        "target_respondents": int(total_respondents),
        "respondents_to_approach": adjusted,
        "number_of_clusters": clusters,
        "planned_respondents_per_cluster": int(average_cluster_size),
        "total_cluster_capacity": clusters * int(average_cluster_size),
        "nonresponse_rate": nr,
        "assumptions": ["Equal average cluster size.", "Common ICC across clusters.", "Design effect uses 1 + (m - 1) × ICC."],
        "warnings": ["The cluster formula is an approximation; unequal cluster sizes, stratification and multistage selection may change variance."],
    }
