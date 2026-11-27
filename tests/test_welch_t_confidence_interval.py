"""Confidence-interval reporting tests for Welch's independent-samples t-test."""
import pandas as pd
import pytest
from scipy.stats import t

from timan_intelligence.core.statistical_engine import run_independent_samples_t_test


def test_welch_t_test_reports_satterthwaite_confidence_interval():
    frame = pd.DataFrame({
        "group": ["A"] * 5 + ["B"] * 4,
        "score": [10., 11., 12., 13., 14., 17., 19., 21., 23.],
    })
    result = run_independent_samples_t_test(frame, "score", "group", confidence_level=0.90)
    summary = result.tables["summary"]
    n1, n2 = summary["group_1_n"], summary["group_2_n"]
    v1 = frame.loc[frame["group"] == "A", "score"].var(ddof=1)
    v2 = frame.loc[frame["group"] == "B", "score"].var(ddof=1)
    se2 = v1 / n1 + v2 / n2
    df = se2**2 / ((v1 / n1)**2 / (n1 - 1) + (v2 / n2)**2 / (n2 - 1))
    difference = summary["mean_difference_group_1_minus_group_2"]
    se = se2**0.5
    critical = t.ppf(0.95, df)
    assert summary["confidence_level"] == pytest.approx(0.90)
    assert summary["standard_error"] == pytest.approx(se)
    assert summary["confidence_interval_lower"] == pytest.approx(difference - critical * se)
    assert summary["confidence_interval_upper"] == pytest.approx(difference + critical * se)
    assert result.metadata["confidence_interval"][0] < difference < result.metadata["confidence_interval"][1]


@pytest.mark.parametrize("level", [0, 1, -0.1, 1.1])
def test_welch_t_test_rejects_invalid_confidence_level(level):
    frame = pd.DataFrame({"group": ["A", "A", "B", "B"], "score": [1., 2., 3., 4.]})
    with pytest.raises(ValueError, match="Confidence level"):
        run_independent_samples_t_test(frame, "score", "group", confidence_level=level)
