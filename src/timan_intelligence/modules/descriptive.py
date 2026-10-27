"""Initial descriptive-statistics functions with deterministic outputs."""

import pandas as pd


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise numeric columns without modifying the input."""
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame(
            columns=["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
        )
    return numeric.describe().T.reset_index(names="variable")


def frequency_table(df: pd.DataFrame, column: str, include_missing: bool = True) -> pd.DataFrame:
    """Return counts and percentages for a categorical variable."""
    if column not in df.columns:
        raise KeyError(f"Column '{column}' was not found.")

    values = df[column]
    counts = values.value_counts(dropna=not include_missing)
    denominator = int(counts.sum())
    result = counts.rename_axis("category").reset_index(name="count")
    result["percent"] = (
        (result["count"] / denominator * 100).round(2) if denominator else 0.0
    )
    return result
