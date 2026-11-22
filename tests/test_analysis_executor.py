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


def test_execution_blocks_inferential_method_when_sampling_weights_are_declared():
    df = pd.DataFrame({
        "score": [1, 2, 3, 5, 6, 7],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    recommendation = {
        "method": "Independent-samples t-test",
        "variables": ["score", "group"],
        "status": "review_required",
        "design_context": {"sampling_design": "simple_random", "sampling_weight": "w"},
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
        "method": "Kruskal–Wallis test",
        "variables": ["score", "group"],
        "status": "review_required",
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

def test_execution_runs_registered_mean_confidence_interval():
    df = pd.DataFrame({"income": [10.0, 12.0, 14.0, 16.0, 18.0]})
    recommendation = {
        "method": "Confidence interval for a mean",
        "method_id": "method.inference.confidence_interval.mean",
        "variables": ["income"],
        "status": "review_required",
        "options": {"confidence_level": 0.90},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.confidence_interval.mean"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)
    assert result.metadata["user_approved"] is True


def test_mean_confidence_interval_executor_blocks_complex_sampling():
    df = pd.DataFrame({"income": [10.0, 12.0, 14.0, 16.0]})
    recommendation = {
        "method": "Confidence interval for a mean",
        "variables": ["income"],
        "status": "review_required",
        "design_context": {"sampling_design": "stratified"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)

def test_execution_runs_registered_proportion_confidence_interval():
    df = pd.DataFrame({"covered": [1, 1, 1, 0, 0, 0]})
    recommendation = {
        "method": "Confidence interval for a proportion",
        "method_id": "method.inference.confidence_interval.proportion",
        "variables": ["covered"],
        "status": "review_required",
        "options": {"confidence_level": 0.90},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.confidence_interval.proportion"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_proportion_confidence_interval_executor_blocks_complex_sampling():
    df = pd.DataFrame({"covered": [1, 1, 0, 0]})
    recommendation = {
        "method": "Confidence interval for a proportion",
        "variables": ["covered"],
        "status": "review_required",
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_runs_registered_welch_mean_difference_interval():
    df = pd.DataFrame({
        "group": ["A", "A", "A", "B", "B", "B"],
        "score": [10.0, 12.0, 14.0, 7.0, 8.0, 9.0],
    })
    recommendation = {
        "method": "Welch confidence interval for a mean difference",
        "method_id": "method.inference.confidence_interval.mean_difference.welch",
        "variables": ["score", "group"],
        "status": "review_required",
        "options": {"confidence_level": 0.90},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.confidence_interval.mean_difference.welch"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_welch_mean_difference_interval_executor_blocks_complex_sampling():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "score": [10.0, 12.0, 7.0, 9.0],
    })
    recommendation = {
        "method": "Welch confidence interval for a mean difference",
        "variables": ["score", "group"],
        "status": "review_required",
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_runs_registered_paired_mean_change_interval():
    df = pd.DataFrame({"before": [10.0, 12.0, 14.0, 16.0], "after": [12.0, 15.0, 15.0, 20.0]})
    recommendation = {
        "method": "Paired mean-change confidence interval",
        "method_id": "method.inference.confidence_interval.mean_difference.paired",
        "variables": ["before", "after"],
        "status": "review_required",
        "design_context": {"study_design": "paired"},
        "options": {"confidence_level": 0.90},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.confidence_interval.mean_difference.paired"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)

def test_paired_mean_change_executor_blocks_complex_sampling():
    df = pd.DataFrame({"before": [1.0, 2.0, 3.0], "after": [2.0, 3.0, 5.0]})
    recommendation = {
        "method": "Paired mean-change confidence interval",
        "variables": ["before", "after"],
        "status": "review_required",
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)


def test_executor_runs_approved_one_sample_t_test_with_reference_value():
    df = pd.DataFrame({"score": [8, 9, 10, 11, 12]})
    recommendation = {
        "method": "One-sample Student's t-test",
        "variables": ["score"],
        "options": {"reference_value": 8, "alternative": "two-sided"},
        "status": "review_required",
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.method == "One-sample Student's t-test"
    assert result.metadata["user_approved"] is True


def test_executor_requires_reference_value_for_one_sample_t_test():
    df = pd.DataFrame({"score": [8, 9, 10]})
    recommendation = {
        "method": "One-sample Student's t-test",
        "variables": ["score"],
        "status": "review_required",
    }
    with pytest.raises(AnalysisExecutionError, match="reference_value"):
        execute_recommendation(df, recommendation, approved=True)


def test_executor_runs_chi_square_independence_and_blocks_complex_sampling():
    from timan_intelligence.core.analysis_executor import AnalysisExecutionError, execute_recommendation
    frame = pd.DataFrame({"training": ["Yes"] * 30 + ["No"] * 30, "employment": ["Yes"] * 24 + ["No"] * 6 + ["Yes"] * 12 + ["No"] * 18})
    recommendation = {"method": "Chi-square test of independence", "method_id": "method.inference.association.chi_square.independence", "variables": ["training", "employment"], "status": "review_required", "design_context": {"study_design": "independent_observations"}}
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.association.chi_square.independence"
    blocked = {**recommendation, "design_context": {"sampling_design": "cluster"}}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, blocked, approved=True)


def test_executor_runs_exact_binomial_test_and_requires_reference_proportion():
    from timan_intelligence.core.analysis_executor import AnalysisExecutionError, execute_recommendation
    frame = pd.DataFrame({"event": [1] * 8 + [0] * 12})
    recommendation = {"method": "Exact one-sample binomial test", "method_id": "method.inference.comparison.binomial.one_sample", "variables": ["event"], "status": "review_required", "options": {"reference_proportion": 0.3, "alternative": "greater"}, "design_context": {"study_design": "independent_observations"}}
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.binomial.one_sample"
    missing = {**recommendation, "options": {}}
    with pytest.raises(AnalysisExecutionError, match="reference_proportion"):
        execute_recommendation(frame, missing, approved=True)
    blocked = {**recommendation, "design_context": {"sampling_design": "cluster"}}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, blocked, approved=True)


def test_executor_runs_fisher_exact_and_blocks_complex_sampling():
    from timan_intelligence.core.analysis_executor import AnalysisExecutionError, execute_recommendation
    frame = pd.DataFrame({"exposure": ["Y"] * 10 + ["N"] * 6, "outcome": ["Y"] * 8 + ["N"] * 2 + ["Y"] + ["N"] * 5})
    recommendation = {"method": "Fisher exact test", "method_id": "method.inference.association.fisher_exact", "variables": ["exposure", "outcome"], "status": "review_required", "options": {"alternative": "two-sided"}, "design_context": {"study_design": "independent_observations"}}
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.association.fisher_exact"
    blocked = {**recommendation, "design_context": {"sampling_design": "cluster"}}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, blocked, approved=True)


def test_execution_runs_registered_two_independent_proportions_comparison():
    df = pd.DataFrame({"event": [1, 1, 1, 0, 0, 1, 0, 0], "group": ["A", "A", "A", "A", "B", "B", "B", "B"]})
    recommendation = {
        "method": "Two-independent-proportions comparison",
        "method_id": "method.inference.comparison.proportions.independent",
        "variables": ["event", "group"], "status": "review_required",
        "options": {"confidence_level": 0.90, "alternative": "greater"},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.proportions.independent"
    assert result.metadata["alternative"] == "greater"


def test_two_independent_proportions_executor_blocks_cluster_sampling():
    df = pd.DataFrame({"event": [1, 0, 1, 0], "group": ["A", "A", "B", "B"]})
    recommendation = {
        "method": "Two-independent-proportions comparison",
        "variables": ["event", "group"], "status": "review_required",
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)


def test_execution_runs_registered_two_proportions_confidence_interval():
    df = pd.DataFrame({"event": [1, 1, 1, 0, 0, 1, 0, 0], "group": ["A", "A", "A", "A", "B", "B", "B", "B"]})
    recommendation = {
        "method": "Confidence interval for difference in two proportions",
        "method_id": "method.inference.confidence_interval.proportions.independent",
        "variables": ["event", "group"], "status": "review_required",
        "options": {"confidence_level": 0.90},
    }
    result = execute_recommendation(df, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.confidence_interval.proportions.independent"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_two_proportions_confidence_interval_executor_blocks_cluster_sampling():
    df = pd.DataFrame({"event": [1, 0, 1, 0], "group": ["A", "A", "B", "B"]})
    recommendation = {
        "method": "Confidence interval for difference in two proportions",
        "variables": ["event", "group"], "status": "review_required",
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(df, recommendation, approved=True)



def test_execution_runs_registered_mann_whitney_u_test():
    frame = pd.DataFrame({"score": [1, 2, 3, 4, 5, 6], "group": ["A", "A", "A", "B", "B", "B"]})
    recommendation = {"method": "Mann–Whitney U test", "method_id": "method.inference.comparison.mann_whitney", "variables": ["score", "group"], "status": "review_required", "options": {"alternative": "less"}}
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.mann_whitney"
    assert result.metadata["alternative"] == "less"


def test_mann_whitney_executor_blocks_cluster_and_repeated_measures_designs():
    frame = pd.DataFrame({"score": [1, 2, 3, 4], "group": ["A", "A", "B", "B"]})
    recommendation = {"method": "Mann–Whitney U test", "variables": ["score", "group"], "status": "review_required", "design_context": {"sampling_design": "cluster"}}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, recommendation, approved=True)
    recommendation["design_context"] = {"study_design": "paired"}
    with pytest.raises(AnalysisExecutionError, match="repeated-measures"):
        execute_recommendation(frame, recommendation, approved=True)
