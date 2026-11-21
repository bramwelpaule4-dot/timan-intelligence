"""Heuristic recognition and non-destructive profiling for questionnaire datasets.

Recognition is advisory: it never changes data or asserts that a dataset is a
probability sample. Sampling-design metadata must be supplied and validated
separately before population inference is attempted.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


QUESTION_HINTS = re.compile(
    r"(^q\d+|question|response|respondent|answer|likert|satisfaction|"
    r"agree|disagree|rating|frequency|sex|gender|age|ward|county|"
    r"education|occupation|household|consent|indicator)",
    re.IGNORECASE,
)
ID_HINTS = re.compile(
    r"(^id$|_id$|^id_|respondent|enumerator|submission|instance|uuid|"
    r"serial|record|household.?number)",
    re.IGNORECASE,
)
LIKERT_LABELS = {
    "strongly disagree", "disagree", "neutral", "agree",
    "strongly agree", "very dissatisfied", "dissatisfied",
    "satisfied", "very satisfied", "never", "rarely", "sometimes",
    "often", "always",
}


def _nonblank(series: pd.Series) -> pd.Series:
    values = series.dropna()
    if values.empty:
        return values
    return values[values.astype(str).str.strip().ne("")]


def _is_delimited_multi_response(series: pd.Series) -> bool:
    values = _nonblank(series)
    if len(values) < 2:
        return False
    text = values.astype(str)
    delimiter_rows = text.str.contains(r"[;,|\\r\\n]", regex=True)
    return bool(delimiter_rows.mean() >= 0.25 and text[delimiter_rows].nunique() >= 1)


def _classify_column(name: Any, series: pd.Series) -> dict[str, Any]:
    values = _nonblank(series)
    unique_count = int(values.nunique()) if len(values) else 0
    label = str(name)
    lower_values = {
        str(value).strip().casefold()
        for value in values.drop_duplicates().head(30).tolist()
    }

    if _is_delimited_multi_response(series):
        kind = "multiple_response"
        reason = "Values contain repeated delimited selections."
    elif lower_values and lower_values.issubset(LIKERT_LABELS) and len(lower_values) >= 2:
        kind = "likert_item"
        reason = "Observed labels match a recognised ordered response scale."
    elif pd.api.types.is_bool_dtype(series) or (
        unique_count == 2 and lower_values.issubset(
            {"0", "1", "true", "false", "yes", "no", "y", "n"}
        )
    ):
        kind = "binary"
        reason = "Two response states were observed."
    elif pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(values, errors="coerce").dropna()
        integer_like = len(numeric) > 0 and bool((numeric % 1 == 0).all())
        if integer_like and 3 <= unique_count <= 7 and numeric.min() >= 1 and numeric.max() <= 7:
            kind = "possible_likert_numeric"
            reason = "Integer responses fall within a common 1–7 scale; confirm the questionnaire codebook."
        else:
            kind = "numeric"
            reason = "Numeric responses detected; measurement meaning requires confirmation."
    else:
        kind = "categorical"
        reason = "Non-numeric response categories detected."

    return {
        "column": label,
        "type": kind,
        "non_missing": int(len(values)),
        "missing": int(len(series) - len(values)),
        "missing_percent": round(float((len(series) - len(values)) / len(series) * 100), 2) if len(series) else 0.0,
        "unique_responses": unique_count,
        "reason": reason,
        "question_name_hint": bool(QUESTION_HINTS.search(label)),
        "identifier_name_hint": bool(ID_HINTS.search(label)),
    }


def profile_survey_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Recognise likely questionnaire structure and profile each response column."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if df.empty or len(df.columns) == 0:
        return {
            "is_survey_like": False,
            "confidence": "low",
            "respondents": int(len(df)),
            "question_count": 0,
            "columns": [],
            "warnings": ["The dataset has no usable rows or columns."],
        }

    columns = [_classify_column(name, df[name]) for name in df.columns]
    question_candidates = [
        item for item in columns
        if item["type"] not in {"numeric"} and not item["identifier_name_hint"]
    ]
    hinted_questions = [item for item in columns if item["question_name_hint"]]
    response_columns = [
        item for item in columns
        if item["type"] in {
            "categorical", "binary", "likert_item",
            "possible_likert_numeric", "multiple_response",
        }
        and not item["identifier_name_hint"]
    ]

    # A dataset is only labelled survey-like when there is evidence of
    # respondent-level categorical/response fields or questionnaire naming.
    score = 0
    score += min(len(response_columns), 4) * 2
    score += min(len(hinted_questions), 3) * 2
    score += 2 if any(item["identifier_name_hint"] for item in columns) else 0
    survey_like = score >= 4 and len(df) >= 1
    confidence = "high" if score >= 10 else "moderate" if score >= 6 else "low"

    warnings = [
        "Recognition is heuristic and should be confirmed against the questionnaire and codebook.",
        "Each row is treated as one record for profiling; respondent uniqueness is not verified.",
        "Missing-response percentages are calculated per column among imported records.",
        "Frequencies and percentages describe the observed dataset and are unweighted.",
        "No population-representative estimate or design-adjusted standard error is produced.",
    ]
    if any(item["type"] == "possible_likert_numeric" for item in columns):
        warnings.append(
            "Possible numeric Likert items require confirmation of scale direction, labels and valid range."
        )
    if any(item["type"] == "multiple_response" for item in columns):
        warnings.append(
            "Delimited multiple-response fields are expanded into option-level counts; verify that the detected delimiters match the questionnaire export format."
        )

    return {
        "is_survey_like": survey_like,
        "confidence": confidence,
        "recognition_score": score,
        "respondents": int(len(df)),
        "variable_count": int(len(df.columns)),
        "question_count": int(len(response_columns)),
        "identifier_candidates": [
            item["column"] for item in columns if item["identifier_name_hint"]
        ],
        "question_name_candidates": [
            item["column"] for item in hinted_questions
        ],
        "response_type_counts": pd.Series(
            [item["type"] for item in columns], dtype="object"
        ).value_counts().to_dict(),
        "columns": columns,
        "warnings": warnings,
    }


def question_frequency_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return unweighted response frequencies, including nonresponse explicitly."""
    if column not in df.columns:
        raise KeyError(f"Column '{column}' was not found.")
    values = df[column]
    cleaned = values.astype("object").where(values.notna(), pd.NA)
    cleaned = cleaned.map(
        lambda value: value.strip() if isinstance(value, str) else value
    )
    cleaned = cleaned.replace("", pd.NA)
    counts = cleaned.value_counts(dropna=False)
    denominator = int(len(df))
    result = counts.rename_axis("response").reset_index(name="count")
    result["percent_of_records"] = (
        (result["count"] / denominator * 100).round(2) if denominator else 0.0
    )
    result["response"] = result["response"].map(
        lambda value: "No response" if pd.isna(value) else str(value)
    )
    return result


def multiple_response_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Count delimited selections; percentages use respondents with >=1 selection.

    A respondent selecting multiple options contributes once to each selected
    option. Therefore option percentages can sum to more than 100 percent.
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' was not found.")
    selections = []
    respondents_with_selection = 0
    for value in df[column].dropna():
        if not str(value).strip():
            continue
        options = [
            option.strip() for option in re.split(r"[;,|\\n]+", str(value))
            if option.strip()
        ]
        if options:
            respondents_with_selection += 1
            selections.extend(dict.fromkeys(options))

    if not selections:
        return pd.DataFrame(
            columns=["option", "respondent_count", "percent_of_respondents"]
        )

    counts = pd.Series(selections, dtype="object").value_counts()
    result = counts.rename_axis("option").reset_index(name="respondent_count")
    result["percent_of_respondents"] = (
        (result["respondent_count"] / respondents_with_selection * 100).round(2)
        if respondents_with_selection else 0.0
    )
    result.attrs["respondents_with_selection"] = respondents_with_selection
    result.attrs["total_records"] = int(len(df))
    return result
