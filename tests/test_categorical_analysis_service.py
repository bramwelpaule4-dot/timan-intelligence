import pandas as pd

from timan_intelligence.services.analysis_service import run_categorical_comparison


def test_shared_service_exposes_categorical_tables_and_test_metadata():
    df = pd.DataFrame({
        "ward": ["North", "North", "South", "South", "East", "East"],
        "employment": ["Yes", "No", "Yes", "Yes", "No", "No"],
    })
    result = run_categorical_comparison(df, "ward", "employment")
    assert "observed_counts" in result.tables
    assert "row_percentages" in result.tables
    assert "column_percentages" in result.tables
    assert result.metadata["row_variable"] == "ward"
    assert result.metadata["column_variable"] == "employment"
    assert result.status in {"success", "descriptive_only"}
