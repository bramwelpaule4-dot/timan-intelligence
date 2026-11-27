"""Tests for internal-consistency reliability estimation."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.statistical_engine import run_cronbach_alpha
from timan_intelligence.core.analysis_executor import execute_recommendation, AnalysisExecutionError


def _scale_frame(n=240, seed=31):
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=n)
    return pd.DataFrame({
        "item_a": latent + rng.normal(scale=0.45, size=n),
        "item_b": latent + rng.normal(scale=0.50, size=n),
        "item_c": latent + rng.normal(scale=0.55, size=n),
        "item_d": latent + rng.normal(scale=0.60, size=n),
    })


def test_cronbach_alpha_reports_reliability_and_item_diagnostics():
    result = run_cronbach_alpha(_scale_frame(), ["item_a", "item_b", "item_c", "item_d"])
    assert result.status == "success"
    alpha = result.tables["reliability_summary"].iloc[0]["Cronbach's alpha"]
    assert 0.7 < alpha < 1.0
    assert len(result.tables["item_diagnostics"]) == 4
    assert "Corrected item-total correlation" in result.tables["item_diagnostics"]
    assert result.metadata["valid_n"] == 240
    assert result.metadata["sampling_design_aware"] is False


def test_cronbach_alpha_uses_listwise_complete_cases_and_reports_exclusions():
    frame = _scale_frame()
    frame.loc[0, "item_a"] = np.nan
    frame.loc[1, "item_c"] = np.inf
    result = run_cronbach_alpha(frame, ["item_a", "item_b", "item_c"])
    assert result.metadata["valid_n"] == len(frame) - 2
    assert result.metadata["excluded_n"] == 2
    assert any("listwise deletion" in item for item in result.limitations)


@pytest.mark.parametrize("variables,match", [
    (["item_a"], "at least two"),
    (["item_a", "item_a"], "only once"),
    (["item_a", "missing"], "Unknown"),
])
def test_cronbach_alpha_rejects_invalid_item_selection(variables, match):
    with pytest.raises(ValueError, match=match):
        run_cronbach_alpha(_scale_frame(), variables)


def test_cronbach_alpha_rejects_non_numeric_items_and_too_few_complete_cases():
    frame = _scale_frame()
    frame["text"] = ["yes"] * len(frame)
    with pytest.raises(TypeError, match="numeric"):
        run_cronbach_alpha(frame, ["item_a", "text"])
    frame.loc[:, ["item_a", "item_b"]] = np.nan
    with pytest.raises(ValueError, match="three complete"):
        run_cronbach_alpha(frame, ["item_a", "item_b"])


def test_cronbach_alpha_runs_only_after_explicit_approval():
    frame = _scale_frame()
    recommendation = {
        "method": "Cronbach's alpha",
        "method_id": "method.measurement.reliability.cronbach_alpha",
        "variables": ["item_a", "item_b", "item_c", "item_d"],
        "status": "review_required",
    }
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.measurement.reliability.cronbach_alpha"



def test_mcdonald_omega_total_is_executable_after_approval():
    from timan_intelligence.core.statistical_engine import run_mcdonald_omega_total
    frame = _scale_frame(n=320, seed=51)
    result = run_mcdonald_omega_total(frame, ["item_a", "item_b", "item_c", "item_d"])
    assert result.status == "success"
    assert 0.70 < result.metadata["omega_total"] <= 1.0
    assert result.metadata["factor_count"] == 1
    assert len(result.tables["item_factor_diagnostics"]) == 4
    recommendation = {
        "method": "McDonald's omega total",
        "method_id": "method.measurement.reliability.mcdonald_omega_total",
        "variables": ["item_a", "item_b", "item_c", "item_d"],
        "status": "review_required",
    }
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    approved = execute_recommendation(frame, recommendation, approved=True)
    assert approved.metadata["method_id"] == "method.measurement.reliability.mcdonald_omega_total"


def test_mcdonald_omega_reports_exclusions_and_model_fit():
    from timan_intelligence.core.statistical_engine import run_mcdonald_omega_total
    frame = _scale_frame(n=320, seed=52)
    frame.loc[0, "item_a"] = np.nan
    result = run_mcdonald_omega_total(frame, ["item_a", "item_b", "item_c", "item_d"])
    assert result.metadata["excluded_n"] == 1
    assert result.metadata["model_degrees_of_freedom"] == 2
    assert any("listwise" in item for item in result.limitations)


def test_mcdonald_omega_rejects_insufficient_items_and_singular_covariance():
    from timan_intelligence.core.statistical_engine import run_mcdonald_omega_total
    frame = _scale_frame(n=320, seed=53)
    with pytest.raises(ValueError, match="at least three"):
        run_mcdonald_omega_total(frame, ["item_a", "item_b"])
    frame["duplicate"] = frame["item_a"]
    with pytest.raises(ValueError, match="singular"):
        run_mcdonald_omega_total(frame, ["item_a", "duplicate", "item_b"])
