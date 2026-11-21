import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.multiple_regression import run_multiple_linear_regression


def test_multiple_regression_estimates_adjusted_coefficients_and_fit():
    df = pd.DataFrame({
        "training_hours": [1, 2, 3, 4, 5, 6, 7, 8],
        "attendance_rate": [70, 75, 80, 85, 90, 95, 100, 105],
    })
    df["score"] = 5 + 2 * df["training_hours"] + 0.5 * df["attendance_rate"]
    result = run_multiple_linear_regression(
        df, ["training_hours", "attendance_rate"], "score"
    )
    metadata = result["metadata"]

    assert metadata["valid_n"] == 8
    assert metadata["predictor_count"] == 2
    assert metadata["r_squared"] == pytest.approx(1.0)
    assert metadata["model_p_value"] == pytest.approx(0.0)
    coefficients = result["coefficients"].set_index("Variable")
    assert coefficients.loc["training_hours", "Estimate"] == pytest.approx(2.0)
    assert coefficients.loc["attendance_rate", "Estimate"] == pytest.approx(0.5)


def test_multiple_regression_excludes_incomplete_and_non_finite_records():
    df = pd.DataFrame({
        "x1": [1, 2, 3, 4, 5, 6],
        "x2": [2, 3, 4, 5, np.nan, 7],
        "y": [4, 7, 10, 13, 16, np.inf],
    })
    result = run_multiple_linear_regression(df, ["x1", "x2"], "y")
    assert result["metadata"]["valid_n"] == 4
    assert result["metadata"]["excluded_n"] == 2


def test_multiple_regression_rejects_rank_deficiency_and_bad_selection():
    df = pd.DataFrame({
        "x1": [1, 2, 3, 4, 5],
        "x2": [2, 4, 6, 8, 10],
        "y": [3, 5, 7, 9, 11],
    })
    with pytest.raises(ValueError, match="collinear"):
        run_multiple_linear_regression(df, ["x1", "x2"], "y")
    with pytest.raises(ValueError, match="at least two"):
        run_multiple_linear_regression(df, ["x1"], "y")
    with pytest.raises(ValueError, match="cannot also be a predictor"):
        run_multiple_linear_regression(df, ["x1", "y"], "y")


def test_multiple_regression_requires_enough_complete_records():
    df = pd.DataFrame({
        "x1": [1, 2, 3],
        "x2": [2, 3, 4],
        "y": [3, 5, 7],
    })
    with pytest.raises(ValueError, match="at least 4"):
        run_multiple_linear_regression(df, ["x1", "x2"], "y")


def test_multiple_regression_does_not_modify_input_dataframe():
    df = pd.DataFrame({
        "x1": [1, 2, 3, 4, 5],
        "x2": [3, 2, 5, 4, 7],
        "y": [5, 7, 9, 12, 14],
    })
    original = df.copy(deep=True)
    run_multiple_linear_regression(df, ["x1", "x2"], "y")
    pd.testing.assert_frame_equal(df, original)
