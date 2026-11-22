import pandas as pd
import pytest

from timan_intelligence.core.categorical_model_recommender import (
    recommend_categorical_outcome_model,
)


def test_two_category_outcome_recommends_binary_logistic():
    frame = pd.DataFrame({"completed": ["Yes"] * 30 + ["No"] * 25})
    result = recommend_categorical_outcome_model(frame, "completed")
    assert result["recommended_model"] == "binary_logistic"
    assert result["category_structure"] == "binary"
    assert result["status"] == "ready"
    assert sum(result["category_counts"].values()) == 55


def test_three_category_outcome_requires_analyst_classification():
    frame = pd.DataFrame({"satisfaction": ["Low", "Medium", "High"] * 20})
    result = recommend_categorical_outcome_model(frame, "satisfaction")
    assert result["status"] == "needs_classification"
    assert result["recommended_model"] is None


def test_ordered_outcome_recommends_ordinal_without_guessing_order():
    frame = pd.DataFrame({"food_security": ["Secure", "Severe", "Moderate"] * 30})
    result = recommend_categorical_outcome_model(frame, "food_security", "ordered")
    assert result["recommended_model"] == "ordinal_logistic"
    assert any("proportional-odds" in warning for warning in result["warnings"])


def test_unordered_outcome_recommends_multinomial():
    frame = pd.DataFrame({"service_type": ["Cash", "Food", "Training"] * 30})
    result = recommend_categorical_outcome_model(frame, "service_type", "nominal")
    assert result["recommended_model"] == "multinomial_logistic"


def test_missing_and_sparse_outcome_categories_are_reported():
    frame = pd.DataFrame({"outcome": ["A"] * 25 + ["B"] * 10 + ["C"] * 2 + [None]})
    result = recommend_categorical_outcome_model(frame, "outcome", "nominal")
    assert result["missing_n"] == 1
    assert result["valid_n"] == 37
    assert any("fewer than 20" in warning for warning in result["warnings"])


def test_constant_outcome_is_not_suitable():
    frame = pd.DataFrame({"outcome": ["Only"] * 12})
    result = recommend_categorical_outcome_model(frame, "outcome")
    assert result["status"] == "not_suitable"
    assert result["recommended_model"] is None


def test_invalid_order_classification_is_rejected_for_binary_outcome():
    frame = pd.DataFrame({"outcome": ["Yes", "No"] * 20})
    with pytest.raises(ValueError, match="two-category"):
        recommend_categorical_outcome_model(frame, "outcome", "ordered")
