import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.binary_logistic_regression import run_binary_logistic_regression


def _logistic_data(n=500, seed=42):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    probability = 1 / (1 + np.exp(-(-0.3 + 0.8 * x1 - 0.6 * x2)))
    y = rng.binomial(1, probability)
    return pd.DataFrame({"exposure": x1, "age_score": x2, "outcome": y})


def test_logistic_regression_returns_odds_ratios_probabilities_and_fit_metrics():
    df = _logistic_data()
    result = run_binary_logistic_regression(df, ["exposure", "age_score"], "outcome")
    assert result["metadata"]["valid_n"] == len(df)
    assert result["metadata"]["event_n"] + result["metadata"]["non_event_n"] == len(df)
    assert result["metadata"]["likelihood_ratio_chi_square"] > 0
    assert "Odds ratio" in result["coefficients"]
    assert result["fitted_data"]["Predicted probability"].between(0, 1).all()
    assert set(result["fitted_data"]["Predicted class (0.5 threshold)"].unique()) <= {0, 1}


def test_logistic_regression_uses_explicit_positive_category():
    df = _logistic_data(300)
    df["outcome_label"] = np.where(df["outcome"].eq(1), "Completed", "Not completed")
    with pytest.raises(ValueError, match="explicitly"):
        run_binary_logistic_regression(df, ["exposure"], "outcome_label")
    result = run_binary_logistic_regression(df, ["exposure"], "outcome_label", "Completed")
    assert result["metadata"]["positive_class"] == "Completed"


def test_logistic_regression_excludes_missing_predictors_and_outcomes():
    df = _logistic_data()
    df.loc[0, "exposure"] = np.nan
    df.loc[1, "outcome"] = np.nan
    result = run_binary_logistic_regression(df, ["exposure", "age_score"], "outcome")
    assert result["metadata"]["valid_n"] == len(df) - 2
    assert result["metadata"]["excluded_n"] == 2


def test_logistic_regression_rejects_invalid_outcome_and_predictors():
    df = _logistic_data(300)
    df["three_level"] = np.arange(len(df)) % 3
    with pytest.raises(ValueError, match="exactly two"):
        run_binary_logistic_regression(df, ["exposure"], "three_level")
    with pytest.raises(ValueError, match="cannot also be a predictor"):
        run_binary_logistic_regression(df, ["exposure", "outcome"], "outcome")
    with pytest.raises(ValueError, match="numeric"):
        df["text_predictor"] = ["a", "b", "c"] * 100
        run_binary_logistic_regression(df, ["text_predictor"], "outcome")


def test_logistic_regression_rejects_sparse_outcomes_and_collinearity():
    df = _logistic_data(300)
    df["rare"] = 0
    df.loc[0, "rare"] = 1
    with pytest.raises(ValueError, match="five complete"):
        run_binary_logistic_regression(df, ["exposure"], "rare")
    df["copy_exposure"] = df["exposure"] * 2
    with pytest.raises(ValueError, match="collinear"):
        run_binary_logistic_regression(df, ["exposure", "copy_exposure"], "outcome")


def test_logistic_regression_does_not_modify_input():
    df = _logistic_data()
    original = df.copy(deep=True)
    run_binary_logistic_regression(df, ["exposure"], "outcome")
    pd.testing.assert_frame_equal(df, original)


def test_meal_training_completion_with_realistic_predictor_scales():
    """Exercise completion modelling with attendance, age, travel and binary access."""
    rng = np.random.default_rng(20261121)
    n = 700
    age_years = rng.integers(18, 46, size=n)
    attendance_percent = rng.uniform(35, 100, size=n)
    travel_distance_km = rng.uniform(0.5, 65, size=n)
    received_learning_support = rng.binomial(1, 0.55, size=n)

    linear_predictor = (
        -2.0
        + 0.035 * (attendance_percent - 65)
        - 0.025 * (travel_distance_km - 25)
        + 0.55 * received_learning_support
        - 0.012 * (age_years - 28)
    )
    completion_probability = 1 / (1 + np.exp(-linear_predictor))
    completed = rng.binomial(1, completion_probability)
    frame = pd.DataFrame({
        "age_years": age_years,
        "attendance_percent": attendance_percent,
        "travel_distance_km": travel_distance_km,
        "received_learning_support": received_learning_support,
        "course_completed": completed,
    })

    result = run_binary_logistic_regression(
        frame,
        ["age_years", "attendance_percent", "travel_distance_km", "received_learning_support"],
        "course_completed",
    )

    assert result["metadata"]["valid_n"] == n
    assert result["metadata"]["event_n"] >= 5
    assert result["metadata"]["non_event_n"] >= 5
    assert result["coefficients"]["Odds ratio"].map(np.isfinite).all()
    assert result["fitted_data"]["Predicted probability"].between(0, 1).all()
    assert result["metadata"]["brier_score"] >= 0


def test_meal_household_service_uptake_with_imbalanced_outcome():
    """Exercise an uncommon MEAL outcome using household-level predictors."""
    rng = np.random.default_rng(712)
    n = 900
    household_size = rng.integers(1, 11, size=n)
    distance_to_service_km = rng.uniform(1, 55, size=n)
    phone_access = rng.binomial(1, 0.48, size=n)
    awareness_visit = rng.binomial(1, 0.30, size=n)

    linear_predictor = (
        -2.25
        - 0.035 * (distance_to_service_km - 25)
        - 0.08 * (household_size - 5)
        + 0.65 * phone_access
        + 0.85 * awareness_visit
    )
    uptake_probability = 1 / (1 + np.exp(-linear_predictor))
    accessed_service = rng.binomial(1, uptake_probability)
    frame = pd.DataFrame({
        "household_size": household_size,
        "distance_to_service_km": distance_to_service_km,
        "phone_access": phone_access,
        "awareness_visit": awareness_visit,
        "accessed_service": accessed_service,
    })

    result = run_binary_logistic_regression(
        frame,
        ["household_size", "distance_to_service_km", "phone_access", "awareness_visit"],
        "accessed_service",
    )

    assert result["metadata"]["valid_n"] == n
    assert 0 < result["metadata"]["event_n"] < n
    assert result["metadata"]["non_event_n"] > result["metadata"]["event_n"]
    assert result["metadata"]["brier_score"] < 0.30
    assert "The smaller outcome category is limited" in " ".join(result["warnings"]) or min(
        result["metadata"]["event_n"], result["metadata"]["non_event_n"]
    ) >= 20


def test_logistic_regression_reports_three_distinct_pseudo_r_squared_indices():
    result = run_binary_logistic_regression(_logistic_data(), ["exposure", "age_score"], "outcome")
    metadata = result["metadata"]
    assert 0 <= metadata["mcfadden_pseudo_r_squared"] <= 1
    assert 0 <= metadata["cox_snell_pseudo_r_squared"] < 1
    assert 0 <= metadata["nagelkerke_pseudo_r_squared"] <= 1
    assert metadata["nagelkerke_pseudo_r_squared"] >= metadata["cox_snell_pseudo_r_squared"]
