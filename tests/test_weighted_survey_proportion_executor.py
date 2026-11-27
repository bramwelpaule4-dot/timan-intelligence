"""Controlled execution tests for weighted survey proportions."""
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)


def _frame():
    return pd.DataFrame({
        "stratum": ["Urban"] * 4 + ["Rural"] * 4,
        "weight": [10.0] * 4 + [20.0] * 4,
        "uptake": ["Yes", "Yes", "No", "No", "Yes", "No", "No", "No"],
    })


def _recommendation(**options):
    return {
        "method": "Weighted survey proportion",
        "method_id": "method.survey.estimation.weighted_proportion",
        "variables": ["uptake", "weight"],
        "status": "review_required",
        "options": {"estimand": "proportion", **options},
        "design_context": {"sampling_design": "stratified", "sampling_weight": "weight"},
    }


def test_weighted_survey_proportion_is_available_and_requires_approval():
    assert "Weighted survey proportion" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_frame(), _recommendation(
            design="stratified_srs", strata_variable="stratum"
        ))


def test_weighted_survey_proportion_executes_stratified_design_after_approval():
    result = execute_recommendation(
        _frame(),
        _recommendation(design="stratified_srs", strata_variable="stratum"),
        approved=True,
    )
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.survey.estimation.weighted_proportion"
    assert result.metadata["estimand"] == "proportion"
    assert result.metadata["design"] == "stratified_srs"
    assert result.metadata["sampling_design_aware"] is True
    assert result.tables["estimates"]["ci_lower_percent"].notna().all()


def test_weighted_descriptive_mode_does_not_claim_design_based_inference():
    recommendation = {
        **_recommendation(design="weighted_descriptive"),
        "design_context": {},
    }
    result = execute_recommendation(_frame(), recommendation, approved=True)
    assert result.metadata["sampling_design_aware"] is False
    assert result.tables["estimates"]["ci_lower_percent"].isna().all()
    assert any("No design-based standard errors" in item for item in result.limitations)


def test_complex_design_cannot_fall_back_to_weights_only():
    recommendation = _recommendation(design="weighted_descriptive")
    with pytest.raises(AnalysisExecutionError, match="Weights alone"):
        execute_recommendation(_frame(), recommendation, approved=True)


def test_weighted_survey_proportion_rejects_unsupported_multistage_design():
    recommendation = _recommendation(
        design="cluster_wr", cluster_variable="psu"
    )
    recommendation["design_context"]["sampling_design"] = "multistage"
    with pytest.raises(AnalysisExecutionError, match="multistage"):
        execute_recommendation(_frame(), recommendation, approved=True)


def test_weighted_survey_proportion_requires_design_identifiers():
    recommendation = _recommendation(design="stratified_srs")
    with pytest.raises(AnalysisExecutionError, match="strata_variable"):
        execute_recommendation(_frame(), recommendation, approved=True)
