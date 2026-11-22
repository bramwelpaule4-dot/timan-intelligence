import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.survey_estimation import estimate_domain_survey
from timan_intelligence.services.analysis_service import run_domain_survey_estimation_service


def _stratified():
    return pd.DataFrame({
        "stratum": ["A"] * 4 + ["B"] * 4,
        "weight": [2.0] * 4 + [3.0] * 4,
        "area": ["Target", "Other", "Target", "Other"] * 2,
        "income": [10., 20., 14., 24., 5., 15., 9., 19.],
        "uptake": ["Yes", "No", "No", "Yes", "Yes", "No", "Yes", "No"],
    })


def _clustered():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "weight": [2.] * 8 + [3.] * 8,
        "area": ["Target", "Other"] * 8,
        "income": [1., 2., 3., 4., 2., 3., 4., 5.,
                   4., 5., 6., 7., 5., 6., 7., 8.],
        "uptake": ["Yes", "Yes", "No", "No"] * 4,
    })


def test_stratified_domain_mean_uses_full_sample_and_returns_interval():
    frame = _stratified()
    result = estimate_domain_survey(
        frame, "income", "weight", "area", "Target",
        "mean", "stratified_srs", strata_variable="stratum",
    )
    row = result["table"].iloc[0]
    assert row["domain_unweighted_n"] == 4
    assert row["estimate"] == pytest.approx((2 * (10 + 14) + 3 * (5 + 9)) / (2 * 2 + 3 * 2))
    assert row["standard_error"] > 0
    assert row["ci_lower"] < row["estimate"] < row["ci_upper"]
    assert len(result["details"]) == 2


def test_stratified_domain_proportion_and_total():
    frame = _stratified()
    prop = estimate_domain_survey(
        frame, "uptake", "weight", "area", "Target",
        "proportion", "stratified_srs", strata_variable="stratum",
    )
    assert set(prop["table"]["category"]) == {"Yes", "No"}
    assert prop["table"]["estimate"].sum() == pytest.approx(1.0)
    assert prop["table"]["standard_error"].notna().all()

    total = estimate_domain_survey(
        frame, "income", "weight", "area", "Target",
        "total", "stratified_srs", strata_variable="stratum",
    )
    assert total["table"].iloc[0]["estimate"] == pytest.approx(2 * 24 + 3 * 14)
    assert total["table"].iloc[0]["standard_error"] > 0


def test_cluster_domain_mean_uses_ultimate_psu_variance():
    result = estimate_domain_survey(
        _clustered(), "income", "weight", "area", "Target",
        "mean", "cluster_wr", strata_variable="stratum",
        cluster_variable="psu",
    )
    assert result["table"].iloc[0]["standard_error"] > 0
    assert "ultimate-PSU" in result["metadata"]["variance_method"]
    assert result["table"].iloc[0]["domain_unweighted_n"] == 8


def test_weighted_descriptive_domain_has_point_estimate_but_no_inference():
    result = estimate_domain_survey(
        _stratified(), "income", "weight", "area", "Target", "mean",
    )
    assert result["table"].iloc[0]["estimate"] == pytest.approx(9.0)
    assert np.isnan(result["table"].iloc[0]["standard_error"])
    assert any("Weights alone" in item for item in result["warnings"])


def test_domain_validation_and_service_wrapper():
    frame = _stratified()
    with pytest.raises(ValueError, match="No records"):
        estimate_domain_survey(frame, "income", "weight", "area", "Missing")
    with pytest.raises(ValueError, match="constant expansion"):
        altered = frame.copy()
        altered.loc[0, "weight"] = 9
        estimate_domain_survey(
            altered, "income", "weight", "area", "Target",
            "mean", "stratified_srs", strata_variable="stratum",
        )
    result = run_domain_survey_estimation_service(
        frame, "income", "weight", "area", "Target",
        "mean", "stratified_srs", strata_variable="stratum",
    )
    assert result.status == "success"
    assert result.metadata["domain_variable"] == "area"
