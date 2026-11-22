"""Poisson regression for non-negative count outcomes.

The guided implementation supports numeric predictors and an optional
positive exposure variable represented as a log offset. It does not adjust
for complex survey designs or clustered observations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln


def run_poisson_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    exposure_variable: str | None = None,
) -> dict:
    """Fit a log-link Poisson GLM by maximum likelihood."""
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
    if n <= p + 1:
        raise ValueError("Insufficient complete records for the selected predictors.")
    if y.sum() <= 0:
        raise ValueError("The count outcome is all zero; a Poisson model cannot be estimated.")
    x = x_frame.to_numpy(dtype=float)
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    if np.any(scales <= 1e-12):
        raise ValueError("A selected predictor is constant and cannot be estimated.")
    x_std = (x - means) / scales
    design = np.column_stack([np.ones(n), x_std])
    if np.linalg.matrix_rank(design) < p + 1:
        raise ValueError("The selected predictors are perfectly or near-perfectly collinear.")

    intercept_start = np.log(max(float(y.sum() / np.exp(offset).sum()), 1e-8))
    initial = np.r_[intercept_start, np.zeros(p)]

    def objective(beta):
        eta = np.clip(offset + design @ beta, -30, 30)
        mu = np.exp(eta)
        return float(np.sum(mu - y * eta + gammaln(y + 1)))

    fit = minimize(objective, initial, method="BFGS", options={"maxiter": 2000, "gtol": 1e-8})
    beta = fit.x
    eta = np.clip(offset + design @ beta, -30, 30)
    mu = np.exp(eta)
    information = design.T @ (mu[:, None] * design)
    covariance_std = np.linalg.pinv(information)
    # Transform estimates and covariance back to original predictor units.
    transform = np.eye(p + 1)
    transform[0, 1:] = -means / scales
    transform[1:, 1:] = np.diag(1.0 / scales)
    beta_original = transform @ beta
    covariance = transform @ covariance_std @ transform.T
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    z_values = np.divide(beta_original, standard_errors, out=np.zeros_like(beta_original), where=standard_errors > 0)
    p_values = 2 * stats.norm.sf(np.abs(z_values))
    ci_low = beta_original - stats.norm.ppf(0.975) * standard_errors
    ci_high = beta_original + stats.norm.ppf(0.975) * standard_errors

    null_rate = y.sum() / np.exp(offset).sum()
    null_mu = np.exp(offset) * null_rate
    def poisson_deviance(observed, expected):
        terms = expected - observed
        positive = observed > 0
        terms = terms.astype(float, copy=True)
        terms[positive] += observed[positive] * np.log(
            observed[positive] / expected[positive]
        )
        return float(2 * np.sum(terms))

    null_deviance = poisson_deviance(y, null_mu)
    fitted_deviance = poisson_deviance(y, mu)
    pearson_chi2 = float(np.sum((y - mu) ** 2 / np.maximum(mu, 1e-12)))
    residual_df = max(n - p - 1, 1)
    dispersion = pearson_chi2 / residual_df
    log_likelihood = -objective(beta)
    aic = 2 * (p + 1) - 2 * log_likelihood
    lr_stat = max(float(null_deviance - fitted_deviance), 0.0)
    lr_p = float(stats.chi2.sf(lr_stat, p))

    rows = []
    names = ["Intercept"] + predictors
    for index, name in enumerate(names):
        rows.append({
            "Variable": name,
            "Coefficient": float(beta_original[index]),
            "Standard error": float(standard_errors[index]),
            "IRR": float(np.exp(np.clip(beta[index], -30, 30))),
            "IRR 95% CI lower": float(np.exp(np.clip(ci_low[index], -30, 30))),
            "IRR 95% CI upper": float(np.exp(np.clip(ci_high[index], -30, 30))),
            "z statistic": float(z_values[index]),
            "p-value": float(p_values[index]),
        })
    fitted = pd.DataFrame({
        "Observed count": y,
        "Predicted count": mu,
        "Pearson residual": (y - mu) / np.sqrt(np.maximum(mu, 1e-12)),
    }, index=df.index[valid])
    findings = [
        f"The model used {n:,} complete records and excluded {excluded_n:,} records.",
        f"The likelihood-ratio test against the intercept-only model was chi-square({p}) = {lr_stat:.3f}, p = {lr_p:.4g}.",
        f"Estimated Pearson dispersion was {dispersion:.3f}.",
    ]
    warnings = [
        "Poisson regression assumes conditional equality of the mean and variance. The dispersion statistic is a screening diagnostic, not a substitute for model assessment.",
        "Incidence rate ratios describe multiplicative associations in the expected count rate; they do not establish causation.",
        "The current guided model uses numeric predictors and does not adjust for survey weights, strata, clusters or repeated observations.",
    ]
    if dispersion > 1.5:
        warnings.insert(0, "Potential overdispersion detected (Pearson chi-square / residual df > 1.5). Consider negative binomial regression and investigate unmodelled heterogeneity.")
    elif dispersion < 0.5:
        warnings.insert(0, "Potential underdispersion detected. The standard Poisson variance assumption may also be unsuitable.")
    if not fit.success and np.linalg.norm(getattr(fit, "jac", np.inf)) > 1e-4:
        warnings.append("The optimiser did not meet its convergence criterion; interpret estimates cautiously.")
    metadata = {
        "valid_n": n, "excluded_n": excluded_n, "predictor_count": p,
        "predictors": predictors, "outcome_variable": outcome_variable,
        "exposure_variable": exposure_variable, "converged": bool(fit.success or np.linalg.norm(getattr(fit, "jac", np.inf)) <= 1e-4),
        "pearson_chi_square": pearson_chi2, "residual_degrees_freedom": residual_df,
        "dispersion": float(dispersion), "deviance": float(fitted_deviance),
        "null_deviance": float(null_deviance), "aic": float(aic),
        "log_likelihood": float(log_likelihood), "likelihood_ratio_chi_square": lr_stat,
        "model_p_value": lr_p, "mean_observed_count": float(y.mean()),
        "mean_predicted_count": float(mu.mean()),
    }
    return {"coefficients": pd.DataFrame(rows), "fitted_data": fitted,
            "findings": findings, "warnings": warnings, "metadata": metadata}
