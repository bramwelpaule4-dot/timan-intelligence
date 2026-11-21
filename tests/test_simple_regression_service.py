import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import (
    run_simple_linear_regression_service,
)


def test_regression_service_exposes_coefficients_and_fitted_values():
    df = pd.DataFrame({
        "household_income": [10, 20, 30, 40, 50],
        "household_expenditure": [8, 15, 22, 29, 36],
    })
    result = run_simple_linear_regression_service(
        df,
        "household_income",
        "household_expenditure",
    )

    assert result.status == "success"
    assert result.metadata["slope"] == pytest.approx(0.7)
    assert result.metadata["intercept"] == pytest.approx(1.0)
    assert result.metadata["r_squared"] == pytest.approx(1.0)
    assert "coefficients" in result.tables
    assert "fitted_data" in result.tables
    assert len(result.tables["fitted_data"]) == 5
