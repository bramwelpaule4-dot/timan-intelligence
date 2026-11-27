"""Tests for one-sample and binary-proportion effect sizes."""
import math
import pandas as pd
import pytest
from timan_intelligence.core.statistical_engine import run_one_sample_t_test, run_two_independent_proportions_test


def _hedges_correction(df):
    return math.exp(math.lgamma(df / 2) - 0.5 * math.log(df / 2) - math.lgamma((df - 1) / 2))


def test_one_sample_t_test_reports_cohen_d_and_hedges_g():
    frame = pd.DataFrame({"score": [1., 2., 3., 4., 5.]})
    result = run_one_sample_t_test(frame, "score", reference_value=2.0)
    expected_d = (3.0 - 2.0) / frame["score"].std(ddof=1)
    assert result.metadata["cohen_d"] == pytest.approx(expected_d)
    assert result.metadata["hedges_g"] == pytest.approx(expected_d * _hedges_correction(4))
    row = result.tables["test"].iloc[0]
    assert row["Cohen's d"] == pytest.approx(expected_d)


def test_one_sample_t_test_with_one_degree_of_freedom_withholds_hedges_g():
    result = run_one_sample_t_test(pd.DataFrame({"score": [1., 3.]}), "score", 0.0)
    assert result.metadata["cohen_d"] is not None
    assert result.metadata["hedges_g"] is None


def test_one_sample_t_test_handles_zero_sd_without_infinite_effect_size():
    result = run_one_sample_t_test(pd.DataFrame({"score": [2., 2., 2.]}), "score", 1.0)
    assert result.metadata["cohen_d"] is None
    assert result.metadata["hedges_g"] is None


def test_two_proportion_test_reports_directional_cohen_h():
    frame = pd.DataFrame({
        "group": ["A"] * 10 + ["B"] * 10,
        "event": [1] * 8 + [0] * 2 + [1] * 3 + [0] * 7,
    })
    result = run_two_independent_proportions_test(frame, "event", "group")
    expected = 2 * (math.asin(math.sqrt(0.8)) - math.asin(math.sqrt(0.3)))
    assert result.metadata["cohen_h"] == pytest.approx(expected)
    assert result.tables["test_summary"].iloc[0]["Cohen's h"] == pytest.approx(expected)
