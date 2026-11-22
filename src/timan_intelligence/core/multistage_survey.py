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
    certainty_psu_variable: str | None = None,
) -> dict[str, Any]:
    """Estimate a population total and Taylor variance under two-stage SRSWOR with optional certainty PSUs.

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
    if certainty_psu_variable:
        columns.append(certainty_psu_variable)
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
    if certainty_psu_variable:
        raw = data[certainty_psu_variable]
        if raw.isna().any():
            raise ValueError("Certainty-PSU classification cannot be missing.")
        if raw.dtype == bool:
            data["__is_certainty_psu__"] = raw.astype(bool)
        else:
            normalized = raw.astype(str).str.strip().str.lower()
            mapping = {"true": True, "false": False, "1": True, "0": False,
                       "yes": True, "no": False, "certainty": True, "non-certainty": False}
            if not normalized.isin(mapping).all():
                raise ValueError("Certainty-PSU values must be Boolean or coded true/false, 1/0, yes/no, certainty/non-certainty.")
            data["__is_certainty_psu__"] = normalized.map(mapping).astype(bool)
        if (data.groupby(psu_keys)["__is_certainty_psu__"].nunique() != 1).any():
            raise ValueError("Certainty-PSU classification must be constant within each PSU.")
    else:
        data["__is_certainty_psu__"] = False

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
        certainty_by_psu = hdata.groupby(psu_variable, sort=False)["__is_certainty_psu__"].first()
        certainty_ids = set(certainty_by_psu[certainty_by_psu].index)
        noncertainty_ids = [pid for pid in psu_frame.index if pid not in certainty_ids]
        n_certainty = len(certainty_ids)
        n_noncertainty = len(noncertainty_ids)
        N_noncertainty = N_h - n_certainty
        if N_noncertainty < 0:
            raise ValueError("Sampled certainty PSUs cannot exceed the declared first-stage PSU population.")
        if n_noncertainty > N_noncertainty:
            raise ValueError("Sampled non-certainty PSUs cannot exceed the non-certainty PSU population.")
        if n_noncertainty == 0 and N_noncertainty != 0:
            raise ValueError("At least two sampled non-certainty PSUs per stratum are required when non-certainty PSUs remain in the population.")
        if n_noncertainty == 1:
            raise ValueError("At least two sampled non-certainty PSUs per stratum are required for first-stage variance estimation.")
        expansion_noncertainty = float(N_noncertainty / n_noncertainty) if n_noncertainty else 0.0
        expanded_by_psu = {}
        stage2_variance_by_psu = {}
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
            stage2_variance = M_hi ** 2 * (1.0 - f2_hi) * s2_hi / m_hi
            is_certainty = bool(certainty_by_psu.loc[psu_id])
            expanded_by_psu[psu_id] = expanded_total
            stage2_variance_by_psu[psu_id] = stage2_variance
            psu_details.append({
                "psu": str(psu_id),
                "certainty_psu": is_certainty,
                "sampled_ssus": int(m_hi),
                "population_ssus": M_hi,
                "stage2_sampling_fraction": float(f2_hi),
                "sampled_outcome_total": sampled_ssu_total,
                "expanded_psu_total": expanded_total,
                "stage2_variance": float(stage2_variance),
            })
        certainty_total = float(sum(expanded_by_psu[x] for x in certainty_ids))
        noncertainty_total = float(sum(expanded_by_psu[x] for x in noncertainty_ids))
        estimate_h = certainty_total + expansion_noncertainty * noncertainty_total
        if n_noncertainty >= 2:
            noncertainty_values = np.asarray([expanded_by_psu[x] for x in noncertainty_ids], dtype=float)
            s2_between = float(np.var(noncertainty_values, ddof=1))
            f1_h = n_noncertainty / N_noncertainty
            variance_stage1 = N_noncertainty ** 2 * (1.0 - f1_h) * s2_between / n_noncertainty
        else:
            f1_h = 1.0 if N_noncertainty == 0 else 0.0
            variance_stage1 = 0.0
        variance_stage2 = sum(
            (1.0 if pid in certainty_ids else expansion_noncertainty) * stage2_variance_by_psu[pid]
            for pid in expanded_by_psu
        )
        variance_h = variance_stage1 + variance_stage2
        total_estimate += estimate_h
        total_variance += variance_h
        total_df += max(n_noncertainty - 1, 0)
        strata_results.append({
            "stratum": str(h),
            "sampled_psus": n_h,
            "population_psus": N_h,
            "sampled_certainty_psus": n_certainty,
            "sampled_noncertainty_psus": n_noncertainty,
            "noncertainty_population_psus": N_noncertainty,
            "stage1_sampling_fraction": f1_h,
            "estimated_total": estimate_h,
            "certainty_psu_total": certainty_total,
            "noncertainty_expansion_factor": expansion_noncertainty,
            "stage1_variance": variance_stage1,
            "stage2_variance": variance_stage2,
            "estimated_variance": variance_h,
            "standard_error": float(np.sqrt(max(variance_h, 0.0))),
            "psu_details": psu_details,
        })

    if total_df <= 0:
        total_df = int(sum(
            max(int(group[ssu_variable].nunique()) - 1, 0)
            for _, group in data.groupby(psu_keys, sort=False)
        ))
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
            "Certainty PSUs are treated as take-all first-stage units when explicitly flagged; remaining non-certainty PSUs are assumed to be sampled by SRSWOR within stratum.",
        ],
        "metadata": {
            "estimator": "Stratified two-stage SRSWOR total estimator with stage-specific FPCs",
            "number_of_strata": int(len(strata_results)),
            "number_of_psus": int(sum(x["sampled_psus"] for x in strata_results)),
            "number_of_ssus": int(len(data)),
            "degrees_of_freedom": int(total_df),
            "variance_stage_1": float(sum(x["stage1_variance"] for x in strata_results)),
            "variance_stage_2": float(sum(x["stage2_variance"] for x in strata_results)),
            "certainty_psu_variable": certainty_psu_variable,
            "number_of_certainty_psus": int(data.loc[data["__is_certainty_psu__"], psu_keys].drop_duplicates().shape[0]),
        },
    }


def _estimate_two_stage_ratio(
    df: pd.DataFrame,
    numerator_variable: str,
    denominator_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None,
    confidence_level: float,
    require_proportion: bool = False,
) -> dict[str, Any]:
    """Taylor-linearised ratio estimator for two-stage SRSWOR samples.

    Numerator and denominator columns must contain SSU-level totals/counts,
    with one row per sampled SSU. The denominator is the number of eligible
    population elements enumerated in each sampled SSU.
    """
    if numerator_variable == denominator_variable:
        raise ValueError("Numerator and denominator variables must be different.")
    required = [numerator_variable, denominator_variable]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")
    numerator = pd.to_numeric(df[numerator_variable], errors="coerce")
    denominator = pd.to_numeric(df[denominator_variable], errors="coerce")
    if numerator.isna().any() or not np.isfinite(numerator.to_numpy(dtype=float)).all():
        raise ValueError("Numerator SSU totals must be complete, numeric and finite.")
    if denominator.isna().any() or not np.isfinite(denominator.to_numpy(dtype=float)).all():
        raise ValueError("Denominator SSU counts must be complete, numeric and finite.")
    if (denominator < 0).any() or not np.equal(denominator, np.floor(denominator)).all():
        raise ValueError("Eligible-element counts must be non-negative whole numbers.")
    if require_proportion and (
        (numerator < 0).any()
        or (numerator > denominator).any()
        or not np.equal(numerator, np.floor(numerator)).all()
    ):
        raise ValueError("For a proportion, successes in each SSU must be whole numbers between zero and its eligible-element count.")

    work = df.copy()
    numerator_col = "__timanstat_ratio_numerator__"
    denominator_col = "__timanstat_ratio_denominator__"
    linearized_col = "__timanstat_ratio_linearized__"
    reserved = {numerator_col, denominator_col, linearized_col}
    if reserved.intersection(work.columns):
        raise ValueError("Dataset contains reserved internal column names; rename those columns and retry.")
    work[numerator_col] = numerator.astype(float)
    work[denominator_col] = denominator.astype(float)

    common = (
        psu_variable, ssu_variable, psu_population_count_variable,
        ssu_population_count_variable, strata_variable, confidence_level,
    )
    numerator_result = estimate_two_stage_total(
        work, numerator_col, common[0], common[1], common[2], common[3], common[4], common[5]
    )
    denominator_result = estimate_two_stage_total(
        work, denominator_col, common[0], common[1], common[2], common[3], common[4], common[5]
    )
    denominator_total = denominator_result["estimate"]
    numerator_total = numerator_result["estimate"]
    if not np.isfinite(denominator_total) or denominator_total <= 0:
        raise ValueError("Estimated population denominator must be positive.")
    ratio = numerator_total / denominator_total
    work[linearized_col] = work[numerator_col] - ratio * work[denominator_col]
    linearized_result = estimate_two_stage_total(
        work, linearized_col, common[0], common[1], common[2], common[3], common[4], common[5]
    )
    variance = max(0.0, linearized_result["variance"] / (denominator_total ** 2))
    standard_error = float(np.sqrt(variance))
    df_design = int(linearized_result["degrees_of_freedom"])
    critical = float(stats.t.ppf(0.5 + confidence_level / 2.0, df_design))
    lower = ratio - critical * standard_error
    upper = ratio + critical * standard_error
    if require_proportion:
        lower, upper = max(0.0, lower), min(1.0, upper)
    kind = "proportion" if require_proportion else "mean"
    return {
        "estimate": float(ratio),
        "numerator_total": float(numerator_total),
        "denominator_total": float(denominator_total),
        "variance": float(variance),
        "standard_error": standard_error,
        "confidence_interval": (float(lower), float(upper)),
        "confidence_level": float(confidence_level),
        "degrees_of_freedom": df_design,
        "strata": linearized_result["strata"],
        "psu_details": linearized_result["psu_details"],
        "findings": [
            f"Estimated population {kind}: {ratio:,.4g}.",
            f"Estimated numerator total: {numerator_total:,.4g}; estimated denominator total: {denominator_total:,.4g}.",
            f"Taylor-linearised standard error: {standard_error:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{lower:,.4g}, {upper:,.4g}].",
        ],
        "warnings": [
            "Assumes independent SRSWOR of PSUs within strata and SRSWOR of SSUs within sampled PSUs.",
            "Each row must be one sampled SSU; numerator and denominator values must be fully enumerated SSU-level totals.",
            "The ratio variance uses first- and second-stage finite population corrections and Taylor linearisation of the ratio.",
            "The confidence interval uses sum_h(n_h - 1) design degrees of freedom; coverage can be approximate with few PSUs.",
            "No PPS, certainty-PSU treatment, respondent subsampling within SSUs, calibration, nonresponse adjustment, replicate weights or domain estimation.",
        ],
        "metadata": {
            "estimator": f"Two-stage Taylor-linearised {kind} ratio estimator with stage-specific FPCs",
            "number_of_strata": int(len(linearized_result["strata"])),
            "number_of_psus": int(len(linearized_result["psu_details"])),
            "number_of_ssus": int(len(work)),
            "degrees_of_freedom": df_design,
            "variance_method": "Taylor linearisation of y - R*x",
            "variance_stage_1": float(linearized_result["metadata"]["variance_stage_1"] / denominator_total**2),
            "variance_stage_2": float(linearized_result["metadata"]["variance_stage_2"] / denominator_total**2),
        },
    }


def estimate_two_stage_mean(
    df: pd.DataFrame,
    outcome_total_variable: str,
    element_count_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a population element mean from SSU outcome totals and sizes."""
    return _estimate_two_stage_ratio(
        df, outcome_total_variable, element_count_variable, psu_variable,
        ssu_variable, psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, False,
    )


def estimate_two_stage_proportion(
    df: pd.DataFrame,
    successes_variable: str,
    eligible_count_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a population proportion from SSU successes and eligible counts."""
    return _estimate_two_stage_ratio(
        df, successes_variable, eligible_count_variable, psu_variable,
        ssu_variable, psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, True,
    )


def _prepare_two_stage_domain(
    df: pd.DataFrame, domain_variable: str, domain_value: Any,
) -> tuple[pd.DataFrame, pd.Series]:
    """Validate SSU-level domain membership and return its Boolean indicator."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if domain_variable not in df.columns:
        raise KeyError(f"Domain variable not found: {domain_variable}.")
    membership = df[domain_variable]
    if membership.isna().any():
        raise ValueError("Domain membership cannot be missing; resolve missing domain values before estimation.")
    indicator = membership.eq(domain_value)
    if not indicator.any():
        raise ValueError("The selected domain has no sampled SSUs; a domain estimate cannot be produced.")
    return df.copy(), indicator.astype(bool)


def estimate_two_stage_domain_total(
    df: pd.DataFrame,
    outcome_variable: str,
    domain_variable: str,
    domain_value: Any,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a domain total, retaining all sampled SSUs for variance estimation.

    Domain membership must be defined at SSU level. SSUs outside the domain
    contribute zero to the domain outcome but remain in the sample design.
    """
    work, indicator = _prepare_two_stage_domain(df, domain_variable, domain_value)
    outcome = pd.to_numeric(work[outcome_variable], errors="coerce")
    if outcome.isna().any() or not np.isfinite(outcome.to_numpy(dtype=float)).all():
        raise ValueError("Domain total outcomes must be complete, numeric and finite.")
    derived = "__timanstat_domain_total_outcome__"
    if derived in work.columns:
        raise ValueError("Dataset contains a reserved internal column name; rename it and retry.")
    work[derived] = outcome.where(indicator, 0.0)
    result = estimate_two_stage_total(
        work, derived, psu_variable, ssu_variable,
        psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level,
    )
    result["findings"] = [
        f"Estimated total for domain {domain_value!r}: {result['estimate']:,.4g}.",
        *result["findings"][1:],
    ]
    result["warnings"] = [
        "Domain membership is treated as an SSU-level characteristic; all elements within an SSU must belong to the same domain.",
        "All sampled SSUs, including those outside the domain, are retained in variance estimation; outside-domain outcomes are set to zero.",
        *[warning for warning in result["warnings"] if "domain estimation" not in warning.lower()],
    ]
    result["metadata"] = {
        **result["metadata"],
        "estimator": "Two-stage design-based domain total with stage-specific FPCs",
        "domain_variable": domain_variable,
        "domain_value": str(domain_value),
        "sampled_domain_ssus": int(indicator.sum()),
        "sampled_non_domain_ssus": int((~indicator).sum()),
    }
    return result


def _estimate_two_stage_domain_ratio(
    df: pd.DataFrame,
    numerator_variable: str,
    denominator_variable: str,
    domain_variable: str,
    domain_value: Any,
    psu_variable: str,
    ssu_variable: str,
    psu_population_count_variable: str,
    ssu_population_count_variable: str,
    strata_variable: str | None,
    confidence_level: float,
    require_proportion: bool,
) -> dict[str, Any]:
    work, indicator = _prepare_two_stage_domain(df, domain_variable, domain_value)
    numerator = pd.to_numeric(work[numerator_variable], errors="coerce")
    denominator = pd.to_numeric(work[denominator_variable], errors="coerce")
    if numerator.isna().any() or not np.isfinite(numerator.to_numpy(dtype=float)).all():
        raise ValueError("Domain numerator values must be complete, numeric and finite.")
    if denominator.isna().any() or not np.isfinite(denominator.to_numpy(dtype=float)).all():
        raise ValueError("Domain denominator values must be complete, numeric and finite.")
    if (denominator < 0).any() or not np.equal(denominator, np.floor(denominator)).all():
        raise ValueError("Domain denominator counts must be non-negative whole numbers.")
    if require_proportion and (
        (numerator < 0).any() or (numerator > denominator).any()
        or not np.equal(numerator, np.floor(numerator)).all()
    ):
        raise ValueError("For a domain proportion, successes must be whole numbers between zero and eligible counts.")
    ncol, dcol = "__timanstat_domain_numerator__", "__timanstat_domain_denominator__"
    if {ncol, dcol}.intersection(work.columns):
        raise ValueError("Dataset contains reserved internal column names; rename them and retry.")
    work[ncol] = numerator.where(indicator, 0.0)
    work[dcol] = denominator.where(indicator, 0.0)
    result = _estimate_two_stage_ratio(
        work, ncol, dcol, psu_variable, ssu_variable,
        psu_population_count_variable, ssu_population_count_variable,
        strata_variable, confidence_level, require_proportion,
    )
    kind = "proportion" if require_proportion else "mean"
    result["findings"] = [
        f"Estimated domain {kind} for {domain_value!r}: {result['estimate']:,.4g}.",
        *result["findings"][1:],
    ]
    result["warnings"] = [
        "Domain membership is treated as an SSU-level characteristic; all elements within an SSU must belong to the same domain.",
        "All sampled SSUs remain in the design variance calculation; non-domain numerator and denominator contributions are set to zero.",
        *result["warnings"],
    ]
    result["metadata"] = {
        **result["metadata"],
        "estimator": f"Two-stage Taylor-linearised domain {kind} estimator with stage-specific FPCs",
        "domain_variable": domain_variable,
        "domain_value": str(domain_value),
        "sampled_domain_ssus": int(indicator.sum()),
        "sampled_non_domain_ssus": int((~indicator).sum()),
    }
    return result


def estimate_two_stage_domain_mean(
    df: pd.DataFrame, outcome_total_variable: str, element_count_variable: str,
    domain_variable: str, domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_population_count_variable: str, ssu_population_count_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a mean among SSUs/elements belonging to an SSU-level domain."""
    return _estimate_two_stage_domain_ratio(
        df, outcome_total_variable, element_count_variable, domain_variable,
        domain_value, psu_variable, ssu_variable, psu_population_count_variable,
        ssu_population_count_variable, strata_variable, confidence_level, False,
    )


def estimate_two_stage_domain_proportion(
    df: pd.DataFrame, successes_variable: str, eligible_count_variable: str,
    domain_variable: str, domain_value: Any, psu_variable: str, ssu_variable: str,
    psu_population_count_variable: str, ssu_population_count_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a proportion among SSUs/elements belonging to an SSU-level domain."""
    return _estimate_two_stage_domain_ratio(
        df, successes_variable, eligible_count_variable, domain_variable,
        domain_value, psu_variable, ssu_variable, psu_population_count_variable,
        ssu_population_count_variable, strata_variable, confidence_level, True,
    )
