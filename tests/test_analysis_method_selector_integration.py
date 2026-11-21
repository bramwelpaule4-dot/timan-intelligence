
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

def test_planner_exposes_registry_status_for_each_recommendation():
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
    recommendations = {item["method"]: item for item in plan.recommendations}

    assert recommendations["Independent-samples t-test"]["method_id"] == (
        "method.inference.comparison.t_test.independent.welch"
    )
    assert recommendations["Independent-samples t-test"]["implementation_status"] == "implemented"
    assert recommendations["Mann–Whitney U test"]["implementation_status"] == "planned"
    assert recommendations["Mann–Whitney U test"]["execution_eligibility"] == "not_assessed"


def test_planner_exposes_registry_metadata_for_descriptive_recommendations():
    df = pd.DataFrame({"income": [10, 20, 30], "sex": ["F", "M", "F"]})
    request = AnalysisRequest(
        question="What is the distribution of income and sex?",
        selected_variables=["income", "sex"],
    )

    plan = plan_analysis(df, request)
    recommendations = {item["method"]: item for item in plan.recommendations}

    assert recommendations["Descriptive statistics"]["method_id"] == (
        "method.descriptive.numeric.summary"
    )
    assert recommendations["Frequency distribution"]["method_id"] == (
        "method.descriptive.categorical.frequency"
    )

def test_planner_passes_confirmed_study_design_to_catalogue_assessment():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["A", "A", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={
            "independent_groups": True,
            "study_design": "independent",
            "preferred_method": "Paired-samples t-test",
        },
    )

    plan = plan_analysis(df, request)
    preferred = next(
        item
        for item in plan.recommendations
        if item.get("is_preferred") is True
    )

    assert preferred["status"] == "ineligible"
    assert "not catalogued" in preferred["reason"].lower()

def test_planner_accepts_explicitly_mapped_paired_measurement_roles():
    df = pd.DataFrame({
        "participant_id": [1, 2, 3, 4],
        "before": [10, 12, 9, 15],
        "after": [8, 10, 7, 12],
        "period": ["Before", "Before", "After", "After"],
    })
    request = AnalysisRequest(
        question="Does the score differ between the two measurements?",
        selected_variables=["after", "period"],
        options={
            "independent_groups": False,
            "study_design": "paired",
            "preferred_method": "Paired-samples t-test",
            "variable_roles": {
                "paired_measurement_before": "before",
                "paired_measurement_after": "after",
                "pair_identifier": "participant_id",
            },
        },
    )

    plan = plan_analysis(df, request)
    preferred = next(
        item for item in plan.recommendations
        if item.get("is_preferred") is True
    )

    assert preferred["status"] == "conditionally_eligible"
    assert preferred["required_variable_roles"] == [
        "paired_measurement_before",
        "paired_measurement_after",
        "pair_identifier",
    ]


def test_planner_does_not_accept_variable_roles_mapped_to_missing_columns():
    df = pd.DataFrame({
        "participant_id": [1, 2, 3, 4],
        "before": [10, 12, 9, 15],
        "after": [8, 10, 7, 12],
        "period": ["Before", "Before", "After", "After"],
    })
    request = AnalysisRequest(
        question="Does the score differ between the two measurements?",
        selected_variables=["after", "period"],
        options={
            "independent_groups": False,
            "study_design": "paired",
            "preferred_method": "Paired-samples t-test",
            "variable_roles": {
                "paired_measurement_before": "missing_before",
                "paired_measurement_after": "after",
                "pair_identifier": "participant_id",
            },
        },
    )

    plan = plan_analysis(df, request)
    preferred = next(
        item for item in plan.recommendations
        if item.get("is_preferred") is True
    )

    assert preferred["status"] == "insufficient_information"
    assert "paired_measurement_before" in preferred["reason"]

def test_planner_rejects_paired_measurement_role_with_non_numeric_column():
    df = pd.DataFrame({
        "participant_id": [1, 2, 3, 4],
        "before": [10, 12, 9, 15],
        "after": [8, 10, 7, 12],
        "period": ["Before", "Before", "After", "After"],
    })
    request = AnalysisRequest(
        question="Does the score differ between the two measurements?",
        selected_variables=["after", "period"],
        options={
            "independent_groups": False,
            "study_design": "paired",
            "preferred_method": "Paired-samples t-test",
            "variable_roles": {
                "paired_measurement_before": "period",
                "paired_measurement_after": "after",
                "pair_identifier": "participant_id",
            },
        },
    )

    plan = plan_analysis(df, request)
    preferred = next(
        item for item in plan.recommendations
        if item.get("is_preferred") is True
    )

    assert preferred["status"] == "insufficient_information"
    assert "paired_measurement_before" in preferred["reason"]



def test_planner_records_unconfirmed_design_without_inferring_from_dataset_shape():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["A", "A", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={"independent_groups": True},
    )

    plan = plan_analysis(df, request)

    assert plan.design_context["study_design"] is None
    assert plan.design_context["sampling_design"] is None
    assert plan.design_context["design_confirmation_required"] is True
    assert plan.design_context["design_was_inferred"] is False
    assert all(
        item["design_confirmation_required"]
        for item in plan.recommendations
    )


def test_planner_requests_cluster_and_weight_details_for_complex_survey():
    df = pd.DataFrame({
        "outcome": [0, 1, 0, 1],
        "cluster": [1, 1, 2, 2],
        "stratum": ["A", "A", "B", "B"],
        "weight": [1.2, 1.1, 0.9, 1.0],
    })
    request = AnalysisRequest(
        question="Is the outcome associated with the groups?",
        selected_variables=["outcome", "cluster"],
        options={
            "study_design": "complex survey",
            "sampling_design": "multistage",
            "cluster_variable": "cluster",
            "stratum_variable": "stratum",
            "sampling_weight_variable": "weight",
        },
    )

    plan = plan_analysis(df, request)

    assert plan.design_context["study_design"] == "complex_survey"
    assert plan.design_context["sampling_design"] == "multistage"
    assert any("design-adjusted" in warning.lower() for warning in plan.warnings)
    assert not any(
        "sampling weights are available" in question.lower()
        for question in plan.information_needed
    )


def test_descriptive_recommendations_are_explicitly_sample_level_and_keep_design_mappings():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "weight": [1.2, 0.8, 1.1, 0.9],
        "cluster": [1, 1, 2, 2],
    })
    request = AnalysisRequest(
        question="What is the distribution of income?",
        selected_variables=["income"],
        options={
            "study_design": "complex survey",
            "sampling_design": "cluster",
            "sampling_weight_variable": "weight",
            "cluster_variable": "cluster",
        },
    )

    plan = plan_analysis(df, request)

    numeric_summary = next(
        item for item in plan.recommendations
        if item["method"] == "Descriptive statistics"
    )
    assert numeric_summary["estimate_scope"] == "observed_dataset"
    assert numeric_summary["population_representative"] is False
    assert any(
        "observed dataset" in check.lower()
        and "population estimates" in check.lower()
        for check in numeric_summary["checks"]
    )
    assert numeric_summary["design_context"]["sampling_weight"] == "weight"
    assert numeric_summary["design_context"]["cluster_identifier"] == "cluster"


def test_planner_rejects_unrecognised_study_design_label():
    df = pd.DataFrame({
        "income": [10, 20, 30, 40],
        "group": ["A", "A", "B", "B"],
    })
    request = AnalysisRequest(
        question="Does income differ between the two groups?",
        selected_variables=["income", "group"],
        options={
            "independent_groups": True,
            "study_design": "maybe experimental",
        },
    )

    plan = plan_analysis(df, request)

    assert plan.design_context["study_design"] is None
    assert any(
        "not recognised" in question.lower()
        for question in plan.information_needed
    )
