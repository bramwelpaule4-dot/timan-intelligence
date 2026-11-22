import pandas as pd
import pytest

from timan_intelligence.core.sampling_selection import (
    select_sample, select_stratified_sample,
)


@pytest.fixture
def frame():
    return pd.DataFrame({
        "id": [f"HH{i:03d}" for i in range(1, 101)],
        "stratum": ["A"] * 40 + ["B"] * 60,
        "mos": list(range(1, 101)),
    })


@pytest.mark.parametrize("method", ["srswor", "srswr", "systematic", "ppswr", "ppswor"])
def test_selection_methods_reproducible(frame, method):
    result = select_sample(
        frame, "id", 20, method=method, seed=77,
        size_column="mos" if method.startswith("pps") else None,
    )
    again = select_sample(
        frame, "id", 20, method=method, seed=77,
        size_column="mos" if method.startswith("pps") else None,
    )
    assert result["selected"]["id"].tolist() == again["selected"]["id"].tolist()
    assert len(result["selected"]) == 20
    assert result["selected"]["selection_order"].tolist() == list(range(1, 21))


def test_reserve_is_separate_and_disjoint(frame):
    result = select_sample(frame, "id", 20, seed=4, reserve_size=10)
    assert len(result["reserve"]) == 10
    assert set(result["selected"].id).isdisjoint(result["reserve"].id)
    assert set(result["reserve"].sample_role) == {"reserve"}


def test_ppswor_probabilities_are_conditional_not_inclusion(frame):
    result = select_sample(frame, "id", 12, method="ppswor", size_column="mos")
    assert result["selected"].draw_probability.between(0, 1).all()
    assert any("not exact first-order" in w for w in result["warnings"])


def test_frame_and_size_validation(frame):
    bad = frame.copy()
    bad.loc[0, "id"] = None
    with pytest.raises(ValueError, match="complete and unique"):
        select_sample(bad, "id", 5)
    bad = frame.copy()
    bad.loc[0, "mos"] = 0
    with pytest.raises(ValueError, match="positive and finite"):
        select_sample(bad, "id", 5, method="ppswr", size_column="mos")


def test_stratified_allocations_and_reserves(frame):
    result = select_stratified_sample(
        frame, "id", "stratum", {"A": 8, "B": 12},
        seed=15, reserve_allocations={"A": 2, "B": 3},
    )
    assert len(result["selected"]) == 20
    assert len(result["reserve"]) == 5
    assert result["selected"].groupby("stratum").size().to_dict() == {"A": 8, "B": 12}
    assert set(result["selected"].id).isdisjoint(result["reserve"].id)


def test_stratified_requires_exact_allocation_coverage(frame):
    with pytest.raises(ValueError, match="every observed stratum"):
        select_stratified_sample(frame, "id", "stratum", {"A": 5})


def test_sample_size_without_replacement_cannot_exceed_frame(frame):
    with pytest.raises(ValueError, match="cannot exceed"):
        select_sample(frame, "id", 101, method="systematic")
