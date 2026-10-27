"""Non-destructive data-quality profiling utilities."""

from typing import Any
import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Return a compact profile without changing the input DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())

    column_profiles = []
    for column in df.columns:
        series = df[column]
        non_missing = series.dropna()
        examples = [str(value)[:80] for value in non_missing.drop_duplicates().head(3).tolist()]
        column_profiles.append({
            "column": str(column),
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_percent": round(float(series.isna().mean() * 100), 2) if len(series) else 0.0,
            "unique_non_missing": int(series.nunique(dropna=True)),
            "examples": examples,
        })

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_cells": missing_cells,
        "missing_percent": round(missing_cells / total_cells * 100, 2) if total_cells else 0.0,
        "duplicate_rows": int(df.duplicated().sum()) if len(df) else 0,
        "column_profiles": column_profiles,
        "warnings": [
            "Duplicate rows are flagged, not removed.",
            "Missing values are reported, not imputed.",
            "Potential outliers and category inconsistencies require additional rules and review.",
        ],
    }
