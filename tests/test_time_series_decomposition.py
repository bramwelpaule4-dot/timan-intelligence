"""Tests for STL time-series decomposition and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)
from timan_intelligence.core.time_series import run_stl_time_series_decomposition


def _seasonal_series():
    rng = np.random.default_rng(442)
    n = 84
    t = np.arange(n)
    values = 25 + 0.12 * t + 5 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 0.5, n)
    return pd.DataFrame({
        "month": pd.date_range("2018-01-01", periods=n, freq="MS"),
        "value": values,
    })


def test_stl_returns_observed_trend_seasonal_and_remainder_components():
    result = run_stl_time_series_decomposition(_seasonal_series(), "month", "value")
    components = result.tables["decomposition"]
    summary = result.tables["summary"].iloc[0]
    assert result.status == "success"
    assert len(components) == 84
    assert {"observed", "trend", "seasonal", "remainder", "robust_remainder_z", "is_remainder_outlier"}.issubset(components.columns)
    assert np.allclose(
        components["observed"],
        components["trend"] + components["seasonal"] + components["remainder"],
        atol=1e-8,
    )
    assert 0 <= summary["trend_strength"] <= 1
    assert 0 <= summary["seasonal_strength"] <= 1
    assert result.metadata["frequency"] == "MS"


def test_stl_sorts_dates_and_validates_seasonal_period_and_sample_size():
    shuffled = _seasonal_series().sample(frac=1, random_state=12)
    result = run_stl_time_series_decomposition(shuffled, "month", "value", seasonal_period=12)
    assert result.tables["decomposition"]["month"].is_monotonic_increasing
    with pytest.raises(ValueError, match="seasonal_period"):
        run_stl_time_series_decomposition(_seasonal_series(), "month", "value", seasonal_period=1)
    with pytest.raises(ValueError, match="At least 30 observations"):
        run_stl_time_series_decomposition(_seasonal_series().head(20), "month", "value", seasonal_period=12)


def test_stl_rejects_irregular_and_nonfinite_series():
    frame = _seasonal_series()
    with pytest.raises(ValueError, match="regularly spaced"):
        run_stl_time_series_decomposition(frame.drop(index=2), "month", "value")
    frame.loc[0, "value"] = np.inf
    with pytest.raises(ValueError, match="complete and finite"):
        run_stl_time_series_decomposition(frame, "month", "value")


def test_stl_executor_is_approval_gated_and_allows_time_series_design():
    frame = _seasonal_series()
    recommendation = {
        "method": "STL time-series decomposition",
        "method_id": "method.forecasting.time_series.stl_decomposition",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"seasonal_period": 12, "robust": True},
        "design_context": {"study_design": "time_series"},
    }
    assert "STL time-series decomposition" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.forecasting.time_series.stl_decomposition"



def test_stl_flags_extreme_remainder_using_mad_score():
    frame = _seasonal_series()
    frame.loc[30, "value"] += 25.0
    result = run_stl_time_series_decomposition(
        frame, "month", "value", seasonal_period=12, robust=True,
        outlier_threshold=3.5,
    )
    components = result.tables["decomposition"]
    summary = result.tables["summary"].iloc[0]
    assert bool(components.loc[30, "is_remainder_outlier"])
    assert abs(components.loc[30, "robust_remainder_z"]) > 3.5
    assert summary["remainder_outlier_count"] >= 1
    assert result.metadata["remainder_outlier_count"] >= 1


def test_stl_validates_outlier_threshold():
    with pytest.raises(ValueError, match="outlier_threshold"):
        run_stl_time_series_decomposition(
            _seasonal_series(), "month", "value", outlier_threshold=1.0
        )
    with pytest.raises(TypeError, match="outlier_threshold"):
        run_stl_time_series_decomposition(
            _seasonal_series(), "month", "value", outlier_threshold=True
        )
