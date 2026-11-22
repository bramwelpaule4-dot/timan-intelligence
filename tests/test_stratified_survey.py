import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.stratified_survey import (
    stratified_weighted_frequencies,
    stratified_weighted_mean,
)


def _sample():
    return pd.DataFrame({
        "stratum": ["Urban"] * 4 + ["Rural"] * 4,
        "weight": [10.0] * 4 + [20.0] * 4,
        "income": [10.0, 12.0, 14.0, 16.0, 4.0, 6.0, 8.0, 10.0],
        "uptake": ["Yes", "Yes", "No", "No", "Yes", "No", "No", "No"],
    })


def test_stratified_weighted_mean_and_se_match_hand_calculation():
    result = stratified_weighted_mean(_sample(), "income", "weight", "stratum")
    row = result["table"].iloc[0]
    # Urban mean=13, rural mean=7; population shares are 40/120 and 80/120.
    assert row["stratified_weighted_mean"] == pytest.approx(9.0)
    # Both within-stratum sample variances equal 20/3; n=4 each.
    expected_variance = (1 / 3) ** 2 * (20 / 3) / 4 + (2 / 3) ** 2 * (20 / 3) / 4
    assert row["standard_error"] == pytest.approx(np.sqrt(expected_variance))
    assert row["ci_lower"] < 9.0 < row["ci_upper"]
    assert result["metadata"]["number_of_strata"] == 2


def test_stratified_weighted_frequencies_include_confidence_intervals():
    result = stratified_weighted_frequencies(
        _sample(), "uptake", "weight", "stratum"
    )
    table = result["table"].set_index("response")
    assert table.loc["Yes", "weighted_percent"] == pytest.approx(33.333333)
    assert table.loc["No", "weighted_percent"] == pytest.approx(66.666667)
    assert table.loc["Yes", "ci_lower_percent"] < table.loc["Yes", "weighted_percent"]
    assert table.loc["Yes", "ci_upper_percent"] > table.loc["Yes", "weighted_percent"]


def test_rejects_weights_that_vary_within_stratum():
    df = _sample()
    df.loc[0, "weight"] = 11.0
    with pytest.raises(ValueError, match="constant expansion weight"):
        stratified_weighted_mean(df, "income", "weight", "stratum")


def test_rejects_stratum_with_only_one_complete_record():
    df = _sample()
    df.loc[0:2, "income"] = np.nan
    with pytest.raises(ValueError, match="At least two"):
        stratified_weighted_mean(df, "income", "weight", "stratum")


def test_rejects_missing_stratum_identifiers():
    df = _sample()
    df.loc[0, "stratum"] = None
    with pytest.raises(ValueError, match="Stratum identifiers"):
        stratified_weighted_mean(df, "income", "weight", "stratum")


def test_rejects_non_numeric_mean_outcome():
    df = _sample()
    with pytest.raises(TypeError, match="must be numeric"):
        stratified_weighted_mean(df, "uptake", "weight", "stratum")


def test_confidence_level_must_be_valid():
    with pytest.raises(ValueError, match="Confidence level"):
        stratified_weighted_mean(_sample(), "income", "weight", "stratum", 1.0)
