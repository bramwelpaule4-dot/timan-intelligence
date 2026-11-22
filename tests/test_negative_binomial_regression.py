import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.negative_binomial_regression import run_negative_binomial_regression


def _overdispersed_meal_counts(n=2200, seed=2027):
    rng = np.random.default_rng(seed)
    attendance = rng.normal(size=n)
    age = rng.normal(35, 9, n)
    alpha = 0.8
    mean = np.exp(0.35 + 0.30 * attendance - 0.04 * (age - 35) / 10)
    size = 1 / alpha
    probability = size / (size + mean)
    visits = rng.negative_binomial(size, probability)
    return pd.DataFrame({
        "attendance_score": attendance, "age": age,
        "household_visits": visits,
    })


def test_negative_binomial_recovers_association_and_detects_overdispersion():
    frame = _overdispersed_meal_counts()
    result = run_negative_binomial_regression(
        frame, ["attendance_score", "age"], "household_visits"
    )
    meta = result["metadata"]
    assert meta["valid_n"] == len(frame)
    assert meta["converged"]
    assert meta["dispersion_alpha"] > 0
    irr = result["coefficients"].set_index("Variable").loc["attendance_score", "IRR"]
    assert irr > 1
    assert np.isfinite(result["fitted_data"]["Predicted count"]).all()
    assert meta["aic"] < meta["poisson_aic"]


def test_negative_binomial_supports_exposure_offset():
    rng = np.random.default_rng(88)
    n = 1600
    exposure = rng.uniform(0.5, 4.0, n)
    score = rng.normal(size=n)
    mean = exposure * np.exp(0.2 + 0.35 * score)
    alpha = 0.6
    size = 1 / alpha
    events = rng.negative_binomial(size, size / (size + mean))
    frame = pd.DataFrame({"score": score, "person_time": exposure, "events": events})
    result = run_negative_binomial_regression(frame, ["score"], "events", "person_time")
    assert result["metadata"]["exposure_variable"] == "person_time"
    assert result["coefficients"].set_index("Variable").loc["score", "IRR"] > 1


def test_negative_binomial_handles_missing_records_without_mutating_input():
    frame = _overdispersed_meal_counts()
    frame.loc[0, "attendance_score"] = np.nan
    original = frame.copy(deep=True)
    result = run_negative_binomial_regression(frame, ["attendance_score"], "household_visits")
    assert result["metadata"]["excluded_n"] == 1
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("bad", [-1, 1.25])
def test_negative_binomial_rejects_non_count_outcomes(bad):
    frame = _overdispersed_meal_counts()
    frame["household_visits"] = frame["household_visits"].astype(float)
    frame.loc[0, "household_visits"] = bad
    with pytest.raises(ValueError, match="non-negative integer"):
        run_negative_binomial_regression(frame, ["attendance_score"], "household_visits")


def test_negative_binomial_rejects_invalid_exposure_and_collinearity():
    frame = _overdispersed_meal_counts()
    frame["bad_exposure"] = 0.0
    with pytest.raises(ValueError, match="Insufficient complete"):
        run_negative_binomial_regression(frame, ["attendance_score"], "household_visits", "bad_exposure")
    frame["attendance_copy"] = frame["attendance_score"]
    with pytest.raises(ValueError, match="collinear"):
        run_negative_binomial_regression(
            frame, ["attendance_score", "attendance_copy"], "household_visits"
        )
