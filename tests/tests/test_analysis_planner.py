
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
