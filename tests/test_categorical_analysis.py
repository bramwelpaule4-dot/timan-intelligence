import pandas as pd
import pytest

from timan_intelligence.core.categorical_analysis import run_categorical_association


def test_crosstab_reports_counts_row_and_column_percentages():
    df = pd.DataFrame({
        "group": ["A", "A", "A", "B", "B", "B"],
        "outcome": ["Yes", "Yes", "No", "Yes", "No", "No"],
    })
    result = run_categorical_association(df, "group", "outcome")
    assert result["counts"].loc["A", "Yes"] == 2
    assert result["row_percentages"].loc["A", "Yes"] == pytest.approx(66.67)
    assert result["column_percentages"].loc["A", "Yes"] == pytest.approx(66.67)
    assert result["metadata"]["valid_n"] == 6
    assert result["metadata"]["test_status"] == "tested"


def test_crosstab_excludes_and_reports_missing_and_blank_values():
    df = pd.DataFrame({
        "group": ["A", "A", "B", None, "B"],
        "outcome": ["Yes", "", "No", "Yes", "No"],
    })
    result = run_categorical_association(df, "group", "outcome")
    assert result["metadata"]["total_records"] == 5
    assert result["metadata"]["valid_n"] == 3
    assert result["metadata"]["excluded_n"] == 2
    assert any("2 record(s)" in warning for warning in result["warnings"])


def test_crosstab_uses_fisher_exact_for_sparse_two_by_two_table():
    df = pd.DataFrame({
        "group": ["A"] * 4 + ["B"] * 4,
        "outcome": ["Yes", "Yes", "Yes", "No", "Yes", "No", "No", "No"],
    })
    result = run_categorical_association(df, "group", "outcome")
    assert result["metadata"]["test"] == "Fisher's exact test (two-sided)"
    assert 0 <= result["metadata"]["p_value"] <= 1


def test_crosstab_withholds_chi_square_for_sparse_larger_table():
    df = pd.DataFrame({
        "group": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
        "outcome": ["X", "Y", "Z"] * 3,
    })
    result = run_categorical_association(df, "group", "outcome")
    assert result["metadata"]["test_status"] == "descriptive_only"
    assert result["metadata"]["p_value"] is None


def test_crosstab_rejects_same_variable_and_high_cardinality():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["m", "n"]})
    with pytest.raises(ValueError, match="different variables"):
        run_categorical_association(df, "a", "a")

    many = pd.DataFrame({
        "identifier": [f"id-{i}" for i in range(51)],
        "outcome": ["Yes", "No"] * 25 + ["Yes"],
    })
    with pytest.raises(ValueError, match="more than 50"):
        run_categorical_association(many, "identifier", "outcome")


def test_crosstab_does_not_modify_input_data():
    df = pd.DataFrame({"group": ["A", "A", "B", "B"], "outcome": ["Y", "N", "Y", "N"]})
    original = df.copy(deep=True)
    run_categorical_association(df, "group", "outcome")
    pd.testing.assert_frame_equal(df, original)
