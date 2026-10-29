
import pandas as pd
import pytest

from timan_intelligence.core.analysis_planner import plan_analysis
from timan_intelligence.core.contracts import AnalysisRequest


def test_planner_recommends_descriptive_statistics_for_numeric_data():
    df = pd.DataFrame({"income": [10, 20, 30]})
    request = AnalysisRequest(
        question="Describe household income",
        selected_variables=["income"],
    )

    plan = plan_analysis(df, request)

    assert plan.status == "review_required"
    assert plan.objective_type == "description"
    assert any(
        item["method"] == "Descriptive statistics"
        for item in plan.recommendations
    )


def test_planner_recommends_frequency_distribution_for_categories():
    df = pd.DataFrame({"ward": ["A", "B", "A"]})
    request = AnalysisRequest(
        question="Describe households by ward",
        selected_variables=["ward"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "description"
    assert any(
        item["method"] == "Frequency distribution"
        for item in plan.recommendations
    )


def test_planner_flags_selected_variable_not_in_dataset():
    df = pd.DataFrame({"income": [10, 20]})
    request = AnalysisRequest(
        question="Compare income",
        selected_variables=["age"],
    )

    plan = plan_analysis(df, request)

    assert plan.status == "needs_input"
    assert any("age" in item for item in plan.information_needed)
    assert plan.recommendations == []


def test_planner_requires_a_research_question():
    df = pd.DataFrame({"income": [10, 20]})
    request = AnalysisRequest(question="   ")

    plan = plan_analysis(df, request)

    assert plan.status == "needs_input"
    assert any(
        "research question" in item.lower()
        for item in plan.information_needed
    )


def test_planner_does_not_modify_dataset():
    df = pd.DataFrame({"income": [10, None, 30]})
    before = df.copy(deep=True)
    request = AnalysisRequest(
        question="Describe income",
        selected_variables=["income"],
    )

    plan_analysis(df, request)

    pd.testing.assert_frame_equal(df, before)


def test_planner_rejects_non_dataframe_input():
    request = AnalysisRequest(question="Describe income")

    with pytest.raises(TypeError):
        plan_analysis([10, 20, 30], request)


def test_comparison_objective_requests_outcome_and_groups():
    df = pd.DataFrame({
        "water_access": ["Yes", "No", "Yes"],
        "household_head_gender": ["Male", "Female", "Male"],
    })
    request = AnalysisRequest(
        question="Does water access differ between male-headed "
        "and female-headed households?",
        selected_variables=["water_access", "household_head_gender"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "comparison"
    assert any(
        "outcome variable" in item.lower()
        and "groups" in item.lower()
        for item in plan.information_needed
    )


def test_association_objective_requests_relationship_variables():
    df = pd.DataFrame({
        "income": [10, 20, 30],
        "education": ["Primary", "Secondary", "Tertiary"],
    })
    request = AnalysisRequest(
        question="Is household income associated with education level?",
        selected_variables=["income", "education"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "association"
    assert any(
        "two variables" in item.lower()
        for item in plan.information_needed
    )


def test_prediction_objective_requests_outcome_and_predictors():
    df = pd.DataFrame({
        "food_security": ["Secure", "Insecure", "Secure"],
        "income": [100, 50, 120],
    })
    request = AnalysisRequest(
        question="Can household income predict food security?",
        selected_variables=["food_security", "income"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "prediction"
    assert any(
        "predict" in item.lower()
        and "outcome" in item.lower()
        for item in plan.information_needed
    )


def test_ambiguous_objective_requires_clarification():
    df = pd.DataFrame({"age": [20, 30, 40], "income": [10, 20, 30]})
    request = AnalysisRequest(
        question="Compare the relationship between age and income.",
        selected_variables=["age", "income"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "ambiguous"
    assert plan.status == "needs_input"
    assert any(
        "clarify the primary research objective" in item.lower()
        for item in plan.information_needed
    )


def test_unrecognised_objective_requires_clarification():
    df = pd.DataFrame({"food_insecurity": ["High", "Low", "Medium"]})
    request = AnalysisRequest(
        question="What factors explain household food insecurity?",
        selected_variables=["food_insecurity"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "unknown"
    assert plan.status == "needs_input"
    assert any(
        "clarify the primary research objective" in item.lower()
        for item in plan.information_needed
    )
