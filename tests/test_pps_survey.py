import pandas as pd
import pytest

from timan_intelligence.core.pps_survey import (
    estimate_two_stage_ppswr_total,
    estimate_two_stage_ppswr_mean,
    estimate_two_stage_ppswr_proportion,
)


def ppswr_sample():
    return pd.DataFrame({
        "stratum": ["A"] * 8,
        "draw": ["d1", "d1", "d2", "d2", "d3", "d3", "d4", "d4"],
        "psu": ["P1", "P1", "P2", "P2", "P1", "P1", "P3", "P3"],
        "ssu": [1, 2] * 4,
        "outcome": [10, 20, 5, 15, 12, 18, 8, 12],
        "ssu_population": [2] * 8,
        "probability": [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25],
        "eligible": [10] * 8,
        "successes": [2, 4, 1, 3, 3, 5, 2, 4],
    })


def test_two_stage_ppswr_total_uses_hansen_hurwitz_expansion_and_draw_variance():
    result = estimate_two_stage_ppswr_total(
        ppswr_sample(), "outcome", "psu", "draw", "ssu",
        "ssu_population", "probability", "stratum",
    )
    # Draw expanded totals are 30, 20, 30, 20; divide by p and average.
    expected = ((30 / .5) + (20 / .25) + (30 / .5) + (20 / .25)) / 4
    assert result["estimate"] == pytest.approx(expected)
    assert result["variance"] > 0
    assert result["degrees_of_freedom"] == 3
    assert result["metadata"]["number_of_psu_draws"] == 4
    assert result["metadata"]["number_of_unique_psus"] == 3
    assert len(result["psu_draw_details"]) == 4


def test_two_stage_ppswr_mean_and_proportion_use_ratio_linearisation():
    df = ppswr_sample()
    mean = estimate_two_stage_ppswr_mean(
        df, "outcome", "eligible", "psu", "draw", "ssu",
        "ssu_population", "probability", "stratum",
    )
    proportion = estimate_two_stage_ppswr_proportion(
        df, "successes", "eligible", "psu", "draw", "ssu",
        "ssu_population", "probability", "stratum",
    )
    assert mean["estimate"] > 0
    assert mean["variance"] >= 0
    assert 0 <= proportion["estimate"] <= 1
    assert 0 <= proportion["confidence_interval"][0] <= 1
    assert 0 <= proportion["confidence_interval"][1] <= 1


def test_two_stage_ppswr_rejects_invalid_probabilities_and_duplicate_draw_ssus():
    df = ppswr_sample()
    df.loc[0, "probability"] = 0
    with pytest.raises(ValueError, match="greater than zero"):
        estimate_two_stage_ppswr_total(
            df, "outcome", "psu", "draw", "ssu",
            "ssu_population", "probability", "stratum",
        )
    df = ppswr_sample()
    df.loc[1, "ssu"] = 1
    with pytest.raises(ValueError, match="must appear once"):
        estimate_two_stage_ppswr_total(
            df, "outcome", "psu", "draw", "ssu",
            "ssu_population", "probability", "stratum",
        )


def test_two_stage_ppswr_requires_two_draws_per_stratum():
    df = ppswr_sample()
    df = df[df["draw"] == "d1"]
    with pytest.raises(ValueError, match="At least two independent PSU draws"):
        estimate_two_stage_ppswr_total(
            df, "outcome", "psu", "draw", "ssu",
            "ssu_population", "probability", "stratum",
        )


def test_two_stage_ppswr_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_two_stage_ppswr_total_service
    result = run_two_stage_ppswr_total_service(
        ppswr_sample(), "outcome", "psu", "draw", "ssu",
        "ssu_population", "probability", "stratum",
    )
    assert result.status == "success"
    assert result.metadata["sampling_design"] == "PPS with replacement at stage 1; SRSWOR at stage 2"
    assert "psu_draw_details" in result.tables
