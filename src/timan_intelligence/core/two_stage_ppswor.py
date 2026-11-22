"""Two-stage PPSWOR estimation with within-PSU SRSWOR.

Stage 1 uses fixed-size PPS sampling without replacement and requires actual
first- and second-order PSU inclusion probabilities. Stage 2 uses SRSWOR of
SSUs within each sampled PSU. Each input row represents one sampled SSU.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from timan_intelligence.core.ppswor_survey import estimate_ppswor_total


def estimate_two_stage_ppswor_total(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    ssu_variable: str,
    psu_inclusion_probability_variable: str,
    ssu_population_count_variable: str,
    joint_psu_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a total under PPSWOR PSU selection and within-PSU SRSWOR.

    The PSU joint-inclusion matrix contains actual pi_ij values for sampled
    PSU pairs. For stratified designs, supply {stratum_label: matrix}.
    The second stage is explicitly SRSWOR; its population SSU count must be
    supplied for every sampled PSU. This function does not infer probabilities
    from weights or size measures.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")

    required = [
        outcome_variable, psu_variable, ssu_variable,
        psu_inclusion_probability_variable, ssu_population_count_variable,
    ]
    if strata_variable:
        required.append(strata_variable)
    if len(set(required)) != len(required):
        raise ValueError("Outcome, PSU, SSU, inclusion probability, population count and stratum variables must be different.")
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")

    work = df[required].copy()
    for column, label in ((psu_variable, "PSU"), (ssu_variable, "SSU")):
        values = work[column].astype("object").map(
            lambda value: value.strip() if isinstance(value, str) else value
        ).replace("", pd.NA)
        if values.isna().any():
            raise ValueError(f"{label} identifiers cannot be missing.")
        work[column] = values

    stratum_key = "__timanstat_stratum__"
    work[stratum_key] = work[strata_variable] if strata_variable else "__ALL__"
    if work[stratum_key].isna().any():
        raise ValueError("Stratum identifiers cannot be missing.")

    y = pd.to_numeric(work[outcome_variable], errors="coerce")
    pi = pd.to_numeric(work[psu_inclusion_probability_variable], errors="coerce")
    population = pd.to_numeric(work[ssu_population_count_variable], errors="coerce")
    if y.isna().any() or not np.isfinite(y.to_numpy(dtype=float)).all():
        raise ValueError("SSU outcome values must be complete, numeric and finite.")
    if pi.isna().any() or not np.isfinite(pi.to_numpy(dtype=float)).all():
        raise ValueError("PSU first-order inclusion probabilities must be complete, numeric and finite.")
    if ((pi <= 0) | (pi > 1)).any():
        raise ValueError("PSU first-order inclusion probabilities must be in (0, 1].")
    if population.isna().any() or not np.isfinite(population.to_numpy(dtype=float)).all():
        raise ValueError("SSU population counts must be complete, numeric and finite.")
    if (population <= 0).any() or not np.equal(population, np.floor(population)).all():
        raise ValueError("SSU population counts must be positive whole numbers.")

    work["__outcome__"] = y.astype(float)
    work["__pi1__"] = pi.astype(float)
    work["__M2__"] = population.astype(int)

    psu_keys = [stratum_key, psu_variable]
    ssu_keys = psu_keys + [ssu_variable]
    if work.duplicated(ssu_keys).any():
        raise ValueError("Exactly one row per sampled SSU is required; aggregate lower-stage records to SSU totals first.")
    if (work.groupby(psu_keys, sort=False)["__pi1__"].nunique() != 1).any():
        raise ValueError("The first-order PSU inclusion probability must be constant within each PSU.")
    if (work.groupby(psu_keys, sort=False)["__M2__"].nunique() != 1).any():
        raise ValueError("The SSU population count must be constant within each PSU.")

    psu_rows = []
    detail_rows = []
    for (stratum, psu), group in work.groupby(psu_keys, sort=False, dropna=False):
        m_i = int(group[ssu_variable].nunique())
        M_i = int(group["__M2__"].iloc[0])
        if M_i < m_i:
            raise ValueError("The SSU population count cannot be smaller than the number of sampled SSUs.")
        if m_i < 2 and M_i > m_i:
            raise ValueError("At least two sampled SSUs per non-census PSU are required to estimate second-stage variance.")
        y_i = group["__outcome__"].to_numpy(dtype=float)
        sample_total = float(y_i.sum())
        expanded_total = float((M_i / m_i) * sample_total)
        f2_i = float(m_i / M_i)
        sample_variance = float(np.var(y_i, ddof=1)) if m_i > 1 else 0.0
        variance_stage2_i = float(M_i ** 2 * (1.0 - f2_i) * sample_variance / m_i)
        pi_i = float(group["__pi1__"].iloc[0])
        psu_rows.append({
            stratum_key: stratum,
            psu_variable: psu,
            "__pi1__": pi_i,
            "__expanded_total__": expanded_total,
        })
        detail_rows.append({
            "stratum": str(stratum),
            "psu": str(psu),
            "first_order_inclusion_probability": pi_i,
            "sampled_ssus": m_i,
            "population_ssus": M_i,
            "second_stage_sampling_fraction": f2_i,
            "sampled_ssu_total": sample_total,
            "estimated_psu_total": expanded_total,
            "second_stage_variance": variance_stage2_i,
            "second_stage_variance_contribution": variance_stage2_i / pi_i,
        })

    psu_frame = pd.DataFrame(psu_rows)
    first_stage = estimate_ppswor_total(
        psu_frame,
        "__expanded_total__",
        psu_variable,
        "__pi1__",
        joint_psu_inclusion_probabilities,
        stratum_key,
        confidence_level,
    )
    stage1_variance = float(first_stage["variance"])
    stage2_variance = float(sum(
        item["second_stage_variance_contribution"] for item in detail_rows
    ))
    total_variance = float(stage1_variance + stage2_variance)
    if not np.isfinite(total_variance) or total_variance < -1e-8:
        raise ValueError("The combined two-stage variance is not finite and non-negative.")
    total_variance = max(0.0, total_variance)
    standard_error = float(np.sqrt(total_variance))
    df_total = int(first_stage["degrees_of_freedom"])
    critical = float(stats.t.ppf(0.5 + confidence_level / 2.0, df_total))
    estimate = float(first_stage["estimate"])
    interval = (
        float(estimate - critical * standard_error),
        float(estimate + critical * standard_error),
    )

    psu_details = pd.DataFrame(detail_rows)
    stratum_details = first_stage["strata"].copy()
    stage2_by_stratum = psu_details.groupby("stratum", sort=False)[
        "second_stage_variance_contribution"
    ].sum()
    stratum_details["second_stage_variance"] = (
        stratum_details["stratum"].map(stage2_by_stratum).fillna(0.0)
    )
    stratum_details["combined_variance"] = (
        stratum_details["estimated_variance"]
        + stratum_details["second_stage_variance"]
    )

    return {
        "estimate": estimate,
        "variance": total_variance,
        "variance_stage_1": stage1_variance,
        "variance_stage_2": stage2_variance,
        "standard_error": standard_error,
        "confidence_interval": interval,
        "confidence_level": float(confidence_level),
        "degrees_of_freedom": df_total,
        "strata": stratum_details,
        "psu_details": psu_details,
        "pairwise_variance": first_stage["pairwise_variance"],
        "findings": [
            f"Two-stage PPSWOR estimated population total: {estimate:,.4g}.",
            f"Combined design-based standard error: {standard_error:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{interval[0]:,.4g}, {interval[1]:,.4g}].",
            f"Stage 1 variance: {stage1_variance:,.4g}; stage 2 variance: {stage2_variance:,.4g}.",
        ],
        "warnings": [
            "Stage 1 is fixed-size PPSWOR within each stratum and uses the supplied actual first- and second-order PSU inclusion probabilities.",
            "Stage 2 is SRSWOR of SSUs within each sampled PSU; the SSU population count must be correct and constant within each PSU.",
            "The variance combines a Sen-Yates-Grundy first-stage component based on expanded PSU totals with a Horvitz-Thompson estimate of the second-stage variance contribution.",
            "The t interval uses sum(n_h - 1) first-stage degrees of freedom as an approximation; interpret small-sample inference cautiously.",
            "This estimator requires one observed outcome total per sampled SSU and does not support additional respondent sampling within SSUs.",
        ],
        "metadata": {
            "estimator": "Two-stage PPSWOR Horvitz-Thompson total with SYG stage 1 and SRSWOR stage 2 variance",
            "sampling_design": "Fixed-size PPSWOR of PSUs within strata; SRSWOR of SSUs within sampled PSUs",
            "number_of_strata": int(psu_details["stratum"].nunique()),
            "number_of_sampled_psus": int(len(psu_details)),
            "number_of_sampled_ssus": int(psu_details["sampled_ssus"].sum()),
            "degrees_of_freedom": df_total,
            "psu_inclusion_probability_variable": psu_inclusion_probability_variable,
            "ssu_population_count_variable": ssu_population_count_variable,
            "joint_psu_inclusion_probabilities_supplied": True,
            "stage_1_variance": stage1_variance,
            "stage_2_variance": stage2_variance,
            "variance_method": "Stage 1 SYG on estimated PSU totals plus HT-estimated stage 2 variance",
        },
    }
