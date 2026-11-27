"""Tests for naïve and seasonal-naïve forecasting benchmarks."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError, available_execution_methods, execute_recommendation,
)
from timan_intelligence.core.time_series import run_naive_forecast_benchmarks


def _frame(n=72):
    values = 10 + np.arange(n) * 0.2 + 2 * np.sin(2 * np.pi * np.arange(n) / 12)
    return pd.DataFrame({
        "month": pd.date_range("2019-01-01", periods=n, freq="MS"),
        "value": values,
    })


def test_naive_and_seasonal_naive_forecasts_and_holdout_accuracy():
    result = run_naive_forecast_benchmarks(
        _frame(), "month", "value", forecast_steps=5,
        seasonal_period=12, validation_steps=8,
    )
    forecasts = result.tables["forecasts"]
    validation = result.tables["holdout_validation"]
    assert result.status == "success"
    assert forecasts["naive_forecast"].eq(_frame()["value"].iloc[-1]).all()
    assert forecasts["seasonal_naive_forecast"].tolist() == pytest.approx(
        _frame()["value"].iloc[-12:-7].tolist()
    )
    assert set(validation["benchmark"]) == {"naive", "seasonal_naive"}
    assert validation["mean_absolute_error"].ge(0).all()
    assert validation["root_mean_squared_error"].ge(validation["mean_absolute_error"]).all()
    assert validation["training_observations"].eq(64).all()
    assert result.metadata["seasonal_period"] == 12


def test_naive_only_forecast_and_no_validation_table_by_default():
    result = run_naive_forecast_benchmarks(
        _frame(), "month", "value", forecast_steps=3
    )
    assert list(result.tables) == ["forecasts"]
    assert "seasonal_naive_forecast" not in result.tables["forecasts"]
    assert result.metadata["validation_steps"] == 0


def test_naive_forecast_validates_series_and_options():
    frame = _frame()
    with pytest.raises(ValueError, match="regularly spaced"):
        run_naive_forecast_benchmarks(frame.drop(index=3), "month", "value")
    with pytest.raises(ValueError, match="unique"):
        duplicate = frame.copy()
        duplicate.loc[1, "month"] = duplicate.loc[0, "month"]
        run_naive_forecast_benchmarks(duplicate, "month", "value")
    with pytest.raises(ValueError, match="complete and finite"):
        missing = frame.copy()
        missing.loc[0, "value"] = np.nan
        run_naive_forecast_benchmarks(missing, "month", "value")
    with pytest.raises(ValueError, match="forecast_steps"):
        run_naive_forecast_benchmarks(frame, "month", "value", forecast_steps=0)
    with pytest.raises(ValueError, match="seasonal_period"):
        run_naive_forecast_benchmarks(frame, "month", "value", seasonal_period=1)
    with pytest.raises(ValueError, match="two seasonal cycles"):
        run_naive_forecast_benchmarks(frame.head(35), "month", "value", seasonal_period=12)


def test_naive_forecast_holdout_requires_minimum_training_data():
    with pytest.raises(ValueError, match="at least 30 training"):
        run_naive_forecast_benchmarks(
            _frame(35), "month", "value", validation_steps=10
        )


def test_naive_forecast_executor_requires_approval_and_time_series_design():
    recommendation = {
        "method": "Naïve forecasting benchmarks",
        "method_id": "method.forecasting.time_series.naive_benchmarks",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"forecast_steps": 4, "seasonal_period": 12, "validation_steps": 6},
        "design_context": {"study_design": "time_series"},
    }
    assert "Naïve forecasting benchmarks" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_frame(), recommendation)
    result = execute_recommendation(_frame(), recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.forecasting.time_series.naive_benchmarks"
    recommendation["design_context"] = {"study_design": "cross_sectional"}
    with pytest.raises(AnalysisExecutionError, match="time_series"):
        execute_recommendation(_frame(), recommendation, approved=True)
