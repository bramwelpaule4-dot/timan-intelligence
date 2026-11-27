"""Guarded univariate non-seasonal ARIMA time-series modelling."""
from __future__ import annotations

from typing import Any
import warnings

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf

from timan_intelligence.core.contracts import AnalysisResult


def run_arima_time_series_model(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    order: tuple[int, int, int] | list[int] = (1, 1, 1),
    forecast_steps: int = 12,
    confidence_level: float = 0.95,
    validation_steps: int = 0,
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
    if isinstance(validation_steps, bool) or not isinstance(validation_steps, (int, np.integer)):
        raise TypeError("validation_steps must be an integer.")
    if not 0 <= int(validation_steps) <= 100:
        raise ValueError("validation_steps must be between zero and 100.")
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
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced; provide a regular time series before ARIMA estimation.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    regular_index = pd.DatetimeIndex(dates, freq=frequency)

    series = pd.Series(values, index=regular_index, name=outcome_variable)
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

    validation_steps = int(validation_steps)
    validation_summary = pd.DataFrame()
    if validation_steps:
        if len(values) - validation_steps < 30:
            raise ValueError("Rolling-origin validation requires at least 30 training observations before the holdout period.")
        training_series = pd.Series(
            values[:-validation_steps],
            index=pd.DatetimeIndex(dates[:-validation_steps], freq=frequency),
            name=outcome_variable,
        )
        validation_model = ARIMA(
            training_series,
            order=(p, d, q),
            enforce_stationarity=True,
            enforce_invertibility=True,
        ).fit()
        validation_convergence = getattr(validation_model, "mle_retvals", {}) or {}
        if not bool(validation_convergence.get("converged", True)):
            raise ValueError("The ARIMA validation model did not converge; reconsider the order or holdout size.")
        validation_forecast = validation_model.get_forecast(steps=validation_steps)
        predicted = np.asarray(validation_forecast.predicted_mean, dtype=float)
        observed = np.asarray(values[-validation_steps:], dtype=float)
        errors = observed - predicted
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        nonzero_observed = np.abs(observed) > np.finfo(float).eps
        mape = float(np.mean(np.abs(errors[nonzero_observed] / observed[nonzero_observed])) * 100.0) if nonzero_observed.any() else np.nan
        validation_dates = dates[-validation_steps:]
        validation_summary = pd.DataFrame([{
            "holdout_observations": validation_steps,
            "training_observations": int(len(training_series)),
            "validation_start": validation_dates[0],
            "validation_end": validation_dates[-1],
            "mean_absolute_error": mae,
            "root_mean_squared_error": rmse,
            "mean_absolute_percentage_error": mape,
            "mape_denominator_excluded": int((~nonzero_observed).sum()),
        }])
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
        *([f"Rolling-origin holdout validation ({validation_steps} observations): MAE={mae:.4g}, RMSE={rmse:.4g}." ] if validation_steps else []),
        f"Ljung-Box residual autocorrelation test p-value: {lb_p:.4g}.",
    ]
    limitations = [
        "This is a non-seasonal univariate ARIMA model with no exogenous regressors or automatic order selection.",
        "The differencing order d is user-specified; stationarity and differencing choices must be assessed before interpreting the model.",
        "Prediction intervals are conditional on the selected model and do not include model-selection uncertainty.",
        "The model assumes a regular time index and complete outcome values; no missing-time or missing-outcome imputation is performed.",
        "Holdout validation, when requested, is a single terminal holdout rather than rolling-origin cross-validation; MAE and RMSE are scale-dependent and MAPE is omitted when all holdout actuals are zero.",
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
            **({"holdout_validation": validation_summary} if validation_steps else {}),
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
            "validation_steps": validation_steps,
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

def run_sarima_time_series_model(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    order: tuple[int, int, int] | list[int] = (1, 0, 0),
    seasonal_order: tuple[int, int, int, int] | list[int] = (1, 0, 0, 12),
    forecast_steps: int = 12,
    confidence_level: float = 0.95,
    validation_steps: int = 0,
) -> AnalysisResult:
    """Fit seasonal ARIMA (P,D,Q,s) plus non-seasonal ARIMA (p,d,q)."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("SARIMA requires a numeric outcome variable.")
    if not isinstance(order, (tuple, list)) or len(order) != 3:
        raise ValueError("Non-seasonal ARIMA order must contain exactly three integers: (p, d, q).")
    if not isinstance(seasonal_order, (tuple, list)) or len(seasonal_order) != 4:
        raise ValueError("Seasonal order must contain exactly four integers: (P, D, Q, s).")
    combined = list(order) + list(seasonal_order)
    if any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) for value in combined):
        raise TypeError("All non-seasonal and seasonal order values must be integers.")
    p, d, q = (int(value) for value in order)
    seasonal_p, seasonal_d, seasonal_q, seasonal_period = (int(value) for value in seasonal_order)
    if not (0 <= p <= 3 and 0 <= d <= 2 and 0 <= q <= 3 and p + q <= 5):
        raise ValueError("Non-seasonal order must satisfy p,q in 0-3, d in 0-2 and p+q no greater than 5.")
    if not (0 <= seasonal_p <= 2 and 0 <= seasonal_d <= 1 and 0 <= seasonal_q <= 2 and seasonal_period in range(2, 53)):
        raise ValueError("Seasonal order must satisfy P,Q in 0-2, D in 0-1 and seasonal period s in 2-52.")
    if seasonal_p + seasonal_q + p + q > 7:
        raise ValueError("Combined autoregressive and moving-average orders are too large for the guarded SARIMA implementation.")
    if isinstance(forecast_steps, bool) or not isinstance(forecast_steps, (int, np.integer)):
        raise TypeError("forecast_steps must be an integer.")
    if not 1 <= int(forecast_steps) <= 100:
        raise ValueError("forecast_steps must be between 1 and 100.")
    if isinstance(validation_steps, bool) or not isinstance(validation_steps, (int, np.integer)):
        raise TypeError("validation_steps must be an integer.")
    if not 0 <= int(validation_steps) <= 100:
        raise ValueError("validation_steps must be between zero and 100.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    level = float(confidence_level)
    if not 0 < level < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique; aggregate duplicate time points before SARIMA.")
    sorted_positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[sorted_positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[sorted_positions]
    if not np.isfinite(values).all():
        raise ValueError("SARIMA outcome values must be complete and finite; resolve missing or infinite values first.")
    minimum_n = max(30, 2 * seasonal_period)
    if len(values) < minimum_n:
        raise ValueError(f"At least {minimum_n} observations (30 and two seasonal cycles) are required for this SARIMA seasonal period.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced; provide a regular time series before SARIMA estimation.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    regular_index = pd.DatetimeIndex(dates, freq=frequency)
    series = pd.Series(values, index=regular_index, name=outcome_variable)
    validation_steps = int(validation_steps)
    validation_summary = pd.DataFrame()
    if validation_steps:
        if len(values) - validation_steps < minimum_n:
            raise ValueError(
                f"Rolling-origin validation requires at least {minimum_n} training observations "
                "before the holdout period."
            )
        training_series = pd.Series(
            values[:-validation_steps],
            index=pd.DatetimeIndex(dates[:-validation_steps], freq=frequency),
            name=outcome_variable,
        )
        validation_model = SARIMAX(
            training_series,
            order=(p, d, q),
            seasonal_order=(seasonal_p, seasonal_d, seasonal_q, seasonal_period),
            enforce_stationarity=True,
            enforce_invertibility=True,
            simple_differencing=False,
        ).fit(disp=False)
        validation_convergence = getattr(validation_model, "mle_retvals", {}) or {}
        if not bool(validation_convergence.get("converged", True)):
            raise ValueError("The SARIMA validation model did not converge; reconsider the selected orders or holdout size.")
        validation_forecast = validation_model.get_forecast(steps=validation_steps)
        predicted = np.asarray(validation_forecast.predicted_mean, dtype=float)
        observed = np.asarray(values[-validation_steps:], dtype=float)
        errors = observed - predicted
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        nonzero_observed = np.abs(observed) > np.finfo(float).eps
        mape = (
            float(np.mean(np.abs(errors[nonzero_observed] / observed[nonzero_observed])) * 100.0)
            if nonzero_observed.any() else np.nan
        )
        validation_dates = dates[-validation_steps:]
        validation_summary = pd.DataFrame([{
            "holdout_observations": validation_steps,
            "training_observations": int(len(training_series)),
            "validation_start": validation_dates[0],
            "validation_end": validation_dates[-1],
            "mean_absolute_error": mae,
            "root_mean_squared_error": rmse,
            "mean_absolute_percentage_error": mape,
            "mape_denominator_excluded": int((~nonzero_observed).sum()),
        }])

    model = SARIMAX(
        series,
        order=(p, d, q),
        seasonal_order=(seasonal_p, seasonal_d, seasonal_q, seasonal_period),
        enforce_stationarity=True,
        enforce_invertibility=True,
        simple_differencing=False,
    )
    fitted = model.fit(disp=False)
    convergence = getattr(fitted, "mle_retvals", {}) or {}
    converged = bool(convergence.get("converged", True))
    if not converged:
        raise ValueError("SARIMA estimation did not converge; reconsider the non-seasonal or seasonal order.")
    forecast_result = fitted.get_forecast(steps=int(forecast_steps))
    forecast_frame = forecast_result.summary_frame(alpha=1.0 - level).copy()
    future_index = pd.date_range(start=dates[-1], periods=int(forecast_steps) + 1, freq=frequency)[1:]
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
    model_df = p + q + seasonal_p + seasonal_q
    diagnostic_lag = min(10, max(model_df + 1, len(residuals) // 5))
    diagnostic_lag = min(diagnostic_lag, len(residuals) - 1)
    ljung_box = acorr_ljungbox(residuals, lags=[diagnostic_lag], model_df=model_df, return_df=True)
    lb_q, lb_p = float(ljung_box["lb_stat"].iloc[0]), float(ljung_box["lb_pvalue"].iloc[0])
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
    return AnalysisResult(
        title=f"SARIMA({p},{d},{q})({seasonal_p},{seasonal_d},{seasonal_q},{seasonal_period}) model: {outcome_variable}",
        method="Seasonal ARIMA (SARIMA)",
        status="success",
        tables={
            "parameter_estimates": params, "forecasts": forecast_frame,
            "residual_diagnostics": diagnostics,
            **({"holdout_validation": validation_summary} if validation_steps else {}),
        },
        findings=[
            f"Fitted SARIMA({p},{d},{q})({seasonal_p},{seasonal_d},{seasonal_q},{seasonal_period}) to {len(values):,} regularly spaced observations ({frequency}).",
            f"Model information criteria: AIC={aic:.4g}; BIC={bic:.4g}.",
            f"Forecasted {int(forecast_steps)} future time point(s) with {level:.1%} model-based prediction intervals.",
            *([f"Rolling-origin holdout validation ({validation_steps} observations): MAE={mae:.4g}, RMSE={rmse:.4g}."] if validation_steps else []),
            f"Ljung-Box residual autocorrelation test p-value: {lb_p:.4g}.",
        ],
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The seasonal period corresponds to the actual calendar frequency and recurring cycle.",
            "The selected non-seasonal and seasonal orders adequately represent temporal dependence.",
            "The fitted model has converged and residual diagnostics are reviewed.",
        ],
        limitations=[
            "Univariate seasonal ARIMA only; no exogenous regressors, automatic order selection, intervention terms or multiple seasonal periods.",
            "At least two seasonal cycles and complete finite outcome values are required; no missing-time or missing-outcome imputation is performed.",
            "Holdout validation, when requested, is a single terminal holdout rather than rolling-origin cross-validation; MAE and RMSE are scale-dependent and MAPE is omitted when all holdout actuals are zero.",
            "Prediction intervals are conditional on the selected model and do not account for model-selection uncertainty.",
            "Ljung-Box and Jarque-Bera tests are diagnostics, not automatic model-acceptance rules.",
            "Not adjusted for complex survey weights, clustering, stratification or multistage sampling.",
        ],
        metadata={
            "time_variable": time_variable, "outcome_variable": outcome_variable,
            "order": (p, d, q), "seasonal_order": (seasonal_p, seasonal_d, seasonal_q, seasonal_period),
            "frequency": frequency, "start": dates[0].isoformat(), "end": dates[-1].isoformat(),
            "n_observations": int(len(values)), "forecast_steps": int(forecast_steps),
            "validation_steps": validation_steps,
            "confidence_level": level, "aic": aic, "bic": bic,
            "log_likelihood": float(fitted.llf), "converged": converged,
            "ljung_box_p_value": lb_p, "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )


def run_stl_time_series_decomposition(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    seasonal_period: int = 12,
    robust: bool = True,
    outlier_threshold: float = 3.5,
) -> AnalysisResult:
    """Decompose a regular univariate time series and flag extreme STL remainders."""
    from statsmodels.tsa.seasonal import STL

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("STL decomposition requires a numeric outcome variable.")
    if isinstance(seasonal_period, bool) or not isinstance(seasonal_period, (int, np.integer)):
        raise TypeError("seasonal_period must be an integer.")
    period = int(seasonal_period)
    if not 2 <= period <= 52:
        raise ValueError("seasonal_period must be between 2 and 52.")
    if not isinstance(robust, bool):
        raise TypeError("robust must be a boolean.")
    if isinstance(outlier_threshold, bool) or not isinstance(outlier_threshold, (int, float)):
        raise TypeError("outlier_threshold must be numeric.")
    threshold = float(outlier_threshold)
    if not np.isfinite(threshold) or not 2.0 <= threshold <= 10.0:
        raise ValueError("outlier_threshold must be between 2 and 10.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique; aggregate duplicate time points before STL decomposition.")
    positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[positions]
    if not np.isfinite(values).all():
        raise ValueError("STL outcome values must be complete and finite; resolve missing or infinite values first.")
    minimum_n = max(30, 2 * period)
    if len(values) < minimum_n:
        raise ValueError(f"At least {minimum_n} observations (30 and two seasonal cycles) are required for this seasonal period.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced; provide a regular time series before STL decomposition.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    index = pd.DatetimeIndex(dates, freq=frequency)
    series = pd.Series(values, index=index, name=outcome_variable)
    fitted = STL(series, period=period, robust=robust).fit()

    trend = np.asarray(fitted.trend, dtype=float)
    seasonal = np.asarray(fitted.seasonal, dtype=float)
    remainder = np.asarray(fitted.resid, dtype=float)
    observed = np.asarray(series, dtype=float)

    def _strength(component: np.ndarray) -> float:
        denominator = float(np.var(component + remainder, ddof=1))
        if not np.isfinite(denominator) or denominator <= np.finfo(float).eps:
            return 0.0
        value = 1.0 - float(np.var(remainder, ddof=1)) / denominator
        return float(np.clip(value, 0.0, 1.0))

    trend_strength = _strength(trend)
    seasonal_strength = _strength(seasonal)
    remainder_median = float(np.median(remainder))
    remainder_mad = float(np.median(np.abs(remainder - remainder_median)))
    if remainder_mad > np.finfo(float).eps:
        robust_remainder_z = 0.6744897501960817 * (remainder - remainder_median) / remainder_mad
    else:
        robust_remainder_z = np.full(len(remainder), np.nan, dtype=float)
    remainder_outlier = np.isfinite(robust_remainder_z) & (np.abs(robust_remainder_z) > threshold)
    decomposition = pd.DataFrame({
        time_variable: dates,
        "observed": observed,
        "trend": trend,
        "seasonal": seasonal,
        "remainder": remainder,
        "robust_remainder_z": robust_remainder_z,
        "is_remainder_outlier": remainder_outlier,
    })
    summary = pd.DataFrame([{
        "observations": int(len(values)),
        "seasonal_period": period,
        "frequency": frequency,
        "robust_fitting": robust,
        "trend_strength": trend_strength,
        "seasonal_strength": seasonal_strength,
        "remainder_mean": float(np.mean(remainder)),
        "remainder_standard_deviation": float(np.std(remainder, ddof=1)),
        "remainder_mad": remainder_mad,
        "outlier_threshold": threshold,
        "remainder_outlier_count": int(remainder_outlier.sum()),
    }])
    findings = [
        f"STL decomposed {len(values):,} observations at frequency {frequency} using seasonal period {period}.",
        f"Descriptive trend strength is {trend_strength:.3f}; seasonal strength is {seasonal_strength:.3f}.",
        f"Flagged {int(remainder_outlier.sum())} unusually large STL remainder(s) using a robust MAD z-score threshold of {threshold:g}.",
        "Review flagged observations against source data and contextual events; these flags are screening signals, not automatic data errors.",
    ]
    limitations = [
        "STL is an additive descriptive decomposition, not a forecasting model or inferential test.",
        "The selected seasonal period is analyst-specified and should match the actual calendar cycle.",
        "Only one seasonal period is modelled; multiple or evolving seasonal cycles may require other methods.",
        "A regular unique time index and complete finite observations are required; no missing-period imputation is performed.",
        "Trend and seasonal strength values are descriptive diagnostics and do not have inferential p-values or confidence intervals.",
        "Remainder outlier flags use a median-absolute-deviation threshold; they are heuristic screening signals, not formal anomaly tests or proof of erroneous observations.",
        "If the remainder MAD is zero or numerically negligible, robust remainder z-scores are unavailable and no outliers are flagged.",
    ]
    return AnalysisResult(
        title=f"STL time-series decomposition: {outcome_variable}",
        method="Seasonal-Trend decomposition using LOESS (STL)",
        status="success",
        tables={"decomposition": decomposition, "summary": summary},
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The selected seasonal period represents a meaningful recurring cycle.",
            "An additive decomposition is informative for the observed series.",
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "seasonal_period": period,
            "frequency": frequency,
            "n_observations": int(len(values)),
            "robust": robust,
            "trend_strength": trend_strength,
            "seasonal_strength": seasonal_strength,
            "outlier_threshold": threshold,
            "remainder_outlier_count": int(remainder_outlier.sum()),
            "remainder_mad": remainder_mad,
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )


def run_stationarity_diagnostics(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    regression: str = "c",
    max_lag: int | None = None,
) -> AnalysisResult:
    """Run complementary ADF and KPSS tests on a regular univariate time series."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("Stationarity diagnostics require a numeric outcome variable.")
    if regression not in {"c", "ct"}:
        raise ValueError("regression must be 'c' (constant) or 'ct' (constant and linear trend).")
    if max_lag is not None:
        if isinstance(max_lag, bool) or not isinstance(max_lag, (int, np.integer)):
            raise TypeError("max_lag must be an integer or None.")
        if not 0 <= int(max_lag) <= 20:
            raise ValueError("max_lag must be between 0 and 20.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique.")
    positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[positions]
    if not np.isfinite(values).all():
        raise ValueError("Outcome values must be complete and finite; resolve missing or infinite values first.")
    if len(values) < 30:
        raise ValueError("At least 30 regularly spaced observations are required for stationarity diagnostics.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    if np.ptp(values) <= np.finfo(float).eps:
        raise ValueError("Stationarity tests are undefined for a constant series.")

    # The tests have complementary null hypotheses: ADF tests a unit root;
    # KPSS tests level or trend stationarity.
    adf_kwargs = {"regression": regression, "autolag": "AIC"}
    if max_lag is not None:
        adf_kwargs["maxlag"] = int(max_lag)
    try:
        adf_stat, adf_p, adf_lags, adf_nobs, adf_critical, _ = adfuller(values, **adf_kwargs)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            kpss_stat, kpss_p, kpss_lags, kpss_critical = kpss(
                values, regression=regression, nlags="auto"
            )
        kpss_warnings = [str(item.message) for item in captured]
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise ValueError(f"Stationarity diagnostics could not be estimated: {exc}") from exc

    results = pd.DataFrame([
        {
            "test": "Augmented Dickey-Fuller (ADF)",
            "null_hypothesis": "The series has a unit root (is non-stationary).",
            "alternative_hypothesis": "The series is stationary under the selected deterministic terms.",
            "statistic": float(adf_stat),
            "p_value": float(adf_p),
            "lags_used": int(adf_lags),
            "observations_used": int(adf_nobs),
            "critical_value_1_percent": float(adf_critical["1%"]),
            "critical_value_5_percent": float(adf_critical["5%"]),
            "critical_value_10_percent": float(adf_critical["10%"]),
        },
        {
            "test": "Kwiatkowski-Phillips-Schmidt-Shin (KPSS)",
            "null_hypothesis": "The series is level- or trend-stationary under the selected deterministic terms.",
            "alternative_hypothesis": "The series has a unit root (is non-stationary).",
            "statistic": float(kpss_stat),
            "p_value": float(kpss_p),
            "lags_used": int(kpss_lags),
            "observations_used": int(len(values)),
            "critical_value_1_percent": float(kpss_critical["1%"]),
            "critical_value_5_percent": float(kpss_critical["5%"]),
            "critical_value_10_percent": float(kpss_critical["10%"]),
        },
    ])
    findings = [
        f"ADF p-value={adf_p:.4g}; its null hypothesis is a unit root.",
        f"KPSS p-value={kpss_p:.4g}; its null hypothesis is stationarity.",
        "Interpret the two tests jointly: agreement can strengthen a conclusion, while disagreement may indicate near-unit-root behaviour, structural breaks, changing variance or misspecified deterministic terms.",
    ]
    limitations = [
        "ADF and KPSS have opposite null hypotheses; neither test alone proves stationarity or non-stationarity.",
        "Results depend on the selected deterministic terms and lag selection; structural breaks, outliers and changing variance can distort inference.",
        "P-values may be reported at table boundaries by the underlying implementation; interpret alongside test statistics and critical values.",
        "These are univariate time-series diagnostics, not forecasting models and not adjustments for complex survey designs.",
    ]
    if kpss_warnings:
        limitations.append("KPSS numerical warnings: " + " | ".join(kpss_warnings))
    return AnalysisResult(
        title=f"Stationarity diagnostics: {outcome_variable}",
        method="Augmented Dickey-Fuller and KPSS stationarity tests",
        status="success",
        tables={"stationarity_tests": results},
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The selected constant or constant-plus-trend deterministic specification is appropriate.",
            "The series is not constant and has sufficient observations for the asymptotic tests.",
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "frequency": frequency,
            "n_observations": int(len(values)),
            "regression": regression,
            "adf_max_lag": max_lag,
            "adf_lags_used": int(adf_lags),
            "kpss_lags_used": int(kpss_lags),
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )



def run_autocorrelation_diagnostics(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    nlags: int = 20,
    confidence_level: float = 0.95,
) -> AnalysisResult:
    """Return ACF/PACF estimates and Ljung-Box residual-dependence diagnostics."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("Autocorrelation diagnostics require a numeric outcome variable.")
    if isinstance(nlags, bool) or not isinstance(nlags, (int, np.integer)):
        raise TypeError("nlags must be an integer.")
    if not 1 <= int(nlags) <= 20:
        raise ValueError("nlags must be between 1 and 20.")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise TypeError("Confidence level must be numeric.")
    level = float(confidence_level)
    if not 0 < level < 1:
        raise ValueError("Confidence level must be greater than 0 and less than 1.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique.")
    positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[positions]
    if not np.isfinite(values).all():
        raise ValueError("Outcome values must be complete and finite; resolve missing or infinite values first.")
    if len(values) < 30:
        raise ValueError("At least 30 regularly spaced observations are required for autocorrelation diagnostics.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    if int(nlags) >= len(values) // 2:
        raise ValueError("nlags must be smaller than half the number of observations for PACF estimation.")
    if np.ptp(values) <= np.finfo(float).eps:
        raise ValueError("Autocorrelation diagnostics are undefined for a constant series.")

    centered = values - float(np.mean(values))
    alpha = 1.0 - level
    acf_values, acf_intervals = acf(
        centered, nlags=int(nlags), alpha=alpha, fft=True, missing="raise"
    )
    pacf_values, pacf_intervals = pacf(
        centered, nlags=int(nlags), alpha=alpha, method="ywm"
    )
    lag_table = pd.DataFrame({
        "lag": np.arange(int(nlags) + 1, dtype=int),
        "autocorrelation": np.asarray(acf_values, dtype=float),
        "acf_confidence_lower": np.asarray(acf_intervals[:, 0], dtype=float),
        "acf_confidence_upper": np.asarray(acf_intervals[:, 1], dtype=float),
        "partial_autocorrelation": np.asarray(pacf_values, dtype=float),
        "pacf_confidence_lower": np.asarray(pacf_intervals[:, 0], dtype=float),
        "pacf_confidence_upper": np.asarray(pacf_intervals[:, 1], dtype=float),
    })
    diagnostic_lags = sorted({min(5, int(nlags)), min(10, int(nlags)), int(nlags)})
    lb = acorr_ljungbox(centered, lags=diagnostic_lags, model_df=0, return_df=True)
    ljung_box = lb.rename_axis("lag").reset_index().rename(columns={
        "lb_stat": "ljung_box_q", "lb_pvalue": "p_value"
    })
    findings = [
        f"Computed ACF and PACF through lag {int(nlags)} for {len(values):,} regularly spaced observations.",
        f"Reported {level:.1%} confidence intervals for the ACF and PACF estimates.",
        "Ljung-Box tests assess the joint null of no autocorrelation through each reported lag; inspect the correlogram and p-values together.",
    ]
    limitations = [
        "ACF and PACF are sample diagnostics for model identification; confidence bands are approximate and do not select ARIMA/SARIMA orders automatically.",
        "Ljung-Box p-values depend on the selected lag range and are not a substitute for residual diagnostics after model fitting.",
        "Structural breaks, trends, seasonality and outliers can create apparent autocorrelation; assess stationarity and consider differencing or seasonal terms.",
        "The analysis is univariate and is not adjusted for complex survey weights, clustering or stratification.",
    ]
    return AnalysisResult(
        title=f"ACF/PACF diagnostics: {outcome_variable}",
        method="Autocorrelation and partial autocorrelation diagnostics",
        status="success",
        tables={"acf_pacf": lag_table, "ljung_box": ljung_box},
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The input series is complete, finite and has non-zero variation.",
            "The selected lag range is appropriate for the available sample size.",
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "frequency": frequency,
            "n_observations": int(len(values)),
            "nlags": int(nlags),
            "confidence_level": level,
            "ljung_box_lags": diagnostic_lags,
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )



def run_naive_forecast_benchmarks(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    forecast_steps: int = 12,
    seasonal_period: int | None = None,
    validation_steps: int = 0,
) -> AnalysisResult:
    """Produce naïve and optional seasonal-naïve point-forecast benchmarks."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("Naïve forecasting requires a numeric outcome variable.")
    for name, value, lower, upper in (
        ("forecast_steps", forecast_steps, 1, 100),
        ("validation_steps", validation_steps, 0, 100),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{name} must be an integer.")
        if not lower <= int(value) <= upper:
            raise ValueError(f"{name} must be between {lower} and {upper}.")
    if seasonal_period is not None:
        if isinstance(seasonal_period, bool) or not isinstance(seasonal_period, (int, np.integer)):
            raise TypeError("seasonal_period must be an integer or None.")
        if not 2 <= int(seasonal_period) <= 52:
            raise ValueError("seasonal_period must be between 2 and 52.")

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique.")
    positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[positions]
    if not np.isfinite(values).all():
        raise ValueError("Outcome values must be complete and finite; resolve missing or infinite values first.")
    if len(values) < 30:
        raise ValueError("At least 30 regularly spaced observations are required for forecasting benchmarks.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))

    validation_steps = int(validation_steps)
    if validation_steps and len(values) - validation_steps < 30:
        raise ValueError("Holdout validation requires at least 30 training observations.")
    if seasonal_period is not None:
        period = int(seasonal_period)
        training_n = len(values) - validation_steps
        if training_n < 2 * period:
            raise ValueError("At least two seasonal cycles are required in the training data.")
    else:
        period = None

    def _naive(train: np.ndarray, horizon: int) -> np.ndarray:
        return np.repeat(float(train[-1]), horizon)

    def _seasonal_naive(train: np.ndarray, horizon: int) -> np.ndarray:
        return np.resize(train[-period:], horizon).astype(float)

    future_dates = pd.date_range(
        start=dates[-1], periods=int(forecast_steps) + 1, freq=frequency
    )[1:]
    forecast_data: dict[str, Any] = {
        time_variable: future_dates,
        "naive_forecast": _naive(values, int(forecast_steps)),
    }
    if period is not None:
        forecast_data["seasonal_naive_forecast"] = _seasonal_naive(values, int(forecast_steps))
    forecasts = pd.DataFrame(forecast_data)

    validation = pd.DataFrame()
    if validation_steps:
        train = values[:-validation_steps]
        actual = values[-validation_steps:]
        methods = [("naive", _naive(train, validation_steps))]
        if period is not None:
            methods.append(("seasonal_naive", _seasonal_naive(train, validation_steps)))
        rows = []
        for method_name, predicted in methods:
            errors = actual - predicted
            rows.append({
                "benchmark": method_name,
                "training_observations": int(len(train)),
                "holdout_observations": int(validation_steps),
                "validation_start": dates[-validation_steps].isoformat(),
                "validation_end": dates[-1].isoformat(),
                "mean_absolute_error": float(np.mean(np.abs(errors))),
                "root_mean_squared_error": float(np.sqrt(np.mean(errors ** 2))),
            })
        validation = pd.DataFrame(rows)

    findings = [
        f"Generated naïve benchmark forecasts for {int(forecast_steps)} future time point(s) at frequency {frequency}.",
        *([f"Generated seasonal-naïve forecasts by repeating the last {period}-observation cycle."] if period is not None else []),
        *([f"Compared benchmark accuracy on a terminal holdout of {validation_steps} observations; the holdout was excluded from model construction."] if validation_steps else ["No holdout validation was requested; forecast accuracy has not been evaluated out of sample."]),
    ]
    limitations = [
        "Naïve forecasts assume the latest observed level persists; seasonal-naïve forecasts repeat the most recent seasonal cycle.",
        "These are transparent benchmark forecasts, not trend, explanatory or probabilistic models; no prediction intervals are produced.",
        "Holdout accuracy is based on a single terminal holdout and may not represent performance across different forecast origins or regimes.",
        "MAE and RMSE are scale-dependent; compare them on the same outcome and holdout window when benchmarking alternative models.",
        "The method is univariate and not adjusted for complex survey weights, clustering or stratification.",
    ]
    return AnalysisResult(
        title=f"Naïve forecasting benchmarks: {outcome_variable}",
        method="Naïve and seasonal-naïve forecasting benchmarks",
        status="success",
        tables={
            "forecasts": forecasts,
            **({"holdout_validation": validation} if validation_steps else {}),
        },
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The most recent observation is a meaningful baseline for the naïve forecast.",
            *([f"The specified seasonal period ({period}) represents a recurring cycle."] if period is not None else []),
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "frequency": frequency,
            "n_observations": int(len(values)),
            "forecast_steps": int(forecast_steps),
            "seasonal_period": period,
            "validation_steps": validation_steps,
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )



def run_exponential_smoothing_forecast(
    df: pd.DataFrame,
    time_variable: str,
    outcome_variable: str,
    forecast_steps: int = 12,
    trend: str | None = "add",
    seasonal: str | None = None,
    seasonal_period: int | None = None,
    damped_trend: bool = False,
    validation_steps: int = 0,
) -> AnalysisResult:
    """Fit a guarded Holt/Winters exponential-smoothing model and forecast."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if not isinstance(time_variable, str) or time_variable not in df.columns:
        raise ValueError("Select a valid time-index variable.")
    if not isinstance(outcome_variable, str) or outcome_variable not in df.columns:
        raise ValueError("Select a valid numeric outcome variable.")
    if time_variable == outcome_variable:
        raise ValueError("Time-index and outcome variables must be different.")
    if not pd.api.types.is_numeric_dtype(df[outcome_variable]):
        raise TypeError("Exponential smoothing requires a numeric outcome variable.")
    if trend not in {None, "add", "mul"}:
        raise ValueError("trend must be None, 'add' or 'mul'.")
    if seasonal not in {None, "add", "mul"}:
        raise ValueError("seasonal must be None, 'add' or 'mul'.")
    if isinstance(damped_trend, bool) is False:
        raise TypeError("damped_trend must be a boolean.")
    for name, value, lower, upper in (
        ("forecast_steps", forecast_steps, 1, 100),
        ("validation_steps", validation_steps, 0, 100),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{name} must be an integer.")
        if not lower <= int(value) <= upper:
            raise ValueError(f"{name} must be between {lower} and {upper}.")
    if damped_trend and trend is None:
        raise ValueError("damped_trend requires an additive or multiplicative trend.")
    if seasonal is None:
        if seasonal_period is not None:
            raise ValueError("seasonal_period can only be supplied when seasonal is 'add' or 'mul'.")
        period = None
    else:
        if isinstance(seasonal_period, bool) or not isinstance(seasonal_period, (int, np.integer)):
            raise TypeError("seasonal_period must be an integer when seasonal terms are requested.")
        if not 2 <= int(seasonal_period) <= 52:
            raise ValueError("seasonal_period must be between 2 and 52.")
        period = int(seasonal_period)

    dates = pd.to_datetime(df[time_variable], errors="coerce")
    if dates.isna().any():
        raise ValueError("Time-index values must be valid and complete.")
    if dates.duplicated().any():
        raise ValueError("Time-index values must be unique.")
    positions = np.argsort(dates.to_numpy())
    dates = pd.DatetimeIndex(dates.iloc[positions])
    values = pd.to_numeric(df[outcome_variable], errors="coerce").to_numpy(dtype=float)[positions]
    if not np.isfinite(values).all():
        raise ValueError("Outcome values must be complete and finite; resolve missing or infinite values first.")
    if len(values) < 30:
        raise ValueError("At least 30 regularly spaced observations are required for exponential smoothing.")
    inferred_frequency = pd.infer_freq(dates)
    if inferred_frequency is None:
        raise ValueError("The time index is not regularly spaced.")
    frequency = getattr(inferred_frequency, "freqstr", str(inferred_frequency))
    validation_steps = int(validation_steps)
    if validation_steps and len(values) - validation_steps < 30:
        raise ValueError("Holdout validation requires at least 30 training observations.")
    training_n = len(values) - validation_steps
    if period is not None and training_n < 2 * period:
        raise ValueError("At least two complete seasonal cycles are required in the training data.")
    if (trend == "mul" or seasonal == "mul") and np.any(values <= 0):
        raise ValueError("Multiplicative trend or seasonality requires strictly positive outcome values.")

    def _fit(series_values: np.ndarray):
        series_index = pd.DatetimeIndex(dates[:len(series_values)], freq=frequency)
        series = pd.Series(series_values, index=series_index, name=outcome_variable)
        model = ExponentialSmoothing(
            series,
            trend=trend,
            damped_trend=damped_trend if trend is not None else False,
            seasonal=seasonal,
            seasonal_periods=period,
            initialization_method="estimated",
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fitted_model = model.fit(optimized=True, remove_bias=False)
        return fitted_model, [str(item.message) for item in captured]

    validation = pd.DataFrame()
    if validation_steps:
        validation_model, validation_warnings = _fit(values[:-validation_steps])
        predicted = np.asarray(validation_model.forecast(validation_steps), dtype=float)
        actual = values[-validation_steps:]
        errors = actual - predicted
        validation = pd.DataFrame([{
            "training_observations": int(len(values) - validation_steps),
            "holdout_observations": int(validation_steps),
            "validation_start": dates[-validation_steps].isoformat(),
            "validation_end": dates[-1].isoformat(),
            "mean_absolute_error": float(np.mean(np.abs(errors))),
            "root_mean_squared_error": float(np.sqrt(np.mean(errors ** 2))),
        }])
    else:
        validation_warnings = []

    fitted, fit_warnings = _fit(values)
    forecast_values = np.asarray(fitted.forecast(int(forecast_steps)), dtype=float)
    future_dates = pd.date_range(
        start=dates[-1], periods=int(forecast_steps) + 1, freq=frequency
    )[1:]
    forecasts = pd.DataFrame({
        time_variable: future_dates,
        "forecast": forecast_values,
    })
    parameter_rows = []
    for name, value in fitted.params.items():
        if np.isscalar(value) and isinstance(value, (int, float, np.integer, np.floating)):
            parameter_rows.append({"parameter": name, "estimate": float(value)})
    parameters = pd.DataFrame(parameter_rows)
    summary = pd.DataFrame([{
        "trend": trend or "none",
        "seasonal": seasonal or "none",
        "seasonal_period": period,
        "damped_trend": bool(damped_trend),
        "observations": int(len(values)),
        "sse": float(fitted.sse),
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
    }])
    findings = [
        f"Fitted exponential smoothing with trend={trend or 'none'}, seasonality={seasonal or 'none'} to {len(values):,} observations.",
        f"Generated {int(forecast_steps)} point forecast(s); the model's in-sample SSE is {float(fitted.sse):.4g}.",
        *([f"Terminal holdout accuracy: MAE={float(validation.iloc[0]['mean_absolute_error']):.4g}, RMSE={float(validation.iloc[0]['root_mean_squared_error']):.4g}."] if validation_steps else ["No holdout validation was requested; out-of-sample accuracy has not been evaluated."]),
    ]
    limitations = [
        "Exponential-smoothing forecasts are conditional on the selected trend, seasonal and damping specification.",
        "This implementation reports point forecasts only; it does not currently provide prediction intervals.",
        "Holdout validation uses one terminal holdout rather than rolling-origin cross-validation.",
        "Multiplicative trend or seasonal components require strictly positive observations.",
        "The method is univariate and is not adjusted for complex survey weights, clustering or stratification.",
    ]
    warning_messages = list(dict.fromkeys(validation_warnings + fit_warnings))
    if warning_messages:
        limitations.append("Model-fitting warnings were raised: " + " | ".join(warning_messages))
    return AnalysisResult(
        title=f"Exponential-smoothing forecast: {outcome_variable}",
        method="Exponential smoothing (Holt/Holt-Winters)",
        status="success",
        tables={
            "forecasts": forecasts,
            "model_summary": summary,
            "parameter_estimates": parameters,
            **({"holdout_validation": validation} if validation_steps else {}),
        },
        findings=findings,
        assumptions=[
            "The time index is unique, ordered and regularly spaced.",
            "The chosen trend and seasonal components are appropriate for the series.",
            "The fitted smoothing parameters provide an adequate representation of level, trend and seasonality.",
        ],
        limitations=limitations,
        metadata={
            "time_variable": time_variable,
            "outcome_variable": outcome_variable,
            "frequency": frequency,
            "n_observations": int(len(values)),
            "forecast_steps": int(forecast_steps),
            "trend": trend,
            "seasonal": seasonal,
            "seasonal_period": period,
            "damped_trend": bool(damped_trend),
            "validation_steps": validation_steps,
            "sse": float(fitted.sse),
            "aic": float(fitted.aic),
            "bic": float(fitted.bic),
            "sampling_design_aware": False,
            "study_design": "time_series",
        },
    )
