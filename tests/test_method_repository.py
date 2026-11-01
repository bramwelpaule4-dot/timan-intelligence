
"""Tests for the TimanStat statistical method repository."""

import pytest

from timan_intelligence.registry.identity import (
    DuplicateCanonicalIDError,
    RegistryIdentityIndex,
)
from timan_intelligence.registry.method import MethodEntity
from timan_intelligence.registry.method_repository import MethodRepository


def make_method(
    entity_id="method.inference.anova.one_way",
    *,
    name="One-way ANOVA",
    use_cases=None,
    record_maturity="reviewed",
    execution_eligibility="eligible",
):
    """Create a representative method entity for repository tests."""
    return MethodEntity(
        entity_id=entity_id,
        name=name,
        description="A statistical method used for testing group means.",
        knowledge_areas=["inferential_statistics"],
        statistical_purposes=["group_comparison"],
        use_cases=use_cases or ["compare_groups"],
        record_maturity=record_maturity,
        execution_eligibility=execution_eligibility,
        statistical_specification={
            "test": "F-test",
            "options": {"equal_variance": True},
        },
    )


@pytest.fixture
def identity_index():
    return RegistryIdentityIndex()


@pytest.fixture
def repository(identity_index):
    return MethodRepository(identity_index)


def test_repository_requires_identity_index():
    with pytest.raises(TypeError):
        MethodRepository(None)


def test_registers_and_retrieves_method(repository, identity_index):
    method = make_method()

    registered = repository.register(method)
    retrieved = repository.get(method.entity_id)

    assert registered.entity_id == method.entity_id
    assert retrieved is not None
    assert retrieved.name == method.name
    assert repository.exists(method.entity_id) is True
    assert repository.count() == 1

    identity = identity_index.get(method.entity_id)
    assert identity.namespace == "statistical"
    assert identity.entity_type == "method"


def test_register_requires_method_entity(repository):
    with pytest.raises(TypeError):
        repository.register("not a method")


def test_rejects_duplicate_method_registration(repository):
    method = make_method()

    repository.register(method)

    with pytest.raises(ValueError, match="already registered"):
        repository.register(method)

    assert repository.count() == 1


def test_rejects_identity_already_registered_in_shared_index(
    repository,
    identity_index,
):
    method = make_method()

    identity_index.register(
        method.entity_id,
        namespace="statistical",
        entity_type="method",
    )

    with pytest.raises(DuplicateCanonicalIDError):
        repository.register(method)

    assert repository.count() == 0


def test_rejects_invalid_method_identifier(repository):
    method = make_method(entity_id="invalid-method-id")

    with pytest.raises(ValueError):
        repository.register(method)

    assert repository.count() == 0


def test_get_returns_none_for_unknown_method(repository):
    assert (
        repository.get("method.inference.anova.one_way")
        is None
    )


def test_exists_returns_false_for_unknown_method(repository):
    assert repository.exists("method.inference.anova.one_way") is False


def test_list_all_returns_all_registered_methods(repository):
    first = make_method()
    second = make_method(
        entity_id="method.inference.t_test.independent.welch",
        name="Welch independent-samples t-test",
    )

    repository.register(first)
    repository.register(second)

    methods = repository.list_all()

    assert isinstance(methods, tuple)
    assert len(methods) == 2
    assert {method.entity_id for method in methods} == {
        first.entity_id,
        second.entity_id,
    }


def test_find_filters_by_use_case(repository):
    first = make_method(
        use_cases=["compare_groups", "evaluate_intervention"]
    )
    second = make_method(
        entity_id="method.inference.correlation.pearson",
        name="Pearson correlation",
        use_cases=["measure_association"],
    )

    repository.register(first)
    repository.register(second)

    results = repository.find(use_case="compare_groups")

    assert len(results) == 1
    assert results[0].entity_id == first.entity_id


def test_find_filters_by_record_maturity(repository):
    reviewed = make_method(record_maturity="reviewed")
    approved = make_method(
        entity_id="method.inference.t_test.independent.welch",
        record_maturity="approved",
    )

    repository.register(reviewed)
    repository.register(approved)

    results = repository.find(record_maturity="approved")

    assert len(results) == 1
    assert results[0].entity_id == approved.entity_id


def test_find_filters_by_execution_eligibility(repository):
    eligible = make_method(execution_eligibility="eligible")
    conditional = make_method(
        entity_id="method.inference.t_test.independent.welch",
        execution_eligibility="conditional",
    )

    repository.register(eligible)
    repository.register(conditional)

    results = repository.find(execution_eligibility="conditional")

    assert len(results) == 1
    assert results[0].entity_id == conditional.entity_id


def test_find_combines_all_filters(repository):
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

    repository.register(matching)
    repository.register(nonmatching)

    results = repository.find(
        use_case="compare_groups",
        record_maturity="approved",
        execution_eligibility="eligible",
    )

    assert len(results) == 1
    assert results[0].entity_id == matching.entity_id


def test_find_returns_empty_tuple_when_no_records_match(repository):
    repository.register(make_method())

    results = repository.find(use_case="nonexistent_use_case")

    assert results == ()


def test_find_without_filters_returns_all_methods(repository):
    first = make_method()
    second = make_method(
        entity_id="method.inference.t_test.independent.welch"
    )

    repository.register(first)
    repository.register(second)

    assert len(repository.find()) == 2


def test_registration_defensively_copies_input_method(repository):
    method = make_method()

    repository.register(method)

    method.name = "Changed outside repository"
    method.use_cases.append("unexpected_use_case")
    method.statistical_specification["options"]["equal_variance"] = False

    stored = repository.get(method.entity_id)

    assert stored is not None
    assert stored.name == "One-way ANOVA"
    assert "unexpected_use_case" not in stored.use_cases
    assert (
        stored.statistical_specification["options"]["equal_variance"]
        is True
    )


def test_retrieval_defensively_copies_nested_method_data(repository):
    method = make_method()

    repository.register(method)

    retrieved = repository.get(method.entity_id)
    assert retrieved is not None

    retrieved.name = "Changed retrieved record"
    retrieved.use_cases.append("unexpected_use_case")
    retrieved.statistical_specification["options"]["equal_variance"] = False

    stored = repository.get(method.entity_id)

    assert stored is not None
    assert stored.name == "One-way ANOVA"
    assert "unexpected_use_case" not in stored.use_cases
    assert (
        stored.statistical_specification["options"]["equal_variance"]
        is True
    )


def test_list_all_returns_defensive_copies(repository):
    repository.register(make_method())

    methods = repository.list_all()
    methods[0].name = "Changed listed record"

    stored = repository.get("method.inference.anova.one_way")

    assert stored is not None
    assert stored.name == "One-way ANOVA"


def test_find_returns_defensive_copies(repository):
    repository.register(make_method())

    results = repository.find(use_case="compare_groups")
    results[0].name = "Changed filtered record"

    stored = repository.get("method.inference.anova.one_way")

    assert stored is not None
    assert stored.name == "One-way ANOVA"
