import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_cluster_weighted_frequency_service,
    run_cluster_weighted_mean_service,
)


def _df():
    return pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "weight": [2.0] * 8 + [3.0] * 8,
        "score": [1., 2., 3., 4., 2., 3., 4., 5.,
                  4., 5., 6., 7., 5., 6., 7., 8.],
        "status": ["Yes", "Yes", "No", "No"] * 4,
    })


def test_cluster_mean_service_returns_shared_analysis_result():
    result = run_cluster_weighted_mean_service(
        _df(), "score", "weight", "psu", "stratum"
    )
    assert result.status == "success"
    assert "cluster_estimate" in result.tables
    assert result.metadata["number_of_clusters"] == 4
    assert result.limitations


def test_cluster_frequency_service_returns_shared_analysis_result():
    result = run_cluster_weighted_frequency_service(
        _df(), "status", "weight", "psu", "stratum"
    )
    assert result.status == "success"
    assert "cluster_frequencies" in result.tables
    assert result.tables["cluster_frequencies"]["weighted_percent"].sum() == pytest.approx(100)
