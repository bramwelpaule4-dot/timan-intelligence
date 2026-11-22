"""Two-stage stratified survey sampling utilities.

The design-based estimator in this module is restricted to independent
stratified SRSWOR at stage 1 (PSUs) and SRSWOR of SSUs within each sampled PSU.
The analysis file must contain exactly one outcome record per sampled SSU.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def inspect_two_stage_design(
    df: pd.DataFrame,
    psu_variable: str,
    ssu_variable: str,
    weight_variable: str,
    strata_variable: str | None = None,
    psu_population_count_variable: str | None = None,
    ssu_population_count_variable: str | None = None,
) -> dict[str, Any]:
    """Validate a two-stage sample hierarchy and report design metadata."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    named = [psu_variable, ssu_variable, weight_variable]
    named.extend(x for x in (
        strata_variable, psu_population_count_variable,
        ssu_population_count_variable,
    ) if x is not None)
    if len(set(named)) != len(named):
        raise ValueError("PSU, SSU, weight, stratum and population-count variables must be different.")
    missing = [x for x in named if x not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")

    def ids(column: str, label: str) -> pd.Series:
        values = df[column].astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)
        if values.isna().any():
            raise ValueError(f"{label} identifiers cannot be missing.")
        return values

    psu, ssu = ids(psu_variable, "PSU"), ids(ssu_variable, "SSU")
    strata = ids(strata_variable, "Stratum") if strata_variable else pd.Series(
        "__ALL__", index=df.index, dtype="object"
    )
    weight = pd.to_numeric(df[weight_variable], errors="coerce")
    if weight.isna().any() or not np.isfinite(weight.to_numpy(dtype=float)).all():
        raise ValueError("Every two-stage design record must have a finite numeric survey weight.")
    if (weight <= 0).any():
        raise ValueError("Survey weights must be strictly positive.")

    hierarchy = pd.DataFrame({"stratum": strata, "psu": psu, "ssu": ssu})
    psu_keys = ["stratum", "psu"]
    ssu_counts = hierarchy.groupby(psu_keys, sort=False)["ssu"].nunique()
    psu_counts = hierarchy[psu_keys].drop_duplicates().groupby("stratum", sort=False).size()

    def population_counts(column, grouping, sampled, label):
        if column is None:
            return None, None
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{label} population counts must be finite numeric values.")
        if (values <= 0).any() or not np.equal(values, np.floor(values)).all():
            raise ValueError(f"{label} population counts must be positive whole numbers.")
        check = pd.DataFrame({"count": values, **{key: hierarchy[key] for key in grouping}})
        variation = check.groupby(grouping, sort=False)["count"].nunique()
        if (variation != 1).any():
            raise ValueError(f"{label} population count must be constant within its sampling unit.")
        declared = check.groupby(grouping, sort=False)["count"].first()
        aligned = declared.reindex(sampled.index)
        if aligned.isna().any() or (aligned.to_numpy() < sampled.to_numpy()).any():
            raise ValueError(f"{label} population counts cannot be smaller than sampled counts.")
        return {str(k): int(v) for k, v in declared.items()}, float(
            (sampled.astype(float) / aligned.astype(float)).mean()
        )

    psu_population, f1 = population_counts(
        psu_population_count_variable, ["stratum"], psu_counts.sort_index(), "First-stage PSU"
    )
    ssu_population, f2 = population_counts(
        ssu_population_count_variable, ["stratum", "psu"], ssu_counts.sort_index(), "Second-stage SSU"
    )
    psu_sizes = hierarchy[psu_keys].drop_duplicates().groupby("stratum").size()
    metadata = {
        "design_type": "stratified two-stage cluster sample" if strata_variable else "two-stage cluster sample",
        "records": int(len(df)),
        "number_of_strata": int(hierarchy["stratum"].nunique()),
        "number_of_psus": int(len(ssu_counts)),
        "number_of_ssus": int(ssu_counts.sum()),
        "minimum_ssus_per_psu": int(ssu_counts.min()),
        "maximum_ssus_per_psu": int(ssu_counts.max()),
        "minimum_psus_per_stratum": int(psu_sizes.min()),
        "maximum_psus_per_stratum": int(psu_sizes.max()),
        "weight_sum": float(weight.sum()),
        "weight_minimum": float(weight.min()),
        "weight_maximum": float(weight.max()),
        "psu_variable": psu_variable,
        "ssu_variable": ssu_variable,
        "weight_variable": weight_variable,
        "strata_variable": strata_variable,
        "psu_population_count_variable": psu_population_count_variable,
        "ssu_population_count_variable": ssu_population_count_variable,
        "psu_population_counts_by_stratum": psu_population,
        "ssu_population_counts_by_psu": ssu_population,
        "mean_first_stage_sampling_fraction": f1,
        "mean_second_stage_sampling_fraction": f2,
        "variance_estimation_available": False,
    }
    return {
        "metadata": metadata,
        "psu_summary": pd.DataFrame({
            "stratum": psu_counts.index.astype(str),
            "sampled_psus": psu_counts.to_numpy(dtype=int),
        }).reset_index(drop=True),
        "ssu_summary": pd.DataFrame({
            "stratum": ssu_counts.index.get_level_values(0).astype(str),
            "psu": ssu_counts.index.get_level_values(1).astype(str),
            "sampled_ssus": ssu_counts.to_numpy(dtype=int),
        }),
        "findings": [
            f"Validated {metadata['number_of_psus']} PSUs and {metadata['number_of_ssus']} SSUs across {metadata['number_of_strata']} stratum/strata.",
            "Every observed SSU is nested within a single PSU.",
        ],
        "warnings": [
            "This inspection validates hierarchy and metadata; it does not itself estimate population parameters.",
            "The supplied weights are checked but are not verified against the declared selection probabilities.",
            "Sampling fractions require valid population counts at the corresponding stages.",
        ],
    }


def estimate_two_stage_total(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a population total and Taylor variance under two-stage SRSWOR.

    Each row must be one sampled SSU with its fully enumerated SSU outcome
    total. PSUs are sampled by SRSWOR within strata; SSUs are sampled by
    SRSWOR within each sampled PSU. Stage-specific FPCs are applied.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    columns = [outcome_variable, psu_variable, ssu_variable,
               psu_population_count_variable, ssu_population_count_variable]
    if strata_variable:
        columns.append(strata_variable)
    if len(set(columns)) != len(columns):
        raise ValueError("Outcome, identifiers, stratum and population-count variables must be different.")
    missing = [x for x in columns if x not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")

    data = df[columns].copy()
    for col, label in ((psu_variable, "PSU"), (ssu_variable, "SSU")):
        values = data[col].astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)
        if values.isna().any():
            raise ValueError(f"{label} identifiers cannot be missing.")
        data[col] = values
    stratum_key = strata_variable or "__timanstat_all_strata__"
    data[stratum_key] = (
        data[strata_variable].astype("object") if strata_variable
        else "__ALL__"
    )
    if data[stratum_key].isna().any():
        raise ValueError("Stratum identifiers cannot be missing.")
    y = pd.to_numeric(data[outcome_variable], errors="coerce")
    if y.isna().any() or not np.isfinite(y.to_numpy(dtype=float)).all():
        raise ValueError("The SSU outcome must be complete, numeric and finite.")
    data["__outcome__"] = y.astype(float)

    for col, label in (
        (psu_population_count_variable, "First-stage PSU"),
        (ssu_population_count_variable, "Second-stage SSU"),
    ):
        values = pd.to_numeric(data[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{label} population counts must be finite numeric values.")
        if (values <= 0).any() or not np.equal(values, np.floor(values)).all():
            raise ValueError(f"{label} population counts must be positive whole numbers.")
        data[col] = values.astype(int)

    # One row is one sampled SSU: repeated SSU rows would imply an unmodelled
    # third sampling stage or duplicated records.
    ssu_keys = [stratum_key, psu_variable, ssu_variable]
    if data.duplicated(ssu_keys).any():
        raise ValueError(
            "Exactly one row per sampled SSU is required; aggregate respondent records to SSU totals first."
        )
    psu_keys = [stratum_key, psu_variable]
    if (data.groupby(psu_keys)[psu_population_count_variable].nunique() != 1).any():
        raise ValueError("First-stage PSU population count must be constant within each stratum.")
    if (data.groupby(ssu_keys)[ssu_population_count_variable].nunique() != 1).any():
        raise ValueError("Second-stage SSU population count must be constant within each PSU.")

    strata_results = []
    total_estimate = 0.0
    total_variance = 0.0
    total_df = 0
    for h, hdata in data.groupby(stratum_key, sort=False):
        psu_frame = hdata.groupby(psu_variable, sort=False).agg(
            N_h=(psu_population_count_variable, "first"),
            sampled_ssus=(ssu_variable, "nunique"),
            M_hi=(ssu_population_count_variable, "first"),
        )
        # M_hi is attached to PSU rows below; varying M_hi across SSUs in a PSU
        # is rejected by the within-PSU constancy check above.
        n_h = len(psu_frame)
        N_values = psu_frame["N_h"].unique()
        if len(N_values) != 1:
            raise ValueError("First-stage PSU population count must be constant within each stratum.")
        N_h = int(N_values[0])
        if N_h < n_h:
            raise ValueError("First-stage PSU population count cannot be smaller than sampled PSUs.")
        if n_h < 2:
            raise ValueError("At least two sampled PSUs per stratum are required for variance estimation.")
        expanded_psu_totals = []
        stage2_variance_sum = 0.0
        psu_details = []
        for psu_id, pdata in hdata.groupby(psu_variable, sort=False):
            m_hi = len(pdata)
            M_values = pdata[ssu_population_count_variable].unique()
            if len(M_values) != 1:
                raise ValueError("Second-stage SSU population count must be constant within each PSU.")
            M_hi = int(M_values[0])
            if M_hi < m_hi:
                raise ValueError("Second-stage SSU population count cannot be smaller than sampled SSUs.")
            if m_hi < 2:
                raise ValueError("At least two sampled SSUs per PSU are required for stage-two variance estimation.")
            y_values = pdata["__outcome__"].to_numpy(dtype=float)
            s2_hi = float(np.var(y_values, ddof=1))
            f2_hi = m_hi / M_hi
            sampled_ssu_total = float(y_values.sum())
            expanded_total = (M_hi / m_hi) * sampled_ssu_total
            expanded_psu_totals.append(expanded_total)
            stage2_variance_sum += (
                M_hi ** 2 * (1.0 - f2_hi) * s2_hi / m_hi
            )
            psu_details.append({
                "psu": str(psu_id),
                "sampled_ssus": int(m_hi),
                "population_ssus": M_hi,
                "stage2_sampling_fraction": float(f2_hi),
                "sampled_outcome_total": sampled_ssu_total,
                "expanded_psu_total": expanded_total,
            })
        t_values = np.asarray(expanded_psu_totals, dtype=float)
        s2_between = float(np.var(t_values, ddof=1))
        f1_h = n_h / N_h
        estimate_h = (N_h / n_h) * float(t_values.sum())
        variance_stage1 = N_h ** 2 * (1.0 - f1_h) * s2_between / n_h
        variance_stage2 = (N_h / n_h) * stage2_variance_sum
        variance_h = variance_stage1 + variance_stage2
        total_estimate += estimate_h
        total_variance += variance_h
        total_df += n_h - 1
        strata_results.append({
            "stratum": str(h),
            "sampled_psus": n_h,
            "population_psus": N_h,
            "stage1_sampling_fraction": f1_h,
            "estimated_total": estimate_h,
            "stage1_variance": variance_stage1,
            "stage2_variance": variance_stage2,
            "estimated_variance": variance_h,
            "standard_error": float(np.sqrt(max(variance_h, 0.0))),
            "psu_details": psu_details,
        })

    if total_df <= 0:
        raise ValueError("Insufficient design degrees of freedom for confidence intervals.")
    standard_error = float(np.sqrt(max(total_variance, 0.0)))
    critical = float(stats.t.ppf(0.5 + confidence_level / 2.0, total_df))
    lower = total_estimate - critical * standard_error
    upper = total_estimate + critical * standard_error
    return {
        "estimate": float(total_estimate),
        "variance": float(total_variance),
        "standard_error": standard_error,
        "confidence_interval": (float(lower), float(upper)),
        "confidence_level": float(confidence_level),
        "degrees_of_freedom": int(total_df),
        "strata": pd.DataFrame([
            {k: v for k, v in item.items() if k != "psu_details"}
            for item in strata_results
        ]),
        "psu_details": pd.DataFrame([
            {"stratum": item["stratum"], **psu}
            for item in strata_results for psu in item["psu_details"]
        ]),
        "findings": [
            f"Estimated population total: {total_estimate:,.4g}.",
            f"Design-based standard error: {standard_error:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{lower:,.4g}, {upper:,.4g}].",
        ],
        "warnings": [
            "Estimator assumes independent SRS without replacement of PSUs within each stratum and SSUs within each sampled PSU.",
            "Each row must represent one sampled SSU with its fully enumerated SSU outcome total; respondent subsampling within SSUs is not supported.",
            "The variance uses first- and second-stage finite population corrections and a Taylor two-stage decomposition.",
            "Confidence interval uses a t critical value with sum_h(n_h - 1) design degrees of freedom; small-sample coverage may be approximate.",
            "No calibration, nonresponse adjustment, PPS selection, certainty-PSU treatment, replicate weights, or domain estimation is implemented.",
        ],
        "metadata": {
            "estimator": "Stratified two-stage SRSWOR total estimator with stage-specific FPCs",
            "number_of_strata": int(len(strata_results)),
            "number_of_psus": int(sum(x["sampled_psus"] for x in strata_results)),
            "number_of_ssus": int(len(data)),
            "degrees_of_freedom": int(total_df),
            "variance_stage_1": float(sum(x["stage1_variance"] for x in strata_results)),
            "variance_stage_2": float(sum(x["stage2_variance"] for x in strata_results)),
        },
    }
