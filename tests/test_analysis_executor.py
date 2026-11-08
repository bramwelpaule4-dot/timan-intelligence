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


def test_execution_registry_exposes_only_implemented_methods():
    methods = available_execution_methods()

    assert "Descriptive statistics" in methods
    assert "Independent-samples t-test" in methods
    assert "One-way ANOVA" in methods
    assert "Frequencies and proportions" not in methods
