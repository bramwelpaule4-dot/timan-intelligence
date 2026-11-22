import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_stratified_weighted_frequency_service,
    run_stratified_weighted_mean_service,
)


def _df():
    return pd.DataFrame({
        "stratum": ["A"] * 4 + ["B"] * 4,
        "weight": [5.0] * 4 + [10.0] * 4,
        "score": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        "status": ["Yes", "Yes", "No", "No", "Yes", "No", "No", "No"],
    })


def test_stratified_mean_service_returns_shared_result():
    result = run_stratified_weighted_mean_service(
        _df(), "score", "weight", "stratum"
    )
    assert result.status == "success"
    assert "stratified_estimate" in result.tables
    assert "strata_summary" in result.tables
    assert result.limitations


def test_stratified_frequency_service_returns_shared_result():
    result = run_stratified_weighted_frequency_service(
        _df(), "status", "weight", "stratum"
    )
    assert result.status == "success"
    assert "stratified_frequencies" in result.tables
    yes = result.tables["stratified_frequencies"].set_index("response").loc["Yes"]
    assert yes["weighted_percent"] == pytest.approx(33.333333)
    assert result.metadata["number_of_strata"] == 2
