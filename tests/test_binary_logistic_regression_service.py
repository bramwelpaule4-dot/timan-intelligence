import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import run_binary_logistic_regression_service


def test_logistic_service_exposes_coefficients_probabilities_and_metadata():
    rng = np.random.default_rng(123)
    x = rng.normal(size=350)
    probability = 1 / (1 + np.exp(-(-0.2 + 0.9 * x)))
    y = rng.binomial(1, probability)
    frame = pd.DataFrame({"exposure": x, "event": y})
    result = run_binary_logistic_regression_service(frame, ["exposure"], "event")
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert "fitted_data" in result.tables
    assert result.metadata["event_n"] + result.metadata["non_event_n"] == len(frame)
    assert "Odds ratio" in result.tables["coefficients"]
    assert result.limitations
