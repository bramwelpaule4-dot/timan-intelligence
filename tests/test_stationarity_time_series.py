"""Tests for time-series stationarity diagnostics and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError, available_execution_methods, execute_recommendation,
)
from timan_intelligence.core.time_series import run_stationarity_diagnostics


def _stationary_frame(n=120):
    rng = np.random.default_rng(7241)
    values = np.zeros(n)
    for i in range(1, n):
        values[i] = 0.45 * values[i - 1] + rng.normal()
    return pd.DataFrame({
        "month": pd.date_range("2010-01-01", periods=n, freq="MS"),
        "value": values,
    })


def test_adf_and_kpss_return_complementary_hypotheses_and_critical_values():
    result = run_stationarity_diagnostics(_stationary_frame(), "month", "value")
    table = result.tables["stationarity_tests"]
    assert result.status == "success"
    assert list(table["test"]) == [
        "Augmented Dickey-Fuller (ADF)",
        "Kwiatkowski-Phillips-Schmidt-Shin (KPSS)",
    ]
    assert "unit root" in table.iloc[0]["null_hypothesis"]
    assert "stationary" in table.iloc[1]["null_hypothesis"]
    assert table["p_value"].between(0, 1).all()
    assert table["critical_value_5_percent"].notna().all()
    assert result.metadata["study_design"] == "time_series"


def test_stationarity_diagnostics_sort_time_and_support_trend_specification():
    frame = _stationary_frame().sample(frac=1, random_state=19).reset_index(drop=True)
    result = run_stationarity_diagnostics(frame, "month", "value", regression="ct", max_lag=6)
    assert result.metadata["regression"] == "ct"
    assert result.metadata["adf_max_lag"] == 6
    assert result.metadata["frequency"] == "MS"


def test_stationarity_diagnostics_reject_invalid_data_and_options():
    frame = _stationary_frame()
    with pytest.raises(ValueError, match="regularly spaced"):
        run_stationarity_diagnostics(frame.drop(index=12), "month", "value")
    with pytest.raises(ValueError, match="unique"):
        duplicate = frame.copy()
        duplicate.loc[1, "month"] = duplicate.loc[0, "month"]
        run_stationarity_diagnostics(duplicate, "month", "value")
    with pytest.raises(ValueError, match="complete and finite"):
        missing = frame.copy()
        missing.loc[0, "value"] = np.nan
        run_stationarity_diagnostics(missing, "month", "value")
    with pytest.raises(ValueError, match="At least 30"):
        run_stationarity_diagnostics(frame.head(20), "month", "value")
    with pytest.raises(ValueError, match="regression"):
        run_stationarity_diagnostics(frame, "month", "value", regression="n")
    with pytest.raises(ValueError, match="max_lag"):
        run_stationarity_diagnostics(frame, "month", "value", max_lag=21)


def test_stationarity_diagnostics_reject_constant_series():
    frame = _stationary_frame()
    frame["value"] = 2.0
    with pytest.raises(ValueError, match="constant series"):
        run_stationarity_diagnostics(frame, "month", "value")


def test_stationarity_executor_is_approval_gated_and_requires_time_series_design():
    frame = _stationary_frame()
    recommendation = {
        "method": "ADF and KPSS stationarity diagnostics",
        "method_id": "method.diagnostic.time_series.stationarity",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"regression": "c"},
        "design_context": {"study_design": "time_series"},
    }
    assert "ADF and KPSS stationarity diagnostics" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.diagnostic.time_series.stationarity"
    recommendation["design_context"] = {"study_design": "cross_sectional"}
    with pytest.raises(AnalysisExecutionError, match="time_series"):
        execute_recommendation(frame, recommendation, approved=True)
