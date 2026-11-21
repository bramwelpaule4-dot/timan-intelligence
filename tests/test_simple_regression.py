import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.simple_regression import run_simple_linear_regression


def test_simple_regression_estimates_slope_intercept_and_fit():
    df = pd.DataFrame({
        "training_hours": [1, 2, 3, 4, 5, 6],
        "assessment_score": [12, 14, 16, 18, 20, 22],
    })
    result = run_simple_linear_regression(df, "training_hours", "assessment_score")
    metadata = result["metadata"]

    assert metadata["slope"] == pytest.approx(2.0)
    assert metadata["intercept"] == pytest.approx(10.0)
    assert metadata["r_squared"] == pytest.approx(1.0)
    assert metadata["rmse"] == pytest.approx(0.0)
    assert metadata["slope_confidence_interval_95"] == pytest.approx([2.0, 2.0])
    assert metadata["valid_n"] == 6
    assert len(result["fitted_data"]) == 6


def test_simple_regression_excludes_missing_and_non_finite_pairs():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, np.inf, 6],
        "y": [3, 5, 7, 9, 11, np.nan],
    })
    result = run_simple_linear_regression(df, "x", "y")
    assert result["metadata"]["valid_n"] == 4
    assert result["metadata"]["excluded_n"] == 2


def test_simple_regression_rejects_invalid_variables_and_small_samples():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
    with pytest.raises(ValueError, match="different predictor and outcome"):
        run_simple_linear_regression(df, "x", "x")
    with pytest.raises(ValueError, match="At least three"):
        run_simple_linear_regression(df.iloc[:2], "x", "y")
    with pytest.raises(ValueError, match="must be numeric"):
        run_simple_linear_regression(
            pd.DataFrame({"x": ["1", "2", "3"], "y": [2, 4, 6]}),
            "x",
            "y",
        )


def test_simple_regression_rejects_constant_predictor_or_outcome():
    with pytest.raises(ValueError, match="predictor must vary"):
        run_simple_linear_regression(
            pd.DataFrame({"x": [1, 1, 1], "y": [2, 3, 4]}), "x", "y"
        )
    with pytest.raises(ValueError, match="outcome must vary"):
        run_simple_linear_regression(
            pd.DataFrame({"x": [1, 2, 3], "y": [4, 4, 4]}), "x", "y"
        )


def test_simple_regression_does_not_modify_input_dataframe():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [4, 5, 7, 8]})
    original = df.copy(deep=True)
    run_simple_linear_regression(df, "x", "y")
    pd.testing.assert_frame_equal(df, original)
