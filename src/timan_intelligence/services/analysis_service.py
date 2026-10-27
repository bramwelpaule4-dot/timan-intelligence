"""Shared orchestration entry points used by the web and desktop interfaces."""

import pandas as pd

from timan_intelligence.core.contracts import AnalysisResult, AnalysisRequest
from timan_intelligence.core.data_quality import profile_dataframe
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
