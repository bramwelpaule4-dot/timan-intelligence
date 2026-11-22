"""Negative binomial regression (NB2) for overdispersed count outcomes.

The model uses a log link and estimates the NB2 dispersion parameter by
maximum likelihood. Numeric predictors and an optional log-exposure offset
are supported; complex survey designs and clustered/repeated observations
are not currently supported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln


def _negative_binomial_log_likelihood(y, mu, alpha):
    """NB2 log likelihood with Var(Y|X) = mu + alpha * mu**2."""
    size = 1.0 / alpha
    return float(np.sum(
        gammaln(y + size) - gammaln(size) - gammaln(y + 1)
        + size * (np.log(size) - np.log(size + mu))
        + y * (np.log(np.maximum(mu, 1e-300)) - np.log(size + mu))
    ))


def _fit_nb2(y, design, offset, initial_beta=None):
    n, columns = design.shape
    beta_start = (
        np.asarray(initial_beta, dtype=float)
        if initial_beta is not None
        else np.r_[np.log(max(float(y.sum() / np.exp(offset).sum()), 1e-8)),
                   np.zeros(columns - 1)]
    )
    start = np.r_[beta_start, np.log(0.5)]

    def negative_log_likelihood(parameters):
        beta = parameters[:-1]
        alpha = float(np.exp(np.clip(parameters[-1], -12, 8)))
        eta = np.clip(offset + design @ beta, -30, 30)
        mu = np.exp(eta)
        return -_negative_binomial_log_likelihood(y, mu, alpha)

    fit = minimize(
        negative_log_likelihood, start, method="L-BFGS-B",
        bounds=[(None, None)] * columns + [(-12, 8)],
        options={"maxiter": 3000, "ftol": 1e-12, "gtol": 1e-7},
    )
    beta = fit.x[:-1]
    alpha = float(np.exp(np.clip(fit.x[-1], -12, 8)))
    mu = np.exp(np.clip(offset + design @ beta, -30, 30))
    return fit, beta, alpha, mu, -float(fit.fun)


def run_negative_binomial_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    exposure_variable: str | None = None,
) -> dict:
    """Fit an NB2 log-link regression by maximum likelihood."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if not isinstance(predictor_variables, (list, tuple)) or not predictor_variables:
        raise ValueError("Select at least one numeric predictor variable.")
    predictors = list(predictor_variables)
    if len(set(predictors)) != len(predictors):
        raise ValueError("Predictor variables must be unique.")
    if len(predictors) > 15:
        raise ValueError("Select no more than 15 predictors in this guided model.")
    if outcome_variable not in df.columns:
        raise ValueError(f"Outcome variable '{outcome_variable}' was not found.")
    if outcome_variable in predictors or exposure_variable in predictors:
        raise ValueError("The outcome and exposure variables cannot also be predictors.")
    if exposure_variable == outcome_variable:
        raise ValueError("The exposure variable cannot be the count outcome.")
    for variable in predictors:
        if variable not in df.columns:
            raise ValueError(f"Predictor variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype) or pd.api.types.is_bool_dtype(df[variable].dtype):
            raise ValueError(f"Predictor '{variable}' must be numeric.")
    if exposure_variable is not None and exposure_variable not in df.columns:
        raise ValueError(f"Exposure variable '{exposure_variable}' was not found.")

    y_raw = pd.to_numeric(df[outcome_variable], errors="coerce")
    x_frame = df[predictors].apply(pd.to_numeric, errors="coerce")
    exposure = (
        pd.to_numeric(df[exposure_variable], errors="coerce")
        if exposure_variable is not None else pd.Series(1.0, index=df.index)
    )
    valid = y_raw.notna() & np.isfinite(y_raw) & np.isfinite(x_frame).all(axis=1)
    valid &= exposure.notna() & np.isfinite(exposure) & (exposure > 0)
    y_check = y_raw.loc[valid].to_numpy(dtype=float)
    if np.any(y_check < 0) or not np.allclose(y_check, np.round(y_check), atol=1e-10):
        raise ValueError("The outcome must contain non-negative integer counts.")
    y = np.round(y_check).astype(int)
    x_frame = x_frame.loc[valid].astype(float)
    offset = np.log(exposure.loc[valid].to_numpy(dtype=float))
    n, p = x_frame.shape
    excluded_n = int(len(df) - n)
    if n <= p + 2:
        raise ValueError("Insufficient complete records for the selected predictors.")
    if y.sum() <= 0:
        raise ValueError("The count outcome is all zero; a negative binomial model cannot be estimated.")

    x = x_frame.to_numpy(dtype=float)
    means, scales = x.mean(axis=0), x.std(axis=0, ddof=0)
    if np.any(scales <= 1e-12):
        raise ValueError("A selected predictor is constant and cannot be estimated.")
    design = np.column_stack([np.ones(n), (x - means) / scales])
    if np.linalg.matrix_rank(design) < p + 1:
        raise ValueError("The selected predictors are perfectly or near-perfectly collinear.")

    fit, beta_std, alpha, mu, log_likelihood = _fit_nb2(y, design, offset)
    if not np.isfinite(log_likelihood) or not np.isfinite(mu).all():
        raise ValueError("The negative binomial optimiser returned non-finite estimates.")

    # Conditional expected-information covariance for beta, given estimated alpha.
    weights = mu / (1.0 + alpha * mu)
    covariance_std = np.linalg.pinv(design.T @ (weights[:, None] * design))
    transform = np.eye(p + 1)
    transform[0, 1:] = -means / scales
    transform[1:, 1:] = np.diag(1.0 / scales)
    beta_original = transform @ beta_std
    covariance = transform @ covariance_std @ transform.T
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    z_values = np.divide(beta_original, standard_errors, out=np.zeros_like(beta_original), where=standard_errors > 0)
    p_values = 2 * stats.norm.sf(np.abs(z_values))
    ci_low = beta_original - stats.norm.ppf(0.975) * standard_errors
    ci_high = beta_original + stats.norm.ppf(0.975) * standard_errors

    null_design = np.ones((n, 1))
    null_fit, _, null_alpha, null_mu, null_ll = _fit_nb2(y, null_design, offset)
    lr_stat = max(2.0 * (log_likelihood - null_ll), 0.0)
    lr_p = float(stats.chi2.sf(lr_stat, p))
    aic = 2 * (p + 2) - 2 * log_likelihood

    # Fit a Poisson reference model on exactly the same complete records.
    def poisson_nll(beta):
        eta = np.clip(offset + design @ beta, -30, 30)
        return float(np.sum(np.exp(eta) - y * eta + gammaln(y + 1)))
    poisson_start = np.r_[np.log(max(float(y.sum() / np.exp(offset).sum()), 1e-8)), np.zeros(p)]
    poisson_fit = minimize(poisson_nll, poisson_start, method="BFGS", options={"maxiter": 2000})
    poisson_ll = -float(poisson_fit.fun)
    poisson_aic = 2 * (p + 1) - 2 * poisson_ll

    names = ["Intercept"] + predictors
    coefficient_rows = []
    for index, name in enumerate(names):
        coefficient_rows.append({
            "Variable": name,
            "Coefficient": float(beta_original[index]),
            "Standard error": float(standard_errors[index]),
            "IRR": float(np.exp(np.clip(beta_original[index], -30, 30))),
            "IRR 95% CI lower": float(np.exp(np.clip(ci_low[index], -30, 30))),
            "IRR 95% CI upper": float(np.exp(np.clip(ci_high[index], -30, 30))),
            "z statistic": float(z_values[index]),
            "p-value": float(p_values[index]),
        })
    fitted = pd.DataFrame({
        "Observed count": y,
        "Predicted count": mu,
        "Pearson residual": (y - mu) / np.sqrt(np.maximum(mu + alpha * mu**2, 1e-12)),
    }, index=df.index[valid])

    findings = [
        f"The model used {n:,} complete records and excluded {excluded_n:,} records.",
        f"Estimated NB2 dispersion (alpha) was {alpha:.4g}; the conditional variance is mu + alpha × mu².",
        f"The likelihood-ratio test against the intercept-only negative binomial model was chi-square({p}) = {lr_stat:.3f}, p = {lr_p:.4g}.",
        f"Negative binomial AIC was {aic:.3f}; Poisson AIC on the same records was {poisson_aic:.3f}.",
    ]
    warnings = [
        "IRRs describe multiplicative associations in the expected count rate, not causal effects.",
        "The model uses the NB2 variance form Var(Y|X) = mu + alpha × mu². Other count-data structures may require a different model.",
        "The guided model supports numeric predictors only and does not adjust for survey weights, strata, clusters or repeated observations.",
        "Coefficient standard errors use the expected-information approximation conditional on the estimated dispersion parameter.",
    ]
    if alpha < 1e-5:
        warnings.insert(0, "The estimated dispersion is close to zero; the negative binomial model is approaching the Poisson limit.")
    if not fit.success:
        warnings.append("The optimiser did not report formal convergence; inspect estimates and diagnostics before interpretation.")
    metadata = {
        "valid_n": n, "excluded_n": excluded_n, "predictor_count": p,
        "predictors": predictors, "outcome_variable": outcome_variable,
        "exposure_variable": exposure_variable, "converged": bool(fit.success),
        "dispersion_alpha": alpha, "null_dispersion_alpha": null_alpha,
        "log_likelihood": log_likelihood, "aic": float(aic),
        "poisson_aic": float(poisson_aic),
        "aic_difference_poisson_minus_nb": float(poisson_aic - aic),
        "likelihood_ratio_chi_square": float(lr_stat),
        "model_p_value": lr_p, "null_log_likelihood": float(null_ll),
        "mean_observed_count": float(y.mean()), "mean_predicted_count": float(mu.mean()),
        "pearson_chi_square": float(np.sum((y - mu)**2 / np.maximum(mu + alpha * mu**2, 1e-12))),
        "residual_degrees_freedom": max(n - p - 1, 1),
        "null_model_converged": bool(null_fit.success),
        "poisson_model_converged": bool(poisson_fit.success),
    }
    return {
        "coefficients": pd.DataFrame(coefficient_rows),
        "fitted_data": fitted, "findings": findings,
        "warnings": warnings, "metadata": metadata,
    }
