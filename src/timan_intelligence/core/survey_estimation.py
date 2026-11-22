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


def estimate_domain_survey(
    df: pd.DataFrame,
    outcome_variable: str,
    weight_variable: str,
    domain_variable: str,
    domain_value: Any,
    estimand: str = "mean",
    design: str = "weighted_descriptive",
    strata_variable: str | None = None,
    cluster_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a domain total, mean or category proportion using the full sample.

    Units outside the requested domain contribute zero to the linearized
    variables. They are never removed before design variance estimation.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty survey dataset is required.")
    if domain_variable not in df.columns:
        raise KeyError(f"Domain variable not found: {domain_variable}.")
    if domain_variable in {outcome_variable, weight_variable}:
        raise ValueError("The domain variable must differ from the outcome and weight variables.")
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between zero and one.")
    if estimand not in {"total", "mean", "proportion"}:
        raise ValueError("Estimand must be total, mean or proportion.")
    if design not in {"weighted_descriptive", "stratified_srs", "cluster_wr"}:
        raise ValueError("Unsupported survey design.")
    if df[domain_variable].isna().any():
        raise ValueError("Domain identifiers cannot be missing; resolve them before estimation.")

    in_domain = df[domain_variable].eq(domain_value).to_numpy()
    if not in_domain.any():
        raise ValueError(f"No records belong to domain {domain_value!r}.")
    if weight_variable not in df.columns:
        raise KeyError(f"Weight variable not found: {weight_variable}.")
    weight_series = pd.to_numeric(df[weight_variable], errors="coerce")
    if weight_series.isna().any() or not np.isfinite(weight_series.to_numpy(float)).all() or (weight_series <= 0).any():
        raise ValueError("Survey weights must be positive, finite and complete.")
    w = weight_series.to_numpy(float)
    y = None
    if estimand in {"total", "mean"}:
        y, w = _numeric_columns(df, outcome_variable, weight_variable)
    elif outcome_variable not in df.columns:
        raise KeyError(f"Outcome variable not found: {outcome_variable}.")
    domain_weights = w * in_domain
    denominator = float(domain_weights.sum())
    if denominator <= 0:
        raise ValueError("The selected domain has no positive weighted denominator.")

    details = pd.DataFrame()
    warnings = [
        "Domain variance is estimated from the full original sample; out-of-domain records contribute zero to domain linearized variables.",
    ]
    if design == "weighted_descriptive":
        warnings.append("Weights alone do not identify design-based standard errors or confidence intervals.")
        if estimand == "total":
            values = pd.to_numeric(df[outcome_variable], errors="coerce")
            if values.isna().any() or not np.isfinite(values.to_numpy(float)).all():
                raise ValueError("Numeric outcome values must be complete and finite.")
            estimate = float(np.dot(w * in_domain, values.to_numpy(float)))
            table = pd.DataFrame([{"domain_variable": domain_variable, "domain": str(domain_value),
                "estimand": estimand, "estimate": estimate, "standard_error": np.nan,
                "ci_lower": np.nan, "ci_upper": np.nan, "domain_unweighted_n": int(in_domain.sum()),
                "domain_weight_total": denominator}])
        elif estimand == "mean":
            estimate = float(np.dot(domain_weights, y) / denominator)
            table = pd.DataFrame([{"domain_variable": domain_variable, "domain": str(domain_value),
                "estimand": estimand, "estimate": estimate, "standard_error": np.nan,
                "ci_lower": np.nan, "ci_upper": np.nan, "domain_unweighted_n": int(in_domain.sum()),
                "domain_weight_total": denominator}])
        else:
            categories = df[outcome_variable].dropna().unique().tolist()
            if df.loc[in_domain, outcome_variable].isna().any():
                raise ValueError("Category outcome values within the domain cannot be missing.")
            rows = []
            for category in categories:
                numerator = float(np.dot(domain_weights, df[outcome_variable].eq(category).to_numpy(float)))
                rows.append({"domain_variable": domain_variable, "domain": str(domain_value),
                    "category": str(category), "estimand": estimand, "estimate": numerator / denominator,
                    "standard_error": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
                    "domain_unweighted_n": int(in_domain.sum()), "domain_weight_total": denominator})
            table = pd.DataFrame(rows)
        return {"table": table, "details": details,
            "metadata": {"domain_variable": domain_variable, "domain_value": str(domain_value),
                "domain_unweighted_n": int(in_domain.sum()), "domain_weight_total": denominator,
                "variance_method": "Not estimated"},
            "findings": [f"Domain {domain_variable}={domain_value!r}: {int(in_domain.sum()):,} sampled records."],
            "warnings": warnings}

    if estimand == "total":
        if outcome_variable not in df:
            raise KeyError(f"Outcome variable not found: {outcome_variable}.")
        values = pd.to_numeric(df[outcome_variable], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(float)).all():
            raise ValueError("Numeric outcome values must be complete and finite.")
        contribution = values.to_numpy(float) * in_domain
        work = df.copy()
        temp = "__timan_domain_contribution__"
        while temp in work.columns:
            temp += "_"
        work[temp] = contribution
        table, metadata, design_warnings, details = _total_estimate(
            work, temp, weight_variable, design, confidence_level,
            strata_variable, cluster_variable,
        )
        table = table.rename(columns={"weighted_total": "estimate"})
        table.insert(0, "estimand", "total")
        table.insert(0, "domain", str(domain_value))
        table.insert(0, "domain_variable", domain_variable)
        table["domain_unweighted_n"] = int(in_domain.sum())
        table["domain_weight_total"] = denominator
        metadata["variance_method"] = metadata["variance_method"] + "; domain indicator linearization"
        warnings.extend(design_warnings)
        findings = [f"Estimated total in domain {domain_variable}={domain_value!r}: {metadata['estimate']:,.4g}."]
    else:
        if estimand == "mean":
            category_values = [None]
        else:
            if df.loc[in_domain, outcome_variable].isna().any():
                raise ValueError("Category outcome values within the domain cannot be missing.")
            category_values = df.loc[in_domain, outcome_variable].dropna().unique().tolist()
        rows = []
        detail_rows = []
        total_df = 0
        for category in category_values:
            if estimand == "mean":
                numeric = pd.to_numeric(df[outcome_variable], errors="coerce")
                if numeric.isna().any() or not np.isfinite(numeric.to_numpy(float)).all():
                    raise ValueError("Numeric outcome values must be complete and finite.")
                indicator = in_domain.astype(float)
                numerator_values = numeric.to_numpy(float) * indicator
                numerator = float(np.dot(w, numerator_values))
                estimate = numerator / denominator
                residual = indicator * (numeric.to_numpy(float) - estimate)
                category_label = None
            else:
                indicator = (in_domain & df[outcome_variable].eq(category).to_numpy()).astype(float)
                numerator = float(np.dot(w, indicator))
                estimate = numerator / denominator
                residual = indicator - estimate * in_domain.astype(float)
                category_label = str(category)

            if design == "stratified_srs":
                if not strata_variable or strata_variable not in df:
                    raise ValueError("Select a valid stratum variable for domain estimation.")
                if df[strata_variable].isna().any():
                    raise ValueError("Stratum identifiers cannot be missing.")
                variance_num = 0.0
                df_resid = 0
                for label, indices in df.groupby(strata_variable, sort=False).groups.items():
                    loc = df.index.get_indexer(indices)
                    n_h = len(loc)
                    weights_h = w[loc]
                    if n_h < 2:
                        raise ValueError(f"At least two sampled records are required in stratum {label!r}.")
                    if not np.allclose(weights_h, weights_h[0]):
                        raise ValueError("Stratified domain inference requires constant expansion weights within each stratum.")
                    variance_num += (n_h * weights_h[0]) ** 2 * float(np.var(residual[loc], ddof=1)) / n_h
                    df_resid += n_h - 1
                    detail_rows.append({"category": category_label or "Domain mean", "stratum": str(label),
                        "sample_n": n_h, "variance_contribution": float((n_h * weights_h[0]) ** 2 * np.var(residual[loc], ddof=1) / n_h)})
                variance = variance_num / denominator ** 2
                method = "Stratified SRS Taylor ratio linearization; no FPC"
            else:
                if not cluster_variable or cluster_variable not in df:
                    raise ValueError("Select a valid PSU variable for domain estimation.")
                if df[cluster_variable].isna().any():
                    raise ValueError("PSU identifiers cannot be missing.")
                strata_values = df[strata_variable] if strata_variable else pd.Series("__ALL__", index=df.index)
                if strata_values.isna().any():
                    raise ValueError("Stratum identifiers cannot be missing.")
                variance_num = 0.0
                df_resid = 0
                for label, indices in strata_values.groupby(strata_values, sort=False).groups.items():
                    loc = df.index.get_indexer(indices)
                    psu_frame = pd.DataFrame({"psu": df.iloc[loc][cluster_variable].to_numpy(),
                        "linearized": (w[loc] * residual[loc])})
                    psu_totals = psu_frame.groupby("psu", sort=False)["linearized"].sum()
                    m_h = len(psu_totals)
                    if m_h < 2:
                        raise ValueError(f"At least two sampled PSUs are required in stratum {label!r}.")
                    contribution_h = float(m_h / (m_h - 1) * np.square(psu_totals - psu_totals.mean()).sum())
                    variance_num += contribution_h
                    df_resid += m_h - 1
                    detail_rows.append({"category": category_label or "Domain mean", "stratum": str(label),
                        "sampled_psus": m_h, "variance_contribution": contribution_h / denominator ** 2})
                variance = variance_num / denominator ** 2
                method = "With-replacement ultimate-PSU Taylor ratio linearization"
            se = float(np.sqrt(max(variance, 0.0)))
            critical = float(t.ppf(1 - (1 - confidence_level) / 2, df_resid))
            rows.append({"domain_variable": domain_variable, "domain": str(domain_value),
                "category": category_label, "estimand": estimand, "estimate": estimate,
                "standard_error": se, "confidence_level": confidence_level,
                "ci_lower": estimate - critical * se, "ci_upper": estimate + critical * se,
                "domain_unweighted_n": int(in_domain.sum()), "domain_weight_total": denominator,
                "degrees_of_freedom": df_resid})
            total_df = max(total_df, df_resid)
        table = pd.DataFrame(rows)
        details = pd.DataFrame(detail_rows)
        metadata = {"domain_variable": domain_variable, "domain_value": str(domain_value),
            "domain_unweighted_n": int(in_domain.sum()), "domain_weight_total": denominator,
            "variance_method": method, "degrees_of_freedom": total_df}
        warnings.extend([
            "Domain mean/proportion intervals use Taylor ratio linearization with the full sample design.",
            "No finite population correction is applied.",
        ])
        findings = [f"Estimated {estimand} for domain {domain_variable}={domain_value!r} using full-sample design information."]

    return {"table": table, "details": details, "metadata": metadata,
        "findings": findings, "warnings": warnings}
