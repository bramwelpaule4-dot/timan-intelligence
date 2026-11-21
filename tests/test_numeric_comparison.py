import pandas as pd
import pytest

from timan_intelligence.core.numeric_comparison import run_numeric_group_comparison


def test_two_group_comparison_uses_welch_t_test_and_reports_confidence_interval():
    df = pd.DataFrame({
        "location": ["North"] * 5 + ["South"] * 5,
        "income": [10, 11, 12, 13, 14, 18, 19, 20, 21, 22],
    })
    result = run_numeric_group_comparison(df, "location", "income")
    metadata = result["metadata"]

    assert metadata["test"] == "Welch's independent-samples t-test"
    assert metadata["test_status"] == "tested"
    assert metadata["valid_n"] == 10
    assert metadata["mean_difference"] == pytest.approx(8)
    assert metadata["confidence_interval_95"][0] < 8
    assert metadata["confidence_interval_95"][1] > 8
    assert 0 <= metadata["p_value"] <= 1


def test_three_or_more_groups_use_welch_one_way_anova():
    df = pd.DataFrame({
        "programme": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
        "score": [10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33],
    })
    result = run_numeric_group_comparison(df, "programme", "score")
    metadata = result["metadata"]

    assert metadata["test"] == "Welch's one-way ANOVA"
    assert metadata["test_status"] == "tested"
    assert metadata["degrees_freedom"]["numerator"] == 2
    assert metadata["p_value"] < 0.05
    assert len(result["group_summaries"]) == 3


def test_comparison_reports_missing_values_and_descriptive_summaries():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B", None, "B"],
        "score": [1, 2, 3, 4, 5, float("inf")],
    })
    result = run_numeric_group_comparison(df, "group", "score")
    assert result["metadata"]["total_records"] == 6
    assert result["metadata"]["valid_n"] == 4
    assert result["metadata"]["excluded_n"] == 2
    assert any("2 record(s)" in warning for warning in result["warnings"])


def test_inference_is_withheld_when_any_group_has_fewer_than_two_records():
    df = pd.DataFrame({
        "group": ["A", "A", "B"],
        "score": [1, 2, 3],
    })
    result = run_numeric_group_comparison(df, "group", "score")
    assert result["metadata"]["test_status"] == "descriptive_only"
    assert result["metadata"]["p_value"] is None
    assert len(result["group_summaries"]) == 2


def test_numeric_comparison_rejects_text_outcome_and_high_cardinality_group():
    text_outcome = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "score": ["1", "2", "3", "4"],
    })
    with pytest.raises(ValueError, match="must be numeric"):
        run_numeric_group_comparison(text_outcome, "group", "score")

    many_groups = pd.DataFrame({
        "group": [f"g{i}" for i in range(51)],
        "score": list(range(51)),
    })
    with pytest.raises(ValueError, match="more than 50"):
        run_numeric_group_comparison(many_groups, "group", "score")


def test_numeric_comparison_rejects_invalid_variable_selections():
    df = pd.DataFrame({"group": ["A", "B"], "score": [1, 2]})
    with pytest.raises(ValueError, match="different variables"):
        run_numeric_group_comparison(df, "group", "group")
    with pytest.raises(ValueError, match="At least two groups"):
        run_numeric_group_comparison(
            pd.DataFrame({"group": ["A", "A"], "score": [1, 2]}),
            "group",
            "score",
        )


def test_numeric_comparison_does_not_modify_input_dataframe():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "score": [1, 2, 3, 4],
    })
    original = df.copy(deep=True)
    run_numeric_group_comparison(df, "group", "score")
    pd.testing.assert_frame_equal(df, original)
