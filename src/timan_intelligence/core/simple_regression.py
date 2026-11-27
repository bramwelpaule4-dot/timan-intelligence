"""Simple linear regression for a numeric outcome and one numeric predictor."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def run_simple_linear_regression(
    df: pd.DataFrame,
    predictor_variable: str,
    outcome_variable: str,
) -> dict:
    """Fit an ordinary least-squares model with one numeric predictor.

    This function reports coefficient uncertainty and basic fit diagnostics.
    It does not perform causal inference, covariate adjustment or survey-design
    correction. Model assumptions must be assessed from the residual diagnostics.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    for variable in (predictor_variable, outcome_variable):
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("Provide valid variable names.")
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype):
            raise ValueError(
                f"Variable '{variable}' must be numeric. Confirm and convert "
                "text-coded numbers during data preparation."
            )
    if predictor_variable == outcome_variable:
        raise ValueError("Choose different predictor and outcome variables.")

    predictor = pd.to_numeric(df[predictor_variable], errors="coerce")
    outcome = pd.to_numeric(df[outcome_variable], errors="coerce")
    finite = np.isfinite(predictor) & np.isfinite(outcome)
    paired = pd.DataFrame({
        "predictor": predictor.loc[finite].astype(float),
        "outcome": outcome.loc[finite].astype(float),
    })
    n = int(len(paired))
    excluded_n = int(len(df) - n)
    if n < 3:
        raise ValueError(
            "At least three complete finite records are required for simple linear regression."
        )
    x = paired["predictor"].to_numpy()
    y = paired["outcome"].to_numpy()
    if np.unique(x).size < 2:
        raise ValueError(
            "The predictor must vary. A constant predictor cannot estimate a slope."
        )
    if np.unique(y).size < 2:
        raise ValueError(
            "The outcome must vary to estimate model fit and inferential statistics."
        )

    fit = stats.linregress(x, y)
    slope = float(fit.slope)
    intercept = float(fit.intercept)
    fitted = intercept + slope * x
    residuals = y - fitted
    residual_df = n - 2
    residual_sum_squares = float(np.sum(residuals ** 2))
    total_sum_squares = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = float(1 - residual_sum_squares / total_sum_squares)
    r_squared = min(1.0, max(0.0, r_squared))
    cohen_f_squared = float(r_squared / (1.0 - r_squared)) if r_squared < 1.0 else float("inf")
    residual_standard_error = float(
        np.sqrt(residual_sum_squares / residual_df)
    )
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    slope_standard_error = float(fit.stderr)
    x_mean = float(np.mean(x))
    sxx = float(np.sum((x - x_mean) ** 2))
    intercept_standard_error = float(
        residual_standard_error * np.sqrt(1 / n + (x_mean ** 2) / sxx)
    )
    critical = float(stats.t.ppf(0.975, residual_df))
    slope_ci = [
        float(slope - critical * slope_standard_error),
        float(slope + critical * slope_standard_error),
    ]
    intercept_ci = [
        float(intercept - critical * intercept_standard_error),
        float(intercept + critical * intercept_standard_error),
    ]

    fitted_data = pd.DataFrame({
        predictor_variable: x,
        outcome_variable: y,
        "Fitted outcome": fitted,
        "Residual": residuals,
    }).sort_values(predictor_variable, kind="stable").reset_index(drop=True)

    warnings = [
        "This is a one-predictor ordinary least-squares model. It does not adjust for other variables or establish a causal effect.",
        "Assess linearity, independence of errors, constant residual variance, influential observations and residual distribution before relying on inference.",
        "The model uses unweighted complete records and does not adjust for survey weights, clustering, repeated measures or complex sample design.",
        "Use the model for interpolation within the observed predictor range. Extrapolation beyond that range may be unreliable.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because predictor or outcome "
            "values were missing or non-finite."
        )
    if n < 30:
        warnings.append(
            "The sample is relatively small; coefficient estimates and diagnostic "
            "checks may be unstable. Interpret inferential results cautiously."
        )

    return {
        "fitted_data": fitted_data,
        "findings": [
            f"The model used {n:,} complete records and excluded {excluded_n:,}.",
            f"Estimated equation: {outcome_variable} = {intercept:.4g} + ({slope:.4g} × {predictor_variable}).",
            f"The model explains {r_squared * 100:.2f}% of the observed variation in {outcome_variable} (R²); Cohen's f² is {cohen_f_squared:.4g}.",
        ],
        "warnings": warnings,
        "metadata": {
            "predictor_variable": predictor_variable,
            "outcome_variable": outcome_variable,
            "total_records": int(len(df)),
            "valid_n": n,
            "excluded_n": excluded_n,
            "intercept": intercept,
            "slope": slope,
            "intercept_standard_error": intercept_standard_error,
            "slope_standard_error": slope_standard_error,
            "intercept_confidence_interval_95": intercept_ci,
            "slope_confidence_interval_95": slope_ci,
            "r_squared": r_squared,
            "cohen_f_squared": cohen_f_squared,
            "effect_size_definition": "Cohen's f-squared = R-squared / (1 - R-squared); overall model effect size, not a causal effect.",
            "adjusted_r_squared": float(
                1 - (1 - r_squared) * (n - 1) / residual_df
            ),
            "rmse": rmse,
            "residual_standard_error": residual_standard_error,
            "residual_degrees_freedom": residual_df,
            "slope_p_value": float(fit.pvalue),
            "correlation": float(fit.rvalue),
            "predictor_minimum": float(np.min(x)),
            "predictor_maximum": float(np.max(x)),
            "test_status": "tested",
        },
    }
