import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.regression_diagnostics import run_regression_diagnostics


def _fitted_frame(n=40):
    x1 = np.linspace(1, 10, n)
    x2 = np.sin(x1 * 1.7)
    y = 4 + 2 * x1 - 0.7 * x2 + np.cos(x1 * 2.3) * 0.2
    design = np.column_stack([np.ones(n), x1, x2])
    fitted = design @ np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - fitted
    return pd.DataFrame({"x1": x1, "x2": x2, "y": y,
                         "Fitted outcome": fitted, "Residual": residual})


def test_regression_diagnostics_returns_tests_vif_and_influence():
    result = run_regression_diagnostics(_fitted_frame(), ["x1", "x2"], "y")
    assert {"Diagnostic", "Statistic", "p-value", "Signal"} <= set(result["diagnostics"])
    assert len(result["diagnostics"]) >= 5
    assert set(result["influential_observations"].columns) >= {
        "Record position", "Leverage", "Cook's distance"
    }
    assert result["metadata"]["valid_n"] == 40
    assert len(result["residual_plot_data"]) == 40


def test_regression_diagnostics_flags_collinearity():
    frame = _fitted_frame()
    frame["x2"] = frame["x1"] * 2
    with pytest.raises(ValueError, match="rank deficient"):
        run_regression_diagnostics(frame, ["x1", "x2"], "y")


def test_regression_diagnostics_validates_required_columns_and_sample():
    frame = _fitted_frame()
    with pytest.raises(ValueError, match="missing required"):
        run_regression_diagnostics(frame.drop(columns=["Residual"]), ["x1"], "y")
    with pytest.raises(ValueError, match="Too few"):
        run_regression_diagnostics(frame.iloc[:2], ["x1", "x2"], "y")


def test_regression_diagnostics_does_not_modify_input():
    frame = _fitted_frame()
    original = frame.copy(deep=True)
    run_regression_diagnostics(frame, ["x1", "x2"], "y")
    pd.testing.assert_frame_equal(frame, original)
