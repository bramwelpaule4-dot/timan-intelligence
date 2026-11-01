
"""Tests for the TimanStat method registry access layer."""

import pytest

from timan_intelligence.registry.access import (
    InvalidMethodIDError,
    MethodRegistryAccess,
    RegistryAccessError,
)
from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.method import MethodEntity
from timan_intelligence.registry.method_repository import MethodRepository


@pytest.fixture
def access():
    """Create an isolated method registry access instance."""
    identity_index = RegistryIdentityIndex()
    repository = MethodRepository(identity_index)

    return MethodRegistryAccess(repository)


def make_method(
    entity_id="method.inference.anova.one_way",
    *,
    name="One-way ANOVA",
    use_cases=None,
    record_maturity="reviewed",
    execution_eligibility="eligible",
):
    """Create a representative method entity."""
    return MethodEntity(
        entity_id=entity_id,
        name=name,
        description="A statistical method for comparing group means.",
        knowledge_areas=["inferential_statistics"],
        statistical_purposes=["group_comparison"],
        use_cases=use_cases or ["compare_groups"],
        record_maturity=record_maturity,
        execution_eligibility=execution_eligibility,
    )


def test_access_requires_method_repository():
    with pytest.raises(TypeError):
        MethodRegistryAccess(None)


def test_error_hierarchy():
    assert issubclass(InvalidMethodIDError, RegistryAccessError)
    assert issubclass(InvalidMethodIDError, ValueError)


def test_get_method_returns_registered_method(access):
    method = make_method()
    access._repository.register(method)

    result = access.get_method(method.entity_id)

    assert result is not None
    assert result.entity_id == method.entity_id
    assert result.name == method.name


def test_get_method_returns_none_for_unknown_valid_id(access):
    result = access.get_method(
        "method.inference.anova.one_way"
    )

    assert result is None


@pytest.mark.parametrize(
    "method_id",
    [
        "invalid-method-id",
        "model.regression.linear.multiple",
        "unknown.inference.anova.one_way",
        "",
        None,
        123,
    ],
)
def test_get_method_rejects_invalid_or_wrong_type_ids(
    access,
    method_id,
):
    with pytest.raises(InvalidMethodIDError):
        access.get_method(method_id)


def test_method_exists_returns_true_for_registered_method(access):
    method = make_method()
    access._repository.register(method)

    assert access.method_exists(method.entity_id) is True


def test_method_exists_returns_false_for_unknown_valid_id(access):
    assert (
        access.method_exists("method.inference.anova.one_way")
        is False
    )


def test_method_exists_rejects_invalid_id(access):
    with pytest.raises(InvalidMethodIDError):
        access.method_exists("invalid-method-id")


def test_list_methods_returns_all_registered_methods(access):
    first = make_method()
    second = make_method(
        entity_id="method.inference.t_test.independent.welch",
        name="Welch independent-samples t-test",
    )

    access._repository.register(first)
    access._repository.register(second)

    results = access.list_methods()

    assert isinstance(results, tuple)
    assert len(results) == 2


def test_find_methods_filters_by_use_case(access):
    first = make_method(use_cases=["compare_groups"])
    second = make_method(
        entity_id="method.inference.correlation.pearson",
        name="Pearson correlation",
        use_cases=["measure_association"],
    )

    access._repository.register(first)
    access._repository.register(second)

    results = access.find_methods(use_case="measure_association")

    assert len(results) == 1
    assert results[0].entity_id == second.entity_id


def test_find_methods_filters_by_record_maturity(access):
    reviewed = make_method(record_maturity="reviewed")
    approved = make_method(
        entity_id="method.inference.t_test.independent.welch",
        record_maturity="approved",
    )

    access._repository.register(reviewed)
    access._repository.register(approved)

    results = access.find_methods(record_maturity="approved")

    assert len(results) == 1
    assert results[0].entity_id == approved.entity_id


def test_find_methods_filters_by_execution_eligibility(access):
    eligible = make_method(execution_eligibility="eligible")
    conditional = make_method(
        entity_id="method.inference.t_test.independent.welch",
        execution_eligibility="conditional",
    )

    access._repository.register(eligible)
    access._repository.register(conditional)

    results = access.find_methods(
        execution_eligibility="conditional"
    )

    assert len(results) == 1
    assert results[0].entity_id == conditional.entity_id


def test_find_methods_combines_filters(access):
    matching = make_method(
        use_cases=["compare_groups"],
        record_maturity="approved",
        execution_eligibility="eligible",
    )
    nonmatching = make_method(
        entity_id="method.inference.t_test.independent.welch",
        use_cases=["compare_groups"],
        record_maturity="approved",
        execution_eligibility="conditional",
    )

    access._repository.register(matching)
    access._repository.register(nonmatching)

    results = access.find_methods(
        use_case="compare_groups",
        record_maturity="approved",
        execution_eligibility="eligible",
    )

    assert len(results) == 1
    assert results[0].entity_id == matching.entity_id


def test_find_methods_returns_empty_tuple_when_no_match(access):
    access._repository.register(make_method())

    results = access.find_methods(use_case="unknown_use_case")

    assert results == ()


def test_get_methods_by_ids_returns_matching_records(access):
    first = make_method()
    second = make_method(
        entity_id="method.inference.t_test.independent.welch",
        name="Welch independent-samples t-test",
    )

    access._repository.register(first)
    access._repository.register(second)

    results = access.get_methods_by_ids(
        [first.entity_id, second.entity_id]
    )

    assert set(results) == {first.entity_id, second.entity_id}
    assert results[first.entity_id].name == first.name
    assert results[second.entity_id].name == second.name


def test_get_methods_by_ids_omits_unknown_valid_ids(access):
    method = make_method()
    access._repository.register(method)

    results = access.get_methods_by_ids(
        [
            method.entity_id,
            "method.inference.t_test.independent.welch",
        ]
    )

    assert list(results) == [method.entity_id]


def test_get_methods_by_ids_resolves_duplicate_ids_once(access):
    method = make_method()
    access._repository.register(method)

    results = access.get_methods_by_ids(
        [method.entity_id, method.entity_id]
    )

    assert len(results) == 1
    assert method.entity_id in results


def test_get_methods_by_ids_rejects_invalid_ids(access):
    with pytest.raises(InvalidMethodIDError):
        access.get_methods_by_ids(
            [
                "method.inference.anova.one_way",
                "invalid-method-id",
            ]
        )


@pytest.mark.parametrize(
    "method_ids",
    [
        None,
        "method.inference.anova.one_way",
        123,
        {},
    ],
)
def test_get_methods_by_ids_requires_a_list(access, method_ids):
    with pytest.raises(TypeError):
        access.get_methods_by_ids(method_ids)


def test_access_returns_defensive_copies(access):
    method = make_method()
    access._repository.register(method)

    result = access.get_method(method.entity_id)
    assert result is not None

    result.name = "Modified through access layer"
    result.use_cases.append("unexpected_use_case")

    stored = access.get_method(method.entity_id)

    assert stored is not None
    assert stored.name == "One-way ANOVA"
    assert "unexpected_use_case" not in stored.use_cases
