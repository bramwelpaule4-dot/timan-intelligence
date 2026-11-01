"""Tests for TimanStat's registry-wide canonical identity index."""

import pytest

from timan_intelligence.registry.identity import (
    DuplicateCanonicalIDError,
    IdentityRecord,
    InvalidCanonicalIDError,
    RegistryIdentityIndex,
    UnknownCanonicalIDError,
)


def test_registers_statistical_entity_identifier():
    index = RegistryIdentityIndex()

    record = index.register(
        "method.inference.anova.one_way",
        namespace="statistical",
    )

    assert isinstance(record, IdentityRecord)
    assert record.canonical_id == "method.inference.anova.one_way"
    assert record.namespace == "statistical"
    assert record.entity_type == "method"


def test_registers_statistical_entity_with_matching_expected_type():
    index = RegistryIdentityIndex()

    record = index.register(
        "model.regression.linear.multiple",
        namespace="statistical",
        entity_type="model",
    )

    assert record.entity_type == "model"


def test_rejects_statistical_entity_with_mismatched_expected_type():
    index = RegistryIdentityIndex()

    with pytest.raises(InvalidCanonicalIDError):
        index.register(
            "method.inference.anova.one_way",
            namespace="statistical",
            entity_type="model",
        )

    assert index.count() == 0


@pytest.mark.parametrize(
    ("canonical_id", "namespace"),
    [
        ("implementation.scipy.stats.welch_t_test", "implementation"),
        ("vocab.method_family.regression", "vocab"),
        ("reference.doi.10_xxxx_xxxx", "reference"),
        ("relationship.method.supported_by.000001", "relationship"),
        ("registry_release.1.0.0", "registry_release"),
    ],
)
def test_registers_non_statistical_namespace_identifiers(
    canonical_id,
    namespace,
):
    index = RegistryIdentityIndex()

    record = index.register(canonical_id, namespace=namespace)

    assert record.canonical_id == canonical_id
    assert record.namespace == namespace
    assert record.entity_type is None


def test_rejects_duplicate_registration_in_same_namespace():
    index = RegistryIdentityIndex()
    identifier = "method.inference.anova.one_way"

    index.register(identifier, namespace="statistical")

    with pytest.raises(DuplicateCanonicalIDError):
        index.register(identifier, namespace="statistical")

    assert index.count() == 1


def test_rejects_identifier_registered_under_incorrect_namespace():
    index = RegistryIdentityIndex()
    identifier = "implementation.scipy.stats.welch_t_test"

    index.register(identifier, namespace="implementation")

    with pytest.raises(InvalidCanonicalIDError):
        index.register(identifier, namespace="vocab")

    assert index.count() == 1
    assert index.get(identifier).namespace == "implementation"


def test_duplicate_attempt_does_not_overwrite_existing_record():
    index = RegistryIdentityIndex()
    identifier = "method.inference.anova.one_way"

    original = index.register(identifier, namespace="statistical")

    with pytest.raises(DuplicateCanonicalIDError):
        index.register(identifier, namespace="statistical")

    assert index.get(identifier) == original
    assert index.count() == 1


@pytest.mark.parametrize(
    ("canonical_id", "namespace"),
    [
        ("unknown.inference.anova.one_way", "statistical"),
        ("implementation.scipy", "implementation"),
        ("vocab.method_family", "vocab"),
        ("reference.unknown.identifier", "reference"),
        ("relationship.method.supported_by.1", "relationship"),
        ("registry_release.01.0.0", "registry_release"),
        ("method.inference.anova.one_way", "unknown"),
    ],
)
def test_rejects_invalid_identifier_or_namespace(canonical_id, namespace):
    index = RegistryIdentityIndex()

    with pytest.raises(InvalidCanonicalIDError):
        index.register(canonical_id, namespace=namespace)

    assert index.count() == 0


@pytest.mark.parametrize(
    "canonical_id",
    [
        None,
        123,
        [],
        {},
    ],
)
def test_rejects_non_string_canonical_ids(canonical_id):
    index = RegistryIdentityIndex()

    with pytest.raises(InvalidCanonicalIDError):
        index.register(canonical_id, namespace="statistical")

    assert index.count() == 0


@pytest.mark.parametrize(
    "namespace",
    [
        None,
        123,
        "",
    ],
)
def test_rejects_invalid_namespace_values(namespace):
    index = RegistryIdentityIndex()

    with pytest.raises(InvalidCanonicalIDError):
        index.register(
            "method.inference.anova.one_way",
            namespace=namespace,
        )

    assert index.count() == 0


def test_get_returns_registered_identity_record():
    index = RegistryIdentityIndex()
    identifier = "implementation.scipy.stats.welch_t_test"

    registered = index.register(
        identifier,
        namespace="implementation",
    )

    assert index.get(identifier) == registered


def test_get_rejects_unknown_identifier():
    index = RegistryIdentityIndex()

    with pytest.raises(UnknownCanonicalIDError):
        index.get("method.inference.anova.one_way")


def test_contains_identifies_registered_and_unregistered_ids():
    index = RegistryIdentityIndex()
    identifier = "vocab.method_family.regression"

    assert index.contains(identifier) is False

    index.register(identifier, namespace="vocab")

    assert index.contains(identifier) is True
    assert index.contains("vocab.method_family.classification") is False


def test_count_returns_number_of_registered_records():
    index = RegistryIdentityIndex()

    assert index.count() == 0

    index.register(
        "method.inference.anova.one_way",
        namespace="statistical",
    )
    index.register(
        "implementation.scipy.stats.welch_t_test",
        namespace="implementation",
    )

    assert index.count() == 2


def test_all_records_returns_immutable_snapshot():
    index = RegistryIdentityIndex()

    index.register(
        "method.inference.anova.one_way",
        namespace="statistical",
    )
    index.register(
        "implementation.scipy.stats.welch_t_test",
        namespace="implementation",
    )

    records = index.all_records()

    assert isinstance(records, tuple)
    assert len(records) == 2
    assert all(isinstance(record, IdentityRecord) for record in records)

    with pytest.raises(AttributeError):
        records.append(
            IdentityRecord(
                canonical_id="vocab.method_family.regression",
                namespace="vocab",
            )
        )


def test_failed_registration_preserves_other_registered_records():
    index = RegistryIdentityIndex()

    original = index.register(
        "method.inference.anova.one_way",
        namespace="statistical",
    )

    with pytest.raises(InvalidCanonicalIDError):
        index.register(
            "implementation.scipy",
            namespace="implementation",
        )

    assert index.count() == 1
    assert index.get(original.canonical_id) == original
