import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import (
    run_cox_survival_service,
    run_kaplan_meier_service,
)


def _frame(n=750, seed=67):
    rng = np.random.default_rng(seed)
    score = rng.normal(size=n)
    event_time = rng.exponential(1 / (0.12 * np.exp(0.4 * score)))
    censor_time = rng.uniform(2, 15, n)
    return pd.DataFrame({
        "follow_up": np.minimum(event_time, censor_time),
        "status": np.where(event_time <= censor_time, "event", "censored"),
        "score": score,
    })


def test_kaplan_meier_service_returns_shared_analysis_result():
    result = run_kaplan_meier_service(
        _frame(), "follow_up", "status", "event"
    )
    assert result.status == "success"
    assert "survival_curve" in result.tables
    assert result.metadata["event_n"] > 0
    assert result.assumptions


def test_cox_service_returns_hazard_ratio_table():
    result = run_cox_survival_service(
        _frame(), ["score"], "follow_up", "status", "event"
    )
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert result.tables["coefficients"].iloc[0]["Hazard ratio"] > 1
    assert "baseline_survival" in result.tables
