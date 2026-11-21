import numpy as np
import pandas as pd

from timan_intelligence.services.analysis_service import run_regression_diagnostics_service


def test_regression_diagnostics_service_exposes_diagnostic_tables():
    x1 = np.linspace(1, 10, 30)
    x2 = np.sin(x1)
    y = 2 + 3 * x1 - x2 + np.cos(x1 * 2) * 0.1
    design = np.column_stack([np.ones(len(x1)), x1, x2])
    fitted = design @ np.linalg.lstsq(design, y, rcond=None)[0]
    frame = pd.DataFrame({
        "x1": x1, "x2": x2, "outcome": y,
        "Fitted outcome": fitted, "Residual": y - fitted,
    })
    result = run_regression_diagnostics_service(frame, ["x1", "x2"], "outcome")
    assert result.status == "success"
    assert "diagnostics" in result.tables
    assert "influential_observations" in result.tables
    assert result.metadata["valid_n"] == 30
    assert result.limitations
