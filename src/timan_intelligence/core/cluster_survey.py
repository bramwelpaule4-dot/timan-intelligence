"""Cluster-adjusted survey estimators using PSU-level Taylor linearization.

Supports one-stage cluster samples, optionally stratified, with independent
PSUs within strata. Uses a with-replacement ultimate-cluster variance estimator.
It does not support multistage sampling, finite population corrections, certainty
PSUs, replicate weights, or domain/subpopulation variance estimation.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t


def _prepare(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    cluster_variable: str,
    strata_variable: str | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    required = [outcome_variable, weight_variable, cluster_variable]
    if strata_variable:
        required.append(strata_variable)
    for column in required:
        if column not in df.columns:
            raise KeyError(f"Variable '{column}' was not found.")
    if len(set(required)) != len(required):
        raise ValueError("Outcome, weight, cluster and stratum variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[weight_variable]):
        raise TypeError("The survey weight variable must be numeric.")
    weights = pd.to_numeric(df[weight_variable], errors="coerce")
    observed_weights = weights.dropna().to_numpy(dtype=float)
    if observed_weights.size == 0 or not np.isfinite(observed_weights).all():
        raise ValueError("Observed survey weights must be finite numeric values.")
    if (observed_weights <= 0).any():
        raise ValueError("All observed survey weights must be strictly positive.")

    clusters = df[cluster_variable].astype("object").map(
        lambda x: x.strip() if isinstance(x, str) else x
    ).replace("", pd.NA)
    if clusters.isna().any():
        raise ValueError("Primary sampling unit (cluster) identifiers cannot be missing.")

    if strata_variable:
        strata = df[strata_variable].astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)
        if strata.isna().any():
            raise ValueError("Stratum identifiers cannot be missing.")
    else:
        strata = pd.Series("__ALL__", index=df.index, dtype="object")

    outcome = df[outcome_variable]
    if pd.api.types.is_numeric_dtype(outcome):
        outcome = pd.to_numeric(outcome, errors="coerce")
        observed = outcome.dropna().to_numpy(dtype=float)
        if not np.isfinite(observed).all():
            raise ValueError("Observed numeric outcomes must be finite.")
    else:
        outcome = outcome.astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)

    work = pd.DataFrame({
        "outcome": outcome, "weight": weights,
        "cluster": clusters, "stratum": strata,
    })
    work = work.loc[work["weight"].notna() & work["outcome"].notna()].copy()
    if work.empty:
        raise ValueError("No complete records with valid outcomes, weights and cluster identifiers remain.")

    # A PSU must belong to exactly one stratum. Cluster IDs may repeat across strata.
    psu_strata = work.groupby("cluster", sort=False)["stratum"].nunique()
    if (psu_strata > 1).any():
        raise ValueError("Each cluster identifier must belong to only one stratum. Create globally unique PSU IDs if needed.")

    psu_counts = work.groupby("stratum", sort=False)["cluster"].nunique()
    if (psu_counts < 2).any():
        bad = ", ".join(map(str, psu_counts[psu_counts < 2].index.tolist()))
        raise ValueError(
            "At least two sampled clusters (PSUs) are required in every stratum "
            f"to estimate cluster variance. Insufficient strata: {bad}."
        )

    cluster_sizes = work.groupby(["stratum", "cluster"], sort=False).size()
    metadata = {
        "records_in_dataset": int(len(df)),
        "records_used": int(len(work)),
        "records_excluded": int(len(df) - len(work)),
        "number_of_strata": int(work["stratum"].nunique()),
        "number_of_clusters": int(len(cluster_sizes)),
        "minimum_cluster_size": int(cluster_sizes.min()),
        "maximum_cluster_size": int(cluster_sizes.max()),
        "sum_of_weights": float(work["weight"].sum()),
        "cluster_variable": cluster_variable,
        "strata_variable": strata_variable,
        "variance_method": "with-replacement ultimate-cluster Taylor linearization",
        "degrees_of_freedom": int(sum(int(n) - 1 for n in psu_counts)),
    }
    return work, metadata


def _ratio_estimate(
    work: pd.DataFrame, value: pd.Series, confidence_level: float
) -> dict[str, float]:
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    total_weight = float(work["weight"].sum())
    estimate = float(np.sum(work["weight"].to_numpy() * value.to_numpy()) / total_weight)
    linearized = work[["stratum", "cluster", "weight"]].copy()
    linearized["score"] = linearized["weight"].to_numpy() * (
        value.to_numpy() - estimate
    )
    variance_total = 0.0
    for _, stratum_data in linearized.groupby("stratum", sort=False):
        psu_scores = stratum_data.groupby("cluster", sort=False)["score"].sum()
        m_h = len(psu_scores)
        centered = psu_scores - psu_scores.mean()
        variance_total += (m_h / (m_h - 1)) * float(np.square(centered).sum())
    variance = variance_total / (total_weight**2)
    se = float(np.sqrt(max(variance, 0.0)))
    df = int(sum(
        stratum_data["cluster"].nunique() - 1
        for _, stratum_data in work.groupby("stratum", sort=False)
    ))
    critical = float(t.ppf(1 - (1 - confidence_level) / 2, df))
    return {
        "estimate": estimate,
        "standard_error": se,
        "confidence_level": float(confidence_level),
        "confidence_interval_lower": estimate - critical * se,
        "confidence_interval_upper": estimate + critical * se,
        "degrees_of_freedom": df,
    }


def cluster_weighted_mean(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    cluster_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a weighted mean with PSU-clustered Taylor standard error."""
    if outcome_variable not in df.columns or not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("The outcome variable must be present and numeric.")
    work, metadata = _prepare(
        df, outcome_variable, weight_variable, cluster_variable, strata_variable
    )
    value = work["outcome"].astype(float)
    estimate = _ratio_estimate(work, value, confidence_level)
    weighted_total = float(np.sum(work["weight"].to_numpy() * value.to_numpy()))
    table = pd.DataFrame([{
        "outcome": outcome_variable,
        "cluster_weighted_mean": estimate["estimate"],
        "standard_error": estimate["standard_error"],
        "confidence_level": estimate["confidence_level"],
        "ci_lower": estimate["confidence_interval_lower"],
        "ci_upper": estimate["confidence_interval_upper"],
        "weighted_total": weighted_total,
        "records_used": metadata["records_used"],
        "number_of_clusters": metadata["number_of_clusters"],
        "number_of_strata": metadata["number_of_strata"],
        "degrees_of_freedom": estimate["degrees_of_freedom"],
    }])
    metadata.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "weighted_total": weighted_total,
        "estimate_type": "cluster-adjusted weighted mean",
    })
    return {
        "table": table,
        "metadata": metadata | estimate,
        "findings": [
            f"Cluster-adjusted weighted mean of {outcome_variable}: {estimate['estimate']:.4g}.",
            f"PSU-clustered standard error: {estimate['standard_error']:.4g}.",
            f"{metadata['number_of_clusters']} clusters across {metadata['number_of_strata']} strata contributed.",
        ],
        "warnings": [
            "Variance uses a with-replacement ultimate-cluster Taylor linearization and assumes independent sampled PSUs within strata.",
            "No finite population correction is applied; this may overestimate variance when PSU sampling fractions are substantial.",
            "This release does not support multistage sampling, certainty PSUs, replicate weights, or domain-specific variance estimation.",
            "The supplied weights must be valid inverse-probability/expansion weights for the target population; the variance estimator does not repair invalid weights.",
        ],
    }


def cluster_weighted_frequencies(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    cluster_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate weighted category proportions with PSU-clustered standard errors."""
    work, metadata = _prepare(
        df, outcome_variable, weight_variable, cluster_variable, strata_variable
    )
    rows = []
    for category in pd.unique(work["outcome"]):
        indicator = work["outcome"].eq(category).astype(float)
        estimate = _ratio_estimate(work, indicator, confidence_level)
        rows.append({
            "response": str(category),
            "weighted_percent": estimate["estimate"] * 100,
            "standard_error_percentage_points": estimate["standard_error"] * 100,
            "ci_lower_percent": estimate["confidence_interval_lower"] * 100,
            "ci_upper_percent": estimate["confidence_interval_upper"] * 100,
            "weighted_count": float(work.loc[work["outcome"] == category, "weight"].sum()),
            "unweighted_n": int((work["outcome"] == category).sum()),
        })
    table = pd.DataFrame(rows).sort_values(
        "weighted_percent", ascending=False
    ).reset_index(drop=True)
    metadata.update({
        "outcome_variable": outcome_variable,
        "weight_variable": weight_variable,
        "estimate_type": "cluster-adjusted weighted category proportions",
        "confidence_level": float(confidence_level),
    })
    return {
        "table": table,
        "metadata": metadata,
        "findings": [
            f"Cluster-adjusted weighted proportions estimated for {len(rows)} categories.",
            f"{metadata['number_of_clusters']} clusters across {metadata['number_of_strata']} strata contributed.",
        ],
        "warnings": [
            "Variance uses a with-replacement ultimate-cluster Taylor linearization and assumes independent sampled PSUs within strata.",
            "No finite population correction is applied; this may overestimate variance when PSU sampling fractions are substantial.",
            "This release does not support multistage sampling, certainty PSUs, replicate weights, or domain-specific variance estimation.",
            "The supplied weights must be valid inverse-probability/expansion weights for the target population; the variance estimator does not repair invalid weights.",
        ],
    }
