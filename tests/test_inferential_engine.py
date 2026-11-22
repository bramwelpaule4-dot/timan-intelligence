
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
