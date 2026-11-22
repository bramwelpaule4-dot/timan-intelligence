"""Right-censored survival analysis: Kaplan-Meier, log-rank and Cox PH.

Times are assumed to be measured on a common non-negative numeric scale.
Event indicators must be explicitly mapped to the event of interest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize


def _prepare_survival_data(df, time_variable, event_variable, event_value):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    for variable in (time_variable, event_variable):
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' was not found.")
    time = pd.to_numeric(df[time_variable], errors="coerce")
    event_raw = df[event_variable]
    valid = time.notna() & np.isfinite(time) & event_raw.notna()
    times = time.loc[valid].to_numpy(dtype=float)
    if np.any(times < 0):
        raise ValueError("Survival or follow-up times must be non-negative.")
    events = (event_raw.loc[valid] == event_value).to_numpy(dtype=int)
    observed_categories = list(pd.unique(event_raw.loc[valid]))
    if len(observed_categories) != 2:
        raise ValueError("The event indicator must have exactly two observed categories.")
    if events.sum() == 0:
        raise ValueError("No events of the selected type were observed.")
    return times, events, valid, observed_categories


def _km_table(times, events):
    event_times = np.sort(np.unique(times[events == 1]))
    survival = 1.0
    greenwood_sum = 0.0
    rows = []
    for event_time in event_times:
        at_risk = int(np.sum(times >= event_time))
        deaths = int(np.sum((times == event_time) & (events == 1)))
        censored = int(np.sum((times == event_time) & (events == 0)))
        survival *= (1.0 - deaths / at_risk)
        if at_risk > deaths:
            greenwood_sum += deaths / (at_risk * (at_risk - deaths))
        if survival > 0 and survival < 1 and greenwood_sum > 0:
            se_loglog = np.sqrt(greenwood_sum) / abs(np.log(survival))
            loglog = np.log(-np.log(survival))
            z = stats.norm.ppf(0.975)
            lower = float(np.exp(-np.exp(loglog + z * se_loglog)))
            upper = float(np.exp(-np.exp(loglog - z * se_loglog)))
        elif survival >= 1:
            lower, upper = 1.0, 1.0
        else:
            lower, upper = 0.0, 0.0
        rows.append({
            "Time": float(event_time), "At risk": at_risk,
            "Events": deaths, "Censored": censored,
            "Survival probability": float(survival),
            "95% CI lower": lower, "95% CI upper": upper,
        })
    return pd.DataFrame(rows)


def _logrank_two_groups(times, events, group_values, labels):
    unique_times = np.sort(np.unique(times[events == 1]))
    observed = np.zeros(2, dtype=float)
    expected = np.zeros(2, dtype=float)
    variance = 0.0
    for t in unique_times:
        risk = np.array([np.sum((times >= t) & (group_values == g)) for g in labels], dtype=float)
        deaths = np.array([np.sum((times == t) & (events == 1) & (group_values == g)) for g in labels], dtype=float)
        n_risk, n_deaths = risk.sum(), deaths.sum()
        if n_risk <= 1 or n_deaths == 0:
            continue
        observed += deaths
        expected += n_deaths * risk / n_risk
        variance += (
            risk[0] * risk[1] * n_deaths * (n_risk - n_deaths)
            / (n_risk**2 * (n_risk - 1))
        )
    statistic = float((observed[0] - expected[0])**2 / variance) if variance > 0 else 0.0
    return {
        "chi_square": statistic,
        "degrees_freedom": 1,
        "p_value": float(stats.chi2.sf(statistic, 1)),
        "observed_events": observed.tolist(),
        "expected_events": expected.tolist(),
        "group_labels": [str(x) for x in labels],
    }


def run_kaplan_meier(
    df: pd.DataFrame,
    time_variable: str,
    event_variable: str,
    event_value,
    group_variable: str | None = None,
) -> dict:
    """Estimate Kaplan-Meier survival curves and optional two-group log-rank test."""
    times, events, valid, categories = _prepare_survival_data(
        df, time_variable, event_variable, event_value
    )
    curve = _km_table(times, events)
    fitted = pd.DataFrame({
        "Time": times, "Event": events,
    }, index=df.index[valid])
    findings = [
        f"Kaplan-Meier analysis used {len(times):,} records, with {int(events.sum()):,} events and {int((events == 0).sum()):,} right-censored observations.",
        f"Median observed follow-up time was {float(np.median(times)):.4g} time units.",
    ]
    warnings = [
        "The event category was selected explicitly; all other observed categories are treated as censored observations.",
        "Censoring is assumed to be non-informative conditional on the analysis; informative loss to follow-up can bias survival estimates.",
        "The analysis treats records as independent and does not account for weights, strata, clusters or competing risks.",
    ]
    metadata = {
        "valid_n": int(len(times)), "excluded_n": int(len(df) - len(times)),
        "event_n": int(events.sum()), "censored_n": int((events == 0).sum()),
        "event_value": str(event_value), "event_categories": [str(x) for x in categories],
        "time_variable": time_variable, "event_variable": event_variable,
        "median_follow_up": float(np.median(times)),
        "median_survival_time": None,
    }
    if not curve.empty and (curve["Survival probability"] <= 0.5).any():
        metadata["median_survival_time"] = float(
            curve.loc[curve["Survival probability"] <= 0.5, "Time"].iloc[0]
        )
        findings.append(
            f"Estimated median survival time was {metadata['median_survival_time']:.4g} time units."
        )
    else:
        findings.append("Median survival was not reached during observed follow-up.")

    tables = {"survival_curve": curve}
    if group_variable is not None:
        if group_variable not in df.columns:
            raise ValueError(f"Grouping variable '{group_variable}' was not found.")
        group = df.loc[valid, group_variable]
        group_valid = group.notna().to_numpy()
        if not group_valid.all():
            times_g, events_g = times[group_valid], events[group_valid]
            group_values = group.to_numpy()[group_valid]
            warnings.append(
                f"{int((~group_valid).sum()):,} records with missing group values were excluded from group-specific estimates."
            )
        else:
            times_g, events_g, group_values = times, events, group.to_numpy()
        labels = list(pd.unique(group_values))
        if len(labels) < 2:
            raise ValueError("Select a grouping variable with at least two observed groups.")
        group_curves = []
        for label in labels:
            mask = group_values == label
            part = _km_table(times_g[mask], events_g[mask])
            if not part.empty:
                part.insert(0, "Group", str(label))
                group_curves.append(part)
        if group_curves:
            tables["group_survival_curves"] = pd.concat(group_curves, ignore_index=True)
        if len(labels) == 2:
            logrank = _logrank_two_groups(times_g, events_g, group_values, labels)
            metadata["logrank_test"] = logrank
            findings.append(
                f"Log-rank test comparing {labels[0]} with {labels[1]}: chi-square(1) = {logrank['chi_square']:.3f}, p = {logrank['p_value']:.4g}."
            )
        else:
            warnings.append(
                "The log-rank comparison is currently provided only for exactly two groups; group-specific Kaplan-Meier curves are still reported."
            )
    return {
        "survival_curve": curve, "tables": tables, "fitted_data": fitted,
        "findings": findings, "warnings": warnings, "metadata": metadata,
    }


def run_cox_proportional_hazards(
    df: pd.DataFrame,
    predictor_variables: list[str],
    time_variable: str,
    event_variable: str,
    event_value,
) -> dict:
    """Fit Cox proportional hazards regression using Breslow tie handling."""
    times, events, valid, _ = _prepare_survival_data(
        df, time_variable, event_variable, event_value
    )
    if not isinstance(predictor_variables, (list, tuple)) or not predictor_variables:
        raise ValueError("Select at least one numeric predictor variable.")
    predictors = list(predictor_variables)
    if len(set(predictors)) != len(predictors):
        raise ValueError("Predictor variables must be unique.")
    if len(predictors) > 15:
        raise ValueError("Select no more than 15 predictors in this guided model.")
    if time_variable in predictors or event_variable in predictors:
        raise ValueError("Time and event variables cannot also be predictors.")
    for name in predictors:
        if name not in df.columns:
            raise ValueError(f"Predictor variable '{name}' was not found.")
        if not pd.api.types.is_numeric_dtype(df[name].dtype) or pd.api.types.is_bool_dtype(df[name].dtype):
            raise ValueError(f"Predictor '{name}' must be numeric.")
    x_frame = df.loc[valid, predictors].apply(pd.to_numeric, errors="coerce")
    complete_x = np.isfinite(x_frame).all(axis=1).to_numpy()
    times, events = times[complete_x], events[complete_x]
    x = x_frame.loc[complete_x].to_numpy(dtype=float)
    n, p = x.shape
    if n <= p + 2:
        raise ValueError("Insufficient complete records for the selected predictors.")
    if events.sum() <= p:
        raise ValueError("There are too few observed events for the selected number of predictors.")
    means, scales = x.mean(axis=0), x.std(axis=0)
    if np.any(scales <= 1e-12):
        raise ValueError("A selected predictor is constant and cannot be estimated.")
    z = (x - means) / scales
    if np.linalg.matrix_rank(np.column_stack([np.ones(n), z])) < p + 1:
        raise ValueError("The selected predictors are perfectly or near-perfectly collinear.")
    event_times = np.sort(np.unique(times[events == 1]))

    def partial_components(beta):
        eta = np.clip(z @ beta, -40, 40)
        risk_score = np.exp(eta)
        loglik = 0.0
        gradient = np.zeros(p)
        information = np.zeros((p, p))
        for t in event_times:
            deaths = (times == t) & (events == 1)
            risk = times >= t
            d = int(deaths.sum())
            scores = risk_score[risk]
            xr = z[risk]
            denom = float(scores.sum())
            weighted_mean = (scores[:, None] * xr).sum(axis=0) / denom
            weighted_second = (xr.T * scores) @ xr / denom
            loglik += float(z[deaths].sum(axis=0) @ beta) - d * np.log(denom)
            gradient += z[deaths].sum(axis=0) - d * weighted_mean
            information += d * (weighted_second - np.outer(weighted_mean, weighted_mean))
        return loglik, gradient, information

    def objective(beta):
        ll, gradient, _ = partial_components(beta)
        return -ll, -gradient

    fit = minimize(
        objective, np.zeros(p), jac=True, method="BFGS",
        options={"maxiter": 2000, "gtol": 1e-7},
    )
    beta_std = fit.x
    loglik, gradient, information = partial_components(beta_std)
    if not np.isfinite(loglik) or np.linalg.matrix_rank(information) < p:
        raise ValueError("The Cox model could not produce identifiable coefficient estimates.")
    covariance_std = np.linalg.pinv(information)
    transform = np.diag(1.0 / scales)
    beta = beta_std / scales
    covariance = transform @ covariance_std @ transform
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    zstat = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    pvalues = 2 * stats.norm.sf(np.abs(zstat))
    lower, upper = beta - 1.96 * se, beta + 1.96 * se

    null_ll, _, _ = partial_components(np.zeros(p))
    lr = max(0.0, 2 * (loglik - null_ll))
    lr_p = float(stats.chi2.sf(lr, p))
    coefficient_table = pd.DataFrame([{
        "Variable": name, "Coefficient": float(beta[i]),
        "Standard error": float(se[i]),
        "Hazard ratio": float(np.exp(np.clip(beta[i], -30, 30))),
        "HR 95% CI lower": float(np.exp(np.clip(lower[i], -30, 30))),
        "HR 95% CI upper": float(np.exp(np.clip(upper[i], -30, 30))),
        "z statistic": float(zstat[i]), "p-value": float(pvalues[i]),
    } for i, name in enumerate(predictors)])

    eta = np.clip(z @ beta_std, -40, 40)
    risk_score = np.exp(eta)
    cumulative_hazard = 0.0
    baseline_rows = []
    for t in event_times:
        deaths = int(np.sum((times == t) & (events == 1)))
        denominator = float(risk_score[times >= t].sum())
        cumulative_hazard += deaths / denominator
        baseline_rows.append({
            "Time": float(t), "Baseline cumulative hazard": cumulative_hazard,
            "Baseline survival": float(np.exp(-cumulative_hazard)),
        })
    fitted = pd.DataFrame({
        "Time": times, "Event": events, "Linear predictor": eta,
        "Relative risk score": risk_score,
    })
    warnings = [
        "The proportional hazards assumption is not formally tested in this guided implementation; assess time-varying effects and Schoenfeld residuals before substantive interpretation.",
        "Breslow approximation is used for tied event times.",
        "The model assumes independent observations and non-informative right censoring conditional on included predictors.",
        "Only numeric predictors are supported. Survey weights, strata, clusters, repeated measures and competing risks are not adjusted for.",
        "Hazard ratios are conditional associations, not causal effects.",
    ]
    if not fit.success:
        warnings.append("The optimiser did not report formal convergence; inspect estimates and model diagnostics before interpretation.")
    findings = [
        f"Cox regression used {n:,} complete records, including {int(events.sum()):,} events.",
        f"Overall likelihood-ratio test: chi-square({p}) = {lr:.3f}, p = {lr_p:.4g}.",
        "Hazard ratios above 1 indicate a higher instantaneous event hazard; below 1 indicate a lower hazard, conditional on the included predictors.",
    ]
    metadata = {
        "valid_n": n, "excluded_n": int(len(df) - n), "event_n": int(events.sum()),
        "predictor_count": p, "predictors": predictors,
        "log_partial_likelihood": float(loglik),
        "null_log_partial_likelihood": float(null_ll),
        "likelihood_ratio_chi_square": float(lr), "model_p_value": lr_p,
        "converged": bool(fit.success), "tie_method": "Breslow",
    }
    return {
        "coefficients": coefficient_table,
        "baseline_survival": pd.DataFrame(baseline_rows),
        "fitted_data": fitted,
        "findings": findings, "warnings": warnings, "metadata": metadata,
    }
