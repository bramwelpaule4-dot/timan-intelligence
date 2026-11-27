"""Risk-ratio and odds-ratio reporting tests for two independent proportions."""
import math
import pandas as pd
import pytest
from scipy.stats import norm
from timan_intelligence.core.statistical_engine import run_two_independent_proportions_test


def test_two_proportion_test_reports_risk_and_odds_ratios_with_log_intervals():
    frame = pd.DataFrame({
        "group": ["A"] * 10 + ["B"] * 10,
        "event": [1] * 8 + [0] * 2 + [1] * 3 + [0] * 7,
    })
    result = run_two_independent_proportions_test(frame, "event", "group", confidence_level=0.90)
    assert result.metadata["risk_ratio"] == pytest.approx((8 / 10) / (3 / 10))
    assert result.metadata["odds_ratio"] == pytest.approx((8 * 7) / (2 * 3))
    z = norm.ppf(0.95)
    rr_se = math.sqrt(1/8 - 1/10 + 1/3 - 1/10)
    or_se = math.sqrt(1/8 + 1/2 + 1/3 + 1/7)
    rr = result.metadata["risk_ratio"]
    odds = result.metadata["odds_ratio"]
    assert result.metadata["risk_ratio_confidence_interval"] == pytest.approx(
        (math.exp(math.log(rr)-z*rr_se), math.exp(math.log(rr)+z*rr_se))
    )
    assert result.metadata["odds_ratio_confidence_interval"] == pytest.approx(
        (math.exp(math.log(odds)-z*or_se), math.exp(math.log(odds)+z*or_se))
    )
    assert "Risk ratio CI lower" in result.tables["test_summary"]


def test_two_proportion_test_does_not_silently_correct_zero_cells():
    frame = pd.DataFrame({
        "group": ["A"] * 4 + ["B"] * 4,
        "event": [1, 1, 1, 1, 0, 0, 0, 0],
    })
    result = run_two_independent_proportions_test(frame, "event", "group")
    assert result.metadata["risk_ratio"] == float("inf")
    assert result.metadata["odds_ratio"] == float("inf")
    assert result.metadata["risk_ratio_confidence_interval"] is None
    assert result.metadata["odds_ratio_confidence_interval"] is None
    assert any("zero cell" in item for item in result.limitations)
