import pandas as pd
import pytest

from timan_intelligence.core.survey_profiler import profile_survey_dataframe


def test_recognises_questionnaire_style_dataset_and_profiles_columns():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3, 4],
        "Q1_gender": ["Female", "Male", "Female", None],
        "Q2_satisfaction": [
            "Satisfied", "Neutral", "Very satisfied", "Satisfied"
        ],
        "monthly_income": [1000, 1500, 1200, 900],
    })

    profile = profile_survey_dataframe(df)

    assert profile["is_survey_like"] is True
    assert profile["respondents"] == 4
    assert profile["variable_count"] == 4
    assert profile["identifier_candidates"] == ["respondent_id"]
    assert profile["question_count"] == 2
    gender = next(item for item in profile["columns"] if item["column"] == "Q1_gender")
    assert gender["missing"] == 1
    assert gender["missing_percent"] == 25.0
    satisfaction = next(
        item for item in profile["columns"]
        if item["column"] == "Q2_satisfaction"
    )
    assert satisfaction["type"] == "likert_item"


def test_flags_numeric_likert_as_possible_and_not_confirmed():
    df = pd.DataFrame({"Q5_service_rating": [1, 2, 3, 4, 5, None]})
    profile = profile_survey_dataframe(df)
    item = profile["columns"][0]

    assert item["type"] == "possible_likert_numeric"
    assert any("require confirmation" in warning for warning in profile["warnings"])


def test_detects_delimited_multiple_response_field():
    df = pd.DataFrame({
        "Q6_services_used": ["Water; health", "Health; education", "Water; education"]
    })
    profile = profile_survey_dataframe(df)

    assert profile["columns"][0]["type"] == "multiple_response"
    assert not any("not yet expanded" in warning for warning in profile["warnings"])


def test_does_not_label_plain_numeric_dataset_as_survey():
    df = pd.DataFrame({"height": [150, 160, 170], "weight": [50, 60, 70]})
    profile = profile_survey_dataframe(df)

    assert profile["is_survey_like"] is False
    assert profile["confidence"] == "low"


def test_empty_dataset_returns_safe_profile():
    profile = profile_survey_dataframe(pd.DataFrame())

    assert profile["is_survey_like"] is False
    assert profile["respondents"] == 0
    assert profile["question_count"] == 0


def test_rejects_non_dataframe_input():
    with pytest.raises(TypeError):
        profile_survey_dataframe([{"Q1": "yes"}])
