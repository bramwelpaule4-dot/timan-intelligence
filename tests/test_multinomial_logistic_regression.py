import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.multinomial_logistic_regression import (
    run_multinomial_logistic_regression,
)


def _nominal_data(n=1800, seed=721):
    rng = np.random.default_rng(seed)
    support = rng.normal(size=n)
    age = rng.normal(34, 9, size=n)
    logits = np.column_stack([
        0.9 * support - 0.15 * (age - 34) / 9,
        -0.65 * support + 0.25 * (age - 34) / 9,
        np.zeros(n),
    ])
    probabilities = np.exp(logits - logits.max(axis=1, keepdims=True))
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    labels = np.array(["Cash assistance", "Food assistance", "No assistance"])
    outcome = [rng.choice(labels, p=row) for row in probabilities]
    return pd.DataFrame({"support_score": support, "age": age, "assistance_type": outcome})


def test_multinomial_returns_category_effects_and_valid_probabilities():
    frame = _nominal_data()
    result = run_multinomial_logistic_regression(
        frame, ["support_score", "age"], "assistance_type", "No assistance"
    )
    metadata = result["metadata"]
    probabilities = result["category_probabilities"]
    assert metadata["converged"]
    assert metadata["reference_category"] == "No assistance"
    assert metadata["valid_n"] == len(frame)
    assert list(probabilities.columns) == metadata["categories"]
    assert np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-8)
    assert probabilities.to_numpy().min() > 0
    coefficients = result["coefficients"]
    assert set(coefficients["Outcome category"]) == {"Cash assistance", "Food assistance"}
    assert set(coefficients["Variable"]) == {"Intercept", "support_score", "age"}
    cash_effect = coefficients.query(
        "`Outcome category` == 'Cash assistance' and Variable == 'support_score'"
    )["Coefficient"].iloc[0]
    food_effect = coefficients.query(
        "`Outcome category` == 'Food assistance' and Variable == 'support_score'"
    )["Coefficient"].iloc[0]
    assert cash_effect > 0
    assert food_effect < 0
    assert result["fitted_data"]["Predicted category"].isin(metadata["categories"]).all()


def test_multinomial_excludes_missing_and_reports_category_counts():
    frame = _nominal_data(n=2400, seed=722)
    frame.loc[0, "support_score"] = np.nan
    frame.loc[1, "assistance_type"] = None
    result = run_multinomial_logistic_regression(
        frame, ["support_score"], "assistance_type", "No assistance"
    )
    assert result["metadata"]["excluded_n"] == 2
    assert result["metadata"]["valid_n"] == len(frame) - 2
    assert min(result["metadata"]["category_counts"].values()) >= 5
    assert np.allclose(result["category_probabilities"].sum(axis=1), 1.0, atol=1e-8)


def test_multinomial_requires_three_categories_and_valid_reference():
    frame = _nominal_data(n=900)
    binary = frame.copy()
    binary["assistance_type"] = binary["assistance_type"].replace("Food assistance", "Cash assistance")
    with pytest.raises(ValueError, match="at least three"):
        run_multinomial_logistic_regression(binary, ["support_score"], "assistance_type")
    with pytest.raises(ValueError, match="reference category"):
        run_multinomial_logistic_regression(
            frame, ["support_score"], "assistance_type", "Other"
        )


def test_multinomial_rejects_sparse_categories_and_invalid_predictors():
    frame = _nominal_data()
    frame["assistance_type"] = "Cash assistance"
    frame.loc[:2, "assistance_type"] = "Food assistance"
    frame.loc[3:5, "assistance_type"] = "No assistance"
    with pytest.raises(ValueError, match="At least five"):
        run_multinomial_logistic_regression(frame, ["support_score"], "assistance_type")
    frame = _nominal_data()
    frame["text_predictor"] = "not numeric"
    with pytest.raises(ValueError, match="must be numeric"):
        run_multinomial_logistic_regression(frame, ["text_predictor"], "assistance_type")


@pytest.mark.parametrize("scenario,seed", [
    ("livelihood_support", 731),
    ("preferred_service_channel", 732),
    ("referral_destination", 733),
])
def test_multinomial_realistic_meal_nominal_scenarios(scenario, seed):
    """Validate nominal outcomes without imposing an artificial category order."""
    rng = np.random.default_rng(seed)
    n = 1600
    x = rng.normal(size=n)
    age = rng.normal(36, 8, size=n)
    labels = ["Agriculture", "Cash transfer", "Vocational training"]
    logits = np.column_stack([
        0.75 * x + 0.1 * (age - 36) / 8,
        -0.55 * x - 0.2 * (age - 36) / 8,
        np.zeros(n),
    ])
    probs = np.exp(logits - logits.max(axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    outcome = [rng.choice(labels, p=row) for row in probs]
    frame = pd.DataFrame({"access_score": x, "age": age, "nominal_outcome": outcome})
    result = run_multinomial_logistic_regression(
        frame, ["access_score", "age"], "nominal_outcome", "Vocational training"
    )
    fitted = result["category_probabilities"]
    assert result["metadata"]["converged"], scenario
    assert np.allclose(fitted.sum(axis=1), 1.0, atol=1e-8)
    assert result["fitted_data"]["Predicted category"].isin(labels).all()
    assert result["metadata"]["category_counts"]["Agriculture"] > 5
