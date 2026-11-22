import pandas as pd
import pytest

from timan_intelligence.services.analysis_service import run_survey_weighting_service


def test_weighting_service_constructs_base_weights_and_diagnostics():
    frame = pd.DataFrame({
        "unit": ["a", "b", "c", "d"],
        "pi": [0.5, 0.25, 0.5, 1.0],
    })
    result = run_survey_weighting_service(frame, "pi")
    weighted = result.tables["weighted_dataset"]
    assert weighted["base_weight"].tolist() == [2.0, 4.0, 2.0, 1.0]
    assert weighted["analysis_weight"].tolist() == [2.0, 4.0, 2.0, 1.0]
    assert result.metadata["diagnostics"]["n"] == 4
    assert result.metadata["final_weight_column"] == "analysis_weight"


def test_weighting_service_zeroes_nonrespondents_after_adjustment():
    frame = pd.DataFrame({
        "pi": [0.5, 0.5, 0.5, 0.5],
        "response": [1, 0, 1, 1],
        "cell": ["A", "A", "B", "B"],
    })
    result = run_survey_weighting_service(
        frame, "pi", response_column="response", adjustment_cells=["cell"]
    )
    weighted = result.tables["weighted_dataset"]
    assert weighted.loc[1, "analysis_weight"] == 0
    assert weighted.loc[0, "analysis_weight"] == pytest.approx(4)
    assert weighted.loc[2, "analysis_weight"] == pytest.approx(8 / 3)
    assert result.metadata["diagnostics"]["n"] == 3


def test_weighting_service_rejects_invalid_probability_values():
    frame = pd.DataFrame({"pi": [0.0, 0.5]})
    with pytest.raises(ValueError, match="first-order inclusion probabilities"):
        run_survey_weighting_service(frame, "pi")


def test_weighting_service_applies_poststratification_and_raking():
    frame = pd.DataFrame({
        "pi": [0.5, 0.5, 0.5, 0.5],
        "sex": ["F", "F", "M", "M"],
        "area": ["R", "U", "R", "U"],
    })
    result = run_survey_weighting_service(
        frame, "pi",
        poststrata_column="sex",
        population_totals={"F": 60, "M": 40},
        raking_margins={"area": {"R": 50, "U": 50}},
    )
    weighted = result.tables["weighted_dataset"]
    assert weighted.loc[weighted.sex == "F", "analysis_weight"].sum() == pytest.approx(60)
    assert weighted.loc[weighted.sex == "M", "analysis_weight"].sum() == pytest.approx(40)
    assert result.metadata["raking"]["converged"]


def test_weighting_service_trims_and_reports_final_stage():
    frame = pd.DataFrame({"pi": [1.0, 0.5, 0.25, 0.01]})
    result = run_survey_weighting_service(frame, "pi", trim_quantiles=(0.1, 0.9))
    assert "trimmed_weight" in result.tables["weighted_dataset"]
    assert result.metadata["stages"][-1].startswith("Winsorised")
