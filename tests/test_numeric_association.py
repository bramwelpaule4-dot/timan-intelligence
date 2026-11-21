import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.numeric_association import run_numeric_association


def test_numeric_association_reports_pearson_and_spearman():
    df = pd.DataFrame({
        "hours": [1, 2, 3, 4, 5, 6],
        "score": [2, 4, 6, 8, 10, 12],
    })
    result = run_numeric_association(df, "hours", "score")
    metadata = result["metadata"]

    assert metadata["valid_n"] == 6
    assert metadata["pearson_r"] == pytest.approx(1.0)
    assert metadata["spearman_rho"] == pytest.approx(1.0)
    assert metadata["pearson_p_value"] <= 1
    assert metadata["spearman_p_value"] <= 1
    assert metadata["pearson_confidence_interval_95"] == [1.0, 1.0]


def test_numeric_association_excludes_missing_and_non_finite_pairs():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, np.inf, 6],
        "y": [2, 4, 6, 8, 10, np.nan],
    })
    result = run_numeric_association(df, "x", "y")
    assert result["metadata"]["total_records"] == 6
    assert result["metadata"]["valid_n"] == 4
    assert result["metadata"]["excluded_n"] == 2


def test_numeric_association_detects_monotonic_non_linear_relationship():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5, 6],
        "y": [1, 4, 9, 16, 25, 36],
    })
    result = run_numeric_association(df, "x", "y")
    assert result["metadata"]["spearman_rho"] == pytest.approx(1.0)
    assert result["metadata"]["pearson_r"] < 1.0


def test_numeric_association_rejects_invalid_selections_and_small_samples():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
    with pytest.raises(ValueError, match="different numeric variables"):
        run_numeric_association(df, "x", "x")
    with pytest.raises(ValueError, match="At least three"):
        run_numeric_association(df.iloc[:2], "x", "y")
    with pytest.raises(ValueError, match="must be numeric"):
        run_numeric_association(pd.DataFrame({"x": ["1", "2", "3"], "y": [2, 4, 6]}), "x", "y")


def test_numeric_association_rejects_constant_variables():
    df = pd.DataFrame({"x": [1, 1, 1, 1], "y": [2, 3, 4, 5]})
    with pytest.raises(ValueError, match="must vary"):
        run_numeric_association(df, "x", "y")


def test_numeric_association_does_not_modify_input_dataframe():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [4, 3, 2, 1]})
    original = df.copy(deep=True)
    run_numeric_association(df, "x", "y")
    pd.testing.assert_frame_equal(df, original)
