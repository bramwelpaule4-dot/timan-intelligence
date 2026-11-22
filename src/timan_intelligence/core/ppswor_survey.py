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


def estimate_ppswor_ratio(
    df: pd.DataFrame,
    numerator_variable: str,
    denominator_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    parameter: str = "mean",
) -> dict[str, Any]:
    """Estimate a PSU-level ratio (mean or proportion) with SYG linearisation.

    The point estimate is the ratio of HT estimates. Variance uses the SYG
    estimator applied to PSU linearised totals z_i = y_i - R*x_i, divided by
    the square of the HT denominator estimate. Matrices must contain actual
    design pi_ij values and be supplied separately by stratum when stratified.
    """
    if parameter not in {"mean", "proportion"}:
        raise ValueError("Parameter must be either 'mean' or 'proportion'.")
    if numerator_variable == denominator_variable:
        raise ValueError("Numerator and denominator variables must be different.")
    required = [numerator_variable, denominator_variable, psu_variable, inclusion_probability_variable]
    if strata_variable:
        required.append(strata_variable)
    if len(set(required)) != len(required):
        raise ValueError("Numerator, denominator, PSU, inclusion probability and stratum variables must be different.")
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")

    numerator = pd.to_numeric(df[numerator_variable], errors="coerce")
    denominator = pd.to_numeric(df[denominator_variable], errors="coerce")
    if numerator.isna().any() or not np.isfinite(numerator.to_numpy(dtype=float)).all():
        raise ValueError("PSU numerator totals must be complete, numeric and finite.")
    if denominator.isna().any() or not np.isfinite(denominator.to_numpy(dtype=float)).all():
        raise ValueError("PSU denominator totals must be complete, numeric and finite.")
    if (denominator < 0).any():
        raise ValueError("PSU denominator totals must be non-negative.")
    if parameter == "proportion" and ((numerator < 0) | (numerator > denominator)).any():
        raise ValueError("For a proportion, each PSU numerator total must be between zero and its denominator total.")

    # Reuse the validated HT/SYG engine for numerator and denominator totals.
    numerator_result = estimate_ppswor_total(
        df, numerator_variable, psu_variable, inclusion_probability_variable,
        joint_inclusion_probabilities, strata_variable, confidence_level,
    )
    denominator_result = estimate_ppswor_total(
        df, denominator_variable, psu_variable, inclusion_probability_variable,
        joint_inclusion_probabilities, strata_variable, confidence_level,
    )
    denominator_hat = denominator_result["estimate"]
    if not np.isfinite(denominator_hat) or denominator_hat <= 0:
        raise ValueError("The estimated population denominator must be positive for ratio estimation.")
    ratio = numerator_result["estimate"] / denominator_hat
    if not np.isfinite(ratio):
        raise ValueError("The estimated ratio is not finite.")

    linearised = df.copy()
    linearised_variable = "__ppswor_linearised_total__"
    while linearised_variable in linearised.columns:
        linearised_variable += "_"
    linearised[linearised_variable] = numerator - ratio * denominator
    linearised_result = estimate_ppswor_total(
        linearised, linearised_variable, psu_variable,
        inclusion_probability_variable, joint_inclusion_probabilities,
        strata_variable, confidence_level,
    )
    variance = linearised_result["variance"] / (denominator_hat ** 2)
    standard_error = float(np.sqrt(max(0.0, variance)))
    df_total = linearised_result["degrees_of_freedom"]
    critical = float(stats.t.ppf(0.5 + confidence_level / 2, df_total))
    ci = (float(ratio - critical * standard_error), float(ratio + critical * standard_error))

    strata = numerator_result["strata"].copy()
    denominator_strata = denominator_result["strata"].set_index("stratum")
    strata = strata.rename(columns={"estimated_total": "estimated_numerator_total"})
    strata["estimated_denominator_total"] = strata["stratum"].map(
        denominator_strata["estimated_total"]
    )
    strata["stratum_ratio"] = (
        strata["estimated_numerator_total"] / strata["estimated_denominator_total"]
    )
    pairwise = linearised_result["pairwise_variance"].copy()
    pairwise["ratio_variance_contribution"] = (
        pairwise["variance_contribution"] / (denominator_hat ** 2)
    )
    pairwise = pairwise.drop(columns=["variance_contribution"])
    label = "proportion" if parameter == "proportion" else "mean"
    warnings = list(linearised_result["warnings"])
    warnings.append(
        "The ratio variance uses first-order Taylor linearisation with the supplied SYG design variance; the t interval is an approximation."
    )
    if parameter == "proportion":
        warnings.append(
            "The proportion confidence interval is not truncated to [0, 1]; boundary estimates and small samples require cautious interpretation."
        )
    return {
        "estimate": float(ratio), "variance": float(variance),
        "standard_error": standard_error, "confidence_interval": ci,
        "confidence_level": float(confidence_level),
        "degrees_of_freedom": int(df_total),
        "numerator_estimate": float(numerator_result["estimate"]),
        "denominator_estimate": float(denominator_hat),
        "strata": strata, "pairwise_variance": pairwise,
        "findings": [
            f"Horvitz-Thompson ratio {label} estimate: {ratio:,.4g}.",
            f"Taylor-linearised Sen-Yates-Grundy standard error: {standard_error:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{ci[0]:,.4g}, {ci[1]:,.4g}].",
        ],
        "warnings": warnings,
        "metadata": {
            "estimator": f"PPSWOR HT ratio {label} with Taylor-linearised SYG variance",
            "sampling_design": "PPS without replacement; fixed-size sample within each stratum",
            "parameter": label,
            "number_of_strata": int(linearised_result["metadata"]["number_of_strata"]),
            "number_of_sampled_psus": int(linearised_result["metadata"]["number_of_sampled_psus"]),
            "degrees_of_freedom": int(df_total),
            "inclusion_probability_variable": inclusion_probability_variable,
            "joint_inclusion_probabilities_supplied": True,
            "numerator_estimate": float(numerator_result["estimate"]),
            "denominator_estimate": float(denominator_hat),
        },
    }




def _ppswor_domain_diagnostics(
    estimate: float,
    variance: float,
    standard_error: float,
    confidence_interval: tuple[float, float],
    sampled_psus: int,
    strata: pd.DataFrame,
    pairwise_variance: pd.DataFrame,
    zero_domain_psus: int,
    zero_domain_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build descriptive precision and variance-allocation diagnostics.

    CV and relative interval width are descriptive precision measures, not
    universal pass/fail thresholds. Zero totals are reported as supplied and
    are not automatically interpreted as proof of domain non-membership.
    """
    cv = (
        float(standard_error / abs(estimate) * 100.0)
        if estimate != 0 else None
    )
    ci_width = float(confidence_interval[1] - confidence_interval[0])
    relative_half_width = (
        float(ci_width / (2.0 * abs(estimate)) * 100.0)
        if estimate != 0 else None
    )
    zero_percent = (
        float(zero_domain_psus / sampled_psus * 100.0)
        if sampled_psus else 0.0
    )
    strata_diagnostics = strata.copy()
    variance_column = (
        "estimated_ratio_variance"
        if "estimated_ratio_variance" in strata_diagnostics.columns
        else "estimated_variance"
    )
    if variance_column in strata_diagnostics.columns:
        strata_diagnostics["variance_share_percent"] = (
            strata_diagnostics[variance_column] / variance * 100.0
            if variance > 0 else 0.0
        )
    pairwise_diagnostics = pairwise_variance.copy()
    if "variance_contribution" in pairwise_diagnostics.columns:
        pairwise_diagnostics["variance_share_percent"] = (
            pairwise_diagnostics["variance_contribution"] / variance * 100.0
            if variance > 0 else 0.0
        )
    elif "ratio_variance_contribution" in pairwise_diagnostics.columns:
        pairwise_diagnostics["variance_share_percent"] = (
            pairwise_diagnostics["ratio_variance_contribution"]
            / variance * 100.0 if variance > 0 else 0.0
        )
    diagnostics = {
        "estimate": float(estimate),
        "standard_error": float(standard_error),
        "coefficient_of_variation_percent": cv,
        "confidence_interval_width": ci_width,
        "relative_confidence_interval_half_width_percent": relative_half_width,
        "sampled_psus": int(sampled_psus),
        "psus_with_zero_domain_value": int(zero_domain_psus),
        "zero_domain_value_percent": zero_percent,
        "sampled_psu_pairs": int(len(pairwise_diagnostics)),
        "minimum_sampled_pair_joint_inclusion_probability": (
            float(pairwise_diagnostics["pi_ij"].min())
            if not pairwise_diagnostics.empty and "pi_ij" in pairwise_diagnostics
            else None
        ),
        "degrees_of_freedom": int(
            strata_diagnostics["sampled_psus"].sum()
            - len(strata_diagnostics)
        ) if "sampled_psus" in strata_diagnostics else None,
        "zero_value_definition": zero_domain_label,
    }
    return (
        pd.DataFrame([diagnostics]),
        strata_diagnostics,
        pairwise_diagnostics,
        diagnostics,
    )


def estimate_ppswor_domain_total(
    df: pd.DataFrame,
    domain_name: str,
    domain_total_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a domain population total using HT/SYG on the full PSU sample.

    The domain total column must contain each sampled PSU's total for the
    specified domain, explicitly set to zero for sampled PSUs with no domain
    members. The input sample and joint-inclusion matrices are never subset
    by domain membership.
    """
    if not isinstance(domain_name, str) or not domain_name.strip():
        raise ValueError("A non-empty domain name is required.")
    output = estimate_ppswor_total(
        df=df,
        outcome_total_variable=domain_total_variable,
        psu_variable=psu_variable,
        inclusion_probability_variable=inclusion_probability_variable,
        joint_inclusion_probabilities=joint_inclusion_probabilities,
        strata_variable=strata_variable,
        confidence_level=confidence_level,
    )
    output["findings"] = [
        f"Domain: {domain_name.strip()}.",
        f"Horvitz-Thompson estimated domain total: {output['estimate']:,.4g}.",
        f"Sen-Yates-Grundy domain standard error: {output['standard_error']:,.4g}.",
        (
            f"{confidence_level:.0%} t confidence interval for the domain total: "
            f"[{output['confidence_interval'][0]:,.4g}, "
            f"{output['confidence_interval'][1]:,.4g}]."
        ),
    ]
    output["warnings"] = [
        *output["warnings"],
        "Domain total estimation requires a domain-specific PSU total for every sampled PSU, with zero totals retained for PSUs containing no domain units. Do not filter those PSUs out.",
        "The domain total is the Horvitz-Thompson expansion of the supplied domain-specific PSU totals under the original PPSWOR design.",
    ]
    domain_values = pd.to_numeric(df[domain_total_variable], errors="coerce")
    zero_domain_psus = int(domain_values.eq(0).sum())
    (
        output["diagnostics"],
        output["strata"],
        output["pairwise_variance"],
        diagnostic_metadata,
    ) = _ppswor_domain_diagnostics(
        output["estimate"], output["variance"], output["standard_error"],
        output["confidence_interval"], output["metadata"]["number_of_sampled_psus"],
        output["strata"], output["pairwise_variance"], zero_domain_psus,
        "sampled PSUs whose supplied domain-specific total equals zero",
    )
    output["findings"].append(
        (
            f"Relative standard error (coefficient of variation): "
            f"{diagnostic_metadata['coefficient_of_variation_percent']:.2f}%."
        )
        if diagnostic_metadata["coefficient_of_variation_percent"] is not None
        else "Relative standard error is undefined because the estimated domain total is zero."
    )
    output["findings"].append(
        f"{zero_domain_psus} of {diagnostic_metadata['sampled_psus']} sampled PSUs "
        f"({diagnostic_metadata['zero_domain_value_percent']:.1f}%) have a supplied "
        "domain-specific total equal to zero."
    )
    if zero_domain_psus:
        output["warnings"].append(
            "Some sampled PSU domain totals are zero. Confirm these are genuine "
            "domain-specific zero contributions and not missing or unconstructed aggregates."
        )
    output["warnings"].append(
        "The coefficient of variation and relative confidence-interval width are "
        "descriptive precision diagnostics; no universal acceptability threshold is applied."
    )
    output["metadata"].update({
        "estimator": "PPSWOR domain Horvitz-Thompson total with Sen-Yates-Grundy variance",
        "domain_name": domain_name.strip(),
        "domain_estimation": True,
        "domain_parameter": "total",
        "domain_total_variable": domain_total_variable,
        "precision_diagnostics": diagnostic_metadata,
    })
    return output


def estimate_ppswor_domain_ratio(
    df: pd.DataFrame,
    domain_name: str,
    domain_numerator_variable: str,
    domain_denominator_variable: str,
    psu_variable: str,
    inclusion_probability_variable: str,
    joint_inclusion_probabilities: pd.DataFrame | dict[Any, pd.DataFrame],
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
    parameter: str = "mean",
) -> dict[str, Any]:
    """Estimate a domain mean/proportion from PSU-level domain aggregates.

    Domain numerator and denominator columns must contain domain-specific
    PSU totals for every sampled PSU, including explicit zeros for PSUs with
    no units in the domain. This preserves the original PPSWOR sample and
    pairwise SYG variance; filtering the sample to domain-positive PSUs is
    not valid for this estimator.
    """
    if not isinstance(domain_name, str) or not domain_name.strip():
        raise ValueError("A non-empty domain name is required.")
    output = estimate_ppswor_ratio(
        df=df,
        numerator_variable=domain_numerator_variable,
        denominator_variable=domain_denominator_variable,
        psu_variable=psu_variable,
        inclusion_probability_variable=inclusion_probability_variable,
        joint_inclusion_probabilities=joint_inclusion_probabilities,
        strata_variable=strata_variable,
        confidence_level=confidence_level,
        parameter=parameter,
    )
    output["findings"] = [
        f"Domain: {domain_name.strip()}.",
        *output["findings"],
    ]
    output["warnings"] = [
        *output["warnings"],
        "Domain estimation requires domain-specific PSU totals for every sampled PSU, with zero totals retained for PSUs containing no domain units. Do not filter those PSUs out.",
        "The estimate is a ratio of design-weighted domain totals; domain-specific numerator and denominator aggregates must be correctly constructed from the full sampled PSU records.",
    ]
    domain_denominator_values = pd.to_numeric(
        df[domain_denominator_variable], errors="coerce"
    )
    zero_domain_psus = int(domain_denominator_values.eq(0).sum())
    # Use the Taylor-linearised variance by stratum, not the numerator
    # total variance, to decompose the ratio variance correctly.
    linearised_strata = linearised_result["strata"].set_index("stratum")
    output["strata"]["estimated_ratio_variance"] = (
        output["strata"]["stratum"].map(
            linearised_strata["estimated_variance"]
        ) / (output["denominator_estimate"] ** 2)
    )
    (
        output["diagnostics"],
        output["strata"],
        output["pairwise_variance"],
        diagnostic_metadata,
    ) = _ppswor_domain_diagnostics(
        output["estimate"], output["variance"], output["standard_error"],
        output["confidence_interval"], output["metadata"]["number_of_sampled_psus"],
        output["strata"], output["pairwise_variance"], zero_domain_psus,
        "sampled PSUs with a zero domain denominator",
    )
    output["findings"].append(
        (
            f"Relative standard error (coefficient of variation): "
            f"{diagnostic_metadata['coefficient_of_variation_percent']:.2f}%."
        )
        if diagnostic_metadata["coefficient_of_variation_percent"] is not None
        else "Relative standard error is undefined because the estimated domain ratio is zero."
    )
    output["findings"].append(
        f"{zero_domain_psus} of {diagnostic_metadata['sampled_psus']} sampled PSUs "
        f"({diagnostic_metadata['zero_domain_value_percent']:.1f}%) have a zero "
        "domain denominator."
    )
    if zero_domain_psus:
        output["warnings"].append(
            "Some sampled PSUs have zero domain denominators. Confirm that these "
            "are structural zero-domain PSUs and that all sampled PSUs remain in the design."
        )
    output["warnings"].append(
        "The coefficient of variation and relative confidence-interval width are "
        "descriptive precision diagnostics; no universal acceptability threshold is applied."
    )
    output["metadata"].update({
        "estimator": output["metadata"]["estimator"].replace(
            "PPSWOR HT ratio", "PPSWOR domain HT ratio"
        ),
        "domain_name": domain_name.strip(),
        "domain_estimation": True,
        "domain_numerator_variable": domain_numerator_variable,
        "domain_denominator_variable": domain_denominator_variable,
        "precision_diagnostics": diagnostic_metadata,
    })
    return output
