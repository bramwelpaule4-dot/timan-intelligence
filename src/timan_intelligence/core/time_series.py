"""Guarded univariate non-seasonal ARIMA time-series modelling."""
from __future__ import annotations

from typing import Any
import warnings

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss

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
) -> AnalysisResult:
    """Decompose a regular univariate time series into trend, seasonal and remainder."""
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
    decomposition = pd.DataFrame({
        time_variable: dates,
        "observed": observed,
        "trend": trend,
        "seasonal": seasonal,
        "remainder": remainder,
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
    }])
    findings = [
        f"STL decomposed {len(values):,} observations at frequency {frequency} using seasonal period {period}.",
        f"Descriptive trend strength is {trend_strength:.3f}; seasonal strength is {seasonal_strength:.3f}.",
        "Review the component plot and remainder pattern; component strengths are descriptive summaries, not significance tests.",
    ]
    limitations = [
        "STL is an additive descriptive decomposition, not a forecasting model or inferential test.",
        "The selected seasonal period is analyst-specified and should match the actual calendar cycle.",
        "Only one seasonal period is modelled; multiple or evolving seasonal cycles may require other methods.",
        "A regular unique time index and complete finite observations are required; no missing-period imputation is performed.",
        "Trend and seasonal strength values are descriptive diagnostics and do not have inferential p-values or confidence intervals.",
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
