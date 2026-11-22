import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.poisson_regression import run_poisson_regression


def _meal_counts(n=1800, seed=2026):
    rng = np.random.default_rng(seed)
    attendance = rng.normal(0, 1, n)
    age = rng.normal(35, 9, n)
    rate = np.exp(0.45 + 0.32 * attendance - 0.08 * (age - 35) / 10)
    visits = rng.poisson(rate)
    return pd.DataFrame({"attendance_score": attendance, "age": age, "household_visits": visits})


def test_poisson_regression_recovers_positive_count_rate_association():
    frame = _meal_counts()
    result = run_poisson_regression(frame, ["attendance_score", "age"], "household_visits")
    meta = result["metadata"]
    assert meta["valid_n"] == len(frame)
    assert meta["converged"]
    assert meta["dispersion"] > 0
    assert result["coefficients"].loc[
        result["coefficients"]["Variable"] == "attendance_score", "IRR"
    ].iloc[0] > 1
    assert (result["fitted_data"]["Predicted count"] > 0).all()
    assert np.isfinite(result["fitted_data"]["Predicted count"]).all()


def test_poisson_regression_supports_exposure_offset():
    rng = np.random.default_rng(44)
    n = 1400
    exposure = rng.uniform(0.5, 4.0, n)
    score = rng.normal(size=n)
    count = rng.poisson(exposure * np.exp(0.2 + 0.4 * score))
    frame = pd.DataFrame({"score": score, "person_time": exposure, "events": count})
    result = run_poisson_regression(frame, ["score"], "events", "person_time")
    assert result["metadata"]["exposure_variable"] == "person_time"
    assert result["coefficients"].loc[
        result["coefficients"]["Variable"] == "score", "IRR"
    ].iloc[0] > 1


def test_poisson_regression_excludes_missing_and_does_not_mutate_input():
    frame = _meal_counts()
    frame.loc[0, "attendance_score"] = np.nan
    original = frame.copy(deep=True)
    result = run_poisson_regression(frame, ["attendance_score"], "household_visits")
    assert result["metadata"]["excluded_n"] == 1
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("bad", [-1, 1.5])
def test_poisson_regression_rejects_non_count_outcomes(bad):
    frame = _meal_counts()
    frame["household_visits"] = frame["household_visits"].astype(float)
    frame.loc[0, "household_visits"] = bad
    with pytest.raises(ValueError, match="non-negative integer"):
        run_poisson_regression(frame, ["attendance_score"], "household_visits")


def test_poisson_regression_rejects_invalid_exposure_and_predictors():
    frame = _meal_counts()
    frame["exposure"] = 0.0
    with pytest.raises(ValueError, match="Insufficient complete"):
        run_poisson_regression(frame, ["attendance_score"], "household_visits", "exposure")
    frame["text"] = "x"
    with pytest.raises(ValueError, match="must be numeric"):
        run_poisson_regression(frame, ["text"], "household_visits")


def test_poisson_regression_flags_overdispersion():
    rng = np.random.default_rng(90)
    n = 2200
    x = rng.normal(size=n)
    latent_rate = np.exp(0.3 + 0.3 * x + rng.normal(0, 0.9, n))
    frame = pd.DataFrame({"x": x, "count": rng.poisson(latent_rate)})
    result = run_poisson_regression(frame, ["x"], "count")
    assert result["metadata"]["dispersion"] > 1.5
    assert any("overdispersion" in warning.lower() for warning in result["warnings"])
