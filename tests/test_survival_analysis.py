import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.survival_analysis import (
    run_cox_proportional_hazards,
    run_kaplan_meier,
)


def _survival_meal_data(n=1200, seed=2028):
    rng = np.random.default_rng(seed)
    training = rng.normal(size=n)
    rate = 0.08 * np.exp(0.45 * training)
    event_time = rng.exponential(1 / rate)
    censor_time = rng.uniform(3, 18, size=n)
    observed_time = np.minimum(event_time, censor_time)
    event = np.where(event_time <= censor_time, "employed", "censored")
    return pd.DataFrame({
        "time_to_employment": observed_time,
        "status": event,
        "training_score": training,
    })


def test_kaplan_meier_estimates_survival_and_censoring():
    frame = _survival_meal_data()
    result = run_kaplan_meier(
        frame, "time_to_employment", "status", "employed"
    )
    curve = result["survival_curve"]
    assert not curve.empty
    assert result["metadata"]["valid_n"] == len(frame)
    assert result["metadata"]["event_n"] > 0
    assert curve["Survival probability"].between(0, 1).all()
    assert curve["Survival probability"].is_monotonic_decreasing
    assert result["metadata"]["censored_n"] > 0


def test_kaplan_meier_two_group_logrank():
    frame = _survival_meal_data()
    frame["programme"] = np.where(frame["training_score"] > 0, "intensive", "standard")
    result = run_kaplan_meier(
        frame, "time_to_employment", "status", "employed", "programme"
    )
    assert "group_survival_curves" in result["tables"]
    assert result["metadata"]["logrank_test"]["degrees_freedom"] == 1
    assert 0 <= result["metadata"]["logrank_test"]["p_value"] <= 1


def test_cox_model_recovers_positive_hazard_association():
    frame = _survival_meal_data()
    result = run_cox_proportional_hazards(
        frame, ["training_score"], "time_to_employment", "status", "employed"
    )
    coefficient = result["coefficients"].iloc[0]
    assert coefficient["Hazard ratio"] > 1
    assert result["metadata"]["valid_n"] == len(frame)
    assert not result["baseline_survival"].empty
    assert result["metadata"]["event_n"] > 20


def test_survival_rejects_negative_time_and_no_event():
    frame = _survival_meal_data()
    frame.loc[0, "time_to_employment"] = -1
    with pytest.raises(ValueError, match="non-negative"):
        run_kaplan_meier(frame, "time_to_employment", "status", "employed")
    frame = _survival_meal_data()
    frame["status"] = "censored"
    with pytest.raises(ValueError, match="No events"):
        run_kaplan_meier(frame, "time_to_employment", "status", "employed")


def test_cox_rejects_constant_predictor_and_preserves_input():
    frame = _survival_meal_data()
    frame["constant"] = 1.0
    original = frame.copy(deep=True)
    with pytest.raises(ValueError, match="constant"):
        run_cox_proportional_hazards(
            frame, ["constant"], "time_to_employment", "status", "employed"
        )
    pd.testing.assert_frame_equal(frame, original)
