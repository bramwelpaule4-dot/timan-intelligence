"""Tests for standardized effect sizes reported by t-test procedures."""
import math
import pandas as pd
import pytest
from timan_intelligence.core.statistical_engine import run_independent_samples_t_test, run_paired_samples_t_test


def _hedges_correction(df):
    return math.exp(math.lgamma(df / 2) - 0.5 * math.log(df / 2) - math.lgamma((df - 1) / 2))


def test_welch_t_test_reports_directional_cohen_d_and_hedges_g():
    frame = pd.DataFrame({"group": ["A"] * 3 + ["B"] * 3, "score": [1., 2., 3., 4., 5., 6.]})
    result = run_independent_samples_t_test(frame, "score", "group")
    row = result.tables["summary"].iloc[0]
    assert row["cohen_d"] == pytest.approx(-3.0)
    assert row["hedges_g"] == pytest.approx(-3.0 * _hedges_correction(4))
    assert row["mean_difference_group_1_minus_group_2"] == pytest.approx(-3.0)
    assert result.metadata["cohen_d"] == pytest.approx(-3.0)


def test_welch_t_test_handles_zero_pooled_variance_without_infinite_effect_size():
    frame = pd.DataFrame({"group": ["A"] * 3 + ["B"] * 3, "score": [2.] * 6})
    result = run_independent_samples_t_test(frame, "score", "group")
    row = result.tables["summary"].iloc[0]
    assert row["cohen_d"] is None
    assert row["hedges_g"] is None


def test_paired_t_test_reports_dz_and_small_sample_corrected_gz():
    frame = pd.DataFrame({"before": [1., 2., 3., 4.], "after": [2., 4., 6., 8.]})
    result = run_paired_samples_t_test(frame, "before", "after")
    differences = frame["after"] - frame["before"]
    expected = differences.mean() / differences.std(ddof=1)
    assert result.metadata["cohen_dz"] == pytest.approx(expected)
    assert result.metadata["hedges_gz"] == pytest.approx(expected * _hedges_correction(3))
    assert result.tables["test"].iloc[0]["Cohen's dz"] == pytest.approx(expected)


def test_paired_t_test_with_one_degree_of_freedom_withholds_hedges_correction():
    frame = pd.DataFrame({"before": [1., 2.], "after": [2., 4.]})
    result = run_paired_samples_t_test(frame, "before", "after")
    assert result.metadata["cohen_dz"] is not None
    assert result.metadata["hedges_gz"] is None
    assert result.metadata["hedges_correction"] is None


def test_paired_t_test_reports_undefined_effect_size_for_constant_change():
    frame = pd.DataFrame({"before": [1., 2., 3.], "after": [2., 3., 4.]})
    result = run_paired_samples_t_test(frame, "before", "after")
    assert result.metadata["cohen_dz"] is None
    assert result.metadata["hedges_gz"] is None
