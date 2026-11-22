import pandas as pd
import pytest

from timan_intelligence.core.sample_size import (
    allocate_stratified_sample,
    calculate_sample_size,
    plan_cluster_sample,
)


def test_proportion_sample_size_with_fpc_design_and_nonresponse():
    result = calculate_sample_size(
        parameter="proportion", confidence_level=.95, margin_of_error=.05,
        population_size=1000, prevalence=.5, design_effect=1.5,
        nonresponse_rate=.1,
    )
    assert result["base_sample_size"] == 385
    assert result["finite_population_correction_applied"] is True
    assert result["recommended_sample_size"] > result["sample_size_after_design_effect"]
    assert result["recommended_sample_size"] <= 1000


def test_mean_sample_size_requires_standard_deviation():
    with pytest.raises(ValueError, match="standard_deviation"):
        calculate_sample_size(parameter="mean")
    result = calculate_sample_size(parameter="mean", standard_deviation=12, margin_of_error=2)
    assert result["recommended_sample_size"] > 0


def test_sample_size_validates_inputs():
    with pytest.raises(ValueError, match="confidence_level"):
        calculate_sample_size(confidence_level=1)
    with pytest.raises(ValueError, match="prevalence"):
        calculate_sample_size(prevalence=1.2)
    with pytest.raises(ValueError, match="nonresponse_rate"):
        calculate_sample_size(nonresponse_rate=1)


@pytest.mark.parametrize("method", ["proportional", "equal", "neyman"])
def test_stratified_allocation_sums_to_requested_total(method):
    frame = pd.DataFrame({
        "stratum": ["A", "B", "C"], "population": [100, 200, 300],
        "sd": [2, 3, 5], "cost": [1, 2, 4],
    })
    result = allocate_stratified_sample(
        frame, 60, allocation=method, standard_deviation_column="sd",
        cost_column="cost" if method == "neyman" else None,
    )
    assert result["allocation"]["allocated_sample"].sum() == 60
    assert (result["allocation"]["allocated_sample"] >= 1).all()


def test_allocation_requires_sd_for_neyman_and_valid_population():
    frame = pd.DataFrame({"population": [10, 20]})
    with pytest.raises(ValueError, match="standard deviation"):
        allocate_stratified_sample(frame, 10, allocation="neyman")
    frame.loc[0, "population"] = 0
    with pytest.raises(ValueError, match="positive"):
        allocate_stratified_sample(frame, 10)


def test_cluster_design_effect_and_cluster_count():
    result = plan_cluster_sample(400, 20, .05, nonresponse_rate=.1)
    assert result["design_effect"] == pytest.approx(1.95)
    assert result["respondents_to_approach"] == 445
    assert result["number_of_clusters"] == 23


def test_cluster_validation():
    with pytest.raises(ValueError, match="between 0 and 1"):
        plan_cluster_sample(100, 10, 1.2)
