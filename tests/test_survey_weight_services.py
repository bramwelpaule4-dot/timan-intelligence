import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_weighted_frequency_service,
    run_weighted_numeric_summary_service,
)


def test_weighted_frequency_service_returns_shared_analysis_result():
    df = pd.DataFrame({
        "uptake": ["Yes", "No", "Yes"],
        "sample_weight": [2.0, 1.0, 3.0],
    })
    result = run_weighted_frequency_service(df, "uptake", "sample_weight")
    assert result.status == "success"
    assert "weighted_frequencies" in result.tables
    assert result.metadata["estimate_type"] == "weighted descriptive population estimate"
    assert result.limitations


def test_weighted_numeric_service_returns_shared_analysis_result():
    df = pd.DataFrame({
        "income": [100.0, 200.0, 300.0],
        "sample_weight": [1.0, 2.0, 1.0],
    })
    result = run_weighted_numeric_summary_service(df, "income", "sample_weight")
    assert result.status == "success"
    assert result.tables["weighted_summary"].iloc[0]["weighted_mean"] == pytest.approx(200.0)
    assert result.assumptions
    assert result.limitations
