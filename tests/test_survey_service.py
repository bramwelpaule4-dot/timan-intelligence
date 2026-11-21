import pandas as pd

from timan_intelligence.services.analysis_service import run_survey_profile


def test_survey_profile_service_returns_traceable_profile():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3],
        "Q1_gender": ["Female", "Male", "Female"],
        "Q2_rating": ["Agree", "Neutral", "Agree"],
    })

    result = run_survey_profile(df)

    assert result.status == "success"
    assert result.method.startswith("Heuristic questionnaire recognition")
    assert result.metadata["is_survey_like"] is True
    assert result.metadata["respondents"] == 3
    assert "response_variable_profile" in result.tables
    assert any("unweighted" in warning.lower() for warning in result.limitations)


def test_survey_profile_service_requests_review_for_general_numeric_data():
    result = run_survey_profile(
        pd.DataFrame({"height": [150, 160], "weight": [50, 60]})
    )

    assert result.status == "needs_input"
    assert result.metadata["is_survey_like"] is False
    assert result.tables["response_variable_profile"].shape[0] == 2
