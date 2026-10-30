
import pandas as pd
import pytest

from timan_intelligence.core.statistical_engine import (
    run_one_way_anova,
)


def test_one_way_anova_returns_correct_result_structure():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "score": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        }
    )

    result = run_one_way_anova(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert result.status == "success"
    assert result.method == "One-way ANOVA"
    assert summary["groups"] == 3
    assert summary["observations"] == 9
    assert summary["f_statistic"] == pytest.approx(27.0)
    assert 0 <= summary["p_value"] <= 1
    assert summary["p_value"] < 0.05
    assert summary["degrees_of_freedom_between"] == 2
    assert summary["degrees_of_freedom_within"] == 6


def test_one_way_anova_handles_unequal_group_sizes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "B", "C", "C", "C", "C"],
            "score": [1, 2, 4, 5, 6, 7, 8, 9, 10],
        }
    )

    result = run_one_way_anova(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["groups"] == 3
    assert summary["observations"] == 9
    assert summary["degrees_of_freedom_between"] == 2
    assert summary["degrees_of_freedom_within"] == 6
    assert 0 <= summary["p_value"] <= 1


def test_one_way_anova_excludes_and_reports_missing_outcomes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "score": [1, None, 3, 4, 5, 6, 7, 8, None],
        }
    )

    result = run_one_way_anova(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["missing_outcomes"] == 2
    assert summary["observations"] == 7


def test_one_way_anova_excludes_and_reports_infinite_outcomes():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "score": [
                1,
                2,
                float("inf"),
                4,
                5,
                6,
                7,
                8,
                float("-inf"),
            ],
        }
    )

    result = run_one_way_anova(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    summary = result.tables["summary"]

    assert summary["infinite_outcomes"] == 2
    assert summary["observations"] == 7


def test_one_way_anova_rejects_missing_outcome_variable():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": [1, 2, 3, 4, 5, 6],
        }
    )

    with pytest.raises(ValueError, match="not found"):
        run_one_way_anova(
            df,
            outcome_variable="income",
            group_variable="group",
        )


def test_one_way_anova_rejects_missing_group_variable():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": [1, 2, 3, 4, 5, 6],
        }
    )

    with pytest.raises(ValueError, match="not found"):
        run_one_way_anova(
            df,
            outcome_variable="score",
            group_variable="ward",
        )


def test_one_way_anova_rejects_non_numeric_outcome():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": ["low", "high", "low", "high", "low", "high"],
        }
    )

    with pytest.raises(TypeError, match="numeric"):
        run_one_way_anova(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_one_way_anova_requires_at_least_two_groups():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "A"],
            "score": [1, 2, 3],
        }
    )

    with pytest.raises(ValueError, match="at least two groups"):
        run_one_way_anova(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_one_way_anova_requires_at_least_two_observations_per_group():
    df = pd.DataFrame(
        {
            "group": ["A", "B", "B"],
            "score": [1, 2, 3],
        }
    )

    with pytest.raises(ValueError, match="at least two"):
        run_one_way_anova(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_one_way_anova_rejects_missing_group_labels():
    df = pd.DataFrame(
        {
            "group": ["A", "A", None, "B", "B", "C", "C"],
            "score": [1, 2, 3, 4, 5, 6, 7],
        }
    )

    with pytest.raises(ValueError, match="group"):
        run_one_way_anova(
            df,
            outcome_variable="score",
            group_variable="group",
        )


def test_one_way_anova_does_not_modify_original_data():
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": [1, 2, 3, 4, 5, 6],
        }
    )
    original = df.copy(deep=True)

    run_one_way_anova(
        df,
        outcome_variable="score",
        group_variable="group",
    )

    pd.testing.assert_frame_equal(df, original)
    
