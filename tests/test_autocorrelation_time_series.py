"""Tests for ACF/PACF time-series diagnostics and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError, available_execution_methods, execute_recommendation,
)
from timan_intelligence.core.time_series import run_autocorrelation_diagnostics


def _frame(n=90):
    rng = np.random.default_rng(9832)
    values = np.zeros(n)
    for i in range(1, n):
        values[i] = 0.7 * values[i - 1] + rng.normal()
    return pd.DataFrame({
        "month": pd.date_range("2017-01-01", periods=n, freq="MS"),
        "value": values,
    })


def test_acf_pacf_and_ljung_box_outputs_are_well_formed():
    result = run_autocorrelation_diagnostics(_frame(), "month", "value", nlags=12)
    table = result.tables["acf_pacf"]
    assert result.status == "success"
    assert len(table) == 13
    assert table.loc[0, "autocorrelation"] == pytest.approx(1.0)
    assert table.loc[0, "partial_autocorrelation"] == pytest.approx(1.0)
    assert table["acf_confidence_lower"].le(table["acf_confidence_upper"]).all()
    assert table["pacf_confidence_lower"].le(table["pacf_confidence_upper"]).all()
    assert set(result.tables["ljung_box"].columns) >= {"lag", "ljung_box_q", "p_value"}
    assert result.tables["ljung_box"]["p_value"].between(0, 1).all()
    assert result.metadata["nlags"] == 12


def test_acf_pacf_sort_time_index_and_validate_options():
    shuffled = _frame().sample(frac=1, random_state=13).reset_index(drop=True)
    result = run_autocorrelation_diagnostics(shuffled, "month", "value", nlags=8)
    assert result.metadata["frequency"] == "MS"
    with pytest.raises(ValueError, match="nlags"):
        run_autocorrelation_diagnostics(_frame(), "month", "value", nlags=0)
    with pytest.raises(ValueError, match="nlags"):
        run_autocorrelation_diagnostics(_frame(40), "month", "value", nlags=20)
    with pytest.raises(ValueError, match="Confidence level"):
        run_autocorrelation_diagnostics(_frame(), "month", "value", confidence_level=1.0)


def test_acf_pacf_reject_invalid_time_series_data():
    frame = _frame()
    with pytest.raises(ValueError, match="regularly spaced"):
        run_autocorrelation_diagnostics(frame.drop(index=10), "month", "value")
    with pytest.raises(ValueError, match="unique"):
        duplicate = frame.copy()
        duplicate.loc[1, "month"] = duplicate.loc[0, "month"]
        run_autocorrelation_diagnostics(duplicate, "month", "value")
    with pytest.raises(ValueError, match="complete and finite"):
        missing = frame.copy()
        missing.loc[0, "value"] = np.inf
        run_autocorrelation_diagnostics(missing, "month", "value")
    with pytest.raises(ValueError, match="constant series"):
        constant = frame.copy()
        constant["value"] = 4.0
        run_autocorrelation_diagnostics(constant, "month", "value")


def test_acf_pacf_executor_requires_approval_and_time_series_design():
    recommendation = {
        "method": "ACF and PACF autocorrelation diagnostics",
        "method_id": "method.diagnostic.time_series.autocorrelation",
        "variables": ["month", "value"],
        "status": "review_required",
        "options": {"nlags": 10},
        "design_context": {"study_design": "time_series"},
    }
    assert "ACF and PACF autocorrelation diagnostics" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_frame(), recommendation)
    result = execute_recommendation(_frame(), recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.diagnostic.time_series.autocorrelation"
    recommendation["design_context"] = {"study_design": "cross_sectional"}
    with pytest.raises(AnalysisExecutionError, match="time_series"):
        execute_recommendation(_frame(), recommendation, approved=True)
