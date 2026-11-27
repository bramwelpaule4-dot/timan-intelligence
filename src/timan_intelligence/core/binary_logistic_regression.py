"""Binary logistic regression with guarded maximum-likelihood estimation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit


def run_binary_logistic_regression(
    df: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
    positive_class=None,
) -> dict:
    """Fit a binary logistic model using numeric predictors and an explicit event.

    Categorical outcomes require positive_class to be supplied. Numeric and
    boolean outcomes must be coded 0/1 (or False/True). Complete finite cases
    are used; no survey-design adjustment or causal interpretation is implied.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if not isinstance(predictor_variables, (list, tuple)) or len(predictor_variables) < 1:
        raise ValueError("Select at least one numeric predictor variable.")
    predictors = list(predictor_variables)
    if len(set(predictors)) != len(predictors):
        raise ValueError("Predictor variables must be unique.")
    if not isinstance(outcome_variable, str) or not outcome_variable.strip():
        raise ValueError("Provide a valid outcome variable.")
    if outcome_variable in predictors:
        raise ValueError("The outcome variable cannot also be a predictor.")
    if len(predictors) > 20:
        raise ValueError("Select no more than 20 predictors in this guided model.")
    for variable in predictors:
        if not isinstance(variable, str) or not variable.strip() or variable not in df.columns:
            raise ValueError(f"Predictor variable '{variable}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[variable].dtype) or pd.api.types.is_bool_dtype(df[variable].dtype):
            raise ValueError(f"Predictor '{variable}' must be numeric.")

    if outcome_variable not in df.columns:
        raise ValueError(f"Outcome variable '{outcome_variable}' was not found.")
    outcome = df[outcome_variable]
    observed_classes = list(pd.unique(outcome.dropna()))
    if len(observed_classes) != 2:
        raise ValueError("The outcome must contain exactly two observed categories.")
    is_numeric_binary = (
        pd.api.types.is_numeric_dtype(outcome.dtype)
        or pd.api.types.is_bool_dtype(outcome.dtype)
    )
    if is_numeric_binary:
        if set(observed_classes) != {0, 1} and set(observed_classes) != {False, True}:
            raise ValueError("Numeric binary outcomes must be coded 0/1 or False/True.")
        event = 1 if positive_class is None else positive_class
        if event not in observed_classes:
            raise ValueError("The selected positive class is not present in the outcome.")
    else:
        if positive_class is None:
            raise ValueError("Choose the positive outcome category explicitly.")
        if positive_class not in observed_classes:
            raise ValueError("The selected positive class is not present in the outcome.")
        event = positive_class

    selected = df[predictors].apply(pd.to_numeric, errors="coerce")
    finite_predictors = np.isfinite(selected).all(axis=1)
    valid = outcome.notna() & finite_predictors
    data = df.loc[valid, predictors].apply(pd.to_numeric, errors="coerce").astype(float)
    y_series = outcome.loc[valid].eq(event)
    y = y_series.to_numpy(dtype=float)
    n = int(len(data))
    p = len(predictors)
    excluded_n = int(len(df) - n)
    if n <= p + 1:
        raise ValueError(
            f"Insufficient complete records: more than {p + 1} are required "
            f"for {p} predictors and an intercept."
        )
    event_n = int(y.sum())
    non_event_n = n - event_n
    if event_n < 5 or non_event_n < 5:
        raise ValueError(
            "At least five complete records in each outcome category are "
            "required for this guided logistic model."
        )

    x = data.to_numpy(dtype=float)
    design = np.column_stack([np.ones(n), x])
    if np.linalg.matrix_rank(design) < p + 1:
        raise ValueError(
            "The selected predictors are perfectly or near-perfectly collinear. "
            "Remove or reconsider redundant predictors."
        )
    prevalence = event_n / n
    initial = np.zeros(p + 1, dtype=float)
    initial[0] = np.log(prevalence / (1.0 - prevalence))

    def negative_log_likelihood(beta):
        linear = design @ beta
        # logaddexp is numerically stable for large positive/negative values.
        return float(np.sum(np.logaddexp(0.0, linear) - y * linear))

    def gradient(beta):
        probabilities = expit(design @ beta)
        return design.T @ (probabilities - y)

    beta = initial.copy()
    converged = False
    for _ in range(200):
        probabilities = expit(design @ beta)
        score = gradient(beta)
        weights_iter = probabilities * (1.0 - probabilities)
        information_iter = design.T @ (weights_iter[:, None] * design)
        try:
            step = np.linalg.solve(information_iter, score)
        except np.linalg.LinAlgError:
            break
        current_nll = negative_log_likelihood(beta)
        scale = 1.0
        candidate = beta - step
        while scale > 1e-8:
            candidate = beta - scale * step
            if negative_log_likelihood(candidate) <= current_nll + 1e-12:
                break
            scale *= 0.5
        if scale <= 1e-8:
            break
        beta = candidate
        if np.max(np.abs(scale * step)) <= 1e-8 and np.max(np.abs(gradient(beta))) <= 1e-6:
            converged = True
            break
    probabilities = expit(design @ beta)
    if (
        not converged
        or not np.isfinite(beta).all()
        or not np.isfinite(probabilities).all()
        or np.max(np.abs(beta)) > 20
        or np.any((probabilities < 1e-10) | (probabilities > 1 - 1e-10))
    ):
        raise ValueError(
            "The logistic model did not converge to a finite, stable solution. "
            "The data may exhibit complete or quasi-complete separation, "
            "sparse categories or an over-complex model. Review predictors "
            "and outcome counts before retrying."
        )

    weights = probabilities * (1.0 - probabilities)
    information = design.T @ (weights[:, None] * design)
    if np.linalg.matrix_rank(information) < p + 1:
        raise ValueError("The fitted model information matrix is singular; stable standard errors cannot be estimated.")
    covariance = np.linalg.inv(information)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    if np.any(standard_errors <= 0) or not np.isfinite(standard_errors).all():
        raise ValueError("The fitted model produced invalid standard errors.")
    z_values = beta / standard_errors
    p_values = 2 * stats.norm.sf(np.abs(z_values))
    critical = float(stats.norm.ppf(0.975))
    lower = beta - critical * standard_errors
    upper = beta + critical * standard_errors
    odds_ratios = np.exp(np.clip(beta, -700, 700))
    odds_lower = np.exp(np.clip(lower, -700, 700))
    odds_upper = np.exp(np.clip(upper, -700, 700))

    log_likelihood = -negative_log_likelihood(beta)
    null_log_likelihood = -negative_log_likelihood(initial)
    lr_statistic = max(0.0, 2.0 * (log_likelihood - null_log_likelihood))
    lr_p_value = float(stats.chi2.sf(lr_statistic, p))
    mcfadden_r2 = float(1.0 - log_likelihood / null_log_likelihood)
    aic = float(-2.0 * log_likelihood + 2.0 * (p + 1))
    brier_score = float(np.mean((y - probabilities) ** 2))
    predicted_class = (probabilities >= 0.5).astype(int)
    accuracy = float(np.mean(predicted_class == y))
    coefficient_rows = []
    names = ["Intercept"] + predictors
    for i, name in enumerate(names):
        coefficient_rows.append({
            "Variable": name,
            "Coefficient": float(beta[i]),
            "Standard error": float(standard_errors[i]),
            "z statistic": float(z_values[i]),
            "p-value": float(p_values[i]),
            "Odds ratio": float(odds_ratios[i]),
            "OR 95% CI lower": float(odds_lower[i]),
            "OR 95% CI upper": float(odds_upper[i]),
            "Coefficient 95% CI lower": float(lower[i]),
            "Coefficient 95% CI upper": float(upper[i]),
        })

    fitted_data = data.copy()
    fitted_data[outcome_variable] = y.astype(int)
    fitted_data["Predicted probability"] = probabilities
    fitted_data["Predicted class (0.5 threshold)"] = predicted_class
    fitted_data["Observed event"] = y.astype(int)
    fitted_data["Positive class"] = str(event)

    warnings = [
        "Odds ratios describe adjusted associations in this fitted model; they do not establish causation.",
        "The model assumes an appropriate logit-linear relationship for continuous predictors and independent observations.",
        "This ordinary maximum-likelihood model does not account for survey weights, strata, clusters, repeated measures or complex sample design.",
        "Wald confidence intervals and p-values are approximate. Review event counts, separation, influential records and model specification.",
        "The 0.5 classification threshold and in-sample accuracy are descriptive only; threshold selection and predictive performance require validation on new data.",
    ]
    if excluded_n:
        warnings.append(
            f"{excluded_n:,} record(s) were excluded because the outcome or one or more predictors were missing or non-finite."
        )
    if min(event_n, non_event_n) < max(20, 5 * (p + 1)):
        warnings.append(
            "The smaller outcome category is limited relative to model complexity. Estimates may be unstable; consider a simpler model or a larger sample."
        )
    return {
        "coefficients": pd.DataFrame(coefficient_rows),
        "fitted_data": fitted_data,
        "findings": [
            f"The model used {n:,} complete records: {event_n:,} events and {non_event_n:,} non-events; {excluded_n:,} records were excluded.",
            f"The overall likelihood-ratio test was chi-square({p}) = {lr_statistic:.4g}, p = {lr_p_value:.4g}.",
            f"McFadden's pseudo-R² was {mcfadden_r2:.4f}; AIC was {aic:.4g} and Brier score was {brier_score:.4f}.",
        ],
        "warnings": warnings,
        "metadata": {
            "predictor_variables": predictors,
            "outcome_variable": outcome_variable,
            "positive_class": event,
            "negative_class": next(value for value in observed_classes if value != event),
            "total_records": int(len(df)),
            "valid_n": n,
            "excluded_n": excluded_n,
            "event_n": event_n,
            "non_event_n": non_event_n,
            "predictor_count": p,
            "log_likelihood": float(log_likelihood),
            "null_log_likelihood": float(null_log_likelihood),
            "likelihood_ratio_chi_square": lr_statistic,
            "model_p_value": lr_p_value,
            "mcfadden_pseudo_r_squared": mcfadden_r2,
            "aic": aic,
            "brier_score": brier_score,
            "apparent_accuracy": accuracy,
            "classification_threshold": 0.5,
            "test_status": "tested",
        },
    }
