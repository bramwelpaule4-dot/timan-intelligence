"""Tests for IID bootstrap confidence intervals and executor safeguards."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)
from timan_intelligence.core.bootstrap import run_bootstrap_confidence_interval


def test_bootstrap_mean_is_reproducible_and_reports_percentile_interval():
    frame = pd.DataFrame({"score": [2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12., 13.]})
    first = run_bootstrap_confidence_interval(frame, "score", n_resamples=1000, random_state=27)
    second = run_bootstrap_confidence_interval(frame, "score", n_resamples=1000, random_state=27)
    a = first.tables["bootstrap_summary"].iloc[0]
    b = second.tables["bootstrap_summary"].iloc[0]
    assert a["estimate"] == pytest.approx(frame["score"].mean())
    assert a["ci_lower"] < a["estimate"] < a["ci_upper"]
    assert a["ci_lower"] == pytest.approx(b["ci_lower"])
    assert a["ci_upper"] == pytest.approx(b["ci_upper"])
    assert a["bootstrap_resamples"] == 1000
    assert a["bootstrap_mean_mcse"] == pytest.approx(a["bootstrap_standard_error"] / np.sqrt(1000))


def test_bootstrap_median_handles_missing_and_nonfinite_numeric_values():
    frame = pd.DataFrame({"score": [1., 2., 3., 4., 5., 6., 7., 8., 9., 10., np.nan, np.inf]})
    result = run_bootstrap_confidence_interval(
        frame, "score", statistic="median", n_resamples=1000, random_state=2
    )
    row = result.tables["bootstrap_summary"].iloc[0]
    assert row["estimate"] == pytest.approx(5.5)
    assert row["excluded_observations"] == 2
    assert result.metadata["sampling_design_aware"] is False


def test_bootstrap_category_proportion_requires_and_uses_category_value():
    frame = pd.DataFrame({"response": ["Yes", "No", "Yes", "No", "Yes", "Yes", "No", "Yes", "No", "Yes"]})
    result = run_bootstrap_confidence_interval(
        frame, "response", statistic="proportion", category_value="Yes",
        n_resamples=1000, random_state=7,
    )
    row = result.tables["bootstrap_summary"].iloc[0]
    assert row["estimate"] == pytest.approx(0.6)
    assert 0 <= row["ci_lower"] <= row["ci_upper"] <= 1
    with pytest.raises(ValueError, match="category_value"):
        run_bootstrap_confidence_interval(
            frame, "response", statistic="proportion", n_resamples=1000
        )


def test_bootstrap_rejects_small_samples_invalid_statistic_and_resample_count():
    with pytest.raises(ValueError, match="At least 10"):
        run_bootstrap_confidence_interval(pd.DataFrame({"x": range(9)}), "x")
    with pytest.raises(ValueError, match="Statistic"):
        run_bootstrap_confidence_interval(pd.DataFrame({"x": range(12)}), "x", statistic="mode")
    with pytest.raises(ValueError, match="between 1000"):
        run_bootstrap_confidence_interval(pd.DataFrame({"x": range(12)}), "x", n_resamples=999)


def test_bootstrap_executor_is_available_and_requires_approval():
    assert "Bootstrap confidence interval" in available_execution_methods()
    recommendation = {
        "method": "Bootstrap confidence interval",
        "method_id": "method.inference.resampling.bootstrap.confidence_interval",
        "variables": ["score"],
        "status": "review_required",
        "options": {"statistic": "mean", "n_resamples": 1000, "random_state": 9},
    }
    frame = pd.DataFrame({"score": np.arange(1, 21, dtype=float)})
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.resampling.bootstrap.confidence_interval"


@pytest.mark.parametrize("context", [
    {"sampling_design": "stratified"},
    {"sampling_design": "cluster"},
    {"study_design": "longitudinal"},
    {"study_design": "time_series"},
])
def test_bootstrap_executor_blocks_complex_or_dependent_designs(context):
    frame = pd.DataFrame({"score": np.arange(1, 21, dtype=float)})
    recommendation = {
        "method": "Bootstrap confidence interval",
        "method_id": "method.inference.resampling.bootstrap.confidence_interval",
        "variables": ["score"],
        "status": "review_required",
        "options": {"n_resamples": 1000},
        "design_context": context,
    }
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, recommendation, approved=True)
