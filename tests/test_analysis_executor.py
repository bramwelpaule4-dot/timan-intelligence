import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)


def test_execution_requires_explicit_user_approval():
    df = pd.DataFrame({"score": [1, 2, 3]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["score"],
        "status": "review_required",
    }

    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(df, recommendation)


def test_execution_blocks_unresolved_clarification_questions():
    df = pd.DataFrame({"score": [1, 2, 3]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["score"],
        "status": "review_required",
    }

    with pytest.raises(AnalysisExecutionError, match="clarification"):
        execute_recommendation(
            df, recommendation, approved=True,
            information_needed=["Confirm the study design."],
        )


def test_execution_blocks_ineligible_recommendation():
    df = pd.DataFrame({
        "score": [1, 2, 3, 4],
        "group": ["A", "A", "B", "B"],
    })
    recommendation = {
        "method": "Independent-samples t-test",
        "variables": ["score", "group"],
        "status": "ineligible",
    }

    with pytest.raises(AnalysisExecutionError, match="ineligible"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_runs_approved_welch_test_and_preserves_review_checks():
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "Independent-samples t-test",
        "variables": ["score", "group"],
        "status": "review_required",
        "checks": ["Review independence of observations."],
    }

    result = execute_recommendation(df, recommendation, approved=True)

    assert result.status == "success"
    assert result.method == "Welch's independent-samples t-test"
    assert result.metadata["user_approved"] is True
    assert result.metadata["execution_registry"] == "controlled"
    assert any("Review required:" in item for item in result.limitations)


def test_execution_runs_one_way_anova():
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7, 8, 9, 10],
        "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
    })
    recommendation = {
        "method": "One-way ANOVA",
        "variables": ["score", "group"],
        "status": "review_required",
    }

    result = execute_recommendation(df, recommendation, approved=True)

    assert result.status == "success"
    assert result.method == "One-way ANOVA"
    assert result.tables["summary"]["groups"] == 3


def test_execution_rejects_methods_without_an_execution_implementation():
    df = pd.DataFrame({"category": ["A", "B", "A"]})
    recommendation = {
        "method": "Frequencies and proportions",
        "variables": ["category"],
        "status": "review_required",
    }

    with pytest.raises(AnalysisExecutionError, match="does not yet"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_rejects_invalid_variable_names():
    df = pd.DataFrame({"score": [1, 2, 3]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["not_a_column"],
        "status": "review_required",
    }

    with pytest.raises(AnalysisExecutionError, match="invalid"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_blocks_inferential_method_for_clustered_sampling_even_if_approved():
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "Independent-samples t-test",
        "variables": ["score", "group"],
        "status": "review_required",
        "design_context": {
            "study_design": "clustered",
            "sampling_design": "cluster",
        },
    }

    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_blocks_inferential_method_for_stratified_sampling():
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "One-way ANOVA",
        "variables": ["score", "group"],
        "status": "review_required",
        "design_context": {"sampling_design": "stratified"},
    }

    with pytest.raises(AnalysisExecutionError, match="design-aware estimator"):
        execute_recommendation(df, recommendation, approved=True)


@pytest.mark.parametrize("study_design", [
    "paired", "repeated_measures", "longitudinal", "time_series",
])
def test_execution_blocks_independent_group_tests_for_repeated_designs(study_design):
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "Independent-samples t-test",
        "variables": ["score", "group"],
        "status": "review_required",
        "design_context": {"study_design": study_design},
    }

    with pytest.raises(AnalysisExecutionError, match="assumes independent groups"):
        execute_recommendation(df, recommendation, approved=True)


def test_descriptive_execution_is_labelled_as_observed_dataset_not_population():
    df = pd.DataFrame({"score": [1, 2, 3, 4]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["score"],
        "status": "review_required",
        "design_context": {
            "study_design": "complex_survey",
            "sampling_design": "cluster",
            "sampling_weight": "weight",
            "cluster_identifier": "cluster",
        },
    }

    result = execute_recommendation(df, recommendation, approved=True)

    assert result.metadata["estimate_scope"] == "observed_dataset"
    assert result.metadata["population_representative"] is False
    assert "not a population estimate" in result.limitations[-1]


def test_execution_registry_exposes_only_implemented_methods():
    methods = available_execution_methods()

    assert "Descriptive statistics" in methods
    assert "Independent-samples t-test" in methods
    assert "One-way ANOVA" in methods
    assert "Frequencies and proportions" not in methods

def test_execution_blocks_catalogued_but_unimplemented_method():
    df = pd.DataFrame({
        "score": [1, 2, 3, 4, 5, 6],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "Mann–Whitney U test",
        "variables": ["score", "group"],
        "status": "review_required",
        "method_id": "method.inference.comparison.mann_whitney",
    }

    with pytest.raises(AnalysisExecutionError, match="does not yet"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_rejects_a_method_identifier_that_does_not_match_catalogue():
    df = pd.DataFrame({"score": [1, 2, 3]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["score"],
        "status": "review_required",
        "method_id": "method.inference.comparison.anova.one_way",
    }

    with pytest.raises(AnalysisExecutionError, match="does not match"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_result_records_catalogue_provenance():
    df = pd.DataFrame({"score": [1, 2, 3, 4]})
    recommendation = {
        "method": "Descriptive statistics",
        "variables": ["score"],
        "status": "review_required",
        "method_id": "method.descriptive.numeric.summary",
    }

    result = execute_recommendation(df, recommendation, approved=True)

    assert result.metadata["method_id"] == "method.descriptive.numeric.summary"
    assert result.metadata["catalogue_version"] == "1.0.0"
    assert result.metadata["sampling_design_aware"] is False
