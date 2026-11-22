"""Two-stage survey design inspection and validation.

This module validates a declared stratified two-stage sample hierarchy and
summarises stage-specific sampling fractions. It deliberately does NOT compute
standard errors, confidence intervals, or population estimates: valid
multistage variance estimation requires additional design-specific assumptions
and estimators beyond hierarchy validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def inspect_two_stage_design(
    df: pd.DataFrame,
    psu_variable: str,
    ssu_variable: str,
    weight_variable: str,
    strata_variable: str | None = None,
    psu_population_count_variable: str | None = None,
    ssu_population_count_variable: str | None = None,
) -> dict[str, Any]:
    """Validate a two-stage sample hierarchy and report design metadata.

    Population-count columns, when supplied, must contain the number of
    population units at that stage and be constant within their sampling unit.
    The PSU population count is constant within a stratum; the SSU population
    count is constant within a PSU. Weights are checked but not recalibrated.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")

    named = [psu_variable, ssu_variable, weight_variable]
    optional = [
        strata_variable,
        psu_population_count_variable,
        ssu_population_count_variable,
    ]
    named.extend(x for x in optional if x is not None)
    if len(set(named)) != len(named):
        raise ValueError("PSU, SSU, weight, stratum and population-count variables must be different.")
    missing = [column for column in named if column not in df.columns]
    if missing:
        raise KeyError(f"Variables not found: {', '.join(missing)}.")

    def identifiers(column: str, label: str) -> pd.Series:
        values = df[column].astype("object").map(
            lambda x: x.strip() if isinstance(x, str) else x
        ).replace("", pd.NA)
        if values.isna().any():
            raise ValueError(f"{label} identifiers cannot be missing.")
        return values

    psu = identifiers(psu_variable, "PSU")
    ssu = identifiers(ssu_variable, "SSU")
    if strata_variable:
        strata = identifiers(strata_variable, "Stratum")
    else:
        strata = pd.Series("__ALL__", index=df.index, dtype="object")

    weight = pd.to_numeric(df[weight_variable], errors="coerce")
    if weight.isna().any() or not np.isfinite(weight.to_numpy(dtype=float)).all():
        raise ValueError("Every two-stage design record must have a finite numeric survey weight.")
    if (weight <= 0).any():
        raise ValueError("Survey weights must be strictly positive.")

    hierarchy = pd.DataFrame({"stratum": strata, "psu": psu, "ssu": ssu})
    # A secondary unit must belong to exactly one parent PSU within its stratum.
    ssu_parent_counts = hierarchy.groupby(
        ["stratum", "ssu"], dropna=False, sort=False
    )["psu"].nunique()
    if (ssu_parent_counts > 1).any():
        raise ValueError("Each SSU identifier must belong to only one PSU within its stratum.")

    # A sampled SSU should be represented once in the analysis file. Multiple
    # respondent records per SSU are valid and are reflected in record counts.
    psu_keys = ["stratum", "psu"]
    ssu_counts = hierarchy.groupby(psu_keys, sort=False)["ssu"].nunique()
    stratum_psu_counts = hierarchy[psu_keys].drop_duplicates().groupby(
        "stratum", sort=False
    ).size()

    def population_counts(
        column: str | None,
        grouping: list[str],
        sampled_counts: pd.Series,
        label: str,
    ) -> tuple[dict[str, int] | None, float | None]:
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
        aligned = declared.reindex(sampled_counts.index)
        if aligned.isna().any() or (aligned.to_numpy() < sampled_counts.to_numpy()).any():
            raise ValueError(f"{label} population counts cannot be smaller than sampled counts.")
        fractions = sampled_counts.astype(float) / aligned.astype(float)
        return {str(k): int(v) for k, v in declared.items()}, float(fractions.mean())

    # Stage-1 population size is specified per stratum.
    psu_sampled = stratum_psu_counts.sort_index()
    psu_population, mean_psu_fraction = population_counts(
        psu_population_count_variable,
        ["stratum"],
        psu_sampled,
        "First-stage PSU",
    )
    # Stage-2 population size is specified per sampled PSU.
    ssu_sampled = ssu_counts.sort_index()
    ssu_population, mean_ssu_fraction = population_counts(
        ssu_population_count_variable,
        ["stratum", "psu"],
        ssu_sampled,
        "Second-stage SSU",
    )

    psu_size = hierarchy[psu_keys].drop_duplicates().groupby(
        "stratum", sort=False
    ).size()
    metadata = {
        "design_type": "stratified two-stage cluster sample" if strata_variable else "two-stage cluster sample",
        "records": int(len(df)),
        "number_of_strata": int(hierarchy["stratum"].nunique()),
        "number_of_psus": int(len(ssu_counts)),
        "number_of_ssus": int(ssu_counts.sum()),
        "minimum_ssus_per_psu": int(ssu_counts.min()),
        "maximum_ssus_per_psu": int(ssu_counts.max()),
        "minimum_psus_per_stratum": int(psu_size.min()),
        "maximum_psus_per_stratum": int(psu_size.max()),
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
        "mean_first_stage_sampling_fraction": mean_psu_fraction,
        "mean_second_stage_sampling_fraction": mean_ssu_fraction,
        "variance_estimation_available": False,
    }
    warnings = [
        "This is a design-structure validation and metadata inspection, not a multistage estimator.",
        "No standard errors, confidence intervals, hypothesis tests, or design-adjusted population estimates are produced.",
        "The supplied final weights are checked for validity but are not verified against selection probabilities or recalibrated.",
        "Stage-specific population counts are optional; sampling fractions are unavailable for a stage when its population-count variable is not supplied.",
        "A future multistage variance engine must explicitly account for within-PSU SSU sampling and the declared stage-specific design.",
    ]
    return {
        "metadata": metadata,
        "psu_summary": pd.DataFrame({
            "stratum": stratum_psu_counts.index.astype(str),
            "sampled_psus": stratum_psu_counts.to_numpy(dtype=int),
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
        "warnings": warnings,
    }
