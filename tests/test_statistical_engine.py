
import pandas as pd
import pytest

from timan_intelligence.core.statistical_engine import (
    run_descriptive_statistics,
)


def test_descriptive_statistics_returns_correct_results():
    df = pd.DataFrame({"income": [10, 20, 30, 40, 50]})

    result = run_descriptive_statistics(df, "income")
    summary = result.tables["summary"]

    assert result.status == "success"
    assert result.method == "Descriptive statistics"
    assert summary["observations"] == 5
    assert summary["missing_values"] == 0
    assert summary["mean"] == pytest.approx(30.0)
    assert summary["median"] == pytest.approx(30.0)
    assert summary["standard_deviation"] == pytest.approx(
        15.811388300841896
    )
    assert summary["minimum"] == pytest.approx(10.0)
    assert summary["maximum"] == pytest.approx(50.0)
    assert summary["q1"] == pytest.approx(20.0)
    assert summary["q3"] == pytest.approx(40.0)


def test_descriptive_statistics_excludes_and_reports_missing_values():
    df = pd.DataFrame({"score": [10, None, 30]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 2
    assert summary["missing_values"] == 1
    assert summary["mean"] == pytest.approx(20.0)


def test_descriptive_statistics_handles_one_observation():
    df = pd.DataFrame({"score": [7]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 1
    assert summary["mean"] == pytest.approx(7.0)
    assert summary["standard_deviation"] is None
    assert len(result.limitations) > 0


def test_descriptive_statistics_rejects_missing_variable():
    df = pd.DataFrame({"income": [10, 20, 30]})

    with pytest.raises(ValueError, match="not found"):
        run_descriptive_statistics(df, "expenditure")


def test_descriptive_statistics_rejects_non_numeric_variable():
    df = pd.DataFrame({"ward": ["A", "B", "A"]})

    with pytest.raises(TypeError, match="must be numeric"):
        run_descriptive_statistics(df, "ward")


def test_descriptive_statistics_rejects_all_missing_values():
    df = pd.DataFrame({"score": [None, None]})

    with pytest.raises(ValueError, match="no usable numeric observations"):
        run_descriptive_statistics(df, "score")


def test_descriptive_statistics_rejects_non_dataframe_input():
    with pytest.raises(TypeError, match="DataFrame"):
        run_descriptive_statistics([10, 20, 30], "income")


def test_descriptive_statistics_does_not_modify_original_data():
    df = pd.DataFrame({"income": [10, None, 30]})
    original = df.copy(deep=True)

    run_descriptive_statistics(df, "income")

    pd.testing.assert_frame_equal(df, original)
