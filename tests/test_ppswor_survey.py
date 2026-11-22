import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.ppswor_survey import estimate_ppswor_total


def ppswor_fixture():
    df = pd.DataFrame({
        "stratum": ["A"] * 3,
        "psu": ["P1", "P2", "P3"],
        "total": [100.0, 200.0, 300.0],
        "pi": [0.5, 0.7, 0.8],
    })
    # Fixed-size sample of 2: pair probabilities are consistent with
    # the first-order probabilities for this three-unit frame.
    joint = pd.DataFrame(
        [[0.5, 0.2, 0.3], [0.2, 0.7, 0.5], [0.3, 0.5, 0.8]],
        index=["P1", "P2", "P3"], columns=["P1", "P2", "P3"],
    )
    return df, joint


def test_ppswor_ht_total_and_syg_variance():
    df, joint = ppswor_fixture()
    result = estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")
    expected = 100 / .5 + 200 / .7 + 300 / .8
    assert result["estimate"] == pytest.approx(expected)
    assert result["variance"] > 0
    assert result["degrees_of_freedom"] == 2
    assert len(result["pairwise_variance"]) == 3
    assert result["metadata"]["number_of_sampled_psus"] == 3


def test_ppswor_rejects_duplicate_psus_and_invalid_pi():
    df, joint = ppswor_fixture()
    df.loc[1, "psu"] = "P1"
    with pytest.raises(ValueError, match="one row per sampled PSU"):
        estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")
    df, joint = ppswor_fixture()
    df.loc[0, "pi"] = 0
    with pytest.raises(ValueError, match="between 0 and 1"):
        estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")


def test_ppswor_requires_positive_joint_probability_for_sampled_pairs():
    df, joint = ppswor_fixture()
    joint.loc["P1", "P2"] = 0
    joint.loc["P2", "P1"] = 0
    with pytest.raises(ValueError, match="positive joint inclusion"):
        estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")


def test_ppswor_validates_joint_matrix_diagonal_and_probability_bounds():
    df, joint = ppswor_fixture()
    joint.loc["P1", "P1"] = .4
    with pytest.raises(ValueError, match="diagonal"):
        estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")
    df, joint = ppswor_fixture()
    joint.loc["P1", "P2"] = .01
    joint.loc["P2", "P1"] = .01
    with pytest.raises(ValueError, match="lower bound"):
        estimate_ppswor_total(df, "total", "psu", "pi", joint, "stratum")


def test_ppswor_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_ppswor_total_service
    df, joint = ppswor_fixture()
    result = run_ppswor_total_service(df, "total", "psu", "pi", joint, "stratum")
    assert result.status == "success"
    assert result.metadata["sampling_design"] == "PPS without replacement; fixed-size sample within each stratum"
