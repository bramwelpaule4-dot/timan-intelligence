"""Multiple linear regression for a numeric outcome and numeric predictors."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def run_multiple_linear_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
) -> dict:
    """Fit an OLS model with two or more numeric predictors.

    Uses complete finite cases, rejects rank-deficient designs and reports
    conventional OLS uncertainty. No survey-design correction or causal
    interpretation is implied.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if not isinstance(predictor_variables, (list, tuple)) or len(predictor_variables) < 2:
        raise ValueError("Select at least two numeric predictor variables.")
    predictors = list(predictor_variables)
    if len(set(predictors)) != len(predictors):
        raise ValueError("Predictor variables must be unique.")
    if not isinstance(outcome_variable, str) or not outcome_variable.strip():
        raise ValueError("Provide a valid outcome variable.")
    if outcome_variable in predictors:
        raise ValueError("The outcome variable cannot also be a predictor.")
    variables = predictors + [outcome_variable]
    for variable in variables:
        if not isinstance(variable, str) or not variable.strip():
            raise ValueError("Provide valid variable names.")
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype) or pd.api.types.is_bool_dtype(df[variable].dtype):
            raise ValueError(
                f"Variable '{variable}' must be numeric. Confirm and convert "
                "text-coded numbers during data preparation."
            )
    if len(predictors) > 20:
        raise ValueError("Select no more than 20 predictors in this guided model.")

    numeric = df[variables].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric).all(axis=1)
    data = numeric.loc[finite].astype(float)
    n = int(len(data))
    excluded_n = int(len(df) - n)
    p = len(predictors)
    residual_df = n - p - 1
    if residual_df < 1:
        raise ValueError(
            f"Insufficient complete records: at least {p + 2} are required "
            f"for {p} predictors."
        )
    x_values = data[predictors].to_numpy(dtype=float)
    y = data[outcome_variable].to_numpy(dtype=float)
    if np.unique(y).size < 2:
        raise ValueError("The outcome must vary to estimate model fit.")
    design = np.column_stack([np.ones(n), x_values])
    coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank < p + 1:
        raise ValueError(
            "The selected predictors are perfectly or near-perfectly collinear. "
            "Remove or reconsider redundant predictors."
        )
    fitted = design @ coefficients
    residuals = y - fitted
    sse = float(residuals @ residuals)
    y_mean = float(np.mean(y))
    sst = float(np.sum((y - y_mean) ** 2))
    if sst <= 0:
        raise ValueError("The outcome has no variation; model fit is undefined.")
    r_squared = float(np.clip(1 - sse / sst, 0, 1))
    adjusted_r_squared = float(1 - (1 - r_squared) * (n - 1) / residual_df)
    mse = sse / residual_df
    rmse = float(np.sqrt(sse / n))
    residual_standard_error = float(np.sqrt(mse))
    xtx_inverse = np.linalg.inv(design.T @ design)
    covariance = mse * xtx_inverse
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    t_statistics = coefficients / standard_errors
    p_values = 2 * stats.t.sf(np.abs(t_statistics), residual_df)
    critical = float(stats.t.ppf(0.975, residual_df))
    lower = coefficients - critical * standard_errors
    upper = coefficients + critical * standard_errors

    model_df = p
    explained_ss = max(0.0, sst - sse)
    if sse <= np.finfo(float).eps * max(sst, 1.0):
        f_statistic = float("inf")
        model_p_value = 0.0
    else:
        f_statistic = float((explained_ss / model_df) / mse)
        model_p_value = float(stats.f.sf(f_statistic, model_df, residual_df))

    coefficient_rows = [{
        "Variable": "Intercept",
        "Estimate": float(coefficients[0]),
        "Standard error": float(standard_errors[0]),
        "t statistic": float(t_statistics[0]),
        "p-value": float(p_values[0]),
        "95% CI lower": float(lower[0]),
        "95% CI upper": float(upper[0]),
    }]
    for index, variable in enumerate(predictors, start=1):
        coefficient_rows.append({
            "Variable": variable,
            "Estimate": float(coefficients[index]),
            "Standard error": float(standard_errors[index]),
            "t statistic": float(t_statistics[index]),
            "p-value": float(p_values[index]),
            "95% CI lower": float(lower[index]),
            "95% CI upper": float(upper[index]),
        })

    fitted_data = data.copy()
    fitted_data["Fitted outcome"] = fitted
    fitted_data["Residual"] = residuals
    fitted_data = fitted_data.sort_values(outcome_variable, kind="stable").reset_index(drop=True)

    warnings = [
        "This is an observational OLS model. Coefficients are adjusted associations conditional on the other included predictors; they do not establish causation.",
        "Assess linearity, independent errors, constant residual variance, influential observations and residual distribution before relying on conventional inference.",
        "The model uses unweighted complete records and does not adjust for survey weights, clustering, repeated measures or complex sample design.",
        "Check multicollinearity and omitted-variable bias. Including more predictors does not automatically improve the validity of a model.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because one or more selected "
            "variables were missing or non-finite."
        )
    if n < max(30, 10 * (p + 1)):
        warnings.append(
            "The sample is small relative to the number of estimated parameters. "
            "Coefficient estimates may be unstable; interpret inference cautiously."
        )
    return {
        "coefficients": pd.DataFrame(coefficient_rows),
        "fitted_data": fitted_data,
        "findings": [
            f"The model used {n:,} complete records, estimated {p:,} predictors and excluded {excluded_n:,} records.",
            f"The model explains {r_squared * 100:.2f}% of observed outcome variation (R²); adjusted R² is {adjusted_r_squared:.4f}.",
            f"Overall model F({model_df}, {residual_df}) = {f_statistic:.4g}; p = {model_p_value:.4g}.",
        ],
        "warnings": warnings,
        "metadata": {
            "predictor_variables": predictors,
            "outcome_variable": outcome_variable,
            "total_records": int(len(df)),
            "valid_n": n,
            "excluded_n": excluded_n,
            "predictor_count": p,
            "residual_degrees_freedom": residual_df,
            "r_squared": r_squared,
            "adjusted_r_squared": adjusted_r_squared,
            "rmse": rmse,
            "residual_standard_error": residual_standard_error,
            "model_f_statistic": f_statistic,
            "model_p_value": model_p_value,
            "test_status": "tested",
        },
    }
