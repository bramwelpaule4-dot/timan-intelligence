"""Survey weight construction, nonresponse adjustment and calibration."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _positive_numeric(values: pd.Series, label: str) -> np.ndarray:
    array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(array).all() or (array <= 0).any():
        raise ValueError(f"{label} must contain positive finite values.")
    return array


def calculate_base_weights(
    frame: pd.DataFrame, inclusion_probability_column: str
) -> pd.Series:
    """Horvitz-Thompson base weights, 1/pi_i, from exact unit inclusion probabilities."""
    if inclusion_probability_column not in frame:
        raise ValueError("The inclusion-probability column is missing.")
    pi = pd.to_numeric(frame[inclusion_probability_column], errors="coerce").to_numpy(float)
    if not np.isfinite(pi).all() or (pi <= 0).any() or (pi > 1).any():
        raise ValueError("Exact first-order inclusion probabilities must be in (0, 1].")
    return pd.Series(1.0 / pi, index=frame.index, name="base_weight")


def adjust_nonresponse(
    frame: pd.DataFrame,
    base_weight_column: str,
    response_column: str,
    adjustment_cells: list[str],
) -> pd.Series:
    """Multiply base weights by inverse weighted response rates within cells."""
    if not adjustment_cells or any(c not in frame for c in adjustment_cells):
        raise ValueError("Valid nonresponse adjustment-cell columns are required.")
    if base_weight_column not in frame or response_column not in frame:
        raise ValueError("Base-weight and response-indicator columns are required.")
    weights = _positive_numeric(frame[base_weight_column], "Base weights")
    response = pd.to_numeric(frame[response_column], errors="coerce").to_numpy(float)
    if not np.isin(response, [0, 1]).all():
        raise ValueError("Response indicator must contain only 0 (nonrespondent) and 1 (respondent).")
    if (response == 0).all():
        raise ValueError("No respondents are present.")
    if frame[adjustment_cells].isna().any().any():
        raise ValueError("Nonresponse adjustment-cell variables cannot contain missing values.")
    grouped = frame.reset_index(drop=True).groupby(adjustment_cells, sort=False).groups
    rate_map = {}
    for key, index in grouped.items():
        normalized_key = key if isinstance(key, tuple) else (key,)
        positions = np.asarray(index, dtype=int)
        cell_weight = weights[positions]
        cell_response = response[positions]
        rate_map[normalized_key] = float(np.dot(cell_weight, cell_response) / cell_weight.sum())
    keys = [tuple(row) for row in frame[adjustment_cells].to_numpy()]
    factors = np.array([rate_map.get(key, np.nan) for key in keys])
    if not np.isfinite(factors).all() or (factors <= 0).any():
        raise ValueError("Every adjustment cell must contain at least one respondent.")
    adjusted = weights / factors
    return pd.Series(adjusted, index=frame.index, name="nonresponse_adjusted_weight")


def calibrate_poststratification(
    frame: pd.DataFrame,
    weight_column: str,
    poststrata_column: str,
    population_totals: dict[Any, float],
) -> pd.Series:
    """Calibrate weights to known population totals for one post-stratification variable."""
    if weight_column not in frame or poststrata_column not in frame:
        raise ValueError("Weight and post-stratification columns are required.")
    weights = _positive_numeric(frame[weight_column], "Weights")
    if not population_totals:
        raise ValueError("Population totals are required.")
    result = weights.copy()
    observed = set(frame[poststrata_column].dropna().unique())
    if frame[poststrata_column].isna().any() or observed != set(population_totals):
        raise ValueError("Population-total categories must exactly match observed sample categories.")
    for category, target in population_totals.items():
        target = float(target)
        if not np.isfinite(target) or target <= 0:
            raise ValueError("Population totals must be positive and finite.")
        mask = frame[poststrata_column].to_numpy() == category
        denominator = result[mask].sum()
        if denominator <= 0:
            raise ValueError(f"Category {category!r} has no positive sample weight.")
        result[mask] *= target / denominator
    return pd.Series(result, index=frame.index, name="calibrated_weight")


def rake_weights(
    frame: pd.DataFrame,
    weight_column: str,
    margins: dict[str, dict[Any, float]],
    max_iterations: int = 100,
    tolerance: float = 1e-6,
) -> tuple[pd.Series, dict[str, Any]]:
    """Iterative proportional fitting to supplied one-way population margins."""
    if weight_column not in frame or not margins:
        raise ValueError("A weight column and at least one population margin are required.")
    if max_iterations < 1 or tolerance <= 0:
        raise ValueError("Iteration limit and tolerance must be positive.")
    weights = _positive_numeric(frame[weight_column], "Weights")
    for column, targets in margins.items():
        if column not in frame or not targets:
            raise ValueError(f"Missing or empty population margin for {column!r}.")
        if frame[column].isna().any() or set(frame[column].unique()) != set(targets):
            raise ValueError(f"Margin categories for {column!r} must exactly match sample categories.")
        vals = np.asarray(list(targets.values()), dtype=float)
        if not np.isfinite(vals).all() or (vals <= 0).any():
            raise ValueError("Raking targets must be positive and finite.")
    converged = False
    max_relative_error = float("inf")
    iteration = 0
    for iteration in range(1, int(max_iterations) + 1):
        for column, targets in margins.items():
            for category, target in targets.items():
                mask = frame[column].to_numpy() == category
                current = weights[mask].sum()
                if current <= 0:
                    raise ValueError(f"Raking category {category!r} has zero current weight.")
                weights[mask] *= float(target) / current
        errors = []
        for column, targets in margins.items():
            for category, target in targets.items():
                current = weights[frame[column].to_numpy() == category].sum()
                errors.append(abs(current - float(target)) / float(target))
        max_relative_error = max(errors, default=0.0)
        if max_relative_error <= tolerance:
            converged = True
            break
    return pd.Series(weights, index=frame.index, name="raked_weight"), {
        "converged": converged, "iterations": iteration,
        "maximum_relative_margin_error": max_relative_error,
        "tolerance": tolerance,
    }


def trim_weights(
    frame: pd.DataFrame, weight_column: str, lower_quantile: float = 0.01,
    upper_quantile: float = 0.99, preserve_total: bool = True,
) -> pd.Series:
    """Winsorise weights at specified sample quantiles; optionally preserve their sum."""
    if weight_column not in frame:
        raise ValueError("Weight column is missing.")
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise ValueError("Quantiles must satisfy 0 <= lower < upper <= 1.")
    weights = _positive_numeric(frame[weight_column], "Weights")
    low, high = np.quantile(weights, [lower_quantile, upper_quantile])
    trimmed = np.clip(weights, low, high)
    if preserve_total:
        trimmed *= weights.sum() / trimmed.sum()
    return pd.Series(trimmed, index=frame.index, name="trimmed_weight")


def weight_diagnostics(weights: pd.Series) -> dict[str, float]:
    values = _positive_numeric(weights, "Weights")
    mean = float(values.mean())
    sd = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    cv = sd / mean if mean else float("nan")
    kish = float(values.sum() ** 2 / np.square(values).sum())
    return {
        "n": int(len(values)), "sum_weights": float(values.sum()),
        "minimum": float(values.min()), "maximum": float(values.max()),
        "mean": mean, "standard_deviation": sd, "coefficient_of_variation": cv,
        "kish_effective_sample_size": kish,
        "kish_deff_approximation": float(len(values) / kish) if kish else float("nan"),
    }
