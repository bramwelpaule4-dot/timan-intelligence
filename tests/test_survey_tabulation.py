import pandas as pd
import pytest

from timan_intelligence.core.survey_profiler import (
    multiple_response_table,
    question_frequency_table,
)
from timan_intelligence.services.analysis_service import run_survey_profile


def test_question_frequency_includes_missing_as_record_percentage():
    df = pd.DataFrame({"Q1": ["Yes", "No", None, "Yes", ""]})

    table = question_frequency_table(df, "Q1")
    rows = table.set_index("response")

    assert rows.loc["Yes", "count"] == 2
    assert rows.loc["Yes", "percent_of_records"] == pytest.approx(40.0)
    assert rows.loc["No response", "count"] == 2
    assert rows.loc["No response", "percent_of_records"] == pytest.approx(40.0)


def test_multiple_response_counts_each_option_once_per_respondent():
    df = pd.DataFrame({
        "Q2_services": [
            "Water; Health; Water",
            "Health; Education",
            None,
            "Water",
            "",
        ]
    })

    table = multiple_response_table(df, "Q2_services").set_index("option")

    assert table.loc["Water", "respondent_count"] == 2
    assert table.loc["Health", "respondent_count"] == 2
    assert table.loc["Education", "respondent_count"] == 1
    assert table.loc["Water", "percent_of_respondents"] == pytest.approx(66.67)


def test_multiple_response_handles_pipe_and_newline_delimiters():
    df = pd.DataFrame({"Q3": ["A|B", "B\nC"]})
    table = multiple_response_table(df, "Q3").set_index("option")

    assert table.loc["A", "respondent_count"] == 1
    assert table.loc["B", "respondent_count"] == 2
    assert table.loc["C", "respondent_count"] == 1


def test_service_exposes_question_and_multiple_response_tables():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3],
        "Q1_gender": ["Female", "Male", "Female"],
        "Q2_services": ["Water; Health", "Health", "Water; Education"],
    })

    result = run_survey_profile(df)

    assert "frequency::Q1_gender" in result.tables
    assert "multiple_response::Q2_services" in result.tables
    assert result.metadata["frequency_columns"] == ["Q1_gender"]
    assert result.metadata["multiple_response_columns"] == ["Q2_services"]


def test_frequency_and_multiple_response_reject_unknown_columns():
    df = pd.DataFrame({"Q1": ["Yes"]})

    with pytest.raises(KeyError):
        question_frequency_table(df, "missing")
    with pytest.raises(KeyError):
        multiple_response_table(df, "missing")
