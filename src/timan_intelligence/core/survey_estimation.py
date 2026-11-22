"""Design-aware survey totals, means and category proportions.

Supported designs:
- Stratified one-stage SRSWOR with constant expansion weights within strata.
- One-stage PSU cluster samples using with-replacement ultimate-cluster variance.
- Weighted descriptive estimates without design-based standard errors.

This module intentionally refuses to imply complex-design inference when the
sampling design information is insufficient.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t

from timan_intelligence.core.stratified_survey import (
    stratified_weighted_mean, stratified_weighted_frequencies,
)
from timan_intelligence.core.cluster_survey import (
    cluster_weighted_mean, cluster_weighted_frequencies,
)
from timan_intelligence.core.survey_weights import (
    weighted_numeric_summary, weighted_frequency_table,
)


def _numeric_columns(df: pd.DataFrame, outcome: str, weight: str) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty survey dataset is required.")
    missing = [column for column in (outcome, weight) if column not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")
    y = pd.to_numeric(df[outcome], errors="coerce")
    w = pd.to_numeric(df[weight], errors="coerce")
    if y.isna().any() or w.isna().any():
        raise ValueError("Outcome and weight must be complete for total estimation.")
    if not np.isfinite(y.to_numpy(float)).all():
        raise ValueError("Outcome values must be finite.")
    if not np.isfinite(w.to_numpy(float)).all() or (w <= 0).any():
        raise ValueError("Survey weights must be positive and finite.")
    return y.to_numpy(float), w.to_numpy(float)


def _total_estimate(
    df: pd.DataFrame, outcome: str, weight: str, design: str,
    confidence_level: float, strata: str | None, cluster: str | None,
) -> tuple[pd.DataFrame, dict[str, Any], list[str], pd.DataFrame]:
    y, w = _numeric_columns(df, outcome, weight)
    estimate = float(np.dot(y, w))
    work = pd.DataFrame({"y": y, "w": w}, index=df.index)

    if design == "stratified_srs":
        if not strata or strata not in df:
            raise ValueError("Select a valid stratum variable for stratified estimation.")
        work["stratum"] = df[strata]
        if work["stratum"].isna().any():
            raise ValueError("Stratum identifiers cannot be missing.")
        variance = 0.0
        df_resid = 0
        rows = []
        for label, group in work.groupby("stratum", sort=False):
            n_h = len(group)
            if n_h < 2:
                raise ValueError(f"At least two complete observations are required in stratum {label!r}.")
            if group["w"].nunique() != 1:
                raise ValueError("Stratified total requires a constant expansion weight within each stratum.")
            weight_h = float(group["w"].iloc[0])
            sample_variance = float(group["y"].var(ddof=1))
            variance_h = (n_h * weight_h) ** 2 * sample_variance / n_h
            variance += variance_h
            df_resid += n_h - 1
            rows.append({
                "stratum": str(label), "sample_n": n_h,
                "expansion_weight": weight_h,
                "estimated_population_size": n_h * weight_h,
                "sample_mean": float(group["y"].mean()),
                "estimated_total": float(n_h * weight_h * group["y"].mean()),
                "variance_contribution": float(variance_h),
            })
        method = "Stratified SRSWOR total; Taylor variance without FPC"
        warnings = [
            "Assumes independent SRSWOR within strata and constant expansion weights within each stratum.",
            "No finite population correction is applied; standard errors may be conservative when sampling fractions are substantial.",
        ]
        details = pd.DataFrame(rows)
    elif design == "cluster_wr":
        if not cluster or cluster not in df:
            raise ValueError("Select a valid primary sampling unit (PSU) variable for cluster estimation.")
        work["cluster"] = df[cluster]
        if work["cluster"].isna().any():
            raise ValueError("PSU identifiers cannot be missing.")
        work["stratum"] = df[strata] if strata else "__ALL__"
        if work["stratum"].isna().any():
            raise ValueError("Stratum identifiers cannot be missing.")
        variance = 0.0
        df_resid = 0
        rows = []
        for label, group in work.groupby("stratum", sort=False):
            psu_totals = group.assign(weighted_y=group["w"] * group["y"]).groupby(
                "cluster", sort=False
            )["weighted_y"].sum()
            m_h = len(psu_totals)
            if m_h < 2:
                raise ValueError(f"At least two sampled PSUs are required in stratum {label!r}.")
            centered = psu_totals - psu_totals.mean()
            variance_h = float(m_h / (m_h - 1) * np.square(centered).sum())
            variance += variance_h
            df_resid += m_h - 1
            rows.append({
                "stratum": str(label), "sampled_psus": m_h,
                "sum_of_weighted_psu_totals": float(psu_totals.sum()),
                "variance_contribution": variance_h,
            })
        method = "Weighted total with with-replacement ultimate-cluster variance"
        warnings = [
            "Assumes independent sampled PSUs within strata and a with-replacement ultimate-cluster variance estimator.",
            "No PSU finite population correction is applied.",
            "This total estimator treats the supplied weights as fixed analysis expansion weights.",
        ]
        details = pd.DataFrame(rows)
    else:
        raise ValueError("Total confidence intervals require stratified_srs or cluster_wr design information.")

    se = float(np.sqrt(max(variance, 0.0)))
    critical = float(t.ppf(1 - (1 - confidence_level) / 2, df_resid))
    lower, upper = estimate - critical * se, estimate + critical * se
    table = pd.DataFrame([{
        "outcome": outcome, "weighted_total": estimate, "standard_error": se,
        "confidence_level": confidence_level, "ci_lower": lower, "ci_upper": upper,
        "records_used": len(work), "degrees_of_freedom": df_resid,
    }])
    metadata = {
        "estimate": estimate, "standard_error": se, "confidence_level": confidence_level,
        "ci_lower": lower, "ci_upper": upper, "degrees_of_freedom": df_resid,
        "variance_method": method, "sum_of_weights": float(w.sum()),
        "records_used": len(work),
    }
    return table, metadata, warnings, details


def estimate_survey(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    estimand: str = "mean",
    design: str = "weighted_descriptive",
    strata_variable: str | None = None,
    cluster_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a survey total, mean or category proportion with guarded inference."""
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between zero and one.")
    if estimand not in {"total", "mean", "proportion"}:
        raise ValueError("Estimand must be total, mean or proportion.")
    if design not in {"weighted_descriptive", "stratified_srs", "cluster_wr"}:
        raise ValueError("Unsupported survey design.")
    if outcome_variable == weight_variable:
        raise ValueError("Outcome and weight variables must be different.")

    if estimand == "total":
        if design == "weighted_descriptive":
            output = weighted_numeric_summary(df, outcome_variable, weight_variable)
            table = output["table"][["outcome", "weighted_total", "unweighted_n", "sum_of_weights"]].copy()
            table["standard_error"] = np.nan
            table["ci_lower"] = np.nan
            table["ci_upper"] = np.nan
            return {
                "table": table, "details": pd.DataFrame(),
                "metadata": output["metadata"] | {"variance_method": "Not estimated"},
                "findings": output["findings"],
                "warnings": output["warnings"] + ["No design-based standard error or confidence interval is available from weights alone."],
            }
        table, metadata, warnings, details = _total_estimate(
            df, outcome_variable, weight_variable, design,
            confidence_level, strata_variable, cluster_variable,
        )
        return {
            "table": table, "details": details, "metadata": metadata,
            "findings": [f"Estimated population total for {outcome_variable}: {metadata['estimate']:,.4g}."],
            "warnings": warnings,
        }

    if estimand == "mean":
        if design == "weighted_descriptive":
            output = weighted_numeric_summary(df, outcome_variable, weight_variable)
            table = output["table"].copy()
            table["standard_error"] = np.nan
            table["ci_lower"] = np.nan
            table["ci_upper"] = np.nan
            return {
                "table": table, "details": pd.DataFrame(),
                "metadata": output["metadata"] | {"variance_method": "Not estimated"},
                "findings": output["findings"],
                "warnings": output["warnings"] + ["No design-based standard error or confidence interval is available from weights alone."],
            }
        if design == "stratified_srs":
            if not strata_variable:
                raise ValueError("Select a stratum variable for stratified estimation.")
            output = stratified_weighted_mean(df, outcome_variable, weight_variable, strata_variable, confidence_level)
        else:
            if not cluster_variable:
                raise ValueError("Select a PSU variable for cluster estimation.")
            output = cluster_weighted_mean(df, outcome_variable, weight_variable, cluster_variable, strata_variable, confidence_level)
        return {
            "table": output["table"], "details": output.get("strata_summary", pd.DataFrame()),
            "metadata": output["metadata"], "findings": output["findings"], "warnings": output["warnings"],
        }

    if design == "weighted_descriptive":
        output = weighted_frequency_table(df, outcome_variable, weight_variable)
        table = output["table"].copy()
        table["standard_error_percentage_points"] = np.nan
        table["ci_lower_percent"] = np.nan
        table["ci_upper_percent"] = np.nan
        return {
            "table": table, "details": pd.DataFrame(),
            "metadata": output["metadata"] | {"variance_method": "Not estimated"},
            "findings": output["findings"],
            "warnings": output["warnings"] + ["No design-based standard errors or confidence intervals are available from weights alone."],
        }
    if design == "stratified_srs":
        if not strata_variable:
            raise ValueError("Select a stratum variable for stratified estimation.")
        output = stratified_weighted_frequencies(df, outcome_variable, weight_variable, strata_variable, confidence_level)
    else:
        if not cluster_variable:
            raise ValueError("Select a PSU variable for cluster estimation.")
        output = cluster_weighted_frequencies(df, outcome_variable, weight_variable, cluster_variable, strata_variable, confidence_level)
    return {
        "table": output["table"], "details": output.get("strata_summary", pd.DataFrame()),
        "metadata": output["metadata"], "findings": output["findings"], "warnings": output["warnings"],
    }
