import pandas as pd
import pytest

from timan_intelligence.core.multistage_survey import (
    estimate_two_stage_total,
    inspect_two_stage_design,
)


def sample():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "ssu": [1, 1, 2, 2, 3, 3, 4, 4] * 2,
        "weight": [2.0] * 8 + [3.0] * 8,
        "psu_population": [10] * 8 + [20] * 8,
        "ssu_population": [5, 5, 5, 5] * 4,
    })


def estimator_sample():
    return pd.DataFrame({
        "stratum": ["A"] * 4 + ["B"] * 4,
        "psu": [1, 1, 2, 2, 3, 3, 4, 4],
        "ssu": [1, 2] * 4,
        "outcome": [10, 20, 30, 40, 5, 15, 25, 35],
        "psu_population": [4] * 4 + [8] * 4,
        "ssu_population": [4] * 8,
    })


def test_inspects_two_stage_hierarchy_and_stage_sampling_fractions():
    result = inspect_two_stage_design(
        sample(), "psu", "ssu", "weight", "stratum",
        "psu_population", "ssu_population",
    )
    meta = result["metadata"]
    assert meta["number_of_strata"] == 2
    assert meta["number_of_psus"] == 4
    assert meta["number_of_ssus"] == 8
    assert meta["mean_first_stage_sampling_fraction"] == pytest.approx(0.15)
    assert meta["mean_second_stage_sampling_fraction"] == pytest.approx(0.4)
    assert meta["variance_estimation_available"] is False
    assert len(result["psu_summary"]) == 2
    assert len(result["ssu_summary"]) == 4


def test_allows_reused_ssu_labels_under_different_psus():
    result = inspect_two_stage_design(sample(), "psu", "ssu", "weight", "stratum")
    assert result["metadata"]["number_of_ssus"] == 8


def test_allows_ssu_labels_to_repeat_across_psus_within_stratum():
    df = sample()
    # SSU labels are local to each PSU; the same label can occur in PSU 1 and PSU 2.
    df.loc[4:7, "ssu"] = [1, 1, 2, 2]
    result = inspect_two_stage_design(df, "psu", "ssu", "weight", "stratum")
    assert result["metadata"]["number_of_ssus"] == 8


def test_rejects_missing_psu_or_ssu_identifiers():
    df = sample()
    df.loc[0, "ssu"] = None
    with pytest.raises(ValueError, match="SSU identifiers"):
        inspect_two_stage_design(df, "psu", "ssu", "weight", "stratum")


def test_rejects_invalid_weights():
    df = sample()
    df.loc[0, "weight"] = 0
    with pytest.raises(ValueError, match="strictly positive"):
        inspect_two_stage_design(df, "psu", "ssu", "weight", "stratum")


def test_rejects_population_count_smaller_than_sampled_count():
    df = sample()
    df["psu_population"] = 1
    with pytest.raises(ValueError, match="smaller than sampled"):
        inspect_two_stage_design(
            df, "psu", "ssu", "weight", "stratum", "psu_population"
        )


def test_rejects_population_counts_that_vary_within_sampling_unit():
    df = sample()
    df.loc[0, "ssu_population"] = 6
    with pytest.raises(ValueError, match="constant within"):
        inspect_two_stage_design(
            df, "psu", "ssu", "weight", "stratum", None, "ssu_population"
        )


def test_requires_distinct_variable_roles():
    with pytest.raises(ValueError, match="must be different"):
        inspect_two_stage_design(sample(), "psu", "ssu", "psu", "stratum")


def test_two_stage_total_estimator_applies_both_stage_expansion_factors():
    result = estimate_two_stage_total(
        estimator_sample(), "outcome", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    # Stratum A: PSU expanded totals 60 and 140; total = 4/2 * 200 = 400.
    # Stratum B: PSU expanded totals 40 and 120; total = 8/2 * 160 = 640.
    assert result["estimate"] == pytest.approx(1040.0)
    assert result["metadata"]["variance_stage_1"] > 0
    assert result["metadata"]["variance_stage_2"] > 0
    assert result["variance"] == pytest.approx(
        result["metadata"]["variance_stage_1"] + result["metadata"]["variance_stage_2"]
    )
    assert result["degrees_of_freedom"] == 2


def test_two_stage_total_estimator_zero_variance_when_census_at_both_stages():
    df = estimator_sample()
    df["psu_population"] = [2] * 4 + [2] * 4
    df["ssu_population"] = 2
    result = estimate_two_stage_total(
        df, "outcome", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert result["variance"] == pytest.approx(0.0)
    assert result["standard_error"] == pytest.approx(0.0)


def test_estimator_requires_one_row_per_sampled_ssu():
    df = estimator_sample()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one row per sampled SSU"):
        estimate_two_stage_total(
            df, "outcome", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )


def test_estimator_requires_at_least_two_psus_per_stratum():
    df = estimator_sample()
    df = df[df["psu"] == 1]
    with pytest.raises(ValueError, match="two sampled PSUs"):
        estimate_two_stage_total(
            df, "outcome", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )


def test_estimator_requires_at_least_two_ssus_per_psu():
    df = estimator_sample()
    df = df[df["ssu"] == 1]
    with pytest.raises(ValueError, match="two sampled SSUs"):
        estimate_two_stage_total(
            df, "outcome", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )
