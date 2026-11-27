"""Guarded univariate non-seasonal ARIMA time-series modelling."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox

from timan_intelligence.core.contracts import AnalysisResult


def run_arima_time_series_model(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    order: tuple[int, int, int] | list[int] = (1, 1, 1),
    forecast_steps: int = 12,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Fit ARIMA(p,d,q), diagnose residuals and forecast a regular univariate series."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("ARIMA requires a numeric outcome variable.")
    if not isinstance(order, (tuple, list)) or len(order) != 3:
        raise ValueError("ARIMA order must contain exactly three integers: (p, d, q).")
    if any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) for value in order):
        raise TypeError("ARIMA order values must be integers.")
    p, d, q = (int(value) for value in order)
    if not (0 <= p <= 3 and 0 <= d <= 2 and 0 <= q <= 3) or p + q > 5:
        raise ValueError("ARIMA order is outside the supported range: p and q 0-3, d 0-2, and p+q no greater than 5.")
    if isinstance(forecast_steps, bool) or not isinstance(forecast_steps, (int, np.integer)):
        raise TypeError("forecast_steps must be an integer.")
    if not 1 <= int(forecast_steps) <= 100:
        raise ValueError("forecast_steps must be between 1 and 100.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    level = float(confidence_level)
    if not 0 < level < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique; aggregate duplicate time points before ARIMA.")
    order_index = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[order_index])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[order_index]
    if not np.isfinite(values).all():
        raise ValueError("ARIMA outcome values must be complete and finite; resolve missing or infinite values first.")
    if len(values) < 30:
        raise ValueError("At least 30 regularly spaced observations are required for ARIMA estimation.")
    frequency = pd.infer_freq(dates)
    if frequency is None:
        raise ValueError("The time index is not regularly spaced; provide a regular time series before ARIMA estimation.")

    series = pd.Series(values, index=dates, name=outcome_variable)
    model = ARIMA(
        series,
        order=(p, d, q),
        enforce_stationarity=True,
        enforce_invertibility=True,
    )
    fitted = model.fit()
    convergence = getattr(fitted, "mle_retvals", {}) or {}
    converged = bool(convergence.get("converged", True))
    if not converged:
        raise ValueError("ARIMA estimation did not converge; reconsider the order or inspect the series.")

    forecast_result = fitted.get_forecast(steps=int(forecast_steps))
    forecast_frame = forecast_result.summary_frame(alpha=1.0 - level).copy()
    future_index = pd.date_range(
        start=dates[-1], periods=int(forecast_steps) + 1, freq=frequency
    )[1:]
    forecast_frame.index = future_index
    forecast_frame.index.name = time_variable
    forecast_frame = forecast_frame.reset_index().rename(columns={
        "mean": "forecast",
        "mean_se": "forecast_standard_error",
        "mean_ci_lower": "prediction_interval_lower",
        "mean_ci_upper": "prediction_interval_upper",
    })

    params = pd.DataFrame({
        "parameter": fitted.param_names,
        "estimate": np.asarray(fitted.params, dtype=float),
        "standard_error": np.asarray(fitted.bse, dtype=float),
        "z_statistic": np.asarray(fitted.tvalues, dtype=float),
        "p_value": np.asarray(fitted.pvalues, dtype=float),
    })
    residuals = np.asarray(fitted.resid, dtype=float)
    residuals = residuals[np.isfinite(residuals)]
    diagnostic_lag = min(10, max(p + q + 1, len(residuals) // 5))
    diagnostic_lag = min(diagnostic_lag, len(residuals) - 1)
    ljung_box = acorr_ljungbox(
        residuals, lags=[diagnostic_lag], model_df=p + q, return_df=True
    )
    lb_q = float(ljung_box["lb_stat"].iloc[0])
    lb_p = float(ljung_box["lb_pvalue"].iloc[0])
    jb = jarque_bera(residuals)
    diagnostics = pd.DataFrame([
        {"diagnostic": "Ljung-Box Q", "statistic": lb_q, "p_value": lb_p,
         "interpretation": "Tests residual autocorrelation up to the selected lag; a small p-value suggests remaining serial dependence."},
        {"diagnostic": "Jarque-Bera", "statistic": float(jb.statistic), "p_value": float(jb.pvalue),
         "interpretation": "Tests residual normality; forecast intervals may be less reliable when residuals are strongly non-normal."},
        {"diagnostic": "Residual mean", "statistic": float(np.mean(residuals)), "p_value": np.nan,
         "interpretation": "Residual mean should be close to zero."},
        {"diagnostic": "Residual standard deviation", "statistic": float(np.std(residuals, ddof=1)), "p_value": np.nan,
         "interpretation": "Summarises the scale of in-sample innovations."},
    ])
    aic, bic = float(fitted.aic), float(fitted.bic)
    findings = [
        f"Fitted non-seasonal ARIMA({p},{d},{q}) to {len(values):,} regularly spaced observations ({frequency}).",
        f"Model information criteria: AIC={aic:.4g}; BIC={bic:.4g}.",
        f"Forecasted {int(forecast_steps)} future time point(s) with {level:.1%} model-based prediction intervals.",
        f"Ljung-Box residual autocorrelation test p-value: {lb_p:.4g}.",
    ]
    limitations = [
        "This is a non-seasonal univariate ARIMA model with no exogenous regressors or automatic order selection.",
        "The differencing order d is user-specified; stationarity and differencing choices must be assessed before interpreting the model.",
        "Prediction intervals are conditional on the selected model and do not include model-selection uncertainty.",
        "The model assumes a regular time index and complete outcome values; no missing-time or missing-outcome imputation is performed.",
        "Not adjusted for complex survey weights, clustering, stratification or multistage sampling.",
    ]
    return AnalysisResult(
        title=f"ARIMA({p},{d},{q}) time-series model: {outcome_variable}",
        method=f"Non-seasonal ARIMA({p},{d},{q})",
        status="success",
        tables={
            "parameter_estimates": params,
            "forecasts": forecast_frame,
            "residual_diagnostics": diagnostics,
        },
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The selected ARIMA order adequately represents the temporal dependence after differencing.",
            "The fitted model has converged and residual diagnostics are reviewed.",
            "Forecasts extrapolate the fitted univariate process without external predictors.",
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "order": (p, d, q),
            "frequency": frequency,
            "start": dates[0].isoformat(),
            "end": dates[-1].isoformat(),
            "n_observations": int(len(values)),
            "forecast_steps": int(forecast_steps),
            "confidence_level": level,
            "aic": aic,
            "bic": bic,
            "log_likelihood": float(fitted.llf),
            "converged": converged,
            "ljung_box_p_value": lb_p,
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )
