
"""Tests for TimanStat's non-statistical namespace identifiers."""

import pytest

from timan_intelligence.registry.namespace_identifiers import (
    NamespaceIdentifierValidationError,
    ParsedNamespaceIdentifier,
    parse_namespace_identifier,
    validate_implementation_id,
    validate_reference_id,
    validate_registry_release_id,
    validate_relationship_id,
    validate_vocabulary_id,
)


@pytest.mark.parametrize(
    "identifier",
    [
        "implementation.scipy.welch_t_test",
        "implementation.scipy.stats.welch_t_test",
        "implementation.timanstat.statistics.anova.one_way",
    ],
)
def test_accepts_valid_variable_depth_implementation_ids(identifier):
    assert validate_implementation_id(identifier) == identifier


@pytest.mark.parametrize(
    "identifier",
    [
        "vocab.method_family.regression",
        "vocab.statistical_method.family.regression",
        "vocab.measurement.scale.interval",
    ],
)
def test_accepts_valid_variable_depth_vocabulary_ids(identifier):
    assert validate_vocabulary_id(identifier) == identifier


@pytest.mark.parametrize(
    "identifier",
    [
        "reference.doi.10_xxxx_xxxx",
        "reference.url.example_com.article",
        "reference.bibliography.author_2024",
    ],
)
def test_accepts_valid_reference_id_structures(identifier):
    assert validate_reference_id(identifier) == identifier


@pytest.mark.parametrize(
    "identifier",
    [
        "relationship.method.supported_by.000001",
        "relationship.model.related_to.000002",
        "relationship.implementation.implements.000003",
        "relationship.vocab.classifies.000004",
    ],
)
def test_accepts_valid_relationship_ids(identifier):
    assert validate_relationship_id(identifier) == identifier


@pytest.mark.parametrize(
    "identifier",
    [
        "registry_release.0.0.0",
        "registry_release.1.0.0",
        "registry_release.2.3.1",
        "registry_release.10.12.25",
    ],
)
def test_accepts_valid_registry_release_ids(identifier):
    assert validate_registry_release_id(identifier) == identifier


@pytest.mark.parametrize(
    ("validator", "identifier"),
    [
        (validate_implementation_id, "implementation"),
        (validate_implementation_id, "implementation.scipy"),
        (validate_implementation_id, "Implementation.scipy.welch_t_test"),
        (validate_implementation_id, "implementation.scipy.welch-t-test"),
        (validate_implementation_id, "implementation.scipy.welch t test"),
        (validate_vocabulary_id, "vocab"),
        (validate_vocabulary_id, "vocab.method_family"),
        (validate_vocabulary_id, "Vocab.method_family.regression"),
        (validate_vocabulary_id, "vocab.method-family.regression"),
        (validate_vocabulary_id, "vocab.method_family.regression."),
        (validate_reference_id, "reference"),
        (validate_reference_id, "reference.unknown.identifier"),
        (validate_reference_id, "reference.doi"),
        (validate_relationship_id, "relationship.method.supported_by"),
        (validate_relationship_id, "relationship.unknown.supported_by.000001"),
        (validate_relationship_id, "relationship.method.supported_by.1"),
        (validate_relationship_id, "relationship.method.supported_by.000001.extra"),
        (validate_registry_release_id, "registry_release.1.0"),
        (validate_registry_release_id, "registry_release.01.0.0"),
        (validate_registry_release_id, "registry_release.1.0.0.1"),
        (validate_registry_release_id, "registry_release.one.0.0"),
    ],
)
def test_rejects_invalid_namespace_identifier_structures(validator, identifier):
    with pytest.raises(NamespaceIdentifierValidationError):
        validator(identifier)


@pytest.mark.parametrize(
    "identifier",
    [
        None,
        123,
        [],
        {},
    ],
)
def test_rejects_non_string_identifiers(identifier):
    validators = [
        validate_implementation_id,
        validate_vocabulary_id,
        validate_reference_id,
        validate_relationship_id,
        validate_registry_release_id,
        parse_namespace_identifier,
    ]

    for validator in validators:
        with pytest.raises(NamespaceIdentifierValidationError):
            validator(identifier)


@pytest.mark.parametrize(
    ("identifier", "expected_namespace", "expected_segments"),
    [
        (
            "implementation.scipy.stats.welch_t_test",
            "implementation",
            ("implementation", "scipy", "stats", "welch_t_test"),
        ),
        (
            "vocab.statistical_method.family.regression",
            "vocab",
            ("vocab", "statistical_method", "family", "regression"),
        ),
        (
            "reference.doi.10_xxxx_xxxx",
            "reference",
            ("reference", "doi", "10_xxxx_xxxx"),
        ),
        (
            "relationship.method.supported_by.000001",
            "relationship",
            ("relationship", "method", "supported_by", "000001"),
        ),
        (
            "registry_release.1.0.0",
            "registry_release",
            ("registry_release", "1", "0", "0"),
        ),
    ],
)
def test_parses_valid_namespace_identifiers(
    identifier,
    expected_namespace,
    expected_segments,
):
    parsed = parse_namespace_identifier(identifier)

    assert isinstance(parsed, ParsedNamespaceIdentifier)
    assert parsed.canonical_id == identifier
    assert parsed.namespace == expected_namespace
    assert parsed.segments == expected_segments


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        "method.inference.anova.one_way",
        "unknown.example.identifier",
        "implementation.scipy",
        "reference.unknown.identifier",
        "relationship.method.supported_by.00000x",
        "registry_release.1.0",
    ],
)
def test_parser_rejects_unsupported_or_invalid_identifiers(identifier):
    with pytest.raises(NamespaceIdentifierValidationError):
        parse_namespace_identifier(identifier)


def test_parser_does_not_silently_normalise_identifiers():
    identifier = "implementation.scipy.stats.welch_t_test"

    parsed = parse_namespace_identifier(identifier)

    assert parsed.canonical_id == identifier


def test_parsed_namespace_identifier_is_immutable():
    parsed = parse_namespace_identifier(
        "implementation.scipy.welch_t_test"
    )

    with pytest.raises(AttributeError):
        parsed.namespace = "vocab"
