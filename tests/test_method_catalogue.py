"""Tests for the curated TimanStat statistical methods catalogue."""

import pytest

from timan_intelligence.registry.method_catalogue import (
    CATALOGUE_VERSION,
    IMPLEMENTED_METHODS,
    create_statistical_method_repository,
    get_statistical_method,
    get_statistical_method_summary,
    get_statistical_methods,
    validate_statistical_method_catalogue,
)


def test_catalogue_has_a_version_and_valid_records():
    assert CATALOGUE_VERSION == "1.0.0"
    assert validate_statistical_method_catalogue() == ()


def test_catalogue_registers_all_records_with_unique_canonical_ids():
    repository = create_statistical_method_repository()
    methods = repository.list_all()

    assert repository.count() == len(methods)
    assert len({method.entity_id for method in methods}) == len(methods)
    assert all(method.entity_id.startswith("method.") for method in methods)


def test_only_existing_execution_methods_are_marked_implemented():
    implemented = {
        method.entity_id
        for method in get_statistical_methods(
            implementation_status="implemented"
        )
    }

    assert implemented == IMPLEMENTED_METHODS
    assert len(implemented) == 3


def test_planned_methods_are_not_marked_executable():
    planned = get_statistical_methods(implementation_status="planned")

    assert planned
    assert all(
        method.execution_eligibility == "not_assessed"
        for method in planned
    )
    assert all(
        method.verification_status == "not_tested"
        for method in planned
    )


def test_method_lookup_returns_expected_record():
    method = get_statistical_method(
        "method.inference.comparison.t_test.independent.welch"
    )

    assert method is not None
    assert method.name == "Welch's independent-samples t-test"
    assert method.implementation_status == "implemented"
    assert method.execution_eligibility == "conditional"


def test_unknown_method_lookup_returns_none():
    assert get_statistical_method("method.unknown.not_registered") is None


def test_catalogue_can_filter_by_family():
    methods = get_statistical_methods(method_family="correlation")

    assert {method.name for method in methods} == {
        "Pearson correlation",
        "Spearman rank correlation",
    }


def test_catalogue_can_filter_by_release_priority():
    methods = get_statistical_methods(release_priority="P1")

    assert methods
    assert all(
        method.metadata["release_priority"] == "P1"
        for method in methods
    )


def test_catalogue_filters_can_be_combined():
    methods = get_statistical_methods(
        implementation_status="implemented",
        method_family="group_comparison",
        release_priority="P1",
    )

    assert len(methods) == 2
    assert {method.name for method in methods} == {
        "Welch's independent-samples t-test",
        "One-way ANOVA",
    }


def test_method_records_expose_requirements_and_validation_contracts():
    methods = get_statistical_methods()

    for method in methods:
        assert method.description.strip()
        assert method.method_families
        assert method.statistical_purposes
        assert method.data_requirements
        assert method.assumptions
        assert method.outputs
        assert method.validation_requirements
        assert method.statistical_specification["release_priority"] in {
            "P1", "P2", "P3"
        }


def test_survey_methods_explicitly_declare_sampling_design_requirements():
    weighted = get_statistical_method(
        "method.survey.estimation.weighted_proportion"
    )
    complex_design = get_statistical_method(
        "method.survey.inference.complex_design"
    )

    assert weighted is not None
    assert complex_design is not None
    assert "sampling_weight" in weighted.statistical_specification[
        "required_variable_roles"
    ]
    assert "stratum_identifier" in complex_design.statistical_specification[
        "required_variable_roles"
    ]
    assert weighted.implementation_status == "planned"
    assert complex_design.implementation_status == "planned"


def test_catalogue_summary_reports_lifecycle_and_priorities():
    summary = get_statistical_method_summary()

    assert summary["catalogue_version"] == CATALOGUE_VERSION
    assert summary["total_methods"] == 23
    assert summary["implementation_status"]["implemented"] == 3
    assert summary["implementation_status"]["planned"] == 20
    assert set(summary["release_priorities"]) == {"P1", "P2", "P3"}


def test_returned_method_records_do_not_mutate_catalogue_state():
    methods = get_statistical_methods()
    first_id = methods[0].entity_id
    methods[0].assumptions.append("External mutation")

    refreshed = get_statistical_method(first_id)

    assert refreshed is not None
    assert "External mutation" not in refreshed.assumptions


def test_repository_returns_defensive_copies():
    repository = create_statistical_method_repository()
    method = repository.list_all()[0]
    original_name = method.name
    method.name = "Mutated externally"

    stored = repository.get(method.entity_id)

    assert stored is not None
    assert stored.name == original_name
