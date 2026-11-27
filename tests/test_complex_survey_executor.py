"""Controlled execution tests for complex survey mean, total and proportion estimates."""
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)


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
        "income": [1., 2., 3., 4., 2., 3., 4., 5., 4., 5., 6., 7., 5., 6., 7., 8.],
        "uptake": ["Yes", "Yes", "No", "No"] * 4,
    })


def _recommendation(variables, **options):
    return {
        "method": "Complex survey estimation",
        "method_id": "method.survey.inference.complex_design",
        "variables": variables,
        "status": "review_required",
        "options": options,
    }


def test_complex_survey_estimation_is_available_and_approval_gated():
    assert "Complex survey estimation" in available_execution_methods()
    recommendation = _recommendation(
        ["income", "weight"], estimand="mean", design="stratified_srs",
        strata_variable="stratum",
    )
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_stratified(), recommendation)


def test_complex_survey_estimation_runs_stratified_mean_and_total():
    frame = _stratified()
    mean = execute_recommendation(
        frame,
        _recommendation(
            ["income", "weight"], estimand="mean", design="stratified_srs",
            strata_variable="stratum",
        ),
        approved=True,
    )
    total = execute_recommendation(
        frame,
        _recommendation(
            ["income", "weight"], estimand="total", design="stratified_srs",
            strata_variable="stratum",
        ),
        approved=True,
    )
    assert mean.status == total.status == "success"
    assert mean.metadata["estimand"] == "mean"
    assert total.metadata["estimand"] == "total"
    assert mean.metadata["sampling_design_aware"] is True
    assert mean.tables["estimates"]["standard_error"].notna().all()
    assert total.tables["estimates"]["standard_error"].notna().all()


def test_complex_survey_estimation_runs_cluster_proportion():
    result = execute_recommendation(
        _clustered(),
        _recommendation(
            ["uptake", "weight"], estimand="proportion", design="cluster_wr",
            strata_variable="stratum", cluster_variable="psu",
        ),
        approved=True,
    )
    assert result.status == "success"
    assert result.metadata["design"] == "cluster_wr"
    assert result.metadata["estimand"] == "proportion"
    assert result.metadata["sampling_design_aware"] is True
    assert result.tables["estimates"]["ci_lower_percent"].notna().all()


def test_complex_survey_estimation_requires_supported_design_and_identifier():
    frame = _stratified()
    with pytest.raises(AnalysisExecutionError, match="Select a supported survey design"):
        execute_recommendation(
            frame,
            _recommendation(["income", "weight"], estimand="mean"),
            approved=True,
        )
    with pytest.raises(AnalysisExecutionError, match="strata_variable"):
        execute_recommendation(
            frame,
            _recommendation(["income", "weight"], estimand="mean", design="stratified_srs"),
            approved=True,
        )


def test_complex_survey_estimation_rejects_unsupported_multistage_design():
    recommendation = _recommendation(
        ["income", "weight"], estimand="mean", design="cluster_wr",
        cluster_variable="psu",
    )
    recommendation["design_context"] = {"sampling_design": "multistage"}
    with pytest.raises(AnalysisExecutionError, match="multistage"):
        execute_recommendation(_stratified(), recommendation, approved=True)
