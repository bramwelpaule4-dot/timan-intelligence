import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import run_poisson_regression_service


def test_poisson_regression_service_returns_shared_analysis_result():
    rng = np.random.default_rng(17)
    x = rng.normal(size=500)
    frame = pd.DataFrame({"score": x, "events": rng.poisson(np.exp(0.2 + 0.3 * x))})
    result = run_poisson_regression_service(frame, ["score"], "events")
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert "fitted_data" in result.tables
    assert result.metadata["valid_n"] == len(frame)
    assert result.assumptions
