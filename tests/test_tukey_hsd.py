"""Tests for Tukey HSD post-hoc comparisons and controlled execution."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError,
    available_execution_methods,
    execute_recommendation,
)
from timan_intelligence.core.statistical_engine import run_tukey_hsd_posthoc


def _frame():
    rng = np.random.default_rng(421)
    return pd.DataFrame({
        "group": ["A"] * 20 + ["B"] * 20 + ["C"] * 20,
        "score": np.concatenate([
            rng.normal(10, 1, 20),
            rng.normal(12, 1, 20),
            rng.normal(18, 1, 20),
        ]),
    })


def test_tukey_hsd_reports_all_pairs_simultaneous_intervals_and_adjusted_p_values():
    result = run_tukey_hsd_posthoc(_frame(), "score", "group")
    table = result.tables["pairwise_comparisons"]
    assert result.status == "success"
    assert len(table) == 3
    assert table["Tukey-adjusted p-value"].between(0, 1).all()
    assert table["95% simultaneous CI lower"].le(
        table["Mean difference (Group 2 - Group 1)"]
    ).all()
    assert table["95% simultaneous CI upper"].ge(
        table["Mean difference (Group 2 - Group 1)"]
    ).all()
    assert result.metadata["adjustment"] == "Tukey HSD"
    assert result.metadata["number_of_comparisons"] == 3
    assert result.metadata["significant_comparisons"] >= 1


def test_tukey_hsd_excludes_missing_and_infinite_outcomes():
    frame = _frame()
    frame.loc[0, "score"] = np.nan
    frame.loc[1, "score"] = np.inf
    result = run_tukey_hsd_posthoc(frame, "score", "group")
    assert result.metadata["excluded_outcomes"] == 2
    assert result.metadata["n_observations"] == len(frame) - 2


@pytest.mark.parametrize("groups,match", [
    (["A", "A", "B", "B"], "at least three"),
    (["A", "A", "B", "B", "C"], "at least two finite"),
])
def test_tukey_hsd_rejects_insufficient_group_structure(groups, match):
    frame = pd.DataFrame({"group": groups, "score": list(range(len(groups)))})
    with pytest.raises(ValueError, match=match):
        run_tukey_hsd_posthoc(frame, "score", "group")


def test_tukey_hsd_rejects_zero_pooled_error_variance_and_missing_group_labels():
    constant = pd.DataFrame({"group": ["A", "A", "B", "B", "C", "C"], "score": [2.] * 6})
    with pytest.raises(ValueError, match="pooled within-group"):
        run_tukey_hsd_posthoc(constant, "score", "group")
    missing_group = _frame()
    missing_group.loc[0, "group"] = None
    with pytest.raises(ValueError, match="missing group"):
        run_tukey_hsd_posthoc(missing_group, "score", "group")


def test_tukey_hsd_rejects_invalid_confidence_level():
    with pytest.raises(ValueError, match="Confidence level"):
        run_tukey_hsd_posthoc(_frame(), "score", "group", confidence_level=1.0)


def test_tukey_hsd_is_available_and_requires_explicit_approval():
    assert "Tukey's honestly significant difference" in available_execution_methods()
    recommendation = {
        "method": "Tukey's honestly significant difference",
        "method_id": "method.inference.comparison.posthoc.tukey",
        "variables": ["score", "group"],
        "status": "review_required",
    }
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(_frame(), recommendation)


def test_tukey_hsd_executes_after_approval_and_blocks_complex_sampling():
    recommendation = {
        "method": "Tukey's honestly significant difference",
        "method_id": "method.inference.comparison.posthoc.tukey",
        "variables": ["score", "group"],
        "status": "review_required",
    }
    result = execute_recommendation(_frame(), recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.posthoc.tukey"
    recommendation["design_context"] = {"sampling_design": "cluster"}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(_frame(), recommendation, approved=True)
