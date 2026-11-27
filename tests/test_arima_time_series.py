"""Tests for non-seasonal ARIMA fitting and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)
from timan_intelligence.core.time_series import run_arima_time_series_model


def _series():
    rng = np.random.default_rng(913)
    values = np.empty(60)
    values[0] = 0.0
    for index in range(1, len(values)):
        values[index] = 0.65 * values[index - 1] + rng.normal(0, 1)
    return pd.DataFrame({
        "month": pd.date_range("2020-01-01", periods=60, freq="MS"),
        "value": values,
    })


def test_arima_fits_model_and_returns_forecasts_prediction_intervals_and_diagnostics():
    frame = _series()
    result = run_arima_time_series_model(
        frame, "month", "value", order=(1, 0, 0), forecast_steps=4
    )
    forecast = result.tables["forecasts"]
    assert result.status == "success"
    assert len(forecast) == 4
    assert forecast["prediction_interval_lower"].le(forecast["forecast"]).all()
    assert forecast["prediction_interval_upper"].ge(forecast["forecast"]).all()
    assert set(result.tables) == {"parameter_estimates", "forecasts", "residual_diagnostics"}
    assert result.metadata["order"] == (1, 0, 0)
    assert result.metadata["frequency"] == "MS"
    assert result.metadata["converged"] is True


def test_arima_sorts_time_index_before_fitting():
    frame = _series().sample(frac=1, random_state=8).reset_index(drop=True)
    result = run_arima_time_series_model(frame, "month", "value", order=(1, 0, 0), forecast_steps=2)
    assert result.metadata["start"].startswith("2020-01")
    assert result.metadata["end"].startswith("2024-12")
    assert result.tables["forecasts"]["month"].is_monotonic_increasing


def test_arima_rejects_irregular_duplicate_missing_and_short_series():
    frame = _series()
    irregular = frame.drop(index=10).reset_index(drop=True)
    with pytest.raises(ValueError, match="regularly spaced"):
        run_arima_time_series_model(irregular, "month", "value", order=(1, 0, 0))
    duplicate = frame.copy()
    duplicate.loc[1, "month"] = duplicate.loc[0, "month"]
    with pytest.raises(ValueError, match="unique"):
        run_arima_time_series_model(duplicate, "month", "value", order=(1, 0, 0))
    missing = frame.copy()
    missing.loc[0, "value"] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        run_arima_time_series_model(missing, "month", "value", order=(1, 0, 0))
    with pytest.raises(ValueError, match="At least 30"):
        run_arima_time_series_model(frame.head(20), "month", "value", order=(1, 0, 0))


def test_arima_rejects_invalid_order_forecast_horizon_and_confidence_level():
    frame = _series()
    with pytest.raises(ValueError, match="ARIMA order"):
        run_arima_time_series_model(frame, "month", "value", order=(5, 0, 0))
    with pytest.raises(ValueError, match="forecast_steps"):
        run_arima_time_series_model(frame, "month", "value", order=(1, 0, 0), forecast_steps=0)
    with pytest.raises(ValueError, match="Confidence level"):
        run_arima_time_series_model(frame, "month", "value", order=(1, 0, 0), confidence_level=1.0)


def test_arima_executor_is_available_requires_approval_and_allows_time_series_design():
    assert "ARIMA time-series model" in available_execution_methods()
    frame = _series()
    recommendation = {
        "method": "ARIMA time-series model",
        "method_id": "method.forecasting.time_series.arima",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"order": [1, 0, 0], "forecast_steps": 3},
        "design_context": {"study_design": "time_series"},
    }
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.forecasting.time_series.arima"


def test_arima_executor_blocks_complex_sampling_design():
    recommendation = {
        "method": "ARIMA time-series model",
        "method_id": "method.forecasting.time_series.arima",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"order": [1, 0, 0], "forecast_steps": 3},
        "design_context": {"sampling_design": "cluster"},
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(_series(), recommendation, approved=True)
