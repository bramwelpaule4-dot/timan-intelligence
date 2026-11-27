
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.statistical_engine import (
    run_independent_samples_t_test,
)


def test_welch_t_test_returns_correct_result_structure():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "score": [1, 2, 3, 4, 5, 6, 7, 8],
        }
    )

    result = run_independent_samples_t_test(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert result.status == "success"
    assert result.method == "Welch's independent-samples t-test"
    assert summary["group_1_n"] == 4
    assert summary["group_2_n"] == 4
    assert summary["group_1_mean"] == pytest.approx(2.5)
    assert summary["group_2_mean"] == pytest.approx(6.5)
    assert summary["t_statistic"] == pytest.approx(-4.38178046)
    assert 0 <= summary["p_value"] <= 1
    assert summary["p_value"] < 0.05
    assert summary["degrees_of_freedom"] == pytest.approx(6.0)


def test_welch_t_test_handles_unequal_group_sizes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B", "B", "B"],
            "score": [10, 12, 14, 20, 21, 22, 23, 24],
        }
    )

    result = run_independent_samples_t_test(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["group_1_n"] == 3
    assert summary["group_2_n"] == 5
    assert summary["group_1_mean"] == pytest.approx(12.0)
    assert summary["group_2_mean"] == pytest.approx(22.0)
    assert 0 <= summary["p_value"] <= 1
    assert summary["degrees_of_freedom"] > 0


def test_welch_t_test_excludes_and_reports_missing_outcomes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B"],
            "score": [10, None, 14, 20, 22, None],
        }
    )

    result = run_independent_samples_t_test(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["group_1_n"] == 2
    assert summary["group_2_n"] == 2
    assert summary["missing_outcomes"] == 2


def test_welch_t_test_rejects_missing_outcome_variable():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "score": [10, 12, 20, 22],
        }
    )

    with pytest.raises(ValueError, match="not found"):
        run_independent_samples_t_test(
            df,
            outcome_variable="income",
            group_variable="group",
        )


def test_welch_t_test_rejects_missing_group_variable():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "score": [10, 12, 20, 22],
        }
    )

    with pytest.raises(ValueError, match="not found"):
        run_independent_samples_t_test(
            df,
            outcome_variable="score",
            group_variable="ward",
        )


def test_welch_t_test_rejects_non_numeric_outcome():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "score": ["low", "high", "low", "high"],
        }
    )

    with pytest.raises(TypeError, match="numeric"):
        run_independent_samples_t_test(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_welch_t_test_requires_exactly_two_groups():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": [10, 12, 20, 22, 30, 32],
        }
    )

    with pytest.raises(ValueError, match="two groups"):
        run_independent_samples_t_test(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_welch_t_test_requires_at_least_two_observations_per_group():
    df = pd.DataFrame(
        {
            "group": ["A", "B", "B"],
            "score": [10, 20, 22],
        }
    )

    with pytest.raises(ValueError, match="at least two"):
        run_independent_samples_t_test(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_welch_t_test_rejects_missing_group_labels():
    df = pd.DataFrame(
        {
            "group": ["A", "A", None, "B", "B"],
            "score": [10, 12, 15, 20, 22],
        }
    )

    with pytest.raises(ValueError, match="group"):
        run_independent_samples_t_test(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_welch_t_test_excludes_and_reports_infinite_outcomes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B"],
            "score": [
                10.0,
                12.0,
                float("inf"),
                20.0,
                22.0,
                float("-inf"),
            ],
        }
    )

    result = run_independent_samples_t_test(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["group_1_n"] == 2
    assert summary["group_2_n"] == 2
    assert summary["infinite_outcomes"] == 2
    assert 0 <= summary["p_value"] <= 1


def test_welch_t_test_does_not_modify_original_data():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "score": [10, 12, 20, 22],
        }
    )
    original = df.copy(deep=True)

    run_independent_samples_t_test(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    pd.testing.assert_frame_equal(df, original)


def test_mean_confidence_interval_returns_estimate_and_interval():
    from timan_intelligence.core.statistical_engine import run_mean_confidence_interval

    result = run_mean_confidence_interval(
        pd.DataFrame({"income": [10, 12, 14, 16, 18]}), "income", 0.95
    )
    assert result.status == "success"
    assert result.metadata["estimate"] == pytest.approx(14.0)
    assert result.metadata["standard_error"] == pytest.approx(1.41421356237)
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 14 < upper
    assert result.metadata["degrees_of_freedom"] == 4
    assert result.metadata["sampling_design_aware"] is False


def test_mean_confidence_interval_reports_missing_and_infinite_values():
    from timan_intelligence.core.statistical_engine import run_mean_confidence_interval

    result = run_mean_confidence_interval(
        pd.DataFrame({"score": [10.0, 20.0, None, float("inf"), 30.0]}),
        "score",
    )
    assert result.metadata["observations"] == 3
    assert result.metadata["missing_values"] == 1
    assert result.metadata["infinite_values"] == 1
    assert any("infinite" in item for item in result.limitations)


def test_mean_confidence_interval_validates_input_and_confidence_level():
    from timan_intelligence.core.statistical_engine import run_mean_confidence_interval

    frame = pd.DataFrame({"score": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="less than 1"):
        run_mean_confidence_interval(frame, "score", 1.0)
    with pytest.raises(ValueError, match="at least two"):
        run_mean_confidence_interval(pd.DataFrame({"score": [1.0]}), "score")
    with pytest.raises(TypeError, match="numeric"):
        run_mean_confidence_interval(pd.DataFrame({"score": ["a", "b"]}), "score")


def test_mean_confidence_interval_service_uses_shared_result_contract():
    from timan_intelligence.services.analysis_service import run_mean_confidence_interval_service

    result = run_mean_confidence_interval_service(
        pd.DataFrame({"score": [2.0, 4.0, 6.0, 8.0]}), "score", 0.90
    )
    assert result.status == "success"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_proportion_confidence_interval_uses_wilson_score_and_binary_data():
    from timan_intelligence.core.statistical_engine import run_proportion_confidence_interval

    result = run_proportion_confidence_interval(
        pd.DataFrame({"covered": [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]}),
        "covered",
        0.95,
    )
    assert result.status == "success"
    assert result.metadata["estimate"] == pytest.approx(0.3)
    lower, upper = result.metadata["confidence_interval"]
    assert 0 < lower < 0.3 < upper < 1
    assert result.method == "Wilson score confidence interval for a proportion"


def test_proportion_confidence_interval_handles_all_successes_and_missing_values():
    from timan_intelligence.core.statistical_engine import run_proportion_confidence_interval

    result = run_proportion_confidence_interval(
        pd.DataFrame({"event": [1, 1, 1, None]}), "event"
    )
    assert result.metadata["estimate"] == pytest.approx(1.0)
    assert result.metadata["observations"] == 3
    assert result.metadata["missing_values"] == 1
    lower, upper = result.metadata["confidence_interval"]
    assert 0 < lower < 1
    assert upper == pytest.approx(1.0)


def test_proportion_confidence_interval_rejects_non_binary_and_empty_data():
    from timan_intelligence.core.statistical_engine import run_proportion_confidence_interval

    with pytest.raises(ValueError, match="only 0 and 1"):
        run_proportion_confidence_interval(pd.DataFrame({"x": [0, 1, 2]}), "x")
    with pytest.raises(ValueError, match="at least one"):
        run_proportion_confidence_interval(pd.DataFrame({"x": [None, None]}), "x")


def test_proportion_confidence_interval_service_returns_shared_result():
    from timan_intelligence.services.analysis_service import run_proportion_confidence_interval_service

    result = run_proportion_confidence_interval_service(
        pd.DataFrame({"event": [1, 0, 1, 0, 1]}), "event", 0.90
    )
    assert result.status == "success"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_welch_mean_difference_interval_uses_group_one_minus_group_two():
    from timan_intelligence.core.statistical_engine import run_welch_mean_difference_confidence_interval

    frame = pd.DataFrame({
        "group": ["A", "A", "A", "B", "B", "B", "B"],
        "score": [10.0, 12.0, 14.0, 7.0, 8.0, 9.0, 10.0],
    })
    result = run_welch_mean_difference_confidence_interval(
        frame, "score", "group", 0.95
    )
    assert result.status == "success"
    assert result.metadata["group_1_label"] == "A"
    assert result.metadata["group_2_label"] == "B"
    assert result.metadata["estimate"] == pytest.approx(3.5)
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 3.5 < upper
    assert result.metadata["degrees_of_freedom"] > 0
    assert result.metadata["sampling_design_aware"] is False


def test_welch_mean_difference_interval_excludes_missing_and_infinite_outcomes():
    from timan_intelligence.core.statistical_engine import run_welch_mean_difference_confidence_interval

    frame = pd.DataFrame({
        "group": ["A", "A", "A", "B", "B", "B"],
        "score": [10.0, 12.0, float("inf"), 7.0, 9.0, None],
    })
    result = run_welch_mean_difference_confidence_interval(frame, "score", "group")
    assert result.metadata["missing_values"] == 1
    assert result.metadata["infinite_values"] == 1
    assert result.metadata["group_1_label"] == "A"
    assert result.metadata["group_2_label"] == "B"


def test_welch_mean_difference_interval_validates_groups_and_sample_sizes():
    from timan_intelligence.core.statistical_engine import run_welch_mean_difference_confidence_interval

    with pytest.raises(ValueError, match="exactly two groups"):
        run_welch_mean_difference_confidence_interval(
            pd.DataFrame({"group": ["A", "A", "A"], "score": [1, 2, 3]}),
            "score", "group",
        )
    with pytest.raises(ValueError, match="At least two finite"):
        run_welch_mean_difference_confidence_interval(
            pd.DataFrame({"group": ["A", "A", "B", "B"], "score": [1, float("inf"), 2, 3]}),
            "score", "group",
        )
    with pytest.raises(ValueError, match="less than 1"):
        run_welch_mean_difference_confidence_interval(
            pd.DataFrame({"group": ["A", "A", "B", "B"], "score": [1, 2, 3, 4]}),
            "score", "group", 1.0,
        )


def test_paired_mean_change_interval_uses_after_minus_before():
    from timan_intelligence.core.statistical_engine import run_paired_mean_difference_confidence_interval
    frame = pd.DataFrame({"before": [10.0, 12.0, 14.0, 16.0], "after": [12.0, 15.0, 15.0, 20.0]})
    result = run_paired_mean_difference_confidence_interval(frame, "before", "after", 0.90)
    assert result.status == "success"
    assert result.metadata["estimate"] == pytest.approx(2.5)
    assert result.metadata["complete_pairs"] == 4
    assert result.metadata["degrees_of_freedom"] == 3
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 2.5 < upper
    assert result.metadata["study_design"] == "paired"

def test_paired_mean_change_interval_excludes_incomplete_pairs():
    from timan_intelligence.core.statistical_engine import run_paired_mean_difference_confidence_interval
    frame = pd.DataFrame({"before": [1.0, 2.0, None, 4.0, float("inf")], "after": [2.0, 4.0, 5.0, 7.0, 8.0]})
    result = run_paired_mean_difference_confidence_interval(frame, "before", "after")
    assert result.metadata["complete_pairs"] == 3
    assert result.metadata["missing_pairs"] == 1
    assert result.metadata["infinite_pairs"] == 1

def test_paired_mean_change_interval_validates_pair_count_and_variables():
    from timan_intelligence.core.statistical_engine import run_paired_mean_difference_confidence_interval
    with pytest.raises(ValueError, match="At least two complete"):
        run_paired_mean_difference_confidence_interval(pd.DataFrame({"b": [1.0, None], "a": [2.0, 3.0]}), "b", "a")
    with pytest.raises(ValueError, match="different variables"):
        run_paired_mean_difference_confidence_interval(pd.DataFrame({"b": [1.0, 2.0]}), "b", "b")


def test_one_sample_t_test_reports_statistic_p_value_and_confidence_interval():
    from timan_intelligence.core.statistical_engine import run_one_sample_t_test

    df = pd.DataFrame({"score": [8, 9, 10, 11, 12]})
    result = run_one_sample_t_test(df, "score", reference_value=8)

    row = result.tables["test"].iloc[0]
    assert result.status == "success"
    assert result.method == "One-sample Student's t-test"
    assert row["Sample mean"] == pytest.approx(10)
    assert row["Mean difference"] == pytest.approx(2)
    assert row["Degrees of freedom"] == 4
    assert 0 <= row["p-value"] <= 1
    assert row["p-value"] < 0.05
    assert row["Lower confidence limit"] < 10 < row["Upper confidence limit"]


def test_one_sample_t_test_supports_directional_alternatives_and_exclusions():
    from timan_intelligence.core.statistical_engine import run_one_sample_t_test

    df = pd.DataFrame({"score": [10, 11, 12, None, float("inf")]})
    result = run_one_sample_t_test(df, "score", 8, alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["observations"] == 3
    assert result.metadata["missing_values"] == 1
    assert result.metadata["infinite_values"] == 1
    assert result.metadata["p_value"] < 0.05


@pytest.mark.parametrize(
    "reference,alternative",
    [(float("nan"), "two-sided"), (1, "invalid")],
)
def test_one_sample_t_test_rejects_invalid_reference_or_alternative(reference, alternative):
    from timan_intelligence.core.statistical_engine import run_one_sample_t_test

    with pytest.raises(ValueError):
        run_one_sample_t_test(
            pd.DataFrame({"score": [1, 2, 3]}),
            "score",
            reference,
            alternative=alternative,
        )


def test_one_sample_t_test_rejects_constant_sample_equal_to_reference():
    from timan_intelligence.core.statistical_engine import run_one_sample_t_test

    with pytest.raises(ValueError, match="undefined"):
        run_one_sample_t_test(
            pd.DataFrame({"score": [5, 5, 5]}), "score", 5
        )



def test_paired_samples_t_test_reports_change_statistic_and_p_value():
    from timan_intelligence.core.statistical_engine import run_paired_samples_t_test
    frame = pd.DataFrame({"before": [10.0, 12.0, 14.0, 16.0], "after": [12.0, 15.0, 15.0, 20.0]})
    result = run_paired_samples_t_test(frame, "before", "after", 0.90)
    row = result.tables["test"].iloc[0]
    assert result.status == "success"
    assert result.method == "Paired-samples Student's t-test"
    assert row["Mean change (after - before)"] == pytest.approx(2.5)
    assert row["Degrees of freedom"] == 3
    assert 0 <= row["p-value"] <= 1
    assert result.metadata["study_design"] == "paired"


def test_paired_samples_t_test_supports_directional_alternatives_and_exclusions():
    from timan_intelligence.core.statistical_engine import run_paired_samples_t_test
    frame = pd.DataFrame({"before": [1.0, 2.0, 3.0, None, float("inf")], "after": [3.0, 4.0, 5.0, 6.0, 8.0]})
    result = run_paired_samples_t_test(frame, "before", "after", alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["complete_pairs"] == 3
    assert result.metadata["missing_pairs"] == 1
    assert result.metadata["infinite_pairs"] == 1
    assert result.metadata["p_value"] < 0.05


def test_paired_samples_t_test_rejects_invalid_pair_inputs():
    from timan_intelligence.core.statistical_engine import run_paired_samples_t_test
    with pytest.raises(ValueError, match="different variables"):
        run_paired_samples_t_test(pd.DataFrame({"before": [1.0, 2.0]}), "before", "before")
    with pytest.raises(ValueError, match="at least two complete"):
        run_paired_samples_t_test(pd.DataFrame({"before": [1.0, None], "after": [2.0, 3.0]}), "before", "after")
    with pytest.raises(ValueError, match="Alternative"):
        run_paired_samples_t_test(pd.DataFrame({"before": [1.0, 2.0], "after": [2.0, 3.0]}), "before", "after", alternative="invalid")


def test_executor_runs_registered_paired_samples_t_test_and_blocks_complex_sampling():
    from timan_intelligence.core.analysis_executor import AnalysisExecutionError, execute_recommendation
    frame = pd.DataFrame({"before": [10.0, 12.0, 14.0, 16.0], "after": [12.0, 15.0, 15.0, 20.0]})
    recommendation = {
        "method": "Paired-samples t-test", "method_id": "method.inference.comparison.t_test.paired",
        "variables": ["before", "after"], "status": "review_required",
        "design_context": {"study_design": "paired"},
        "options": {"confidence_level": 0.90, "alternative": "greater"},
    }
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.t_test.paired"
    blocked = {**recommendation, "design_context": {"study_design": "paired", "sampling_design": "cluster"}}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, blocked, approved=True)


def test_chi_square_independence_returns_tables_and_effect_size():
    from timan_intelligence.core.statistical_engine import run_chi_square_test_of_independence
    frame = pd.DataFrame({"training": ["Yes"] * 30 + ["No"] * 30, "employed": ["Yes"] * 24 + ["No"] * 6 + ["Yes"] * 12 + ["No"] * 18})
    result = run_chi_square_test_of_independence(frame, "training", "employed")
    assert result.status == "success"
    assert result.metadata["n_observations"] == 60
    assert result.metadata["degrees_of_freedom"] == 1
    assert 0 <= result.metadata["p_value"] <= 1
    assert 0 <= result.metadata["cramers_v"] <= 1
    assert "expected_counts" in result.tables and "pearson_residuals" in result.tables


def test_chi_square_independence_excludes_missing_and_flags_small_expected_counts():
    from timan_intelligence.core.statistical_engine import run_chi_square_test_of_independence
    frame = pd.DataFrame({"sex": ["F", "F", "M", "M", "F", None], "completed": ["Y", "Y", "N", "N", "N", "Y"]})
    result = run_chi_square_test_of_independence(frame, "sex", "completed")
    assert result.metadata["n_observations"] == 5
    assert result.metadata["missing_pairs_excluded"] == 1
    assert result.metadata["expected_cells_below_5"] > 0


def test_chi_square_independence_rejects_invalid_variables():
    from timan_intelligence.core.statistical_engine import run_chi_square_test_of_independence
    with pytest.raises(ValueError, match="different categorical variables"):
        run_chi_square_test_of_independence(pd.DataFrame({"x": ["a", "b"]}), "x", "x")
    with pytest.raises(TypeError, match="Both variables must be categorical"):
        run_chi_square_test_of_independence(pd.DataFrame({"x": [0, 1], "y": ["a", "b"]}), "x", "y")
    with pytest.raises(ValueError, match="at least two observed categories"):
        run_chi_square_test_of_independence(pd.DataFrame({"x": ["a", "a"], "y": ["b", "c"]}), "x", "y")


def test_fisher_exact_returns_exact_p_value_and_odds_ratio():
    from timan_intelligence.core.statistical_engine import run_fisher_exact_test
    frame = pd.DataFrame({"exposed": ["Yes"] * 10 + ["No"] * 6, "outcome": ["Yes"] * 8 + ["No"] * 2 + ["Yes"] + ["No"] * 5})
    result = run_fisher_exact_test(frame, "exposed", "outcome")
    assert result.status == "success"
    assert result.metadata["odds_ratio"] == pytest.approx(20.0)
    assert 0 <= result.metadata["p_value"] <= 1
    assert result.tables["contingency_table"].shape[0] == 2


def test_fisher_exact_supports_directional_alternative_and_missing_values():
    from timan_intelligence.core.statistical_engine import run_fisher_exact_test
    frame = pd.DataFrame({"group": ["A", "A", "A", "B", "B", "B", None], "event": ["Y", "Y", "N", "Y", "N", "N", "Y"]})
    result = run_fisher_exact_test(frame, "group", "event", alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["missing_pairs_excluded"] == 1
    assert 0 <= result.metadata["p_value"] <= 1


def test_fisher_exact_rejects_non_2_by_2_and_invalid_alternative():
    from timan_intelligence.core.statistical_engine import run_fisher_exact_test
    with pytest.raises(ValueError, match="exactly two observed categories"):
        run_fisher_exact_test(pd.DataFrame({"a": ["x", "y", "z", "x"], "b": ["u", "u", "v", "v"]}), "a", "b")
    with pytest.raises(ValueError, match="Alternative must"):
        run_fisher_exact_test(pd.DataFrame({"a": ["x", "x", "y", "y"], "b": ["u", "v", "u", "v"]}), "a", "b", "invalid")


def test_exact_one_sample_binomial_test_and_clopper_pearson_interval():
    from timan_intelligence.core.statistical_engine import run_one_sample_binomial_test
    frame = pd.DataFrame({"success": [1] * 8 + [0] * 12})
    result = run_one_sample_binomial_test(frame, "success", 0.3, confidence_level=0.95)
    assert result.status == "success"
    assert result.metadata["successes"] == 8
    assert result.metadata["observations"] == 20
    assert result.metadata["estimate"] == pytest.approx(0.4)
    assert 0 <= result.metadata["p_value"] <= 1
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 0.4 < upper


def test_exact_binomial_supports_directional_alternative_and_missing_values():
    from timan_intelligence.core.statistical_engine import run_one_sample_binomial_test
    frame = pd.DataFrame({"event": [1, 1, 1, 1, 0, None]})
    result = run_one_sample_binomial_test(frame, "event", 0.5, alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["missing_values_excluded"] == 1
    assert result.metadata["p_value"] < 0.5


def test_exact_binomial_rejects_invalid_binary_values_reference_and_alternative():
    from timan_intelligence.core.statistical_engine import run_one_sample_binomial_test
    frame = pd.DataFrame({"event": [0, 1, 2]})
    with pytest.raises(ValueError, match="only 0 and 1"):
        run_one_sample_binomial_test(frame, "event", 0.5)
    valid = pd.DataFrame({"event": [0, 1, 1]})
    with pytest.raises(ValueError, match="between 0 and 1"):
        run_one_sample_binomial_test(valid, "event", 1.2)
    with pytest.raises(ValueError, match="Alternative must"):
        run_one_sample_binomial_test(valid, "event", 0.5, alternative="invalid")


def test_two_independent_proportions_returns_score_test_and_newcombe_interval():
    from timan_intelligence.core.statistical_engine import run_two_independent_proportions_test
    frame = pd.DataFrame({"group": ["A"] * 10 + ["B"] * 10, "event": [1] * 7 + [0] * 3 + [1] * 3 + [0] * 7})
    result = run_two_independent_proportions_test(frame, "event", "group")
    assert result.status == "success"
    assert result.metadata["group_1_proportion"] == pytest.approx(0.7)
    assert result.metadata["group_2_proportion"] == pytest.approx(0.3)
    assert result.metadata["estimate"] == pytest.approx(0.4)
    assert 0 <= result.metadata["p_value"] <= 1
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 0.4 < upper
    assert result.metadata["sampling_design_aware"] is False


def test_two_independent_proportions_supports_directional_test_and_missing_pairs():
    from timan_intelligence.core.statistical_engine import run_two_independent_proportions_test
    frame = pd.DataFrame({"group": ["A", "A", "A", "A", "B", "B", "B", "B", None],
                          "event": [1, 1, 1, 0, 1, 0, 0, 0, 1]})
    result = run_two_independent_proportions_test(frame, "event", "group", alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["p_value"] < 0.5
    assert result.metadata["incomplete_pairs_excluded"] == 1


def test_two_independent_proportions_rejects_invalid_binary_and_group_count():
    from timan_intelligence.core.statistical_engine import run_two_independent_proportions_test
    with pytest.raises(ValueError, match="only 0 and 1"):
        run_two_independent_proportions_test(pd.DataFrame({"event": [0, 1, 2, 0], "group": ["A", "A", "B", "B"]}), "event", "group")
    with pytest.raises(ValueError, match="exactly two"):
        run_two_independent_proportions_test(pd.DataFrame({"event": [0, 1, 0], "group": ["A", "B", "C"]}), "event", "group")


def test_two_independent_proportions_service_uses_shared_result_contract():
    from timan_intelligence.services.analysis_service import run_two_independent_proportions_test_service
    frame = pd.DataFrame({"event": [1, 1, 0, 0, 1, 0], "group": ["A", "A", "A", "B", "B", "B"]})
    result = run_two_independent_proportions_test_service(frame, "event", "group", 0.90)
    assert result.status == "success"
    assert result.metadata["confidence_level"] == pytest.approx(0.90)


def test_two_proportions_confidence_interval_estimates_newcombe_difference():
    from timan_intelligence.core.statistical_engine import run_two_proportions_confidence_interval
    frame = pd.DataFrame({"group": ["A"] * 10 + ["B"] * 10, "event": [1] * 7 + [0] * 3 + [1] * 3 + [0] * 7})
    result = run_two_proportions_confidence_interval(frame, "event", "group", 0.90)
    assert result.status == "success"
    assert result.metadata["estimate"] == pytest.approx(0.4)
    assert result.metadata["confidence_level"] == pytest.approx(0.90)
    lower, upper = result.metadata["confidence_interval"]
    assert lower < 0.4 < upper
    assert "p_value" not in result.metadata
    assert result.metadata["sampling_design_aware"] is False


def test_two_proportions_confidence_interval_handles_boundary_rates_and_missing_pairs():
    from timan_intelligence.core.statistical_engine import run_two_proportions_confidence_interval
    frame = pd.DataFrame({"group": ["A", "A", "B", "B", "B", None], "event": [1, 1, 0, 0, 0, 1]})
    result = run_two_proportions_confidence_interval(frame, "event", "group")
    assert result.metadata["group_1_proportion"] == pytest.approx(1.0)
    assert result.metadata["group_2_proportion"] == pytest.approx(0.0)
    assert result.metadata["incomplete_pairs_excluded"] == 1


def test_two_proportions_confidence_interval_rejects_invalid_inputs():
    from timan_intelligence.core.statistical_engine import run_two_proportions_confidence_interval
    with pytest.raises(ValueError, match="exactly two"):
        run_two_proportions_confidence_interval(pd.DataFrame({"event": [0, 1, 0], "group": ["A", "B", "C"]}), "event", "group")
    with pytest.raises(ValueError, match="only 0 and 1"):
        run_two_proportions_confidence_interval(pd.DataFrame({"event": [0, 1, 2, 0], "group": ["A", "A", "B", "B"]}), "event", "group")



def test_mann_whitney_u_test_reports_rank_test_and_directional_effect_size():
    from timan_intelligence.core.statistical_engine import run_mann_whitney_u_test
    frame = pd.DataFrame({"score": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"]})
    result = run_mann_whitney_u_test(frame, "score", "group")
    row = result.tables["test"].iloc[0]
    assert result.status == "success"
    assert result.method == "Mann–Whitney U test"
    assert row["U statistic (Group 1)"] == pytest.approx(0.0)
    assert row["Rank-biserial correlation"] == pytest.approx(-1.0)
    assert row["P-value"] < 0.05
    assert result.metadata["study_design"] == "independent_groups"


def test_mann_whitney_supports_alternatives_and_excludes_missing_and_infinite_outcomes():
    from timan_intelligence.core.statistical_engine import run_mann_whitney_u_test
    frame = pd.DataFrame({"score": [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, None, float("inf")], "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B", "A", "B"]})
    result = run_mann_whitney_u_test(frame, "score", "group", alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["missing_outcomes"] == 1
    assert result.metadata["infinite_outcomes"] == 1
    assert result.metadata["p_value"] < 0.05


def test_mann_whitney_rejects_invalid_grouping_and_small_samples():
    from timan_intelligence.core.statistical_engine import run_mann_whitney_u_test
    with pytest.raises(ValueError, match="exactly two"):
        run_mann_whitney_u_test(pd.DataFrame({"y": [1, 2, 3], "g": ["A", "B", "C"]}), "y", "g")
    with pytest.raises(ValueError, match="at least two"):
        run_mann_whitney_u_test(pd.DataFrame({"y": [1, 2, 3], "g": ["A", "B", "B"]}), "y", "g")
    with pytest.raises(ValueError, match="Alternative"):
        run_mann_whitney_u_test(pd.DataFrame({"y": [1, 2, 3, 4], "g": ["A", "A", "B", "B"]}), "y", "g", "invalid")


def test_mann_whitney_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_mann_whitney_u_test_service
    frame = pd.DataFrame({"y": [1, 2, 3, 4], "g": ["A", "A", "B", "B"]})
    result = run_mann_whitney_u_test_service(frame, "y", "g")
    assert result.status == "success"
    assert result.method == "Mann–Whitney U test"


def test_kruskal_wallis_compares_three_independent_groups_and_reports_effect_size():
    from timan_intelligence.core.statistical_engine import run_kruskal_wallis_test
    frame = pd.DataFrame({"score": [1, 2, 3, 5, 6, 7, 9, 10, 11], "group": ["A"]*3 + ["B"]*3 + ["C"]*3})
    result = run_kruskal_wallis_test(frame, "score", "group")
    assert result.status == "success"
    assert result.method == "Kruskal–Wallis test"
    assert result.metadata["group_count"] == 3
    assert result.metadata["degrees_of_freedom"] == 2
    assert result.metadata["p_value"] < 0.05
    assert result.metadata["epsilon_squared"] > 0
    assert list(result.tables["group_summary"]["Group"]) == ["A", "B", "C"]


def test_kruskal_wallis_excludes_missing_and_infinite_outcomes():
    from timan_intelligence.core.statistical_engine import run_kruskal_wallis_test
    frame = pd.DataFrame({"score": [1,2,3,5,6,7,9,10,11,None,float("inf")], "group": ["A"]*3+["B"]*3+["C"]*3+["A","B"]})
    result = run_kruskal_wallis_test(frame, "score", "group")
    assert result.metadata["missing_outcomes"] == 1
    assert result.metadata["infinite_outcomes"] == 1
    assert result.metadata["n_observations"] == 9


def test_kruskal_wallis_rejects_two_groups_small_groups_and_all_ties():
    from timan_intelligence.core.statistical_engine import run_kruskal_wallis_test
    with pytest.raises(ValueError, match="at least three"):
        run_kruskal_wallis_test(pd.DataFrame({"y":[1,2,3,4],"g":["A","A","B","B"]}),"y","g")
    with pytest.raises(ValueError, match="at least two"):
        run_kruskal_wallis_test(pd.DataFrame({"y":[1,2,3,4,5],"g":["A","A","B","C","C"]}),"y","g")
    with pytest.raises(ValueError, match="identical"):
        run_kruskal_wallis_test(pd.DataFrame({"y":[1]*6,"g":["A","A","B","B","C","C"]}),"y","g")


def test_kruskal_wallis_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_kruskal_wallis_test_service
    frame = pd.DataFrame({"y":[1,2,3,5,6,7,9,10,11],"g":["A"]*3+["B"]*3+["C"]*3})
    assert run_kruskal_wallis_test_service(frame,"y","g").status == "success"


def test_dunn_posthoc_uses_tie_corrected_ranks_and_holm_adjustment():
    from timan_intelligence.core.statistical_engine import run_dunn_posthoc_test
    frame = pd.DataFrame({"score": [1,2,3,5,6,7,9,10,11,1,5,9], "group": ["A"]*3+["B"]*3+["C"]*3+["A","B","C"]})
    result = run_dunn_posthoc_test(frame, "score", "group")
    pairs = result.tables["pairwise_comparisons"]
    assert result.status == "success"
    assert result.metadata["adjustment"] == "Holm"
    assert len(pairs) == 3
    assert (pairs["Holm-adjusted p-value"] >= pairs["Unadjusted p-value"]).all()
    assert (pairs["Holm-adjusted p-value"] <= 1).all()
    assert pairs["Significant at 0.05"].equals(pairs["Holm-adjusted p-value"].lt(0.05))
    assert pairs["Pairwise rank-biserial correlation (1 - 2)"].between(-1, 1).all()
    assert np.sign(pairs["Pairwise rank-biserial correlation (1 - 2)"]).equals(
        np.sign(pairs["Mean rank difference (1 - 2)"])
    )


def test_dunn_posthoc_rejects_invalid_group_counts_and_all_ties():
    from timan_intelligence.core.statistical_engine import run_dunn_posthoc_test
    with pytest.raises(ValueError, match="at least three"):
        run_dunn_posthoc_test(pd.DataFrame({"y":[1,2,3,4],"g":["A","A","B","B"]}), "y", "g")
    with pytest.raises(ValueError, match="at least two"):
        run_dunn_posthoc_test(pd.DataFrame({"y":[1,2,3,4,5],"g":["A","A","B","C","C"]}), "y", "g")
    with pytest.raises(ValueError, match="all observations are tied"):
        run_dunn_posthoc_test(pd.DataFrame({"y":[1]*6,"g":["A","A","B","B","C","C"]}), "y", "g")


def test_dunn_posthoc_excludes_missing_and_infinite_outcomes():
    from timan_intelligence.core.statistical_engine import run_dunn_posthoc_test
    frame = pd.DataFrame({"y":[1,2,3,5,6,7,9,10,11,None,float("inf")],"g":["A"]*3+["B"]*3+["C"]*3+["A","B"]})
    result = run_dunn_posthoc_test(frame, "y", "g")
    assert result.metadata["missing_outcomes"] == 1
    assert result.metadata["infinite_outcomes"] == 1


def test_wilcoxon_signed_rank_reports_paired_change_and_effect_size():
    from timan_intelligence.core.statistical_engine import run_wilcoxon_signed_rank_test
    frame = pd.DataFrame({"before":[1,2,3,4,5,6,7,8],"after":[3,4,5,7,8,9,10,12]})
    result = run_wilcoxon_signed_rank_test(frame,"before","after")
    assert result.status == "success"
    assert result.metadata["study_design"] == "paired"
    assert result.tables["test"].loc[0, "Matched-pairs rank-biserial correlation"] == pytest.approx(
        result.metadata["rank_biserial_correlation"]
    )
    assert result.metadata["p_value"] < 0.05
    assert result.metadata["rank_biserial_correlation"] == pytest.approx(1.0)
    assert result.metadata["complete_pairs"] == 8


def test_wilcoxon_signed_rank_supports_direction_and_excludes_incomplete_pairs():
    from timan_intelligence.core.statistical_engine import run_wilcoxon_signed_rank_test
    frame = pd.DataFrame({"before":[1,2,3,4,5,None,7],"after":[2,3,4,5,6,8,float("inf")]})
    result = run_wilcoxon_signed_rank_test(frame,"before","after",alternative="greater")
    assert result.metadata["alternative"] == "greater"
    assert result.metadata["missing_pairs"] == 1
    assert result.metadata["infinite_pairs"] == 1
    assert result.metadata["p_value"] < 0.05


def test_wilcoxon_signed_rank_rejects_invalid_pairs_and_all_zero_differences():
    from timan_intelligence.core.statistical_engine import run_wilcoxon_signed_rank_test
    with pytest.raises(ValueError,match="at least two complete"):
        run_wilcoxon_signed_rank_test(pd.DataFrame({"b":[1,None],"a":[2,3]}),"b","a")
    with pytest.raises(ValueError,match="all paired differences are zero"):
        run_wilcoxon_signed_rank_test(pd.DataFrame({"b":[1,2,3],"a":[1,2,3]}),"b","a")


def test_wilcoxon_signed_rank_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_wilcoxon_signed_rank_test_service
    frame = pd.DataFrame({"b":[1,2,3,4],"a":[2,3,4,5]})
    result = run_wilcoxon_signed_rank_test_service(frame,"b","a")
    assert result.status == "success"
    assert result.method == "Wilcoxon signed-rank test"


def test_friedman_test_detects_change_across_three_related_measurements():
    from timan_intelligence.core.statistical_engine import run_friedman_test
    frame = pd.DataFrame({"baseline":[1,2,3,4,5,6,7,8],"midline":[2,3,4,5,6,7,8,9],"endline":[4,5,6,7,8,9,10,11]})
    result = run_friedman_test(frame, ["baseline","midline","endline"])
    assert result.status == "success"
    assert result.metadata["study_design"] == "repeated_measures"
    assert result.metadata["n_complete"] == 8
    assert result.metadata["p_value"] < 0.05
    assert result.metadata["kendall_w"] == pytest.approx(1.0)
    assert len(result.tables["measurement_ranks"]) == 3


def test_friedman_test_excludes_incomplete_rows_and_reports_rank_order():
    from timan_intelligence.core.statistical_engine import run_friedman_test
    frame = pd.DataFrame({"t0":[1,2,3,4,5],"t1":[2,3,4,5,None],"t2":[3,4,5,6,7]})
    result = run_friedman_test(frame, ["t0","t1","t2"])
    assert result.metadata["n_complete"] == 4
    assert result.metadata["n_incomplete"] == 1
    ranks = result.tables["measurement_ranks"].set_index("Measurement")
    assert ranks.loc["t0","Mean within-unit rank"] < ranks.loc["t2","Mean within-unit rank"]


def test_friedman_test_validates_repeated_measurements_and_all_ties():
    from timan_intelligence.core.statistical_engine import run_friedman_test
    with pytest.raises(ValueError,match="at least three"):
        run_friedman_test(pd.DataFrame({"a":[1,2],"b":[2,3]}),["a","b"])
    with pytest.raises(ValueError,match="at least two complete"):
        run_friedman_test(pd.DataFrame({"a":[1,None],"b":[2,3],"c":[3,4]}),["a","b","c"])
    with pytest.raises(ValueError,match="undefined"):
        run_friedman_test(pd.DataFrame({"a":[1,2,3],"b":[1,2,3],"c":[1,2,3]}),["a","b","c"])


def test_friedman_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_friedman_test_service
    frame = pd.DataFrame({"a":[1,2,3,4],"b":[2,3,4,5],"c":[3,4,5,6]})
    result = run_friedman_test_service(frame,["a","b","c"])
    assert result.status == "success"
    assert result.method == "Friedman test"




def test_friedman_pairwise_posthoc_uses_holm_adjustment():
    from timan_intelligence.core.statistical_engine import run_friedman_pairwise_posthoc
    frame = pd.DataFrame({"baseline":[1,2,3,4,5,6,7,8],"midline":[2,3,4,5,6,7,8,9],"endline":[4,5,6,7,8,9,10,11]})
    result = run_friedman_pairwise_posthoc(frame, ["baseline","midline","endline"])
    table = result.tables["pairwise_comparisons"]
    assert result.status == "success"
    assert result.metadata["number_of_comparisons"] == 3
    assert result.metadata["adjustment"] == "Holm"
    assert (table["Holm-adjusted p-value"] >= table["P-value"]).all()
    assert table["Significant at 0.05"].all()


def test_friedman_pairwise_posthoc_uses_consistent_complete_case_set():
    from timan_intelligence.core.statistical_engine import run_friedman_pairwise_posthoc
    frame = pd.DataFrame({"a":[1,2,3,4,5],"b":[2,3,4,5,None],"c":[3,4,5,6,7]})
    result = run_friedman_pairwise_posthoc(frame, ["a","b","c"])
    assert result.metadata["n_complete"] == 4
    assert result.metadata["n_incomplete"] == 1
    with pytest.raises(ValueError, match="at least three"):
        run_friedman_pairwise_posthoc(frame, ["a","b"])



def test_repeated_measures_anova_reports_sphericity_corrections_and_holm_followups():
    from timan_intelligence.core.statistical_engine import run_repeated_measures_anova
    frame = pd.DataFrame({"baseline":[10,12,11,13,9,14,12,10,15,11],"midline":[12,14,12,16,10,17,15,13,18,14],"endline":[15,16,17,19,14,20,16,17,21,16]})
    result = run_repeated_measures_anova(frame, ["baseline","midline","endline"])
    summary = result.tables["test_summary"].iloc[0]
    assert result.status == "success" and summary["F statistic"] > 0
    assert 0 < summary["Greenhouse-Geisser epsilon"] <= 1
    assert 0 < summary["Huynh-Feldt epsilon"] <= 1
    assert 0 <= summary["Greenhouse-Geisser p-value"] <= 1
    assert result.tables["sphericity_test"].iloc[0]["Mauchly's W"] <= 1
    pairs = result.tables["pairwise_comparisons"]
    assert len(pairs) == 3
    assert (pairs["Holm-adjusted p-value"] >= pairs["P-value"] - 1e-12).all()
    assert result.metadata["partial_eta_squared"] > 0


def test_repeated_measures_anova_excludes_incomplete_rows_consistently():
    from timan_intelligence.core.statistical_engine import run_repeated_measures_anova
    frame = pd.DataFrame({"a":[1,2,3,4,5],"b":[2,3,5,5,None],"c":[4,5,6,8,8]})
    result = run_repeated_measures_anova(frame, ["a","b","c"])
    assert result.metadata["n_complete"] == 4 and result.metadata["n_incomplete"] == 1


def test_repeated_measures_anova_validates_measurement_count_and_sample_size():
    from timan_intelligence.core.statistical_engine import run_repeated_measures_anova
    with pytest.raises(ValueError, match="at least three"):
        run_repeated_measures_anova(pd.DataFrame({"a":[1,2,3],"b":[2,3,4]}), ["a","b"])
    with pytest.raises(ValueError, match="at least three complete"):
        run_repeated_measures_anova(pd.DataFrame({"a":[1,2],"b":[2,3],"c":[3,4]}), ["a","b","c"])
