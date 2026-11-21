"""Proportional-odds ordinal logistic regression with explicit category order."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import expit


def run_ordinal_logistic_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    ordered_categories: list,
) -> dict:
    """Fit a cumulative-logit proportional-odds model.

    Category order must be supplied explicitly. Predictors in this guided
    implementation are numeric; survey design and categorical predictors
    are not modelled.
    """
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
    if outcome_variable in predictors:
        raise ValueError("The outcome variable cannot also be a predictor.")
    for variable in predictors:
        if variable not in df.columns:
            raise ValueError(f"Predictor variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype) or pd.api.types.is_bool_dtype(df[variable].dtype):
            raise ValueError(f"Predictor '{variable}' must be numeric.")

    observed = list(pd.unique(df[outcome_variable].dropna()))
    if not isinstance(ordered_categories, (list, tuple)) or len(ordered_categories) < 3:
        raise ValueError("Specify the complete order of at least three outcome categories.")
    if len(set(ordered_categories)) != len(ordered_categories):
        raise ValueError("Outcome categories in the specified order must be unique.")
    if set(observed) != set(ordered_categories):
        raise ValueError(
            "The specified category order must include every observed outcome category exactly once."
        )

    x_frame = df[predictors].apply(pd.to_numeric, errors="coerce")
    valid = df[outcome_variable].notna() & np.isfinite(x_frame).all(axis=1)
    x_frame = x_frame.loc[valid].astype(float)
    y_values = df.loc[valid, outcome_variable]
    category_to_code = {category: i for i, category in enumerate(ordered_categories)}
    y = y_values.map(category_to_code).to_numpy(dtype=int)
    n, p = x_frame.shape
    k = len(ordered_categories)
    excluded_n = int(len(df) - n)
    counts = np.bincount(y, minlength=k)
    if n <= p + k:
        raise ValueError("Insufficient complete records for the selected predictors and outcome categories.")
    if np.any(counts < 5):
        raise ValueError("At least five complete records are required in every outcome category.")
    x = x_frame.to_numpy(dtype=float)
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    if np.any(scales <= 1e-12):
        raise ValueError("A selected predictor is constant and cannot be estimated.")
    x = (x - means) / scales
    design = np.column_stack([np.ones(n), x])
    if np.linalg.matrix_rank(design) < p + 1:
        raise ValueError("The selected predictors are perfectly or near-perfectly collinear.")

    cumulative = np.cumsum(counts)[:-1] / n
    initial_cuts = np.log(cumulative / (1 - cumulative))
    initial = np.r_[initial_cuts[0], np.log(np.diff(initial_cuts)), np.zeros(p)]

    def unpack(parameters):
        cuts = np.r_[parameters[0], parameters[0] + np.cumsum(np.exp(np.clip(parameters[1:k-1], -20, 20)))]
        return cuts, parameters[k-1:]

    def objective(parameters):
        cuts, beta = unpack(parameters)
        eta = x @ beta
        cumulative_prob = expit(cuts[None, :] - eta[:, None])
        probabilities = np.column_stack([
            cumulative_prob[:, 0],
            np.diff(cumulative_prob, axis=1),
            1.0 - cumulative_prob[:, -1],
        ])
        chosen = probabilities[np.arange(n), y]
        if np.any(chosen <= 1e-14) or not np.isfinite(chosen).all():
            return 1e100
        return float(-np.log(chosen).sum())

    fit = minimize(
        objective, initial, method="BFGS",
        options={"maxiter": 2000, "gtol": 1e-7},
    )
    cuts, beta_std = unpack(fit.x)
    eta = x @ beta_std
    cumulative_prob = expit(cuts[None, :] - eta[:, None])
    probabilities = np.column_stack([
        cumulative_prob[:, 0],
        np.diff(cumulative_prob, axis=1),
        1.0 - cumulative_prob[:, -1],
    ])
    if (not fit.success and np.linalg.norm(fit.jac) > 1e-4) or not np.isfinite(probabilities).all() or np.any(probabilities <= 0):
        raise ValueError(
            "The ordinal model did not converge to a stable solution. Review sparse categories, "
            "predictor collinearity, separation and model complexity."
        )
    if not np.all(np.diff(cuts) > 0):
        raise ValueError("The model could not estimate correctly ordered category thresholds.")

    # BFGS inverse-Hessian approximation supplies an approximate covariance matrix.
    covariance_std = np.asarray(fit.hess_inv, dtype=float)
    if covariance_std.shape != (len(fit.x), len(fit.x)) or not np.isfinite(covariance_std).all():
        raise ValueError("Stable standard errors could not be estimated for this ordinal model.")
    beta_cov_std = covariance_std[k-1:, k-1:]
    transform = np.diag(1.0 / scales)
    beta = beta_std / scales
    covariance = transform @ beta_cov_std @ transform
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    if np.any(se <= 0) or not np.isfinite(se).all():
        raise ValueError("The model produced invalid coefficient standard errors.")
    z = beta / se
    p_values = 2 * stats.norm.sf(np.abs(z))
    odds_ratio = np.exp(np.clip(beta, -700, 700))
    lower = np.exp(np.clip(beta - 1.96 * se, -700, 700))
    upper = np.exp(np.clip(beta + 1.96 * se, -700, 700))

    null_cuts = np.log(cumulative / (1 - cumulative))
    null_prob = np.column_stack([
        np.full(n, cumulative[0]),
        np.tile(np.diff(cumulative), (n, 1)),
        np.full(n, 1 - cumulative[-1]),
    ])
    ll = -float(fit.fun)
    null_ll = float(np.log(null_prob[np.arange(n), y]).sum())
    lr = max(0.0, 2 * (ll - null_ll))
    lr_p = float(stats.chi2.sf(lr, p))
    aic = float(-2 * ll + 2 * (p + k - 1))

    coefficients = pd.DataFrame({
        "Variable": predictors,
        "Coefficient": beta,
        "Standard error": se,
        "z statistic": z,
        "p-value": p_values,
        "Odds ratio": odds_ratio,
        "OR 95% CI lower": lower,
        "OR 95% CI upper": upper,
    })
    fitted = x_frame.copy()
    fitted[outcome_variable] = y_values.to_numpy()
    fitted["Predicted category"] = [ordered_categories[i] for i in probabilities.argmax(axis=1)]
    for i, category in enumerate(ordered_categories):
        fitted[f"Pr({category})"] = probabilities[:, i]

    warnings = [
        "The proportional-odds assumption is required but is not formally tested by this implementation; assess it before relying on model inference.",
        "Odds ratios describe adjusted associations, not causal effects. A common odds ratio is assumed across cumulative category splits.",
        "This guided model uses numeric predictors and independent observations; it does not adjust for survey weights, strata, clusters, repeated measures or complex sample design.",
        "Standard errors use the optimiser's approximate inverse-Hessian matrix; p-values and confidence intervals are approximate.",
    ]
    if excluded_n:
        warnings.append(f"{excluded_n:,} record(s) were excluded because the outcome or one or more predictors were missing or non-finite.")
    if counts.min() < max(20, 5 * (p + 1)):
        warnings.append("At least one outcome category is small relative to model complexity; estimates may be unstable.")

    return {
        "coefficients": coefficients,
        "fitted_data": fitted,
        "category_probabilities": pd.DataFrame(probabilities, columns=[str(c) for c in ordered_categories]),
        "findings": [
            f"The model used {n:,} complete records across {k} ordered categories; {excluded_n:,} records were excluded.",
            f"The overall likelihood-ratio test was chi-square({p}) = {lr:.4g}, p = {lr_p:.4g}.",
            f"AIC was {aic:.4g}; log-likelihood was {ll:.4g}.",
        ],
        "warnings": warnings,
        "metadata": {
            "predictor_variables": predictors,
            "outcome_variable": outcome_variable,
            "ordered_categories": list(ordered_categories),
            "category_counts": {str(c): int(counts[i]) for i, c in enumerate(ordered_categories)},
            "total_records": int(len(df)),
            "valid_n": n,
            "excluded_n": excluded_n,
            "predictor_count": p,
            "log_likelihood": ll,
            "null_log_likelihood": null_ll,
            "likelihood_ratio_chi_square": lr,
            "model_p_value": lr_p,
            "aic": aic,
            "converged": bool(fit.success or np.linalg.norm(fit.jac) <= 1e-4),
            "test_status": "tested",
        },
    }
