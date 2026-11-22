"""Baseline-category multinomial logistic regression for nominal outcomes."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax


def run_multinomial_logistic_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    reference_category=None,
) -> dict:
    """Fit a baseline-category multinomial logit using numeric predictors.

    The outcome categories are nominal (unordered). The reference category is
    explicit when supplied and otherwise the final observed category. Numeric
    predictors, independent observations and ordinary maximum likelihood are
    assumed; survey-design corrections are not performed.
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
        if (
            not pd.api.types.is_numeric_dtype(df[variable].dtype)
            or pd.api.types.is_bool_dtype(df[variable].dtype)
        ):
            raise ValueError(f"Predictor '{variable}' must be numeric.")

    observed_categories = list(pd.unique(df[outcome_variable].dropna()))
    if len(observed_categories) < 3:
        raise ValueError("The outcome must contain at least three observed nominal categories.")
    if reference_category is None:
        reference_category = observed_categories[-1]
    if reference_category not in observed_categories:
        raise ValueError("The selected reference category is not present in the outcome.")
    categories = [c for c in observed_categories if c != reference_category] + [reference_category]

    selected = df[predictors].apply(pd.to_numeric, errors="coerce")
    valid = df[outcome_variable].notna() & np.isfinite(selected).all(axis=1)
    x_frame = selected.loc[valid].astype(float)
    y_values = df.loc[valid, outcome_variable]
    category_to_code = {category: i for i, category in enumerate(categories)}
    y = y_values.map(category_to_code).to_numpy(dtype=int)
    n, p = x_frame.shape
    k = len(categories)
    q = k - 1
    excluded_n = int(len(df) - n)
    counts = np.bincount(y, minlength=k)
    if n <= (p + 1) * q:
        raise ValueError("Insufficient complete records for the selected predictors and outcome categories.")
    if np.any(counts < 5):
        raise ValueError("At least five complete records are required in every outcome category.")

    x_raw = x_frame.to_numpy(dtype=float)
    means = x_raw.mean(axis=0)
    scales = x_raw.std(axis=0, ddof=0)
    if np.any(scales <= 1e-12):
        raise ValueError("A selected predictor is constant and cannot be estimated.")
    x = (x_raw - means) / scales
    design = np.column_stack([np.ones(n), x])
    if np.linalg.matrix_rank(design) < p + 1:
        raise ValueError("The selected predictors are perfectly or near-perfectly collinear.")

    # The final category is the reference; each row of B models one other class.
    parameter_count = q * (p + 1)
    initial = np.zeros((q, p + 1), dtype=float)
    for j in range(q):
        initial[j, 0] = np.log(counts[j] / counts[-1])
    initial = initial.ravel()

    def objective(parameters):
        beta = parameters.reshape(q, p + 1)
        logits = np.column_stack([design @ beta.T, np.zeros(n)])
        return float(np.sum(logsumexp(logits, axis=1) - logits[np.arange(n), y]))

    def gradient(parameters):
        beta = parameters.reshape(q, p + 1)
        probabilities = softmax(np.column_stack([design @ beta.T, np.zeros(n)]), axis=1)
        residuals = probabilities[:, :q] - np.eye(k)[y, :q]
        return (residuals.T @ design).ravel()

    fit = minimize(
        objective,
        initial,
        method="BFGS",
        jac=gradient,
        options={"maxiter": 3000, "gtol": 1e-7},
    )
    beta_std = fit.x.reshape(q, p + 1)
    probabilities = softmax(
        np.column_stack([design @ beta_std.T, np.zeros(n)]), axis=1
    )
    gradient_norm = float(np.linalg.norm(gradient(fit.x), ord=np.inf))
    if (
        (not fit.success and gradient_norm > 1e-4)
        or not np.isfinite(beta_std).all()
        or not np.isfinite(probabilities).all()
        or np.any(probabilities <= 1e-12)
        or np.max(np.abs(beta_std)) > 25
    ):
        raise ValueError(
            "The multinomial model did not converge to a finite, stable solution. "
            "Review sparse categories, separation, collinearity and model complexity."
        )

    # Observed information matrix in standardised parameter space.
    information = np.zeros((parameter_count, parameter_count), dtype=float)
    for i in range(n):
        probs = probabilities[i, :q]
        class_cov = np.diag(probs) - np.outer(probs, probs)
        information += np.kron(class_cov, np.outer(design[i], design[i]))
    if np.linalg.matrix_rank(information) < parameter_count:
        raise ValueError("The fitted model information matrix is singular; stable standard errors cannot be estimated.")
    covariance_std = np.linalg.inv(information)
    if not np.isfinite(covariance_std).all():
        raise ValueError("Stable standard errors could not be estimated for this multinomial model.")

    # Convert standardised coefficients and their covariance to original units.
    transform_one = np.eye(p + 1)
    transform_one[0, 1:] = -means / scales
    transform_one[1:, 1:] = np.diag(1.0 / scales)
    transform = np.kron(np.eye(q), transform_one)
    beta_original = (transform_one @ beta_std.T).T
    covariance = transform @ covariance_std @ transform.T

    coefficient_rows = []
    for j, category in enumerate(categories[:-1]):
        block = slice(j * (p + 1), (j + 1) * (p + 1))
        estimates = beta_original[j]
        standard_errors = np.sqrt(np.maximum(np.diag(covariance)[block], 0))
        if np.any(standard_errors <= 0) or not np.isfinite(standard_errors).all():
            raise ValueError("The fitted model produced invalid coefficient standard errors.")
        z_values = estimates / standard_errors
        p_values = 2 * stats.norm.sf(np.abs(z_values))
        lower = estimates - stats.norm.ppf(0.975) * standard_errors
        upper = estimates + stats.norm.ppf(0.975) * standard_errors
        for index, variable in enumerate(["Intercept"] + predictors):
            coefficient_rows.append({
                "Outcome category": str(category),
                "Reference category": str(reference_category),
                "Variable": variable,
                "Coefficient": float(estimates[index]),
                "Standard error": float(standard_errors[index]),
                "z statistic": float(z_values[index]),
                "p-value": float(p_values[index]),
                "Relative risk ratio": float(np.exp(np.clip(estimates[index], -700, 700))),
                "RRR 95% CI lower": float(np.exp(np.clip(lower[index], -700, 700))),
                "RRR 95% CI upper": float(np.exp(np.clip(upper[index], -700, 700))),
            })

    log_likelihood = -float(fit.fun)
    null_probabilities = counts / n
    null_log_likelihood = float(np.log(null_probabilities[y]).sum())
    lr_statistic = max(0.0, 2.0 * (log_likelihood - null_log_likelihood))
    degrees_freedom = p * q
    lr_p_value = float(stats.chi2.sf(lr_statistic, degrees_freedom))
    mcfadden_r2 = float(1.0 - log_likelihood / null_log_likelihood)
    aic = float(-2.0 * log_likelihood + 2.0 * (parameter_count))
    predicted_codes = probabilities.argmax(axis=1)
    accuracy = float(np.mean(predicted_codes == y))
    log_loss = float(-np.mean(np.log(probabilities[np.arange(n), y])))

    probability_frame = pd.DataFrame(
        probabilities, columns=[str(category) for category in categories]
    )
    fitted = x_frame.copy()
    fitted[outcome_variable] = y_values.to_numpy()
    fitted["Predicted category"] = [categories[index] for index in predicted_codes]
    fitted["Maximum predicted probability"] = probabilities.max(axis=1)

    warnings = [
        "Relative risk ratios compare each non-reference outcome category with the selected reference category; they are adjusted associations, not causal effects.",
        "The model treats outcome categories as nominal and does not impose an ordering.",
        "The model assumes independent observations and a correctly specified linear relationship between numeric predictors and category log-odds.",
        "This guided model uses numeric predictors and does not adjust for survey weights, strata, clusters, repeated measures or complex sample design.",
        "Wald confidence intervals and p-values use the observed-information covariance matrix; assess model fit and validate predictions on new data.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because the outcome or one or more predictors were missing or non-finite."
        )
    if counts.min() < max(20, 5 * (p + 1)):
        warnings.append(
            "At least one outcome category is small relative to model complexity; estimates may be unstable."
        )

    return {
        "coefficients": pd.DataFrame(coefficient_rows),
        "fitted_data": fitted,
        "category_probabilities": probability_frame,
        "findings": [
            f"The model used {n:,} complete records across {k} nominal categories; {excluded_n:,} records were excluded.",
            f"The overall likelihood-ratio test was chi-square({degrees_freedom}) = {lr_statistic:.4g}, p = {lr_p_value:.4g}.",
            f"McFadden's pseudo-R² was {mcfadden_r2:.4f}; AIC was {aic:.4g}; in-sample log loss was {log_loss:.4g}.",
        ],
        "warnings": warnings,
        "metadata": {
            "predictor_variables": predictors,
            "outcome_variable": outcome_variable,
            "categories": [str(c) for c in categories],
            "reference_category": str(reference_category),
            "category_counts": {str(c): int(counts[i]) for i, c in enumerate(categories)},
            "total_records": int(len(df)),
            "valid_n": int(n),
            "excluded_n": excluded_n,
            "predictor_count": p,
            "category_count": k,
            "log_likelihood": log_likelihood,
            "null_log_likelihood": null_log_likelihood,
            "likelihood_ratio_chi_square": lr_statistic,
            "likelihood_ratio_df": degrees_freedom,
            "model_p_value": lr_p_value,
            "mcfadden_pseudo_r_squared": mcfadden_r2,
            "aic": aic,
            "log_loss": log_loss,
            "apparent_accuracy": accuracy,
            "converged": bool(fit.success or gradient_norm <= 1e-4),
            "test_status": "tested",
        },
    }
