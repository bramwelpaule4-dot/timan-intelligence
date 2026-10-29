
import pandas as pd

from timan_intelligence.core.analysis_planner import plan_analysis
from timan_intelligence.core.contracts import AnalysisRequest


def test_planner_recommends_methods_for_numeric_comparison():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40, 50, 60],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={"independent_groups": True},
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "comparison"
    assert any(
        item["method"] == "Independent-samples t-test"
        for item in plan.recommendations
    )
    assert any(
        item["method"] == "Mann–Whitney U test"
        for item in plan.recommendations
    )


def test_planner_requests_confirmation_for_group_independence():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["A", "A", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "comparison"
    assert any(
        "independent observations" in item.lower()
        for item in plan.information_needed
    )
    assert not any(
        item["method"] == "Independent-samples t-test"
        for item in plan.recommendations
    )


def test_planner_recommends_correlation_for_numeric_association():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40, 50],
        "expenditure": [8, 15, 25, 32, 45],
    })
    request = AnalysisRequest(
        question="Is income associated with expenditure?",
        selected_variables=["income", "expenditure"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "association"
    assert any(
        item["method"] == "Pearson correlation"
        for item in plan.recommendations
    )
    assert any(
        item["method"] == "Spearman rank correlation"
        for item in plan.recommendations
    )


def test_planner_requests_predictor_for_prediction():
    df = pd.DataFrame({
        "food_security": [0, 1, 0, 1],
        "income": [20, 40, 25, 60],
    })
    request = AnalysisRequest(
        question="Can income predict food security?",
        selected_variables=["food_security"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "prediction"
    assert any(
        "predictor variable" in item.lower()
        for item in plan.information_needed
    )
    assert not any(
        item["method"] == "Logistic regression"
        for item in plan.recommendations
    )


def test_planner_does_not_recommend_methods_for_unknown_objective():
    df = pd.DataFrame({"income": [10, 20, 30]})
    request = AnalysisRequest(
        question="What factors explain household food insecurity?",
        selected_variables=["income"],
    )

    plan = plan_analysis(df, request)

    assert plan.objective_type == "unknown"
    assert plan.status == "needs_input"
    assert any(
        "clarify the primary research objective" in item.lower()
        for item in plan.information_needed
    )
    assert not any(
        item["method"] in {
            "Independent-samples t-test",
            "Mann–Whitney U test",
            "One-way ANOVA",
            "Kruskal–Wallis test",
            "Pearson correlation",
            "Spearman rank correlation",
            "Logistic regression",
            "Linear regression",
        }
        for item in plan.recommendations
    )


def test_planner_assesses_preferred_method_conditionally():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40, 50, 60],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={
            "independent_groups": True,
            "preferred_method": "Independent-samples t-test",
        },
    )

    plan = plan_analysis(df, request)

    preferred = next(
        item
        for item in plan.recommendations
        if item.get("is_preferred") is True
    )

    assert preferred["method"] == "Independent-samples t-test"
    assert preferred["status"] == "conditionally_eligible"
    assert preferred["checks"]
    assert any(
        "assumptions have not been verified" in warning.lower()
        for warning in plan.warnings
    )


def test_planner_rejects_incompatible_preferred_method_and_offers_alternatives():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40, 50, 60, 70, 80, 90],
        "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
    })
    request = AnalysisRequest(
        question="Does income differ between the groups?",
        selected_variables=["income", "group"],
        options={
            "independent_groups": True,
            "preferred_method": "Independent-samples t-test",
        },
    )

    plan = plan_analysis(df, request)

    preferred = next(
        item
        for item in plan.recommendations
        if item.get("is_preferred") is True
    )
    alternative_methods = {
        item["method"]
        for item in plan.recommendations
        if not item.get("is_preferred", False)
    }

    assert plan.objective_type == "comparison"
    assert preferred["status"] == "ineligible"
    assert "two independent groups" in preferred["reason"].lower()
    assert "One-way ANOVA" in alternative_methods
    assert "Kruskal–Wallis test" in alternative_methods


def test_planner_recommends_multi_group_methods():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40, 50, 60, 70, 80, 90],
        "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
    })
    request = AnalysisRequest(
        question="Does income differ between the groups?",
        selected_variables=["income", "group"],
        options={"independent_groups": True},
    )

    plan = plan_analysis(df, request)

    methods = {
        item["method"]
        for item in plan.recommendations
    }

    assert plan.objective_type == "comparison"
    assert "One-way ANOVA" in methods
    assert "Kruskal–Wallis test" in methods
    assert not any(
        "initial comparison selector supports two groups" in item.lower()
        for item in plan.information_needed
    )


def test_planner_requests_clarification_for_invalid_outcome_variable():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["A", "A", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the groups?",
        selected_variables=["income", "group"],
        options={
            "independent_groups": True,
            "outcome_variable": "missing_column",
            "group_variable": "group",
        },
    )

    plan = plan_analysis(df, request)

    assert any(
        "missing_column" in item
        for item in plan.information_needed
    )
    assert not any(
        item.get("is_preferred") is True
        for item in plan.recommendations
    )


def test_planner_does_not_recommend_independent_tests_for_paired_design():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["Before", "Before", "After", "After"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={"independent_groups": False},
    )

    plan = plan_analysis(df, request)

    methods = {
        item["method"]
        for item in plan.recommendations
    }

    assert "Independent-samples t-test" not in methods
    assert "Mann–Whitney U test" not in methods
    assert any(
        "paired/repeated-measures" in item.lower()
        for item in plan.information_needed
    )
