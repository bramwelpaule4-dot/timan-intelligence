
"""Safe, deterministic statistical calculations for TimanStat.

This initial execution engine provides descriptive statistics only.
It does not execute arbitrary code or select inferential tests.
"""

from typing import Any

import pandas as pd

from timan_intelligence.core.contracts import AnalysisResult


def run_descriptive_statistics(
    df: pd.DataFrame,
    variable: str,
) -> AnalysisResult:
    """Calculate descriptive statistics for one numeric variable.

    Missing values are excluded from the calculations and reported.
    The original DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("Provide a valid variable name.")

    if variable not in df.columns:
        raise ValueError(
            f"Variable '{variable}' was not found in the dataset."
        )

    series = df[variable]
    non_missing = series.dropna()

    # Check for an entirely missing column before checking its data type.
    if non_missing.empty:
        raise ValueError(
            f"Variable '{variable}' contains no usable numeric observations."
        )

    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError(
            f"Variable '{variable}' must be numeric."
        )

    values = non_missing.astype(float)

    summary: dict[str, Any] = {
        "variable": variable,
        "observations": int(values.count()),
        "missing_values": int(series.isna().sum()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "standard_deviation": (
            float(values.std(ddof=1))
            if len(values) > 1
            else None
        ),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "q1": float(values.quantile(0.25)),
        "q3": float(values.quantile(0.75)),
    }

    assumptions = [
        "Missing values were excluded from the calculations.",
        "The standard deviation is the sample standard deviation.",
        "Descriptive statistics do not establish causation.",
    ]

    limitations = []

    if len(values) == 1:
        limitations.append(
            "Only one usable observation is available; "
            "sample standard deviation cannot be calculated."
        )

    return AnalysisResult(
        title=f"Descriptive statistics: {variable}",
        method="Descriptive statistics",
        status="success",
        tables={"summary": summary},
        findings=[
            f"{variable} has {len(values)} usable numeric observations.",
            f"The mean is {values.mean():.4g} and the median is "
            f"{values.median():.4g}.",
        ],
        assumptions=assumptions,
        limitations=limitations,
        metadata={
            "variable": variable,
            "observations": int(values.count()),
            "missing_values": int(series.isna().sum()),
        },
    )
