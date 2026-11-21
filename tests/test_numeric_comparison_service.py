import pandas as pd

from timan_intelligence.services.analysis_service import (
    run_numeric_group_comparison_service,
)


def test_shared_service_exposes_numeric_group_summaries_and_inference():
    df = pd.DataFrame({
        "ward": ["North"] * 4 + ["South"] * 4,
        "household_size": [2, 3, 4, 5, 5, 6, 7, 8],
    })
    result = run_numeric_group_comparison_service(
        df,
        "ward",
        "household_size",
    )

    assert "group_summaries" in result.tables
    assert result.metadata["group_variable"] == "ward"
    assert result.metadata["outcome_variable"] == "household_size"
    assert result.metadata["test"] == "Welch's independent-samples t-test"
    assert result.status == "success"
    assert result.metadata["confidence_interval_95"] is not None


def test_shared_service_preserves_descriptive_only_status():
    df = pd.DataFrame({
        "group": ["A", "A", "B"],
        "score": [1, 2, 3],
    })
    result = run_numeric_group_comparison_service(df, "group", "score")

    assert result.status == "descriptive_only"
    assert result.metadata["p_value"] is None
    assert result.tables["group_summaries"].shape[0] == 2
