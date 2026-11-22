"""Reproducible probability-sample selection from a sampling frame.

PPSWOR is implemented as successive probability-proportional-to-size sampling.
Its reported probabilities are conditional draw probabilities, NOT exact
first-order inclusion probabilities. Do not pass them to estimators requiring
joint inclusion probabilities.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _validate_frame(frame: pd.DataFrame, id_column: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("A non-empty sampling frame is required.")
    if id_column not in frame.columns:
        raise ValueError("The selected identifier column is not in the frame.")
    if frame[id_column].isna().any() or frame[id_column].duplicated().any():
        raise ValueError("Sampling-frame identifiers must be complete and unique.")
    return frame.reset_index(drop=True).copy()


def _size_weights(frame: pd.DataFrame, size_column: str) -> np.ndarray:
    if size_column not in frame:
        raise ValueError("The selected size-measure column is not in the frame.")
    values = pd.to_numeric(frame[size_column], errors="coerce").to_numpy(float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("PPS size measures must be positive and finite.")
    return values


def _draw(
    frame: pd.DataFrame, id_column: str, method: str, sample_size: int,
    rng: np.random.Generator, size_column: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    n, N = int(sample_size), len(frame)
    if isinstance(sample_size, bool) or n != sample_size or n <= 0:
        raise ValueError("sample_size must be a positive integer.")
    if method not in {"srswor", "srswr", "systematic", "ppswr", "ppswor"}:
        raise ValueError("Unsupported selection method.")
    if method != "srswr" and n > N:
        raise ValueError("Sample size cannot exceed frame size without replacement.")
    warnings: list[str] = []
    if method in {"srswor", "srswr"}:
        indices = rng.choice(N, size=n, replace=(method == "srswr"))
        probs = [1 / N] * n
    elif method == "systematic":
        interval = N / n
        start = rng.uniform(0, interval)
        indices = np.floor(start + np.arange(n) * interval).astype(int)
        probs = [n / N] * n
        warnings.append(
            "Systematic sampling can be affected by periodic ordering in the frame; inspect frame order before fieldwork."
        )
    else:
        if not size_column:
            raise ValueError("PPS selection requires a size-measure column.")
        weights = _size_weights(frame, size_column)
        if method == "ppswr":
            probabilities = weights / weights.sum()
            indices = rng.choice(N, size=n, replace=True, p=probabilities)
            probs = probabilities[indices].tolist()
            warnings.append(
                "PPSWR reports per-draw selection probabilities. Repeated selection of the same unit is possible."
            )
        else:
            remaining = np.arange(N)
            selected: list[int] = []
            probs = []
            for _ in range(n):
                conditional = weights[remaining] / weights[remaining].sum()
                chosen_position = int(rng.choice(len(remaining), p=conditional))
                selected.append(int(remaining[chosen_position]))
                probs.append(float(conditional[chosen_position]))
                remaining = np.delete(remaining, chosen_position)
            indices = np.asarray(selected, dtype=int)
            warnings.append(
                "PPSWOR uses successive conditional size-proportional draws. Reported probabilities are conditional draw probabilities, not exact first-order inclusion probabilities."
            )
    result = frame.iloc[indices].copy()
    result.insert(0, "selection_order", np.arange(1, n + 1))
    result.insert(1, "draw_probability", np.asarray(probs, dtype=float))
    return result.reset_index(drop=True), warnings


def select_sample(
    frame: pd.DataFrame,
    id_column: str,
    sample_size: int,
    method: str = "srswor",
    seed: int = 2026,
    size_column: str | None = None,
    reserve_size: int = 0,
) -> dict[str, Any]:
    """Select a main sample and a separate reserve from one frame."""
    source = _validate_frame(frame, id_column)
    if isinstance(seed, bool) or int(seed) != seed:
        raise ValueError("seed must be an integer.")
    if isinstance(reserve_size, bool) or int(reserve_size) != reserve_size or reserve_size < 0:
        raise ValueError("reserve_size must be a non-negative integer.")
    if method != "srswr" and sample_size + reserve_size > len(source):
        raise ValueError("Main sample plus reserve cannot exceed frame size.")
    rng = np.random.default_rng(int(seed))
    main, warnings = _draw(source, id_column, method, sample_size, rng, size_column)
    remaining = source.loc[~source[id_column].isin(main[id_column])].copy()
    reserve = pd.DataFrame(columns=source.columns)
    if reserve_size:
        reserve_method = "srswor" if method == "srswr" else method
        if reserve_method in {"ppswr", "ppswor"}:
            reserve, reserve_warnings = _draw(
                remaining, id_column, reserve_method, reserve_size, rng, size_column
            )
        else:
            reserve, reserve_warnings = _draw(
                remaining, id_column, reserve_method, reserve_size, rng
            )
        warnings.extend(reserve_warnings)
    main.insert(2, "sample_role", "main")
    if not reserve.empty:
        reserve.insert(2, "sample_role", "reserve")
    combined = pd.concat([main, reserve], ignore_index=True)
    return {
        "selected": main,
        "reserve": reserve,
        "combined": combined,
        "method": method,
        "seed": int(seed),
        "population_size": len(source),
        "sample_size": len(main),
        "reserve_size": len(reserve),
        "warnings": list(dict.fromkeys(warnings)),
        "metadata": {
            "identifier": id_column,
            "method": method,
            "seed": int(seed),
            "population_size": len(source),
            "sample_size": len(main),
            "reserve_size": len(reserve),
            "with_replacement": method == "srswr" or method == "ppswr",
        },
    }


def select_stratified_sample(
    frame: pd.DataFrame,
    id_column: str,
    strata_column: str,
    allocations: dict[Any, int],
    method: str = "srswor",
    seed: int = 2026,
    size_column: str | None = None,
    reserve_allocations: dict[Any, int] | None = None,
) -> dict[str, Any]:
    """Select independently within each stratum using explicit allocations."""
    source = _validate_frame(frame, id_column)
    if strata_column not in source or source[strata_column].isna().any():
        raise ValueError("A complete stratum column is required.")
    if source[strata_column].nunique() != len(allocations):
        raise ValueError("Allocations must cover every observed stratum exactly.")
    if set(source[strata_column].unique()) != set(allocations):
        raise ValueError("Allocation labels must match the observed stratum values.")
    reserve_allocations = reserve_allocations or {key: 0 for key in allocations}
    if set(reserve_allocations) != set(allocations):
        raise ValueError("Reserve allocations must cover every stratum.")
    rng = np.random.default_rng(int(seed))
    selected_parts, reserve_parts, warnings = [], [], []
    for stratum, group in source.groupby(strata_column, sort=False, dropna=False):
        main, notes = _draw(group.reset_index(drop=True), id_column, method, allocations[stratum], rng, size_column)
        remaining = group.loc[~group[id_column].isin(main[id_column])].reset_index(drop=True)
        r_n = reserve_allocations[stratum]
        reserve = pd.DataFrame(columns=source.columns)
        if r_n:
            r_method = "srswor" if method in {"srswr", "ppswr"} else method
            reserve, reserve_notes = _draw(remaining, id_column, r_method, r_n, rng, size_column if r_method == "ppswor" else None)
            notes.extend(reserve_notes)
        main.insert(2, "sample_role", "main")
        if not reserve.empty:
            reserve.insert(2, "sample_role", "reserve")
        selected_parts.append(main)
        reserve_parts.append(reserve)
        warnings.extend(notes)
    selected = pd.concat(selected_parts, ignore_index=True)
    reserve = pd.concat(reserve_parts, ignore_index=True) if reserve_parts else pd.DataFrame()
    return {
        "selected": selected, "reserve": reserve,
        "combined": pd.concat([selected, reserve], ignore_index=True),
        "method": method, "seed": int(seed),
        "population_size": len(source), "sample_size": len(selected),
        "reserve_size": len(reserve),
        "warnings": list(dict.fromkeys(warnings)),
        "metadata": {
            "identifier": id_column, "strata": strata_column, "method": method,
            "seed": int(seed), "population_size": len(source),
            "sample_size": len(selected), "reserve_size": len(reserve),
            "allocation": {str(k): int(v) for k, v in allocations.items()},
        },
    }
