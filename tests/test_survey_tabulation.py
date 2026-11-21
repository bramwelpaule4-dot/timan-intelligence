import pandas as pd
import pytest

from timan_intelligence.core.survey_profiler import (
    multiple_response_table,
    question_frequency_table,
    likert_item_table,
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


def test_likert_item_uses_ordered_labels_and_reports_valid_and_record_percentages():
    df = pd.DataFrame({
        "Q1_agreement": [
            "Agree", "Strongly agree", "Neutral", "Disagree",
            None, "  Agree  ", "",
        ]
    })

    table = likert_item_table(df, "Q1_agreement")
    rows = table.set_index("response")

    assert list(table["response"][:5]) == [
        "strongly disagree", "disagree", "neutral", "agree", "strongly agree"
    ]
    assert rows.loc["agree", "count"] == 2
    assert rows.loc["agree", "percent_valid"] == pytest.approx(40.0)
    assert rows.loc["agree", "percent_of_records"] == pytest.approx(28.57)
    assert rows.loc["No response", "count"] == 2
    assert table.attrs["valid_n"] == 5
    assert table.attrs["missing_n"] == 2
    assert table.attrs["median_response"] == "agree"
    assert table.attrs["scale_direction_assumed"] is False


def test_likert_numeric_codes_require_explicit_codebook_order():
    df = pd.DataFrame({"Q2_rating": [1, 2, 3, 4, 5, None]})

    with pytest.raises(ValueError, match="explicit response_order"):
        likert_item_table(df, "Q2_rating")

    table = likert_item_table(
        df, "Q2_rating", response_order=[1, 2, 3, 4, 5]
    )
    rows = table.set_index("response")
    assert rows.loc[1, "count"] == 1
    assert rows.loc[5, "count"] == 1
    assert table.attrs["median_response"] == 3


def test_likert_item_rejects_unrecognised_labels_without_codebook_order():
    df = pd.DataFrame({"Q3": ["Poor", "Fair", "Good", "Excellent"]})

    with pytest.raises(ValueError, match="do not match a recognised"):
        likert_item_table(df, "Q3")


def test_likert_item_rejects_values_outside_confirmed_response_order():
    df = pd.DataFrame({"Q4": [1, 2, 6]})

    with pytest.raises(ValueError, match="fall outside"):
        likert_item_table(df, "Q4", response_order=[1, 2, 3, 4, 5])


def test_survey_service_exposes_labelled_likert_item_analysis():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3, 4],
        "Q1_agreement": [
            "Agree", "Neutral", "Strongly agree", "Disagree"
        ],
    })

    result = run_survey_profile(df)

    assert result.metadata["likert_columns"] == ["Q1_agreement"]
    assert "likert::Q1_agreement" in result.tables

