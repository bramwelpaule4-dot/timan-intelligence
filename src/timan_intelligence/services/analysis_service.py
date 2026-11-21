"""Shared orchestration entry points used by the web and desktop interfaces."""

import pandas as pd

from timan_intelligence.core.contracts import AnalysisResult, AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe
from timan_intelligence.core.survey_profiler import profile_survey_dataframe
from timan_intelligence.modules.descriptive import numeric_summary, frequency_table


def run_data_quality(df: pd.DataFrame) -> AnalysisResult:
    profile = profile_dataframe(df)
    return AnalysisResult(
        title="Data quality profile",
        method="Deterministic data profiling",
        tables={"column_profiles": pd.DataFrame(profile["column_profiles"])},
        findings=[
            f"Dataset contains {profile['rows']:,} rows and {profile['columns']:,} columns.",
            f"{profile['missing_cells']:,} missing cells ({profile['missing_percent']}% of all cells).",
            f"{profile['duplicate_rows']:,} fully duplicated rows detected; none were removed.",
        ],
        limitations=profile["warnings"],
        metadata={"rows": profile["rows"], "columns": profile["columns"]},
    )


def run_survey_profile(df: pd.DataFrame) -> AnalysisResult:
    """Recognise and profile questionnaire-style data without modifying it."""
    profile = profile_survey_dataframe(df)
    status = "success" if profile["is_survey_like"] else "needs_input"
    findings = [
        (
            "Questionnaire-style response structure detected "
            f"({profile['confidence']} confidence)."
            if profile["is_survey_like"]
            else "The dataset does not yet show enough evidence of questionnaire-style structure."
        ),
        f"{profile['respondents']:,} records and {profile.get('variable_count', 0):,} variables inspected.",
        f"{profile['question_count']:,} response-like variables identified.",
    ]
    if profile.get("identifier_candidates"):
        findings.append(
            "Possible respondent or record identifiers: "
            + ", ".join(profile["identifier_candidates"])
            + ". Confirm these against the data dictionary."
        )
    return AnalysisResult(
        title="Survey data recognition and profile",
        method="Heuristic questionnaire recognition and deterministic response profiling",
        status=status,
        tables={"response_variable_profile": pd.DataFrame(profile["columns"])},
        findings=findings,
        limitations=profile["warnings"],
        metadata={
            "is_survey_like": profile["is_survey_like"],
            "confidence": profile["confidence"],
            "recognition_score": profile.get("recognition_score", 0),
            "respondents": profile["respondents"],
            "variable_count": profile.get("variable_count", 0),
            "question_count": profile["question_count"],
            "identifier_candidates": profile.get("identifier_candidates", []),
            "response_type_counts": profile.get("response_type_counts", {}),
        },
    )


def run_numeric_summary(df: pd.DataFrame, request: AnalysisRequest | None = None) -> AnalysisResult:
    summary = numeric_summary(df)
    if summary.empty:
        return AnalysisResult(
            title="Numeric summary",
            method="Descriptive statistics",
            status="needs_input",
            findings=["No numeric columns were detected. Check variable types or select a different analysis."],
        )
    return AnalysisResult(
        title="Numeric summary",
        method="Descriptive statistics",
        tables={"numeric_summary": summary},
        findings=[f"Summary statistics were calculated for {len(summary)} numeric variables."],
        limitations=["These are descriptive summaries; they do not account for survey weights or complex sampling design."],
    )


def run_frequency(df: pd.DataFrame, column: str) -> AnalysisResult:
    table = frequency_table(df, column)
    return AnalysisResult(
        title=f"Frequency distribution: {column}",
        method="Unweighted frequency distribution",
        tables={"frequency_table": table},
        findings=[f"Frequency distribution calculated for '{column}'."],
        limitations=["Percentages are unweighted unless a future survey-design module is explicitly used."],
    )
