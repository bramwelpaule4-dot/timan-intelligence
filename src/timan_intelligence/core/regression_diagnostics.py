"""Reusable OLS regression diagnostics for fitted linear models."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def run_regression_diagnostics(
    fitted_data: pd.DataFrame,
    predictor_variables: list[str],
    outcome_variable: str,
) -> dict:
    """Assess residual behaviour, variance, leverage, influence and collinearity.

    Diagnostic tests are evidence to investigate, not automatic pass/fail
    decisions. Independence and study-design assumptions require context that
    cannot be inferred from a rectangular dataset alone.
    """
    if not isinstance(fitted_data, pd.DataFrame):
        raise TypeError("Fitted data must be a pandas DataFrame.")
    if not isinstance(predictor_variables, (list, tuple)) or not predictor_variables:
        raise ValueError("Provide at least one predictor variable.")
    predictors = list(predictor_variables)
    required = predictors + [outcome_variable, "Fitted outcome", "Residual"]
    missing = [column for column in required if column not in fitted_data.columns]
    if missing:
        raise ValueError("Fitted data is missing required diagnostic columns: " + ", ".join(missing))
    numeric = fitted_data[required].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric).all(axis=1)
    data = numeric.loc[finite].astype(float)
    n = len(data)
    p = len(predictors)
    if n <= p + 1:
        raise ValueError("Too few complete fitted records for regression diagnostics.")

    x = data[predictors].to_numpy()
    y = data[outcome_variable].to_numpy()
    fitted = data["Fitted outcome"].to_numpy()
    residuals = data["Residual"].to_numpy()
    design = np.column_stack([np.ones(n), x])
    rank = int(np.linalg.matrix_rank(design))
    if rank < p + 1:
        raise ValueError("The diagnostic design matrix is rank deficient; review collinear predictors.")
    residual_df = n - rank
    sse = float(residuals @ residuals)
    mse = sse / residual_df if residual_df > 0 else float("nan")
    rows = []

    def add(name, statistic=None, p_value=None, status="Review", interpretation=""):
        rows.append({
            "Diagnostic": name,
            "Statistic": statistic,
            "p-value": p_value,
            "Signal": status,
            "Interpretation": interpretation,
        })

    # Shapiro-Wilk: cap sample to the documented reliable upper range.
    if 3 <= n <= 5000 and np.std(residuals) > 0:
        shapiro = stats.shapiro(residuals)
        add(
            "Residual normality (Shapiro-Wilk)",
            float(shapiro.statistic),
            float(shapiro.pvalue),
            "Investigate" if shapiro.pvalue < 0.05 else "No strong signal",
            "Evidence against normally distributed residuals; inspect the Q-Q plot and context."
            if shapiro.pvalue < 0.05 else
            "No strong evidence against residual normality; this does not prove normality.",
        )
    else:
        add("Residual normality (Shapiro-Wilk)", status="Not assessed",
            interpretation="Requires 3–5,000 records and non-constant residuals.")

    # Breusch-Pagan LM test using squared residuals and all predictors.
    if residual_df > 0 and np.std(residuals) > 0:
        auxiliary_y = residuals ** 2
        auxiliary_coef, _, _, _ = np.linalg.lstsq(design, auxiliary_y, rcond=None)
        auxiliary_fit = design @ auxiliary_coef
        centered = auxiliary_y - np.mean(auxiliary_y)
        total = float(centered @ centered)
        aux_sse = float(np.sum((auxiliary_y - auxiliary_fit) ** 2))
        aux_r2 = max(0.0, min(1.0, 1.0 - aux_sse / total)) if total > 0 else 0.0
        bp_stat = float(n * aux_r2)
        bp_p = float(stats.chi2.sf(bp_stat, p))
        add("Heteroscedasticity (Breusch-Pagan)", bp_stat, bp_p,
            "Investigate" if bp_p < 0.05 else "No strong signal",
            "Evidence of non-constant residual variance; inspect residual plots and consider robust inference."
            if bp_p < 0.05 else
            "No strong evidence of non-constant variance; this does not prove homoscedasticity.")
    else:
        add("Heteroscedasticity (Breusch-Pagan)", status="Not assessed",
            interpretation="Residual variation or residual degrees of freedom is insufficient.")

    # Variance inflation factors.
    vif_rows = []
    for index, variable in enumerate(predictors):
        target = x[:, index]
        other = np.delete(x, index, axis=1)
        if other.shape[1] == 0:
            vif = 1.0
        elif np.var(target) == 0:
            vif = float("inf")
        else:
            aux_design = np.column_stack([np.ones(n), other])
            coef, _, _, _ = np.linalg.lstsq(aux_design, target, rcond=None)
            residual = target - aux_design @ coef
            total = float(np.sum((target - np.mean(target)) ** 2))
            r2 = 1.0 - float(residual @ residual) / total if total > 0 else 1.0
            vif = float("inf") if r2 >= 1.0 - 1e-12 else float(1.0 / (1.0 - r2))
        vif_rows.append({"Predictor": variable, "VIF": vif,
                         "Signal": "High" if vif >= 10 else ("Elevated" if vif >= 5 else "Lower")})
    for item in vif_rows:
        add(f"Multicollinearity: {item['Predictor']}", item["VIF"], None,
            item["Signal"], "VIF ≥ 10 is commonly treated as high; thresholds are heuristics, not universal rules.")

    # Leverage and Cook's distance.
    hat = design @ np.linalg.pinv(design.T @ design) @ design.T
    leverage = np.clip(np.diag(hat), 0.0, 1.0)
    if mse > 0 and np.isfinite(mse):
        cooks = (residuals ** 2 / ((p + 1) * mse)) * (
            leverage / np.maximum((1.0 - leverage) ** 2, 1e-12)
        )
        max_cook = float(np.max(cooks))
        max_leverage = float(np.max(leverage))
        add("Influential observations (maximum Cook's distance)", max_cook, None,
            "Investigate" if max_cook > 4 / n else "No prominent signal",
            "At least one record exceeds the 4/n screening heuristic; review data quality and influence."
            if max_cook > 4 / n else
            "No record exceeds the 4/n screening heuristic; influential observations may still exist.")
    else:
        cooks = np.zeros(n)
        max_cook = 0.0
        max_leverage = float(np.max(leverage))
        add("Influential observations (Cook's distance)", status="Not assessed",
            interpretation="Residual mean square is zero or undefined.")
    influence = pd.DataFrame({
        "Record position": np.arange(1, n + 1),
        "Residual": residuals,
        "Leverage": leverage,
        "Cook's distance": cooks,
    }).sort_values("Cook's distance", ascending=False).head(10).reset_index(drop=True)

    # Residual shape summaries and diagnostic plot data.
    skewness = float(stats.skew(residuals, bias=False)) if n > 2 else float("nan")
    kurtosis = float(stats.kurtosis(residuals, fisher=True, bias=False)) if n > 3 else float("nan")
    residual_plot = pd.DataFrame({
        "Fitted outcome": fitted,
        "Residual": residuals,
        "Standardised residual": residuals / np.sqrt(mse) if mse > 0 else np.zeros(n),
    })
    return {
        "diagnostics": pd.DataFrame(rows),
        "influential_observations": influence,
        "residual_plot_data": residual_plot,
        "metadata": {
            "valid_n": int(n),
            "predictor_count": int(p),
            "maximum_cooks_distance": max_cook,
            "maximum_leverage": max_leverage,
            "residual_skewness": skewness,
            "residual_excess_kurtosis": kurtosis,
            "test_status": "tested",
        },
        "warnings": [
            "Diagnostic p-values are screening evidence, not definitive pass/fail decisions. Interpret them alongside plots, study design and subject-matter knowledge.",
            "These diagnostics do not test independence of errors. Independence depends on how observations were sampled, ordered, clustered or repeatedly measured.",
            "VIF thresholds and Cook's distance 4/n are heuristics. Investigate flagged records; do not remove observations automatically.",
            "Conventional OLS p-values and confidence intervals may be unreliable when model assumptions are materially violated.",
        ],
    }
