import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import run_ordinal_logistic_regression_service


def test_ordinal_logistic_service_exposes_results_assumptions_and_metadata():
    rng = np.random.default_rng(301)
    x = rng.normal(size=600)
    latent = 0.8 * x + rng.logistic(size=600)
    outcome = np.where(latent < -0.7, "Low", np.where(latent < 0.7, "Moderate", "High"))
    frame = pd.DataFrame({"programme_support": x, "satisfaction": outcome})
    result = run_ordinal_logistic_regression_service(
        frame, ["programme_support"], "satisfaction", ["Low", "Moderate", "High"]
    )
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert "category_probabilities" in result.tables
    assert result.metadata["ordered_categories"] == ["Low", "Moderate", "High"]
    assert result.assumptions
    assert result.limitations
