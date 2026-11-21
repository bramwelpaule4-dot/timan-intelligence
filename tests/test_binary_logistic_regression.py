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
