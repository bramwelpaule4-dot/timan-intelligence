import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.two_stage_ppswor import estimate_two_stage_ppswor_total


def fixture():
    rows = []
    psus = ["P1", "P2", "P3"]
    values = [[10.0, 20.0], [30.0, 40.0], [5.0, 15.0]]
    for psu, outcomes, pi in zip(psus, values, [0.5, 0.7, 0.8]):
        for ssu, outcome in enumerate(outcomes, start=1):
            rows.append({
                "stratum": "A",
                "psu": psu,
                "ssu": ssu,
                "outcome": outcome,
                "pi": pi,
                "ssu_population": 4,
            })
    data = pd.DataFrame(rows)
    joint = pd.DataFrame(
        [[0.5, 0.2, 0.3], [0.2, 0.7, 0.5], [0.3, 0.5, 0.8]],
        index=psus, columns=psus,
    )
    return data, joint


def test_two_stage_ppswor_total_expands_both_sampling_stages():
    data, joint = fixture()
    result = estimate_two_stage_ppswor_total(
        data, "outcome", "psu", "ssu", "pi", "ssu_population",
        joint, "stratum",
    )
    expanded = [60.0, 140.0, 40.0]
    expected = sum(total / pi for total, pi in zip(expanded, [0.5, 0.7, 0.8]))
    assert result["estimate"] == pytest.approx(expected)
    assert result["variance"] == pytest.approx(
        result["variance_stage_1"] + result["variance_stage_2"]
    )
    assert result["variance_stage_1"] > 0
    assert result["variance_stage_2"] > 0
    assert result["metadata"]["number_of_sampled_psus"] == 3
    assert result["metadata"]["number_of_sampled_ssus"] == 6
    assert len(result["psu_details"]) == 3


def test_two_stage_ppswor_second_stage_variance_matches_srswor_formula():
    data, joint = fixture()
    result = estimate_two_stage_ppswor_total(
        data, "outcome", "psu", "ssu", "pi", "ssu_population",
        joint, "stratum",
    )
    expected = 0.0
    for values, pi in zip(([10.0, 20.0], [30.0, 40.0], [5.0, 15.0]), [0.5, 0.7, 0.8]):
        sample_variance = np.var(values, ddof=1)
        within_variance = 4 ** 2 * (1 - 2 / 4) * sample_variance / 2
        expected += within_variance / pi
    assert result["variance_stage_2"] == pytest.approx(expected)


def test_two_stage_ppswor_stratified_matrices_are_combined():
    data_a, joint_a = fixture()
    data_b, joint_b = fixture()
    data_b["stratum"] = "B"
    data_b["psu"] = ["Q1" if x == "P1" else "Q2" if x == "P2" else "Q3" for x in data_b["psu"]]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([data_a, data_b], ignore_index=True)
    result = estimate_two_stage_ppswor_total(
        combined, "outcome", "psu", "ssu", "pi", "ssu_population",
        {"A": joint_a, "B": joint_b}, "stratum",
    )
    assert result["metadata"]["number_of_strata"] == 2
    assert result["metadata"]["number_of_sampled_psus"] == 6
    assert len(result["pairwise_variance"]) == 6


def test_two_stage_ppswor_allows_certainty_psus():
    data, _ = fixture()
    data["pi"] = data["psu"].map({"P1": 1.0, "P2": 0.5, "P3": 0.5})
    joint = pd.DataFrame(
        [[1.0, 0.5, 0.5], [0.5, 0.5, 0.25], [0.5, 0.25, 0.5]],
        index=["P1", "P2", "P3"], columns=["P1", "P2", "P3"],
    )
    result = estimate_two_stage_ppswor_total(
        data, "outcome", "psu", "ssu", "pi", "ssu_population",
        joint, "stratum",
    )
    assert result["estimate"] > 0
    assert result["variance_stage_2"] > 0


@pytest.mark.parametrize("field,value", [
    ("pi", 0.0),
    ("pi", 1.2),
    ("ssu_population", 1),
])
def test_two_stage_ppswor_rejects_invalid_probability_or_population(field, value):
    data, joint = fixture()
    data.loc[0, field] = value
    with pytest.raises(ValueError):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )


def test_two_stage_ppswor_rejects_inconsistent_psu_probability_and_population():
    data, joint = fixture()
    data.loc[0, "pi"] = 0.6
    with pytest.raises(ValueError, match="constant within each PSU"):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )
    data, joint = fixture()
    data.loc[0, "ssu_population"] = 5
    with pytest.raises(ValueError, match="constant within each PSU"):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )


def test_two_stage_ppswor_rejects_duplicate_ssu_and_insufficient_second_stage_sample():
    data, joint = fixture()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one row per sampled SSU"):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )
    data, joint = fixture()
    data = data[data["ssu"] == 1]
    with pytest.raises(ValueError, match="At least two sampled SSUs"):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )


def test_two_stage_ppswor_rejects_missing_joint_probability_pairs():
    data, joint = fixture()
    joint.loc["P1", "P2"] = 0.0
    joint.loc["P2", "P1"] = 0.0
    with pytest.raises(ValueError, match="positive joint inclusion"):
        estimate_two_stage_ppswor_total(
            data, "outcome", "psu", "ssu", "pi", "ssu_population",
            joint, "stratum",
        )
