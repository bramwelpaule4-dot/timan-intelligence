import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import run_survey_weighting_service
from timan_intelligence.services.survey_weighting_report import (
    generate_survey_weighting_pdf_report,
)


def test_survey_weighting_pdf_report_is_a_valid_pdf():
    frame = pd.DataFrame({
        "unit": ["u1", "u2", "u3", "u4"],
        "pi": [0.5, 0.25, 0.5, 1.0],
        "sex": ["F", "F", "M", "M"],
    })
    result = run_survey_weighting_service(
        frame, "pi",
        poststrata_column="sex",
        population_totals={"F": 60, "M": 40},
    )
    pdf = generate_survey_weighting_pdf_report(
        result, project_name="Household survey", prepared_by="M&E Unit"
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1500
    assert "weight_stage_diagnostics" in result.tables
    assert result.metadata["weighting_specification"]["poststratification_variable"] == "sex"


def test_survey_weighting_report_documents_nonresponse_and_raking():
    frame = pd.DataFrame({
        "pi": [0.5, 0.5, 0.5, 0.5],
        "response": [1, 0, 1, 1],
        "cell": ["A", "A", "B", "B"],
        "sex": ["F", "F", "M", "M"],
        "area": ["R", "U", "R", "U"],
    })
    result = run_survey_weighting_service(
        frame, "pi", response_column="response", adjustment_cells=["cell"],
        raking_margins={"area": {"R": 2.0, "U": 2.0}},
    )
    pdf = generate_survey_weighting_pdf_report(result)
    assert pdf.startswith(b"%PDF-")
    assert result.metadata["weighting_specification"]["response_column"] == "response"
    assert result.metadata["raking"]["converged"] is True


def test_survey_weighting_report_rejects_incomplete_result():
    class IncompleteResult:
        tables = {}
        metadata = {}

    with pytest.raises(ValueError, match="weighted dataset"):
        generate_survey_weighting_pdf_report(IncompleteResult())
