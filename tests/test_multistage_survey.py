import pandas as pd
import pytest

from timan_intelligence.core.multistage_survey import inspect_two_stage_design


def sample():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "ssu": [1, 1, 2, 2] * 4,
        "weight": [2.0] * 8 + [3.0] * 8,
        "psu_population": [10] * 8 + [20] * 8,
        "ssu_population": [5, 5, 5, 5] * 4,
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


def test_rejects_ssu_assigned_to_multiple_psus_within_stratum():
    df = sample()
    df.loc[4, "ssu"] = 1
    with pytest.raises(ValueError, match="only one PSU"):
        inspect_two_stage_design(df, "psu", "ssu", "weight", "stratum")


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
