import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_numeric_association_service,
)


def test_numeric_association_service_exposes_results_and_scatter_data():
    df = pd.DataFrame({
        "training_hours": [1, 2, 3, 4, 5],
        "assessment_score": [10, 20, 30, 40, 50],
    })
    result = run_numeric_association_service(
        df,
        "training_hours",
        "assessment_score",
    )

    assert result.status == "success"
    assert result.metadata["valid_n"] == 5
    assert result.metadata["pearson_r"] == pytest.approx(1.0)
    assert result.metadata["spearman_rho"] == pytest.approx(1.0)
    assert "descriptive_summary" in result.tables
    assert "paired_observations" in result.tables
    assert list(result.tables["paired_observations"].columns) == [
        "training_hours",
        "assessment_score",
    ]


def test_numeric_association_service_preserves_exclusion_count():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4],
        "y": [2, None, 6, 8],
    })
    result = run_numeric_association_service(df, "x", "y")
    assert result.metadata["valid_n"] == 3
    assert result.metadata["excluded_n"] == 1
