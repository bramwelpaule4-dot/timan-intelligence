import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_two_stage_survey_design_inspection_service,
    run_two_stage_survey_total_service,
)


def test_two_stage_design_service_returns_shared_analysis_result():
    df = pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "ssu": [1, 1, 2, 2, 3, 3, 4, 4] * 2,
        "weight": [2.0] * 8 + [3.0] * 8,
    })
    result = run_two_stage_survey_design_inspection_service(
        df, "psu", "ssu", "weight", "stratum"
    )
    assert result.status == "success"
    assert "psu_summary" in result.tables
    assert "ssu_summary" in result.tables
    assert result.metadata["variance_estimation_available"] is False
    assert result.limitations


def test_two_stage_total_service_returns_estimate_and_variance():
    df = pd.DataFrame({
        "stratum": ["A"] * 4 + ["B"] * 4,
        "psu": [1, 1, 2, 2, 3, 3, 4, 4],
        "ssu": [1, 2] * 4,
        "outcome": [10, 20, 30, 40, 5, 15, 25, 35],
        "psu_population": [4] * 4 + [8] * 4,
        "ssu_population": [4] * 8,
    })
    result = run_two_stage_survey_total_service(
        df, "outcome", "psu", "ssu", "psu_population", "ssu_population", "stratum"
    )
    assert result.status == "success"
    assert result.metadata["estimate"] == pytest.approx(1040.0)
    assert result.metadata["standard_error"] > 0
    assert result.metadata["confidence_interval"][0] < 1040.0
    assert result.metadata["confidence_interval"][1] > 1040.0
    assert "stratum_estimates" in result.tables



def test_two_stage_mean_and_proportion_services_return_shared_results():
    from timan_intelligence.services.analysis_service import (
        run_two_stage_survey_mean_service,
        run_two_stage_survey_proportion_service,
    )
    df = pd.DataFrame({
        "stratum": ["A"] * 4 + ["B"] * 4,
        "psu": [1, 1, 2, 2, 3, 3, 4, 4],
        "ssu": [1, 2] * 4,
        "outcome_total": [10, 20, 30, 40, 5, 15, 25, 35],
        "successes": [1, 2, 3, 4, 2, 3, 4, 5],
        "eligible": [10] * 8,
        "psu_population": [4] * 4 + [8] * 4,
        "ssu_population": [4] * 8,
    })
    mean = run_two_stage_survey_mean_service(
        df, "outcome_total", "eligible", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    proportion = run_two_stage_survey_proportion_service(
        df, "successes", "eligible", "psu", "ssu",
        "psu_population", "ssu_population", "stratum",
    )
    assert mean.status == "success"
    assert mean.metadata["estimate"] == pytest.approx(1040 / 960)
    assert "psu_details" in mean.tables
    assert proportion.status == "success"
    assert 0 <= proportion.metadata["estimate"] <= 1
