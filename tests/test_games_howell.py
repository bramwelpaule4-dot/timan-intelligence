"""Tests for Games-Howell heteroscedastic post-hoc comparisons."""
import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.analysis_executor import (
    AnalysisExecutionError, available_execution_methods, execute_recommendation,
)
from timan_intelligence.core.statistical_engine import run_games_howell_posthoc


def _frame():
    rng = np.random.default_rng(4419)
    return pd.DataFrame({
        "group": ["A"] * 12 + ["B"] * 18 + ["C"] * 25,
        "score": np.concatenate([
            rng.normal(10, 0.5, 12),
            rng.normal(13, 3.0, 18),
            rng.normal(18, 1.5, 25),
        ]),
    })


def test_games_howell_reports_pairwise_welch_df_and_simultaneous_intervals():
    result = run_games_howell_posthoc(_frame(), "score", "group")
    table = result.tables["pairwise_comparisons"]
    assert result.status == "success"
    assert len(table) == 3
    assert table["Games-Howell p-value"].between(0, 1).all()
    assert table["Welch-Satterthwaite degrees of freedom"].gt(0).all()
    assert table["95% simultaneous CI lower"].le(
        table["Mean difference (Group 2 - Group 1)"]
    ).all()
    assert table["95% simultaneous CI upper"].ge(
        table["Mean difference (Group 2 - Group 1)"]
    ).all()
    assert result.metadata["equal_variances_assumed"] is False
    assert result.metadata["adjustment"] == "Games-Howell studentized range"
    assert result.metadata["number_of_comparisons"] == 3


def test_games_howell_excludes_nonfinite_outcomes_and_rejects_missing_groups():
    frame = _frame()
    frame.loc[0, "score"] = np.nan
    frame.loc[1, "score"] = np.inf
    result = run_games_howell_posthoc(frame, "score", "group")
    assert result.metadata["excluded_outcomes"] == 2
    assert result.metadata["n_observations"] == len(frame) - 2
    frame.loc[2, "group"] = None
    with pytest.raises(ValueError, match="missing group"):
        run_games_howell_posthoc(frame, "score", "group")


def test_games_howell_rejects_insufficient_groups_and_zero_pair_variance():
    with pytest.raises(ValueError, match="at least three"):
        run_games_howell_posthoc(
            pd.DataFrame({"score": [1, 2, 3, 4], "group": ["A", "A", "B", "B"]}),
            "score", "group",
        )
    constant_pair = pd.DataFrame({
        "score": [1, 1, 2, 2, 3, 4],
        "group": ["A", "A", "B", "B", "C", "C"],
    })
    with pytest.raises(ValueError, match="zero or negligible"):
        run_games_howell_posthoc(constant_pair, "score", "group")


def test_games_howell_is_approval_gated_and_available_for_independent_groups():
    frame = _frame()
    recommendation = {
        "method": "Games-Howell post-hoc test",
        "method_id": "method.inference.comparison.posthoc.games_howell",
        "variables": ["score", "group"],
        "status": "review_required",
    }
    assert "Games-Howell post-hoc test" in available_execution_methods()
    with pytest.raises(AnalysisExecutionError, match="approval"):
        execute_recommendation(frame, recommendation)
    result = execute_recommendation(frame, recommendation, approved=True)
    assert result.status == "success"
    assert result.metadata["method_id"] == "method.inference.comparison.posthoc.games_howell"
    recommendation["design_context"] = {"sampling_design": "cluster"}
    with pytest.raises(AnalysisExecutionError, match="not validated"):
        execute_recommendation(frame, recommendation, approved=True)
