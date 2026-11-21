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
    delimiter_rows = text.str.contains(r"[;,|\r\n]", regex=True)
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
            option.strip() for option in re.split(r"[;,|\r\n]+", str(value))
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


LIKERT_RESPONSE_ORDERS = (
    ("strongly disagree", "disagree", "neutral", "agree", "strongly agree"),
    ("very dissatisfied", "dissatisfied", "satisfied", "very satisfied"),
    ("never", "rarely", "sometimes", "often", "always"),
)


def likert_item_table(
    df: pd.DataFrame,
    column: str,
    response_order: list[Any] | tuple[Any, ...] | None = None,
) -> pd.DataFrame:
    """Summarise one ordinal Likert item without assuming a positive direction.

    Text labels are ordered only when they match a recognised response scale.
    Numeric or custom-coded responses require an explicit ordered list supplied
    from the questionnaire/codebook. Percentages among valid responses and
    among all imported records are both reported.
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' was not found.")

    raw = df[column]
    cleaned = raw.astype("object").where(raw.notna(), pd.NA)
    cleaned = cleaned.map(
        lambda value: value.strip() if isinstance(value, str) else value
    )
    cleaned = cleaned.replace("", pd.NA)
    observed = list(pd.unique(cleaned.dropna()))

    if response_order is None:
        if not observed or not all(isinstance(value, str) for value in observed):
            raise ValueError(
                "Numeric or custom-coded Likert responses require an explicit "
                "response_order from the questionnaire or codebook."
            )
        observed_normalised = {str(value).casefold() for value in observed}
        matching_orders = [
            order for order in LIKERT_RESPONSE_ORDERS
            if observed_normalised.issubset(set(order))
        ]
        if not matching_orders:
            raise ValueError(
                "The response labels do not match a recognised ordered scale. "
                "Supply response_order from the questionnaire or codebook."
            )
        order = list(min(matching_orders, key=len))
        label_lookup = {label.casefold(): label for label in order}
        cleaned = cleaned.map(
            lambda value: label_lookup.get(value.casefold(), value)
            if isinstance(value, str) else value
        )
    else:
        order = list(response_order)
        if not order or len(order) != len(set(order)):
            raise ValueError("response_order must contain unique ordered values.")
        unexpected = [value for value in observed if value not in order]
        if unexpected:
            raise ValueError(
                "Observed responses fall outside the confirmed response_order: "
                + ", ".join(map(str, unexpected[:10]))
            )

    valid = cleaned.dropna()
    valid_n = int(len(valid))
    total_n = int(len(df))
    counts = valid.value_counts().to_dict()
    records = []
    cumulative = 0.0
    for response in order:
        count = int(counts.get(response, 0))
        percent_valid = round(count / valid_n * 100, 2) if valid_n else 0.0
        cumulative = round(cumulative + percent_valid, 2)
        records.append({
            "response": response,
            "count": count,
            "percent_valid": percent_valid,
            "percent_of_records": round(count / total_n * 100, 2) if total_n else 0.0,
            "cumulative_percent_valid": cumulative,
        })

    missing_n = total_n - valid_n
    if missing_n:
        records.append({
            "response": "No response",
            "count": missing_n,
            "percent_valid": 0.0,
            "percent_of_records": round(missing_n / total_n * 100, 2) if total_n else 0.0,
            "cumulative_percent_valid": cumulative,
        })

    table = pd.DataFrame(records)
    ranked = valid.map({value: index for index, value in enumerate(order)})
    median_response = None
    mode_responses = []
    if valid_n:
        median_rank = float(ranked.median())
        median_index = int(median_rank // 1)
        if median_rank % 1:
            median_index = int(round(median_rank))
        median_response = order[median_index]
        max_count = max(counts.values())
        mode_responses = [value for value in order if counts.get(value, 0) == max_count]

    table.attrs.update({
        "valid_n": valid_n,
        "missing_n": missing_n,
        "total_records": total_n,
        "median_response": median_response,
        "mode_responses": mode_responses,
        "response_order": order,
        "scale_direction_assumed": False,
    })
    return table
