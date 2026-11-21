import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.ordinal_logistic_regression import run_ordinal_logistic_regression


CATEGORIES = ["Low", "Moderate", "High"]


def _ordinal_data(n=900, seed=73):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    latent = 0.9 * x + rng.logistic(size=n)
    outcome = np.select([latent <= -0.8, latent <= 0.8], CATEGORIES[:2], default="High")
    return pd.DataFrame({"support_score": x, "age": rng.normal(35, 8, n), "rating": outcome})


def test_ordinal_logistic_returns_ordered_category_probabilities_and_effects():
    frame = _ordinal_data()
    result = run_ordinal_logistic_regression(
        frame, ["support_score", "age"], "rating", CATEGORIES
    )
    metadata = result["metadata"]
    assert metadata["valid_n"] == len(frame)
    assert metadata["ordered_categories"] == CATEGORIES
    assert metadata["converged"]
    assert result["category_probabilities"].shape == (len(frame), 3)
    assert np.allclose(result["category_probabilities"].sum(axis=1), 1.0, atol=1e-7)
    assert result["category_probabilities"].to_numpy().min() > 0
    assert "Odds ratio" in result["coefficients"]
    assert result["coefficients"].loc[
        result["coefficients"]["Variable"] == "support_score", "Odds ratio"
    ].iloc[0] > 1
    assert result["fitted_data"]["Predicted category"].isin(CATEGORIES).all()
    assert any("proportional-odds" in warning.lower() for warning in result["warnings"])


def test_ordinal_logistic_excludes_missing_values_without_mutating_input():
    frame = _ordinal_data()
    original = frame.copy(deep=True)
    frame.loc[0, "support_score"] = np.nan
    frame.loc[1, "rating"] = None
    expected = frame.copy(deep=True)
    result = run_ordinal_logistic_regression(frame, ["support_score"], "rating", CATEGORIES)
    assert result["metadata"]["valid_n"] == len(frame) - 2
    assert result["metadata"]["excluded_n"] == 2
    pd.testing.assert_frame_equal(frame, expected)
    assert len(original) == len(frame)


def test_ordinal_logistic_requires_explicit_complete_category_order():
    frame = _ordinal_data()
    with pytest.raises(ValueError, match="complete order"):
        run_ordinal_logistic_regression(frame, ["support_score"], "rating", None)
    with pytest.raises(ValueError, match="include every observed"):
        run_ordinal_logistic_regression(frame, ["support_score"], "rating", ["Low", "High", "Other"])


def test_ordinal_logistic_rejects_invalid_predictors_and_outcomes():
    frame = _ordinal_data()
    with pytest.raises(ValueError, match="cannot also be a predictor"):
        run_ordinal_logistic_regression(frame, ["support_score", "rating"], "rating", CATEGORIES)
    frame["text_predictor"] = "not numeric"
    with pytest.raises(ValueError, match="must be numeric"):
        run_ordinal_logistic_regression(frame, ["text_predictor"], "rating", CATEGORIES)
    with pytest.raises(ValueError, match="collinear"):
        frame["duplicate_support"] = frame["support_score"] * 2
        run_ordinal_logistic_regression(frame, ["support_score", "duplicate_support"], "rating", CATEGORIES)


def test_ordinal_logistic_rejects_sparse_category_counts():
    frame = _ordinal_data()
    frame["rating"] = "Low"
    frame.loc[:2, "rating"] = "Moderate"
    frame.loc[3:5, "rating"] = "High"
    with pytest.raises(ValueError, match="At least five"):
        run_ordinal_logistic_regression(frame, ["support_score"], "rating", CATEGORIES)
