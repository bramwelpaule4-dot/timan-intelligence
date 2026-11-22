import numpy as np
import pandas as pd
import pytest

from timan_intelligence.core.two_stage_ppswor import estimate_two_stage_ppswor_total
from timan_intelligence.core.two_stage_ppswor_estimands import (
    estimate_two_stage_ppswor_domain_total,
    estimate_two_stage_ppswor_mean,
    estimate_two_stage_ppswor_proportion,
)


def fixture():
    rows = []
    psus = ["P1", "P2", "P3"]
    values = [[10.0, 20.0], [30.0, 40.0], [5.0, 15.0]]
    domains = [["A", "B"], ["A", "A"], ["B", "B"]]
    binary = [[1, 0], [1, 1], [0, 1]]
    for psu, outcomes, labels, flags, pi in zip(
        psus, values, domains, binary, [0.5, 0.7, 0.8]
    ):
        for ssu, (outcome, domain, flag) in enumerate(
            zip(outcomes, labels, flags), start=1
        ):
            rows.append({
                "stratum": "S1",
                "psu": psu,
                "ssu": ssu,
                "outcome": outcome,
                "binary": flag,
                "domain": domain,
                "pi": pi,
                "ssu_population": 4,
            })
    frame = pd.DataFrame(rows)
    joint = pd.DataFrame(
        [[0.5, 0.2, 0.3], [0.2, 0.7, 0.5], [0.3, 0.5, 0.8]],
        index=psus, columns=psus,
    )
    common = (
        "psu", "ssu", "pi", "ssu_population", joint, "stratum"
    )
    return frame, common


def test_two_stage_ppswor_mean_scales_total_and_variance():
    frame, common = fixture()
    result = estimate_two_stage_ppswor_mean(
        frame, "outcome", 12, *common
    )
    total = estimate_two_stage_ppswor_total(
        frame, "outcome", *common
    )
    assert result["estimate"] == pytest.approx(total["estimate"] / 12)
    assert result["variance"] == pytest.approx(total["variance"] / 12**2)
    assert result["variance"] == pytest.approx(
        result["variance_stage_1"] + result["variance_stage_2"]
    )
    assert result["metadata"]["estimand"] == "population mean"
    assert result["metadata"]["fixed_denominator"] == 12


def test_two_stage_ppswor_mean_rejects_invalid_population_count():
    frame, common = fixture()
    for invalid in (0, -2, 12.5, np.nan, np.inf):
        with pytest.raises(ValueError):
            estimate_two_stage_ppswor_mean(frame, "outcome", invalid, *common)


def test_two_stage_ppswor_proportion_requires_binary_outcome():
    frame, common = fixture()
    result = estimate_two_stage_ppswor_proportion(
        frame, "binary", 12, *common
    )
    assert 0 <= result["estimate"] <= 1
    assert result["metadata"]["estimand"] == "population proportion"
    with pytest.raises(ValueError, match="whole number"):
        estimate_two_stage_ppswor_proportion(
            frame, "binary", 12.5, *common
        )
    frame.loc[0, "binary"] = 2
    with pytest.raises(ValueError, match="binary values"):
        estimate_two_stage_ppswor_proportion(
            frame, "binary", 12, *common
        )


def test_two_stage_ppswor_domain_total_retains_out_of_domain_ssus():
    frame, common = fixture()
    result = estimate_two_stage_ppswor_domain_total(
        frame, "outcome", "domain", "A", *common
    )
    assert result["metadata"]["estimand"] == "domain total"
    assert result["metadata"]["domain_value"] == "A"
    assert result["metadata"]["number_of_sampled_ssus"] == 6
    assert result["psu_details"]["sampled_ssus"].sum() == 6
    assert any("retained in the original sample design" in warning for warning in result["warnings"])


def test_two_stage_ppswor_domain_total_rejects_missing_domain_and_outcome():
    frame, common = fixture()
    frame.loc[0, "domain"] = None
    with pytest.raises(ValueError, match="Domain identifiers"):
        estimate_two_stage_ppswor_domain_total(
            frame, "outcome", "domain", "A", *common
        )
    frame, common = fixture()
    frame.loc[0, "outcome"] = np.nan
    with pytest.raises(ValueError, match="within the selected domain"):
        estimate_two_stage_ppswor_domain_total(
            frame, "outcome", "domain", "A", *common
        )



def test_shared_services_wrap_mean_proportion_and_domain_estimands():
    from timan_intelligence.services.analysis_service import (
        run_two_stage_ppswor_domain_total_service,
        run_two_stage_ppswor_mean_service,
        run_two_stage_ppswor_proportion_service,
    )

    frame, common = fixture()
    mean = run_two_stage_ppswor_mean_service(
        frame, "outcome", 12, *common
    )
    proportion = run_two_stage_ppswor_proportion_service(
        frame, "binary", 12, *common
    )
    domain = run_two_stage_ppswor_domain_total_service(
        frame, "outcome", "domain", "A", *common
    )
    assert mean.status == proportion.status == domain.status == "success"
    assert mean.metadata["estimand"] == "population mean"
    assert proportion.metadata["estimand"] == "population proportion"
    assert domain.metadata["estimand"] == "domain total"
    assert "psu_details" in domain.tables
