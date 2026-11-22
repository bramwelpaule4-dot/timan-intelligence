import pandas as pd
import pytest

from timan_intelligence.core.multistage_survey import (
    estimate_two_stage_total,
    estimate_two_stage_mean,
    estimate_two_stage_proportion,
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



def test_two_stage_mean_uses_ratio_linearisation_and_both_fpcs():
    df = estimator_sample()
    df["element_count"] = [10] * len(df)
    result = estimate_two_stage_mean(
        df, "outcome", "element_count", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert result["estimate"] == pytest.approx(1040.0 / 480.0)
    assert result["standard_error"] >= 0
    assert result["metadata"]["variance_method"] == "Taylor linearisation of y - R*x"
    assert result["metadata"]["variance_stage_1"] + result["metadata"]["variance_stage_2"] == pytest.approx(result["variance"])


def test_two_stage_proportion_is_bounded_and_validates_success_counts():
    df = estimator_sample()
    df["eligible"] = [10] * len(df)
    df["successes"] = [1, 2, 3, 4, 2, 3, 4, 5]
    result = estimate_two_stage_proportion(
        df, "successes", "eligible", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert 0 <= result["estimate"] <= 1
    assert 0 <= result["confidence_interval"][0] <= 1
    assert 0 <= result["confidence_interval"][1] <= 1
    df["successes"] = df["successes"].astype(float)
    df.loc[0, "successes"] = 1.5
    with pytest.raises(ValueError, match="whole numbers"):
        estimate_two_stage_proportion(
            df, "successes", "eligible", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )
    df.loc[0, "successes"] = 11
    with pytest.raises(ValueError, match="between zero"):
        estimate_two_stage_proportion(
            df, "successes", "eligible", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )


def test_two_stage_ratio_rejects_zero_population_denominator():
    df = estimator_sample()
    df["element_count"] = 0
    with pytest.raises(ValueError, match="denominator must be positive"):
        estimate_two_stage_mean(
            df, "outcome", "element_count", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )


def test_two_stage_domain_mean_retains_non_domain_ssus_in_variance():
    from timan_intelligence.core.multistage_survey import estimate_two_stage_domain_mean
    df = estimator_sample()
    df["domain"] = ["target", "other"] * 4
    df["element_count"] = [10] * len(df)
    result = estimate_two_stage_domain_mean(
        df, "outcome", "element_count", "domain", "target", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert result["estimate"] == pytest.approx(520 / 160)
    assert result["metadata"]["sampled_domain_ssus"] == 4
    assert result["metadata"]["sampled_non_domain_ssus"] == 4
    assert len(result["psu_details"]) == 4
    assert result["standard_error"] >= 0


def test_two_stage_domain_proportion_and_total_are_supported():
    from timan_intelligence.core.multistage_survey import (
        estimate_two_stage_domain_proportion, estimate_two_stage_domain_total,
    )
    df = estimator_sample()
    df["domain"] = ["target", "other"] * 4
    df["eligible"] = [10] * len(df)
    df["successes"] = [1, 8, 2, 7, 3, 6, 4, 5]
    proportion = estimate_two_stage_domain_proportion(
        df, "successes", "eligible", "domain", "target", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    total = estimate_two_stage_domain_total(
        df, "outcome", "domain", "target", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert proportion["estimate"] == pytest.approx(10 / 40)
    assert 0 <= proportion["confidence_interval"][0] <= 1
    assert 0 <= proportion["confidence_interval"][1] <= 1
    assert total["estimate"] == pytest.approx(260)
    assert len(total["psu_details"]) == 4


def test_two_stage_domain_rejects_missing_or_absent_domain():
    from timan_intelligence.core.multistage_survey import estimate_two_stage_domain_total
    df = estimator_sample()
    df["domain"] = ["target"] * len(df)
    df.loc[0, "domain"] = None
    with pytest.raises(ValueError, match="cannot be missing"):
        estimate_two_stage_domain_total(
            df, "outcome", "domain", "target", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )
    df["domain"] = ["other"] * len(df)
    with pytest.raises(ValueError, match="no sampled SSUs"):
        estimate_two_stage_domain_total(
            df, "outcome", "domain", "target", "psu", "ssu",
            "psu_population", "ssu_population", "stratum",
        )
