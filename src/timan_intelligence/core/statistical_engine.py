
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

    Missing and infinite values are excluded from calculations and
    counted separately. The original DataFrame is not modified.
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

    # Check entirely missing columns before validating their inferred dtype.
    if series.isna().all():
        raise ValueError(
            f"Variable '{variable}' contains no usable numeric observations."
        )

    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError(
            f"Variable '{variable}' must be numeric."
        )

    missing_values = int(series.isna().sum())

    # Remove missing values, then identify positive and negative infinity.
    non_missing = series.dropna().astype(float)
    infinite_mask = non_missing.isin(
        [float("inf"), float("-inf")]
    )
    infinite_values = int(infinite_mask.sum())

    # Retain only finite observations for statistical calculations.
    values = non_missing[~infinite_mask]

    if values.empty:
        raise ValueError(
            f"Variable '{variable}' contains no usable numeric observations."
        )

    observations = int(values.count())
    mean = float(values.mean())
    median = float(values.median())

    standard_deviation = (
        float(values.std(ddof=1))
        if observations > 1
        else None
    )

    summary: dict[str, Any] = {
        "variable": variable,
        "observations": observations,
        "missing_values": missing_values,
        "infinite_values": infinite_values,
        "mean": mean,
        "median": median,
        "standard_deviation": standard_deviation,
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "q1": float(values.quantile(0.25)),
        "q3": float(values.quantile(0.75)),
    }

    assumptions = [
        "Missing values were excluded from the calculations.",
        "Infinite values were excluded from the calculations.",
        "The standard deviation is the sample standard deviation.",
        "Descriptive statistics do not establish causation.",
    ]

    limitations = []

    if infinite_values > 0:
        limitations.append(
            f"{infinite_values} infinite value(s) were excluded "
            "from the calculations."
        )

    if observations == 1:
        limitations.append(
            "Only one usable observation is available; "
            "sample standard deviation cannot be calculated."
        )

    findings = [
        f"{variable} has {observations} usable numeric observations.",
        f"The mean is {mean:.4g} and the median is {median:.4g}.",
    ]

    if infinite_values > 0:
        findings.append(
            f"{infinite_values} infinite value(s) were excluded."
        )

    return AnalysisResult(
        title=f"Descriptive statistics: {variable}",
        method="Descriptive statistics",
        status="success",
        tables={"summary": summary},
        findings=findings,
        assumptions=assumptions,
        limitations=limitations,
        metadata={
            "variable": variable,
            "observations": observations,
            "missing_values": missing_values,
            "infinite_values": infinite_values,
        },
    )
