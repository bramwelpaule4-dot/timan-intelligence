import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.survey_weights import (
    weighted_frequency_table,
    weighted_numeric_summary,
)


def test_weighted_frequency_uses_weighted_denominator():
    df = pd.DataFrame({
        "response": ["Yes", "Yes", "No"],
        "weight": [2.0, 3.0, 5.0],
    })
    result = weighted_frequency_table(df, "response", "weight")
    table = result["table"].set_index("response")
    assert table.loc["Yes", "weighted_count"] == pytest.approx(5.0)
    assert table.loc["No", "weighted_count"] == pytest.approx(5.0)
    assert table.loc["Yes", "weighted_percent"] == pytest.approx(50.0)
    assert result["metadata"]["effective_sample_size_kish"] == pytest.approx(100.0 / 38.0)


def test_weighted_frequency_can_include_nonresponse():
    df = pd.DataFrame({
        "response": ["Yes", None, "No"],
        "weight": [2.0, 3.0, 5.0],
    })
    result = weighted_frequency_table(df, "response", "weight", include_missing=True)
    table = result["table"].set_index("response")
    assert table.loc["No response", "weighted_count"] == pytest.approx(3.0)
    assert result["metadata"]["weighted_denominator"] == pytest.approx(10.0)


def test_weighted_frequency_excludes_missing_outcome_by_default():
    df = pd.DataFrame({
        "response": ["Yes", None, "No"],
        "weight": [2.0, 3.0, 5.0],
    })
    result = weighted_frequency_table(df, "response", "weight")
    assert result["metadata"]["weighted_denominator"] == pytest.approx(7.0)
    assert result["metadata"]["records_excluded_missing_outcome"] == 1


def test_weighted_numeric_summary_matches_hand_calculation():
    df = pd.DataFrame({
        "income": [10.0, 20.0, 30.0],
        "weight": [1.0, 2.0, 1.0],
    })
    result = weighted_numeric_summary(df, "income", "weight")
    row = result["table"].iloc[0]
    assert row["weighted_mean"] == pytest.approx(20.0)
    assert row["weighted_total"] == pytest.approx(80.0)
    assert row["weighted_standard_deviation"] == pytest.approx(np.sqrt(50.0))


def test_missing_weights_and_outcomes_are_excluded_without_mutation():
    df = pd.DataFrame({
        "income": [10.0, None, 30.0],
        "weight": [1.0, 2.0, None],
    })
    original = df.copy(deep=True)
    result = weighted_numeric_summary(df, "income", "weight")
    assert result["metadata"]["records_used"] == 1
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("weights", [[0.0, 1.0], [-1.0, 2.0], [np.inf, 1.0]])
def test_invalid_observed_weights_are_rejected(weights):
    df = pd.DataFrame({"outcome": ["A", "B"], "weight": weights})
    with pytest.raises(ValueError):
        weighted_frequency_table(df, "outcome", "weight")


def test_weight_variable_must_be_numeric():
    df = pd.DataFrame({"outcome": ["A", "B"], "weight": ["1", "2"]})
    with pytest.raises(TypeError):
        weighted_frequency_table(df, "outcome", "weight")


def test_outcome_and_weight_must_differ():
    df = pd.DataFrame({"value": [1.0, 2.0]})
    with pytest.raises(ValueError):
        weighted_numeric_summary(df, "value", "value")


def test_numeric_summary_rejects_non_numeric_outcome():
    df = pd.DataFrame({"outcome": ["low", "high"], "weight": [1.0, 2.0]})
    with pytest.raises(TypeError):
        weighted_numeric_summary(df, "outcome", "weight")
