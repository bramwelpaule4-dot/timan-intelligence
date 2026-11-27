"""Tests for exponential-smoothing forecasting and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError, available_execution_methods, execute_recommendation,
)
from timan_intelligence.core.time_series import run_exponential_smoothing_forecast


def _frame(n=84, positive=True):
    t = np.arange(n)
    values = 30 + 0.15 * t + 3.5 * np.sin(2 * np.pi * t / 12)
    if not positive:
        values = values - 40
    return pd.DataFrame({
        "month": pd.date_range("2017-01-01", periods=n, freq="MS"),
        "value": values,
    })


def test_holt_winter_seasonal_model_forecasts_and_validates_holdout():
    result = run_exponential_smoothing_forecast(
        _frame(), "month", "value", forecast_steps=6,
        trend="add", seasonal="add", seasonal_period=12,
        damped_trend=True, validation_steps=8,
    )
    assert result.status == "success"
    assert len(result.tables["forecasts"]) == 6
    assert set(result.tables) == {
        "forecasts", "model_summary", "parameter_estimates", "holdout_validation"
    }
    validation = result.tables["holdout_validation"].iloc[0]
    assert validation["training_observations"] == 76
    assert validation["mean_absolute_error"] >= 0
    assert validation["root_mean_squared_error"] >= validation["mean_absolute_error"]
    assert result.metadata["seasonal"] == "add"
    assert result.metadata["damped_trend"] is True


def test_simple_and_holt_models_are_supported():
    simple = run_exponential_smoothing_forecast(
        _frame(), "month", "value", forecast_steps=3, trend=None
    )
    holt = run_exponential_smoothing_forecast(
        _frame(), "month", "value", forecast_steps=3, trend="add"
    )
    assert len(simple.tables["forecasts"]) == 3
    assert len(holt.tables["forecasts"]) == 3
    assert simple.metadata["trend"] is None
    assert holt.metadata["trend"] == "add"


def test_exponential_smoothing_validates_model_options_and_series():
    frame = _frame()
    with pytest.raises(ValueError, match="trend"):
        run_exponential_smoothing_forecast(frame, "month", "value", trend="linear")
    with pytest.raises(TypeError, match="seasonal_period"):
        run_exponential_smoothing_forecast(
            frame, "month", "value", seasonal="add"
        )
    with pytest.raises(ValueError, match="damped_trend"):
        run_exponential_smoothing_forecast(
            frame, "month", "value", trend=None, damped_trend=True
        )
    with pytest.raises(ValueError, match="strictly positive"):
        run_exponential_smoothing_forecast(
            _frame(84, positive=False), "month", "value", trend="mul"
        )
    with pytest.raises(ValueError, match="two complete seasonal cycles"):
        run_exponential_smoothing_forecast(
            frame.head(35), "month", "value", seasonal="add", seasonal_period=18
        )
    with pytest.raises(ValueError, match="at least 30 training"):
        run_exponential_smoothing_forecast(
            frame.head(35), "month", "value", validation_steps=10
        )


def test_exponential_smoothing_executor_is_approval_gated_and_design_restricted():
    recommendation = {
        "method": "Exponential smoothing (Holt/Holt-Winters)",
        "method_id": "method.forecasting.time_series.exponential_smoothing",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {
            "trend": "add", "seasonal": "add", "seasonal_period": 12,
            "forecast_steps": 4, "validation_steps": 6,
        },
        "design_context": {"study_design": "time_series"},
    }
    assert "Exponential smoothing (Holt/Holt-Winters)" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_frame(), recommendation)
    result = execute_recommendation(_frame(), recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.forecasting.time_series.exponential_smoothing"
    recommendation["design_context"] = {"study_design": "cross_sectional"}
    with pytest.raises(AnalysisExecutionError, match="time_series"):
        execute_recommendation(_frame(), recommendation, approved=True)
