import pandas as pd

from timan_intelligence.services.analysis_service import run_survey_weighting_service


def test_weighting_result_contains_audit_stage_diagnostics_and_specification():
    frame = pd.DataFrame({
        "pi": [0.5, 0.5, 0.5, 0.5],
        "response": [1, 0, 1, 1],
        "cell": ["A", "A", "B", "B"],
    })
    result = run_survey_weighting_service(
        frame, "pi", response_column="response", adjustment_cells=["cell"]
    )
    stages = result.tables["weight_stage_diagnostics"]
    assert stages["stage"].tolist() == ["base_weight", "nonresponse_adjusted_weight"]
    assert result.metadata["weighting_specification"]["records_in_input"] == 4
    assert result.metadata["weighting_specification"]["records_in_weighted_analysis"] == 3
    assert result.metadata["weighting_specification"]["records_with_zero_analysis_weight"] == 1
    assert result.metadata["stage_diagnostics"][0]["stage"] == "base_weight"
