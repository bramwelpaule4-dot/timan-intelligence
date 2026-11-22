import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import (
    run_multinomial_logistic_regression_service,
)


def test_multinomial_service_exposes_effects_probabilities_and_limitations():
    rng = np.random.default_rng(812)
    n = 900
    x = rng.normal(size=n)
    logits = np.column_stack([0.8 * x, -0.5 * x, np.zeros(n)])
    probs = np.exp(logits - logits.max(axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    labels = ["Agriculture", "Cash transfer", "Training"]
    outcome = [rng.choice(labels, p=row) for row in probs]
    frame = pd.DataFrame({"access_score": x, "support_type": outcome})
    result = run_multinomial_logistic_regression_service(
        frame, ["access_score"], "support_type", "Training"
    )
    assert result.status == "success"
    assert "coefficients" in result.tables
    assert "category_probabilities" in result.tables
    assert result.metadata["reference_category"] == "Training"
    assert result.assumptions
    assert result.limitations
