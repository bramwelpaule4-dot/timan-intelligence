"""PPS without-replacement (PPSWOR) Horvitz-Thompson estimator.

This first release is deliberately PSU-level: each row must contain a fully
observed PSU total. Two-stage SSU sampling is not inferred or approximated.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def estimate_ppswor_total(
    df: pd.DataFrame,
    outcome_total_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate stratified HT totals and SYG variance from supplied pi_i/pi_ij.

    The joint-probability matrix must be indexed and columned by sampled PSU
    identifiers (or, when stratified, supplied as {stratum: matrix}). Its
    off-diagonal entries must be the actual design joint inclusion
    probabilities for the corresponding sampled PSU pairs.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    required = [outcome_total_variable, psu_variable, inclusion_probability_variable]
    if strata_variable:
        required.append(strata_variable)
    if len(set(required)) != len(required):
        raise ValueError("Outcome, PSU, inclusion probability and stratum variables must be different.")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")
    work = df[required].copy()
    if work[psu_variable].isna().any() or work[psu_variable].astype(str).str.strip().eq("").any():
        raise ValueError("PSU identifiers cannot be missing.")
    if work.duplicated([strata_variable, psu_variable] if strata_variable else [psu_variable]).any():
        raise ValueError("PPSWOR input must contain exactly one row per sampled PSU.")
    y = pd.to_numeric(work[outcome_total_variable], errors="coerce")
    pi = pd.to_numeric(work[inclusion_probability_variable], errors="coerce")
    if y.isna().any() or not np.isfinite(y.to_numpy(dtype=float)).all():
        raise ValueError("PSU outcome totals must be complete, numeric and finite.")
    if pi.isna().any() or not np.isfinite(pi.to_numpy(dtype=float)).all():
        raise ValueError("First-order inclusion probabilities must be complete, numeric and finite.")
    if ((pi <= 0) | (pi > 1)).any():
        raise ValueError("First-order inclusion probabilities must be in (0, 1].")
    work["__y__"] = y.astype(float)
    work["__pi__"] = pi.astype(float)
    work["__stratum__"] = work[strata_variable] if strata_variable else "__ALL__"
    if work["__stratum__"].isna().any():
        raise ValueError("Stratum identifiers cannot be missing.")

    estimate = variance = 0.0
    df_total = 0
    stratum_rows = []
    pair_rows = []
    for h, group in work.groupby("__stratum__", sort=False):
        ids = group[psu_variable].tolist()
        n = len(group)
        if n < 2:
            raise ValueError(f"At least two sampled PSUs are required in stratum {h!r} for SYG variance estimation.")
        matrix = (
            joint_inclusion_probabilities.get(h)
            if isinstance(joint_inclusion_probabilities, dict)
            else joint_inclusion_probabilities
        )
        if not isinstance(matrix, pd.DataFrame):
            raise ValueError(f"A joint-inclusion matrix is required for stratum {h!r}.")
        if not matrix.index.is_unique or not matrix.columns.is_unique:
            raise ValueError("Joint-inclusion matrix row and column labels must be unique.")
        absent = [v for v in ids if v not in matrix.index or v not in matrix.columns]
        if absent:
            raise ValueError(f"Joint-inclusion matrix is missing sampled PSU labels: {absent}.")
        sub = matrix.loc[ids, ids].apply(pd.to_numeric, errors="coerce")
        values = sub.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Required joint inclusion probabilities must be numeric and finite.")
        if not np.allclose(values, values.T, rtol=1e-9, atol=1e-12):
            raise ValueError("Joint inclusion probabilities must be symmetric.")
        p = group["__pi__"].to_numpy(dtype=float)
        if not np.allclose(np.diag(values), p, rtol=1e-8, atol=1e-10):
            raise ValueError("Joint-inclusion matrix diagonal must equal the supplied first-order inclusion probabilities.")
        if np.any(values < 0) or np.any(values > 1 + 1e-10):
            raise ValueError("Joint inclusion probabilities must lie between zero and one.")
        if np.any(values - np.minimum.outer(p, p) > 1e-10):
            raise ValueError("A joint inclusion probability cannot exceed either corresponding first-order probability.")
        off_diagonal = values[~np.eye(n, dtype=bool)]
        if np.any(off_diagonal <= 0):
            raise ValueError(
                "The SYG variance estimator requires positive joint inclusion probabilities for every sampled PSU pair; this design has a zero-probability pair."
            )
        lower_bounds = np.maximum(0.0, p[:, None] + p[None, :] - 1.0)
        if np.any(values + 1e-10 < lower_bounds):
            raise ValueError("A joint inclusion probability is below its probability-theory lower bound.")
        y_values = group["__y__"].to_numpy(dtype=float)
        estimate_h = float(np.sum(y_values / p))
        variance_h = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                pij = float(values[i, j])
                if pij <= 0:
                    raise ValueError(
                        "The SYG variance estimator requires positive joint inclusion probabilities for every sampled PSU pair; this design has a zero-probability pair."
                    )
                delta = pij - p[i] * p[j]
                term = -(delta / pij) * (y_values[i] / p[i] - y_values[j] / p[j]) ** 2
                variance_h += float(term)
                pair_rows.append({
                    "stratum": str(h), "psu_i": str(ids[i]), "psu_j": str(ids[j]),
                    "pi_i": float(p[i]), "pi_j": float(p[j]), "pi_ij": pij,
                    "variance_contribution": float(term),
                })
        if variance_h < -1e-8:
            raise ValueError(
                "The supplied joint inclusion probabilities do not yield a non-negative Sen-Yates-Grundy variance estimate for this sample; use a design-compatible variance estimator."
            )
        variance_h = max(0.0, float(variance_h))
        estimate += estimate_h
        variance += variance_h
        df_total += n - 1
        stratum_rows.append({
            "stratum": str(h), "sampled_psus": n, "estimated_total": estimate_h,
            "estimated_variance": variance_h, "sum_first_order_probabilities": float(p.sum()),
        })
    se = float(np.sqrt(variance))
    critical = float(stats.t.ppf(0.5 + confidence_level / 2, df_total))
    ci = (float(estimate - critical * se), float(estimate + critical * se))
    return {
        "estimate": float(estimate), "variance": float(variance),
        "standard_error": se, "confidence_interval": ci,
        "confidence_level": float(confidence_level), "degrees_of_freedom": int(df_total),
        "strata": pd.DataFrame(stratum_rows), "pairwise_variance": pd.DataFrame(pair_rows),
        "findings": [
            f"Horvitz-Thompson estimated population total: {estimate:,.4g}.",
            f"Sen-Yates-Grundy design-based standard error: {se:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{ci[0]:,.4g}, {ci[1]:,.4g}].",
        ],
        "warnings": [
            "This estimator is PSU-level and requires a fully observed total for each sampled PSU; it does not estimate SSU subsampling variance.",
            "The supplied first- and second-order inclusion probabilities must come from the actual fixed-size PPSWOR design.",
            "The Sen-Yates-Grundy variance estimator requires positive joint inclusion probabilities for every sampled PSU pair represented in the sample.",
            "PPSWR probabilities, size measures, normalized weights, or reconstructed joint probabilities are not substitutes for design inclusion probabilities.",
            "The t interval uses sum(n_h - 1) degrees of freedom as an approximation; small-sample design inference should be interpreted cautiously.",
        ],
        "metadata": {
            "estimator": "Stratified Horvitz-Thompson total with Sen-Yates-Grundy variance",
            "sampling_design": "PPS without replacement; fixed-size sample within each stratum",
            "number_of_strata": int(work["__stratum__"].nunique()),
            "number_of_sampled_psus": int(len(work)),
            "degrees_of_freedom": int(df_total),
            "inclusion_probability_variable": inclusion_probability_variable,
            "joint_inclusion_probabilities_supplied": True,
        },
    }
