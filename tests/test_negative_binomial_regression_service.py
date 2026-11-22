import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import run_negative_binomial_regression_service


def test_negative_binomial_service_returns_shared_analysis_result():
    rng = np.random.default_rng(29)
    x = rng.normal(size=900)
    mean = np.exp(0.25 + 0.3 * x)
    alpha = 0.7
    size = 1 / alpha
    count = rng.negative_binomial(size, size / (size + mean))
    frame = pd.DataFrame({"score": x, "events": count})
    result = run_negative_binomial_regression_service(frame, ["score"], "events")
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert "fitted_data" in result.tables
    assert result.metadata["valid_n"] == len(frame)
    assert result.metadata["dispersion_alpha"] > 0
    assert result.assumptions
