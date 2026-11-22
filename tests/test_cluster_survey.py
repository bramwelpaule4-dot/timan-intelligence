import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.cluster_survey import (
    cluster_weighted_frequencies,
    cluster_weighted_mean,
)


def _sample():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "weight": [2.0] * 8 + [3.0] * 8,
        "outcome": [1., 2., 3., 4., 2., 3., 4., 5.,
                    4., 5., 6., 7., 5., 6., 7., 8.],
        "status": ["Yes", "Yes", "No", "No"] * 4,
    })


def test_cluster_weighted_mean_uses_psu_level_variance():
    result = cluster_weighted_mean(_sample(), "outcome", "weight", "psu", "stratum")
    row = result["table"].iloc[0]
    assert row["cluster_weighted_mean"] == pytest.approx(5.0)
    assert row["standard_error"] > 0
    assert row["number_of_clusters"] == 4
    assert row["degrees_of_freedom"] == 2
    assert row["ci_lower"] < row["cluster_weighted_mean"] < row["ci_upper"]


def test_cluster_weighted_frequencies_sum_to_100():
    result = cluster_weighted_frequencies(
        _sample(), "status", "weight", "psu", "stratum"
    )
    assert result["table"]["weighted_percent"].sum() == pytest.approx(100.0)
    assert "standard_error_percentage_points" in result["table"]


def test_cluster_estimator_without_strata_uses_one_stratum():
    result = cluster_weighted_mean(_sample(), "outcome", "weight", "psu")
    assert result["metadata"]["number_of_strata"] == 1
    assert result["metadata"]["degrees_of_freedom"] == 3


def test_rejects_single_psu_in_a_stratum():
    df = _sample()
    df.loc[df["stratum"] == "B", "psu"] = 3
    with pytest.raises(ValueError, match="At least two sampled clusters"):
        cluster_weighted_mean(df, "outcome", "weight", "psu", "stratum")


def test_psu_labels_may_repeat_across_strata():
    df = _sample()
    df.loc[df["stratum"] == "B", "psu"] = df.loc[
        df["stratum"] == "B", "psu"
    ].map({3: 1, 4: 2})
    result = cluster_weighted_mean(df, "outcome", "weight", "psu", "stratum")
    assert result["metadata"]["number_of_clusters"] == 4


def test_rejects_missing_cluster_identifiers():
    df = _sample()
    df.loc[0, "psu"] = None
    with pytest.raises(ValueError, match="cannot be missing"):
        cluster_weighted_mean(df, "outcome", "weight", "psu", "stratum")


def test_rejects_invalid_confidence_level():
    with pytest.raises(ValueError, match="Confidence level"):
        cluster_weighted_mean(
            _sample(), "outcome", "weight", "psu", "stratum", 1.0
        )
