
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
