import pandas as pd
import pytest

from timan_intelligence.core.contracts import AnalysisResult
from timan_intelligence.services.survey_estimation_report import (
    generate_survey_estimation_pdf_report,
)


def _result(design="stratified_srs", domain=False):
    estimates = pd.DataFrame([{
        "estimand": "mean",
        "estimate": 24.5,
        "standard_error": 2.1,
        "confidence_level": 0.95,
        "ci_lower": 19.2,
        "ci_upper": 29.8,
        "domain_unweighted_n": 45 if domain else None,
    }])
    details = pd.DataFrame([
        {"stratum": "North", "sample_n": 20, "variance_contribution": 3.2},
        {"stratum": "South", "sample_n": 25, "variance_contribution": 1.2},
    ])
    metadata = {
        "estimand": "mean",
        "design": design,
        "outcome_variable": "income",
        "weight_variable": "analysis_weight",
        "variance_method": "Stratified SRS Taylor linearization",
        "degrees_of_freedom": 43,
        "records_used": 100,
    }
    if domain:
        metadata.update({
            "domain_variable": "county",
            "domain_value": "Turkana",
            "domain_unweighted_n": 45,
        })
    return AnalysisResult(
        title="Survey mean",
        method=metadata["variance_method"],
        status="success",
        tables={"estimates": estimates, "design_details": details},
        findings=["Estimated mean income is 24.5."],
        assumptions=["The sampling design was correctly specified."],
        limitations=["No finite population correction was applied."],
        metadata=metadata,
    )


def test_generate_survey_estimation_pdf_contains_expected_sections():
    pdf = generate_survey_estimation_pdf_report(
        _result(), project_name="Household Survey", prepared_by="Timan Analytics",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1500


def test_domain_report_identifies_subpopulation_and_descriptive_warning():
    result = _result("weighted_descriptive", domain=True)
    result.metadata["variance_method"] = "Not estimated"
    result.tables["estimates"]["standard_error"] = float("nan")
    result.tables["estimates"]["ci_lower"] = float("nan")
    result.tables["estimates"]["ci_upper"] = float("nan")
    pdf = generate_survey_estimation_pdf_report(result)
    assert len(pdf) > 1500


def test_report_rejects_missing_estimates_table():
    result = _result()
    result.tables["estimates"] = pd.DataFrame()
    with pytest.raises(ValueError, match="estimates table"):
        generate_survey_estimation_pdf_report(result)


def test_report_rejects_non_analysis_result():
    with pytest.raises(TypeError, match="AnalysisResult"):
        generate_survey_estimation_pdf_report({"estimates": pd.DataFrame([{"estimate": 1}])})
