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
    with pytest.raises(ValueError, match=r"\(0, 1\]"):
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



def test_ppswor_combines_stratum_specific_totals_and_syg_variances():
    df_a, joint_a = ppswor_fixture()
    df_b, joint_b = ppswor_fixture()
    df_a["stratum"] = "A"
    df_b["stratum"] = "B"
    df_b["psu"] = ["Q1", "Q2", "Q3"]
    df_b["total"] = [50.0, 80.0, 120.0]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([df_a, df_b], ignore_index=True)

    result = estimate_ppswor_total(
        combined, "total", "psu", "pi",
        {"A": joint_a, "B": joint_b}, "stratum",
    )

    expected_a = 100 / .5 + 200 / .7 + 300 / .8
    expected_b = 50 / .5 + 80 / .7 + 120 / .8
    assert result["estimate"] == pytest.approx(expected_a + expected_b)
    assert result["variance"] == pytest.approx(
        result["strata"]["estimated_variance"].sum()
    )
    assert result["degrees_of_freedom"] == 4
    assert result["metadata"]["number_of_strata"] == 2
    assert len(result["pairwise_variance"]) == 6


def test_ppswor_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_ppswor_total_service
    df, joint = ppswor_fixture()
    result = run_ppswor_total_service(df, "total", "psu", "pi", joint, "stratum")
    assert result.status == "success"
    assert result.metadata["sampling_design"] == "PPS without replacement; fixed-size sample within each stratum"


def test_ppswor_ratio_mean_uses_taylor_linearised_syg_variance():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_ratio
    df, joint = ppswor_fixture()
    df["numerator"] = [20.0, 40.0, 90.0]
    df["denominator"] = [10.0, 20.0, 30.0]
    result = estimate_ppswor_ratio(
        df, "numerator", "denominator", "psu", "pi", joint, "stratum",
        parameter="mean",
    )
    expected = (20 / .5 + 40 / .7 + 90 / .8) / (10 / .5 + 20 / .7 + 30 / .8)
    assert result["estimate"] == pytest.approx(expected)
    assert result["variance"] > 0
    assert result["standard_error"] == pytest.approx(np.sqrt(result["variance"]))
    assert result["metadata"]["parameter"] == "mean"
    assert len(result["pairwise_variance"]) == 3
    assert "stratum_ratio" in result["strata"]


def test_ppswor_ratio_proportion_and_stratum_combination():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_ratio
    df_a, joint_a = ppswor_fixture()
    df_b, joint_b = ppswor_fixture()
    df_a["numerator"] = [2.0, 5.0, 8.0]
    df_a["denominator"] = [10.0, 20.0, 30.0]
    df_b["stratum"] = "B"
    df_b["psu"] = ["Q1", "Q2", "Q3"]
    df_b["numerator"] = [1.0, 3.0, 6.0]
    df_b["denominator"] = [8.0, 12.0, 24.0]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([df_a, df_b], ignore_index=True)
    result = estimate_ppswor_ratio(
        combined, "numerator", "denominator", "psu", "pi",
        {"A": joint_a, "B": joint_b}, "stratum", parameter="proportion",
    )
    expected_num = (2 / .5 + 5 / .7 + 8 / .8) + (1 / .5 + 3 / .7 + 6 / .8)
    expected_den = (10 / .5 + 20 / .7 + 30 / .8) + (8 / .5 + 12 / .7 + 24 / .8)
    assert result["estimate"] == pytest.approx(expected_num / expected_den)
    assert result["metadata"]["number_of_strata"] == 2
    assert result["degrees_of_freedom"] == 4


def test_ppswor_ratio_rejects_invalid_denominator_and_proportion_totals():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_ratio
    df, joint = ppswor_fixture()
    df["numerator"] = [2.0, 5.0, 8.0]
    df["denominator"] = [10.0, -1.0, 30.0]
    with pytest.raises(ValueError, match="non-negative"):
        estimate_ppswor_ratio(
            df, "numerator", "denominator", "psu", "pi", joint, "stratum"
        )
    df["denominator"] = [10.0, 20.0, 30.0]
    df["numerator"] = [2.0, 25.0, 8.0]
    with pytest.raises(ValueError, match="between zero"):
        estimate_ppswor_ratio(
            df, "numerator", "denominator", "psu", "pi", joint, "stratum",
            parameter="proportion",
        )


def test_ppswor_ratio_service_returns_shared_analysis_result():
    from timan_intelligence.services.analysis_service import run_ppswor_ratio_service
    df, joint = ppswor_fixture()
    df["numerator"] = [20.0, 40.0, 90.0]
    df["denominator"] = [10.0, 20.0, 30.0]
    result = run_ppswor_ratio_service(
        df, "numerator", "denominator", "psu", "pi", joint, "stratum"
    )
    assert result.status == "success"
    assert result.metadata["parameter"] == "mean"


def test_ppswor_domain_ratio_retains_zero_domain_psus_and_design_variance():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio
    df, joint = ppswor_fixture()
    df["domain_num"] = [10.0, 0.0, 30.0]
    df["domain_den"] = [5.0, 0.0, 10.0]
    result = estimate_ppswor_domain_ratio(
        df, "Women", "domain_num", "domain_den", "psu", "pi",
        joint, "stratum", parameter="mean",
    )
    expected = (10 / .5 + 0 / .7 + 30 / .8) / (5 / .5 + 0 / .7 + 10 / .8)
    assert result["estimate"] == pytest.approx(expected)
    assert result["variance"] > 0
    assert result["metadata"]["domain_estimation"] is True
    assert result["metadata"]["domain_name"] == "Women"
    assert len(result["pairwise_variance"]) == 3
    assert any("Do not filter" in warning for warning in result["warnings"])


def test_ppswor_domain_ratio_rejects_missing_domain_name():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio
    df, joint = ppswor_fixture()
    df["domain_num"] = [10.0, 20.0, 30.0]
    df["domain_den"] = [5.0, 10.0, 15.0]
    with pytest.raises(ValueError, match="domain name"):
        estimate_ppswor_domain_ratio(
            df, " ", "domain_num", "domain_den", "psu", "pi", joint, "stratum"
        )


def test_ppswor_domain_ratio_service_returns_domain_metadata():
    from timan_intelligence.services.analysis_service import run_ppswor_domain_ratio_service
    df, joint = ppswor_fixture()
    df["domain_num"] = [2.0, 0.0, 8.0]
    df["domain_den"] = [10.0, 0.0, 20.0]
    result = run_ppswor_domain_ratio_service(
        df, "Youth", "domain_num", "domain_den", "psu", "pi", joint, "stratum",
        parameter="proportion",
    )
    assert result.status == "success"
    assert result.metadata["domain_name"] == "Youth"
    assert result.metadata["domain_estimation"] is True


def test_ppswor_domain_variance_uses_all_psus_including_zero_domain_units():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio

    df, joint = ppswor_fixture()
    df["domain_num"] = [10.0, 0.0, 30.0]
    df["domain_den"] = [5.0, 0.0, 10.0]
    result = estimate_ppswor_domain_ratio(
        df, "Women", "domain_num", "domain_den", "psu", "pi",
        joint, "stratum", parameter="mean",
    )
    ratio = result["estimate"]
    denominator_hat = 5 / .5 + 0 / .7 + 10 / .8
    z = np.array([10.0, 0.0, 30.0]) - ratio * np.array([5.0, 0.0, 10.0])
    pi = np.array([.5, .7, .8])
    pij = joint.to_numpy(dtype=float)
    expected_linearised_variance = 0.0
    for i in range(3):
        for j in range(i + 1, 3):
            expected_linearised_variance += -(
                (pij[i, j] - pi[i] * pi[j]) / pij[i, j]
            ) * (z[i] / pi[i] - z[j] / pi[j]) ** 2
    expected_ratio_variance = expected_linearised_variance / denominator_hat**2

    assert result["variance"] == pytest.approx(expected_ratio_variance)
    assert len(result["pairwise_variance"]) == 3
    assert set(result["pairwise_variance"]["psu_i"]) | set(
        result["pairwise_variance"]["psu_j"]
    ) == {"P1", "P2", "P3"}


def test_ppswor_domain_ratio_rejects_zero_estimated_domain_denominator():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio

    df, joint = ppswor_fixture()
    df["domain_num"] = [0.0, 0.0, 0.0]
    df["domain_den"] = [0.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="denominator must be positive"):
        estimate_ppswor_domain_ratio(
            df, "No members", "domain_num", "domain_den",
            "psu", "pi", joint, "stratum", parameter="mean",
        )


def test_ppswor_stratified_domain_ratio_combines_strata_and_full_pair_sets():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio

    df_a, joint_a = ppswor_fixture()
    df_b, joint_b = ppswor_fixture()
    df_a["domain_num"] = [2.0, 0.0, 8.0]
    df_a["domain_den"] = [10.0, 0.0, 20.0]
    df_b["stratum"] = "B"
    df_b["psu"] = ["Q1", "Q2", "Q3"]
    df_b["domain_num"] = [1.0, 3.0, 0.0]
    df_b["domain_den"] = [5.0, 15.0, 0.0]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([df_a, df_b], ignore_index=True)

    result = estimate_ppswor_domain_ratio(
        combined, "Youth", "domain_num", "domain_den", "psu", "pi",
        {"A": joint_a, "B": joint_b}, "stratum", parameter="proportion",
    )
    expected_num = (2 / .5 + 0 / .7 + 8 / .8) + (1 / .5 + 3 / .7 + 0 / .8)
    expected_den = (10 / .5 + 0 / .7 + 20 / .8) + (5 / .5 + 15 / .7 + 0 / .8)

    assert result["estimate"] == pytest.approx(expected_num / expected_den)
    assert result["metadata"]["number_of_strata"] == 2
    assert len(result["pairwise_variance"]) == 6


def test_ppswor_domain_total_uses_all_sampled_psus_and_syg_pairs():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    df, joint = ppswor_fixture()
    df["domain_total"] = [10.0, 0.0, 30.0]
    result = estimate_ppswor_domain_total(
        df, "Women", "domain_total", "psu", "pi", joint, "stratum",
    )
    expected_total = 10 / .5 + 0 / .7 + 30 / .8
    assert result["estimate"] == pytest.approx(expected_total)
    assert result["variance"] > 0
    assert len(result["pairwise_variance"]) == 3
    assert set(result["pairwise_variance"]["psu_i"]) | set(
        result["pairwise_variance"]["psu_j"]
    ) == {"P1", "P2", "P3"}
    assert result["metadata"]["domain_parameter"] == "total"
    assert result["metadata"]["domain_estimation"] is True
    assert any("Do not filter" in warning for warning in result["warnings"])


def test_ppswor_stratified_domain_total_combines_stratum_estimates_and_variances():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    df_a, joint_a = ppswor_fixture()
    df_b, joint_b = ppswor_fixture()
    df_a["domain_total"] = [10.0, 0.0, 30.0]
    df_b["stratum"] = "B"
    df_b["psu"] = ["Q1", "Q2", "Q3"]
    df_b["domain_total"] = [5.0, 15.0, 0.0]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([df_a, df_b], ignore_index=True)

    result = estimate_ppswor_domain_total(
        combined, "Youth", "domain_total", "psu", "pi",
        {"A": joint_a, "B": joint_b}, "stratum",
    )
    expected = (10 / .5 + 0 / .7 + 30 / .8) + (5 / .5 + 15 / .7 + 0 / .8)
    assert result["estimate"] == pytest.approx(expected)
    assert result["metadata"]["number_of_strata"] == 2
    assert len(result["pairwise_variance"]) == 6


def test_ppswor_domain_total_rejects_missing_domain_name():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    df, joint = ppswor_fixture()
    df["domain_total"] = [1.0, 0.0, 3.0]
    with pytest.raises(ValueError, match="domain name"):
        estimate_ppswor_domain_total(
            df, " ", "domain_total", "psu", "pi", joint, "stratum",
        )


def test_ppswor_domain_total_service_returns_domain_metadata():
    from timan_intelligence.services.analysis_service import run_ppswor_domain_total_service

    df, joint = ppswor_fixture()
    df["domain_total"] = [10.0, 0.0, 30.0]
    result = run_ppswor_domain_total_service(
        df, "Women", "domain_total", "psu", "pi", joint, "stratum",
    )
    assert result.status == "success"
    assert result.metadata["domain_name"] == "Women"
    assert result.metadata["domain_parameter"] == "total"
    assert result.metadata["domain_estimation"] is True
    assert len(result.tables["pairwise_variance"]) == 3



def test_ppswor_domain_total_reports_precision_and_zero_value_diagnostics():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    df, joint = ppswor_fixture()
    df["domain_total"] = [10.0, 0.0, 30.0]
    result = estimate_ppswor_domain_total(
        df, "Women", "domain_total", "psu", "pi", joint, "stratum",
    )

    diagnostics = result["diagnostics"].iloc[0]
    assert diagnostics["sampled_psus"] == 3
    assert diagnostics["psus_with_zero_domain_value"] == 1
    assert diagnostics["zero_domain_value_percent"] == pytest.approx(100 / 3)
    assert diagnostics["coefficient_of_variation_percent"] == pytest.approx(
        result["standard_error"] / abs(result["estimate"]) * 100
    )
    assert result["strata"]["variance_share_percent"].sum() == pytest.approx(100)
    assert result["pairwise_variance"]["variance_share_percent"].sum() == pytest.approx(100)
    assert "precision_diagnostics" in result["metadata"]
    assert any("zero" in warning.lower() for warning in result["warnings"])


def test_ppswor_domain_ratio_reports_zero_denominators_and_linearised_variance_shares():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_ratio

    df_a, joint_a = ppswor_fixture()
    df_b, joint_b = ppswor_fixture()
    df_a["domain_num"] = [2.0, 0.0, 8.0]
    df_a["domain_den"] = [10.0, 0.0, 20.0]
    df_b["stratum"] = "B"
    df_b["psu"] = ["Q1", "Q2", "Q3"]
    df_b["domain_num"] = [1.0, 3.0, 0.0]
    df_b["domain_den"] = [5.0, 15.0, 0.0]
    joint_b.index = ["Q1", "Q2", "Q3"]
    joint_b.columns = ["Q1", "Q2", "Q3"]
    combined = pd.concat([df_a, df_b], ignore_index=True)

    result = estimate_ppswor_domain_ratio(
        combined, "Youth", "domain_num", "domain_den", "psu", "pi",
        {"A": joint_a, "B": joint_b}, "stratum", parameter="proportion",
    )
    diagnostics = result["diagnostics"].iloc[0]
    assert diagnostics["psus_with_zero_domain_value"] == 2
    assert diagnostics["sampled_psus"] == 6
    assert result["strata"]["variance_share_percent"].sum() == pytest.approx(100)
    assert result["pairwise_variance"]["variance_share_percent"].sum() == pytest.approx(100)
    assert result["strata"]["estimated_ratio_variance"].sum() == pytest.approx(
        result["variance"]
    )
    assert "precision_diagnostics" in result["metadata"]


def test_ppswor_domain_total_zero_estimate_has_undefined_cv_not_infinite_value():
    from timan_intelligence.core.ppswor_survey import estimate_ppswor_domain_total

    df, joint = ppswor_fixture()
    df["domain_total"] = [0.0, 0.0, 0.0]
    result = estimate_ppswor_domain_total(
        df, "Empty domain", "domain_total", "psu", "pi", joint, "stratum",
    )
    diagnostics = result["diagnostics"].iloc[0]
    assert result["estimate"] == pytest.approx(0.0)
    assert diagnostics["coefficient_of_variation_percent"] is None
    assert diagnostics["relative_confidence_interval_half_width_percent"] is None


def test_ppswor_domain_total_service_exposes_diagnostics_table():
    from timan_intelligence.services.analysis_service import run_ppswor_domain_total_service

    df, joint = ppswor_fixture()
    df["domain_total"] = [10.0, 0.0, 30.0]
    result = run_ppswor_domain_total_service(
        df, "Women", "domain_total", "psu", "pi", joint, "stratum",
    )
    assert "diagnostics" in result.tables
    assert result.tables["diagnostics"].iloc[0]["psus_with_zero_domain_value"] == 1



def test_ppswor_domain_ratio_service_exposes_precision_diagnostics():
    from timan_intelligence.services.analysis_service import run_ppswor_domain_ratio_service

    df, joint = ppswor_fixture()
    df["domain_num"] = [2.0, 0.0, 8.0]
    df["domain_den"] = [10.0, 0.0, 20.0]
    result = run_ppswor_domain_ratio_service(
        df, "Youth", "domain_num", "domain_den", "psu", "pi",
        joint, "stratum", parameter="proportion",
    )
    assert "diagnostics" in result.tables
    assert result.tables["diagnostics"].iloc[0]["sampled_psus"] == 3
    assert "coefficient_of_variation_percent" in result.metadata["precision_diagnostics"]
