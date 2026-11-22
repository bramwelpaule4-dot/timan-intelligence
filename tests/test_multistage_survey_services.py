import pandas as pd

from timan_intelligence.services.analysis_service import (
    run_two_stage_survey_design_inspection_service,
)


def test_two_stage_design_service_returns_shared_analysis_result():
    df = pd.DataFrame({
        "stratum": ["A"] * 8 + ["B"] * 8,
        "psu": [1] * 4 + [2] * 4 + [3] * 4 + [4] * 4,
        "ssu": [1, 1, 2, 2, 3, 3, 4, 4] * 2,
        "weight": [2.0] * 8 + [3.0] * 8,
    })
    result = run_two_stage_survey_design_inspection_service(
        df, "psu", "ssu", "weight", "stratum"
    )
    assert result.status == "success"
    assert "psu_summary" in result.tables
    assert "ssu_summary" in result.tables
    assert result.metadata["variance_estimation_available"] is False
    assert result.limitations
