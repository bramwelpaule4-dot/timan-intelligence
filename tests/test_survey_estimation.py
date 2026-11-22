import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.survey_estimation import estimate_survey
from timan_intelligence.services.analysis_service import run_survey_estimation_service


def _stratified():
    return pd.DataFrame({
        "stratum": ["Urban"] * 4 + ["Rural"] * 4,
        "weight": [10.0] * 4 + [20.0] * 4,
        "income": [10., 12., 14., 16., 4., 6., 8., 10.],
        "uptake": ["Yes", "Yes", "No", "No", "Yes", "No", "No", "No"],
    })


def _clustered():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "weight": [2.] * 8 + [3.] * 8,
        "income": [1., 2., 3., 4., 2., 3., 4., 5.,
                   4., 5., 6., 7., 5., 6., 7., 8.],
        "uptake": ["Yes", "Yes", "No", "No"] * 4,
    })


def test_stratified_total_and_standard_error_match_hand_calculation():
    result = estimate_survey(
        _stratified(), "income", "weight", "total", "stratified_srs",
        strata_variable="stratum",
    )
    row = result["table"].iloc[0]
    assert row["weighted_total"] == pytest.approx(1080.0)
    expected_variance = (4 * 10) ** 2 * (20 / 3) / 4 + (4 * 20) ** 2 * (20 / 3) / 4
    assert row["standard_error"] == pytest.approx(np.sqrt(expected_variance))
    assert row["ci_lower"] < row["weighted_total"] < row["ci_upper"]
    assert len(result["details"]) == 2


def test_cluster_total_uses_ultimate_psu_variance():
    result = estimate_survey(
        _clustered(), "income", "weight", "total", "cluster_wr",
        strata_variable="stratum", cluster_variable="psu",
    )
    row = result["table"].iloc[0]
    assert row["weighted_total"] == pytest.approx(264.0)
    assert row["standard_error"] > 0
    assert row["degrees_of_freedom"] == 2
    assert row["ci_lower"] < row["weighted_total"] < row["ci_upper"]


def test_stratified_mean_and_proportions_return_design_intervals():
    frame = _stratified()
    mean = estimate_survey(
        frame, "income", "weight", "mean", "stratified_srs",
        strata_variable="stratum",
    )
    assert "standard_error" in mean["table"]
    prop = estimate_survey(
        frame, "uptake", "weight", "proportion", "stratified_srs",
        strata_variable="stratum",
    )
    assert prop["table"]["weighted_percent"].sum() == pytest.approx(100)
    assert prop["table"]["ci_lower_percent"].notna().all()


def test_cluster_mean_and_proportions_return_psu_adjusted_intervals():
    frame = _clustered()
    mean = estimate_survey(
        frame, "income", "weight", "mean", "cluster_wr",
        strata_variable="stratum", cluster_variable="psu",
    )
    assert mean["metadata"]["variance_method"].startswith("with-replacement ultimate-cluster")
    prop = estimate_survey(
        frame, "uptake", "weight", "proportion", "cluster_wr",
        strata_variable="stratum", cluster_variable="psu",
    )
    assert prop["table"]["standard_error_percentage_points"].notna().all()


def test_weighted_descriptive_mode_does_not_claim_design_standard_errors():
    result = estimate_survey(_stratified(), "income", "weight", "mean")
    assert result["table"]["standard_error"].isna().all()
    assert any("No design-based standard error" in warning for warning in result["warnings"])


def test_service_wraps_result_with_design_and_estimand_metadata():
    result = run_survey_estimation_service(
        _stratified(), "income", "weight", "total", "stratified_srs",
        strata_variable="stratum",
    )
    assert result.status == "success"
    assert result.metadata["estimand"] == "total"
    assert "estimates" in result.tables


def test_rejects_incomplete_total_records_and_invalid_design():
    frame = _stratified()
    frame.loc[0, "income"] = np.nan
    with pytest.raises(ValueError, match="complete"):
        estimate_survey(frame, "income", "weight", "total", "stratified_srs", "stratum")
    with pytest.raises(ValueError, match="Unsupported survey design"):
        estimate_survey(_stratified(), "income", "weight", design="complex_magic")


def test_rejects_single_psu_in_cluster_total_stratum():
    frame = _clustered()
    frame.loc[frame["stratum"] == "B", "psu"] = 3
    with pytest.raises(ValueError, match="At least two sampled PSUs"):
        estimate_survey(
            frame, "income", "weight", "total", "cluster_wr",
            strata_variable="stratum", cluster_variable="psu",
        )
