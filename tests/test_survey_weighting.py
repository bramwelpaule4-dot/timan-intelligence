import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.survey_weighting import (
    calculate_base_weights, adjust_nonresponse, calibrate_poststratification,
    rake_weights, trim_weights, weight_diagnostics,
)


def test_base_weights_are_inverse_inclusion_probabilities():
    frame = pd.DataFrame({"pi": [0.5, 0.25, 1.0]})
    assert calculate_base_weights(frame, "pi").tolist() == [2.0, 4.0, 1.0]


@pytest.mark.parametrize("values", [[0, 0.5], [1.1, 0.5], [np.nan, 0.5]])
def test_base_weight_rejects_invalid_probability(values):
    with pytest.raises(ValueError):
        calculate_base_weights(pd.DataFrame({"pi": values}), "pi")


def test_nonresponse_adjustment_by_cells():
    frame = pd.DataFrame({
        "w": [2., 2., 2., 2.], "response": [1, 0, 1, 1],
        "cell": ["A", "A", "B", "B"],
    })
    result = adjust_nonresponse(frame, "w", "response", ["cell"])
    assert result.tolist() == pytest.approx([4., 4., 8/3, 8/3])


def test_nonresponse_rejects_empty_response_cell():
    frame = pd.DataFrame({"w": [1., 1.], "r": [1, 0], "cell": ["A", "B"]})
    with pytest.raises(ValueError, match="at least one respondent"):
        adjust_nonresponse(frame, "w", "r", ["cell"])


def test_poststratification_matches_known_totals():
    frame = pd.DataFrame({"w": [1., 1., 1.], "group": ["A", "A", "B"]})
    result = calibrate_poststratification(frame, "w", "group", {"A": 80, "B": 20})
    assert result[frame.group == "A"].sum() == pytest.approx(80)
    assert result[frame.group == "B"].sum() == pytest.approx(20)


def test_raking_matches_two_margins():
    frame = pd.DataFrame({
        "w": [1.] * 4, "sex": ["F", "F", "M", "M"],
        "area": ["R", "U", "R", "U"],
    })
    targets = {"sex": {"F": 60., "M": 40.}, "area": {"R": 50., "U": 50.}}
    result, info = rake_weights(frame, "w", targets)
    assert info["converged"]
    for col, margin in targets.items():
        for category, target in margin.items():
            assert result[frame[col] == category].sum() == pytest.approx(target, abs=1e-4)


def test_trimming_preserves_total_when_requested():
    frame = pd.DataFrame({"w": [1., 2., 3., 100.]})
    result = trim_weights(frame, "w", 0.25, 0.75)
    assert result.sum() == pytest.approx(106.)
    assert result.max() < 100


def test_weight_diagnostics():
    result = weight_diagnostics(pd.Series([1., 1., 2., 2.]))
    assert result["kish_effective_sample_size"] == pytest.approx(3.6)
    assert result["kish_deff_approximation"] == pytest.approx(4 / 3.6)
