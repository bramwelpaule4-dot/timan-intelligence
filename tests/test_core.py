import pandas as pd
import pytest

from timan_intelligence.core.data_quality import profile_dataframe
from timan_intelligence.modules.descriptive import numeric_summary, frequency_table
from timan_intelligence.services.analysis_service import run_data_quality


def test_profile_counts_missing_and_duplicate_rows():
    df = pd.DataFrame({
        "ward": ["A", "B", "B"],
        "households": [10, None, None],
    })
    profile = profile_dataframe(df)
    assert profile["rows"] == 3
    assert profile["columns"] == 2
    assert profile["missing_cells"] == 2
    assert profile["duplicate_rows"] == 1


def test_profile_does_not_change_input():
    df = pd.DataFrame({"x": [1, None, 3]})
    before = df.copy(deep=True)
    profile_dataframe(df)
    pd.testing.assert_frame_equal(df, before)


def test_numeric_summary_has_expected_mean():
    df = pd.DataFrame({"income": [10, 20, 30], "ward": ["A", "B", "A"]})
    result = numeric_summary(df)
    row = result.loc[result["variable"] == "income"].iloc[0]
    assert row["mean"] == pytest.approx(20.0)


def test_frequency_table_percentages():
    df = pd.DataFrame({"sex": ["F", "M", "F", None]})
    result = frequency_table(df, "sex")
    female = result.loc[result["category"] == "F"].iloc[0]
    assert female["count"] == 2
    assert female["percent"] == pytest.approx(50.0)


def test_analysis_service_returns_traceable_result():
    df = pd.DataFrame({"ward": ["A", "B"], "access": [1, None]})
    result = run_data_quality(df)
    assert result.method == "Deterministic data profiling"
    assert result.metadata["rows"] == 2
