"""Two-stage PPS-with-replacement survey estimators.

Stage 1 selects PSU draws independently with replacement, with a known
per-draw PSU selection probability. Stage 2 selects SSUs by SRSWOR within
each selected PSU draw. A draw identifier is required so repeated selections
of the same physical PSU remain distinct sampling events.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def _prepare_ppswr_draws(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    draw_variable: str,
    ssu_variable: str,
    ssu_population_count_variable: str,
    selection_probability_variable: str,
    strata_variable: str | None,
) -> tuple[pd.DataFrame, list[str], str]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    columns = [outcome_variable, psu_variable, draw_variable, ssu_variable,
               ssu_population_count_variable, selection_probability_variable]
    if strata_variable:
        columns.append(strata_variable)
    if len(set(columns)) != len(columns):
        raise ValueError("Outcome, draw, PSU, SSU, probability, population and stratum variables must be different.")
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")
    work = df[columns].copy()
    for col, label in ((psu_variable, "PSU"), (draw_variable, "PSU draw"),
                       (ssu_variable, "SSU")):
        values = work[col].astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)
        if values.isna().any():
            raise ValueError(f"{label} identifiers cannot be missing.")
        work[col] = values
    stratum_key = strata_variable or "__ppswr_all_strata__"
    work[stratum_key] = work[strata_variable].astype("object") if strata_variable else "__ALL__"
    if work[stratum_key].isna().any():
        raise ValueError("Stratum identifiers cannot be missing.")
    numeric = {}
    for col, label in ((outcome_variable, "Outcome"),
                       (ssu_population_count_variable, "SSU population"),
                       (selection_probability_variable, "PSU selection probability")):
        values = pd.to_numeric(work[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{label} values must be complete, numeric and finite.")
        numeric[col] = values.astype(float)
    if (numeric[ssu_population_count_variable] <= 0).any() or not np.equal(
        numeric[ssu_population_count_variable],
        np.floor(numeric[ssu_population_count_variable])
    ).all():
        raise ValueError("SSU population counts must be positive whole numbers.")
    probability = numeric[selection_probability_variable]
    if ((probability <= 0) | (probability > 1)).any():
        raise ValueError("Each per-draw PSU selection probability must be greater than zero and at most one.")
    work["__outcome__"] = numeric[outcome_variable]
    work["__ssu_population__"] = numeric[ssu_population_count_variable].astype(int)
    work["__selection_probability__"] = probability
    draw_keys = [stratum_key, draw_variable]
    if work.duplicated(draw_keys + [ssu_variable]).any():
        raise ValueError("Each sampled SSU must appear once within its PSU draw.")
    draw_psu_count = work.groupby(draw_keys, sort=False)[psu_variable].nunique()
    if (draw_psu_count != 1).any():
        raise ValueError("Each PSU draw must identify exactly one selected physical PSU.")
    for col, label in ((psu_variable, "PSU selection probability"),
                       ("__selection_probability__", "PSU selection probability"),
                       ("__ssu_population__", "SSU population count")):
        if col == psu_variable:
            continue
        variation = work.groupby(draw_keys, sort=False)[col].nunique()
        if (variation != 1).any():
            raise ValueError(f"{label} must be constant within each PSU draw.")
    # A physical PSU has one fixed per-draw selection probability and SSU frame size.
    physical_keys = [stratum_key, psu_variable]
    if (work.groupby(physical_keys, sort=False)["__selection_probability__"].nunique() != 1).any():
        raise ValueError("A physical PSU must have the same selection probability across its observed draws.")
    if (work.groupby(physical_keys, sort=False)["__ssu_population__"].nunique() != 1).any():
        raise ValueError("SSU population count must be constant for each physical PSU.")
    sampled_ssus = work.groupby(draw_keys, sort=False)[ssu_variable].nunique()
    population_ssus = work.groupby(draw_keys, sort=False)["__ssu_population__"].first()
    if (population_ssus < sampled_ssus).any():
        raise ValueError("SSU population counts cannot be smaller than sampled SSUs in a draw.")
    if (sampled_ssus < 2).any():
        raise ValueError("At least two sampled SSUs per PSU draw are required for stage-two variance estimation.")
    return work, draw_keys, stratum_key


def _ppswr_draw_estimates(
    work: pd.DataFrame,
    draw_keys: list[str],
    stratum_key: str,
    outcome: pd.Series,
    numerator: pd.Series | None = None,
    denominator: pd.Series | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for key, group in work.groupby(draw_keys, sort=False):
        m = len(group)
        M = int(group["__ssu_population__"].iloc[0])
        p = float(group["__selection_probability__"].iloc[0])
        y = outcome.loc[group.index].to_numpy(dtype=float)
        y_total_hat = float(M / m * y.sum())
        y_variance_hat = float(M**2 * (1 - m / M) * np.var(y, ddof=1) / m)
        row = {
            stratum_key: key[0] if isinstance(key, tuple) else "__ALL__",
            "__draw_id__": key[-1] if isinstance(key, tuple) else key,
            "__p__": p,
            "__y_total_hat__": y_total_hat,
            "__stage2_y_variance__": y_variance_hat,
        }
        if numerator is not None and denominator is not None:
            row["__x_total_hat__"] = float(M / m * numerator.loc[group.index].sum())
            row["__d_total_hat__"] = float(M / m * denominator.loc[group.index].sum())
        rows.append(row)
    draws = pd.DataFrame(rows)
    return draws, {}


def estimate_two_stage_ppswr_total(
    df: pd.DataFrame,
    outcome_variable: str,
    psu_variable: str,
    draw_variable: str,
    ssu_variable: str,
    ssu_population_count_variable: str,
    selection_probability_variable: str,
    strata_variable: str | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Estimate a total for PPS-with-replacement PSU draws and SRSWOR SSUs."""
    if not 0 < confidence_level < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    work, draw_keys, stratum_key = _prepare_ppswr_draws(
        df, outcome_variable, psu_variable, draw_variable, ssu_variable,
        ssu_population_count_variable, selection_probability_variable, strata_variable,
    )
    draws, _ = _ppswr_draw_estimates(work, draw_keys, stratum_key, work["__outcome__"])
    estimate = variance = stage2_component = 0.0
    degrees_freedom = 0
    stratum_rows = []
    for h, group in draws.groupby(stratum_key, sort=False):
        n = len(group)
        if n < 2:
            raise ValueError("At least two independent PSU draws per stratum are required for variance estimation.")
        z = group["__y_total_hat__"].to_numpy() / group["__p__"].to_numpy()
        estimate_h = float(z.mean())
        variance_h = float(np.var(z, ddof=1) / n)
        stage2_h = float(np.mean(
            group["__stage2_y_variance__"].to_numpy() / group["__p__"].to_numpy()**2
        ) / n)
        estimate += estimate_h
        variance += variance_h
        stage2_component += stage2_h
        degrees_freedom += n - 1
        stratum_rows.append({
            "stratum": str(h), "psu_draws": n, "estimated_total": estimate_h,
            "estimated_variance": variance_h, "estimated_stage2_variance_component": stage2_h,
        })
    se = float(np.sqrt(max(variance, 0.0)))
    critical = float(stats.t.ppf(0.5 + confidence_level / 2, degrees_freedom))
    ci = (float(estimate - critical * se), float(estimate + critical * se))
    details = draws.rename(columns={
        "__draw_id__": "psu_draw", "__p__": "selection_probability",
        "__y_total_hat__": "expanded_ssu_total", "__stage2_y_variance__": "stage2_variance_of_expanded_total",
    })
    details.insert(1, "physical_psu", [
        str(work.loc[(work[stratum_key] == row[stratum_key]) &
                     (work[draw_variable] == row["psu_draw"]), psu_variable].iloc[0])
        for _, row in details.iterrows()
    ])
    return {
        "estimate": float(estimate), "variance": float(variance),
        "standard_error": se, "confidence_interval": ci,
        "confidence_level": float(confidence_level),
        "degrees_of_freedom": int(degrees_freedom),
        "strata": pd.DataFrame(stratum_rows), "psu_draw_details": details,
        "findings": [
            f"Estimated population total: {estimate:,.4g}.",
            f"Design-based standard error: {se:,.4g}.",
            f"{confidence_level:.0%} t confidence interval: [{ci[0]:,.4g}, {ci[1]:,.4g}].",
        ],
        "warnings": [
            "Stage 1 is independent PPS sampling with replacement within each stratum, using the supplied per-draw PSU selection probabilities.",
            "Stage 2 is SRSWOR of SSUs within each selected PSU draw; repeated selections of the same physical PSU must have distinct draw identifiers.",
            "The Hansen-Hurwitz estimator and draw-level variance include stage-two sampling variation; the reported stage-two component is a diagnostic decomposition estimate.",
            "PPS without replacement, certainty-PSU flags, nonresponse adjustments, calibration and respondent subsampling are not supported by this estimator.",
            "Selection probabilities must come from the actual first-stage PPS design and sum to one over the eligible PSU frame within each stratum.",
        ],
        "metadata": {
            "estimator": "Two-stage Hansen-Hurwitz total estimator: PPSWR PSUs and SRSWOR SSUs",
            "sampling_design": "PPS with replacement at stage 1; SRSWOR at stage 2",
            "number_of_strata": int(draws[stratum_key].nunique()),
            "number_of_psu_draws": int(len(draws)),
            "number_of_unique_psus": int(work[[stratum_key, psu_variable]].drop_duplicates().shape[0]),
            "number_of_ssu_records": int(len(work)),
            "variance_stage_1_plus_stage_2": float(variance),
            "estimated_stage2_variance_component": float(stage2_component),
            "degrees_of_freedom": int(degrees_freedom),
            "selection_probability_variable": selection_probability_variable,
            "draw_variable": draw_variable,
        },
    }


def _estimate_two_stage_ppswr_ratio(
    df: pd.DataFrame,
    numerator_variable: str,
    denominator_variable: str,
    psu_variable: str,
    draw_variable: str,
    ssu_variable: str,
    ssu_population_count_variable: str,
    selection_probability_variable: str,
    strata_variable: str | None,
    confidence_level: float,
    require_proportion: bool,
) -> dict[str, Any]:
    if numerator_variable == denominator_variable:
        raise ValueError("Numerator and denominator variables must be different.")
    work, draw_keys, stratum_key = _prepare_ppswr_draws(
        df, numerator_variable, psu_variable, draw_variable, ssu_variable,
        ssu_population_count_variable, selection_probability_variable, strata_variable,
    )
    denominator = pd.to_numeric(df[denominator_variable], errors="coerce")
    if denominator.isna().any() or not np.isfinite(denominator.to_numpy(dtype=float)).all():
        raise ValueError("Denominator SSU values must be complete, numeric and finite.")
    numerator = work["__outcome__"]
    denominator = denominator.astype(float)
    if (denominator < 0).any():
        raise ValueError("Denominator SSU values must be non-negative.")
    if require_proportion and (
        (numerator < 0).any() or (numerator > denominator).any()
        or not np.equal(numerator, np.floor(numerator)).all()
        or not np.equal(denominator, np.floor(denominator)).all()
    ):
        raise ValueError("For a proportion, successes and eligible counts must be whole numbers with successes between zero and eligible counts.")
    draws, _ = _ppswr_draw_estimates(
        work, draw_keys, stratum_key, numerator,
        numerator=numerator, denominator=denominator,
    )
    total_y = total_x = 0.0
    for _, group in draws.groupby(stratum_key, sort=False):
        p = group["__p__"].to_numpy()
        total_y += float(np.mean(group["__y_total_hat__"].to_numpy() / p))
        total_x += float(np.mean(group["__d_total_hat__"].to_numpy() / p))
    if total_x <= 0 or not np.isfinite(total_x):
        raise ValueError("Estimated population denominator must be positive.")
    ratio = total_y / total_x
    draws["__linearized__"] = (
        draws["__y_total_hat__"] - ratio * draws["__d_total_hat__"]
    ) / draws["__p__"]
    variance_total = 0.0
    stage2_component = 0.0
    df_total = 0
    stratum_rows = []
    for h, group in draws.groupby(stratum_key, sort=False):
        n = len(group)
        if n < 2:
            raise ValueError("At least two independent PSU draws per stratum are required for variance estimation.")
        variance_h = float(np.var(group["__linearized__"].to_numpy(), ddof=1) / n / total_x**2)
        # Delta-method stage-two diagnostic based on linearized SSU values.
        stage2_h = 0.0
        for key, source_group in work.groupby(draw_keys, sort=False):
            if (key[0] if isinstance(key, tuple) else "__ALL__") != h:
                continue
            m = len(source_group)
            M = int(source_group["__ssu_population__"].iloc[0])
            p = float(source_group["__selection_probability__"].iloc[0])
            lin = numerator.loc[source_group.index].to_numpy() - ratio * denominator.loc[source_group.index].to_numpy()
            s2 = float(np.var(lin, ddof=1))
            stage2_h += M**2 * (1-m/M) * s2 / m / (p**2) / n / total_x**2
        variance_total += variance_h
        stage2_component += stage2_h
        df_total += n - 1
        stratum_rows.append({"stratum": str(h), "psu_draws": n, "linearized_variance": variance_h,
                             "estimated_stage2_variance_component": stage2_h})
    se = float(np.sqrt(max(variance_total, 0.0)))
    critical = float(stats.t.ppf(0.5 + confidence_level / 2, df_total))
    lower, upper = ratio - critical * se, ratio + critical * se
    if require_proportion:
        lower, upper = max(0.0, lower), min(1.0, upper)
    return {
        "estimate": float(ratio), "numerator_total": float(total_y),
        "denominator_total": float(total_x), "variance": float(variance_total),
        "standard_error": se, "confidence_interval": (float(lower), float(upper)),
        "confidence_level": float(confidence_level), "degrees_of_freedom": int(df_total),
        "strata": pd.DataFrame(stratum_rows),
        "findings": [f"Estimated population {'proportion' if require_proportion else 'mean'}: {ratio:,.4g}.",
                     f"Taylor-linearised standard error: {se:,.4g}.",
                     f"{confidence_level:.0%} t confidence interval: [{lower:,.4g}, {upper:,.4g}]."],
        "warnings": [
            "Stage 1 uses independent PPS sampling with replacement and Hansen-Hurwitz expansion.",
            "Stage 2 uses SRSWOR within each selected PSU draw; draw identifiers distinguish repeated physical PSU selections.",
            "Ratio variance is estimated by Taylor linearisation of numerator minus ratio times denominator.",
            "PPS without replacement and certainty-PSU handling are not supported by this PPSWR estimator.",
        ],
        "metadata": {
            "estimator": "Two-stage PPSWR Taylor-linearised " + ("proportion" if require_proportion else "mean"),
            "sampling_design": "PPSWR PSUs; SRSWOR SSUs",
            "number_of_strata": int(draws[stratum_key].nunique()),
            "number_of_psu_draws": int(len(draws)),
            "degrees_of_freedom": int(df_total),
            "draw_variable": draw_variable,
            "selection_probability_variable": selection_probability_variable,
            "estimated_stage2_variance_component": float(stage2_component),
        },
    }


def estimate_two_stage_ppswr_mean(
    df: pd.DataFrame, outcome_total_variable: str, element_count_variable: str,
    psu_variable: str, draw_variable: str, ssu_variable: str,
    ssu_population_count_variable: str, selection_probability_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> dict[str, Any]:
    return _estimate_two_stage_ppswr_ratio(
        df, outcome_total_variable, element_count_variable, psu_variable,
        draw_variable, ssu_variable, ssu_population_count_variable,
        selection_probability_variable, strata_variable, confidence_level, False,
    )


def estimate_two_stage_ppswr_proportion(
    df: pd.DataFrame, successes_variable: str, eligible_count_variable: str,
    psu_variable: str, draw_variable: str, ssu_variable: str,
    ssu_population_count_variable: str, selection_probability_variable: str,
    strata_variable: str | None = None, confidence_level: float = 0.95,
) -> dict[str, Any]:
    return _estimate_two_stage_ppswr_ratio(
        df, successes_variable, eligible_count_variable, psu_variable,
        draw_variable, ssu_variable, ssu_population_count_variable,
        selection_probability_variable, strata_variable, confidence_level, True,
    )
