import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_multiple_linear_regression_service,
)


def test_multiple_regression_service_exposes_model_tables_and_metadata():
    df = pd.DataFrame({
        "experience": [1, 2, 3, 4, 5, 6, 7],
        "training": [2, 5, 3, 7, 4, 8, 6],
    })
    df["productivity"] = 10 + 3 * df["experience"] + 2 * df["training"]
    result = run_multiple_linear_regression_service(
        df,
        ["experience", "training"],
        "productivity",
    )

    assert result.status == "success"
    assert result.metadata["predictor_count"] == 2
    assert result.metadata["r_squared"] == pytest.approx(1.0)
    assert "coefficients" in result.tables
    assert "fitted_data" in result.tables
    coefficients = result.tables["coefficients"].set_index("Variable")
    assert coefficients.loc["experience", "Estimate"] == pytest.approx(3.0)
    assert coefficients.loc["training", "Estimate"] == pytest.approx(2.0)
