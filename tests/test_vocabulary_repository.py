
"""Tests for the TimanStat controlled vocabulary repository."""

import pytest

from timan_intelligence.registry.identity import (
    DuplicateCanonicalIDError,
    RegistryIdentityIndex,
)
from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)
from timan_intelligence.registry.vocabulary_repository import (
    VocabularyRepository,
)


def make_repository():
    """Create a repository with an independent identity index."""
    identity_index = RegistryIdentityIndex()
    repository = VocabularyRepository(identity_index)
    return repository, identity_index


def make_vocabulary(
    vocabulary_id="vocab.definition.statistical_purpose",
):
    """Create a valid vocabulary definition for testing."""
    return VocabularyDefinition(
        vocabulary_id=vocabulary_id,
        name="Statistical purposes",
        description="Defines the purposes of statistical analysis.",
        extensibility="controlled",
        completeness="exhaustive",
        status="active",
        version="1.0.0",
    )


def make_member(
    member_id="vocab.statistical_purpose.descriptive",
    vocabulary_id="vocab.definition.statistical_purpose",
    value="descriptive",
):
    """Create a valid vocabulary member for testing."""
    return VocabularyMember(
        member_id=member_id,
        vocabulary_id=vocabulary_id,
        value=value,
        label=value.replace("_", " ").title(),
        description=f"Represents {value} statistical analysis.",
    )


def test_repository_requires_registry_identity_index():
    with pytest.raises(TypeError):
        VocabularyRepository(identity_index=object())


def test_register_and_retrieve_vocabulary():
    repository, identity_index = make_repository()
    definition = make_vocabulary()

    repository.register_vocabulary(definition)

    retrieved = repository.get_vocabulary(
        "vocab.definition.statistical_purpose"
    )

    assert retrieved == definition
    assert repository.vocabulary_exists(
        "vocab.definition.statistical_purpose"
    )
    assert identity_index.contains(
        "vocab.definition.statistical_purpose"
    )


def test_register_vocabulary_rejects_wrong_object_type():
    repository, _ = make_repository()

    with pytest.raises(TypeError):
        repository.register_vocabulary(object())


def test_register_vocabulary_rejects_duplicate_id():
    repository, _ = make_repository()
    definition = make_vocabulary()

    repository.register_vocabulary(definition)

    with pytest.raises(ValueError, match="already registered"):
        repository.register_vocabulary(definition)


def test_register_vocabulary_rejects_id_already_in_global_index():
    repository, identity_index = make_repository()
    vocabulary_id = "vocab.definition.statistical_purpose"

    identity_index.register(
        canonical_id=vocabulary_id,
        namespace="vocab",
    )

    with pytest.raises(ValueError, match="already registered"):
        repository.register_vocabulary(
            make_vocabulary(vocabulary_id)
        )


def test_get_vocabulary_returns_none_for_unknown_valid_id():
    repository, _ = make_repository()

    assert repository.get_vocabulary(
        "vocab.definition.unknown"
    ) is None


def test_register_and_retrieve_vocabulary_member():
    repository, identity_index = make_repository()
    definition = make_vocabulary()
    member = make_member()

    repository.register_vocabulary(definition)
    repository.register_member(member)

    retrieved = repository.get_member(
        "vocab.statistical_purpose.descriptive"
    )

    assert retrieved == member
    assert repository.member_exists(
        "vocab.definition.statistical_purpose",
        "descriptive",
    )
    assert identity_index.contains(
        "vocab.statistical_purpose.descriptive"
    )


def test_register_member_rejects_wrong_object_type():
    repository, _ = make_repository()

    with pytest.raises(TypeError):
        repository.register_member(object())


def test_register_member_requires_existing_parent_vocabulary():
    repository, _ = make_repository()

    with pytest.raises(ValueError, match="is not registered"):
        repository.register_member(make_member())


def test_register_member_rejects_duplicate_member_id():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    member = make_member()
    repository.register_member(member)

    with pytest.raises(ValueError, match="already registered"):
        repository.register_member(member)


def test_register_member_rejects_id_already_in_global_index():
    repository, identity_index = make_repository()
    repository.register_vocabulary(make_vocabulary())

    member_id = "vocab.statistical_purpose.descriptive"

    identity_index.register(
        canonical_id=member_id,
        namespace="vocab",
    )

    with pytest.raises(ValueError, match="already registered"):
        repository.register_member(
            make_member(member_id=member_id)
        )


def test_register_member_rejects_empty_value():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    member = make_member(value=" ")

    with pytest.raises(ValueError, match="non-empty string"):
        repository.register_member(member)


def test_register_member_rejects_empty_label():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    member = make_member()
    member.label = " "

    with pytest.raises(ValueError, match="non-empty string"):
        repository.register_member(member)


def test_register_member_rejects_duplicate_value_within_vocabulary():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    repository.register_member(make_member())

    duplicate_value_member = make_member(
        member_id="vocab.statistical_purpose.summary",
        value="descriptive",
    )

    with pytest.raises(ValueError, match="already exists"):
        repository.register_member(duplicate_value_member)


def test_same_member_value_is_allowed_in_different_vocabularies():
    repository, _ = make_repository()

    first_vocabulary = make_vocabulary(
        "vocab.definition.statistical_purpose"
    )
    second_vocabulary = VocabularyDefinition(
        vocabulary_id="vocab.definition.method_family",
        name="Method families",
        description="Defines statistical method families.",
        extensibility="controlled",
        completeness="illustrative",
    )

    repository.register_vocabulary(first_vocabulary)
    repository.register_vocabulary(second_vocabulary)

    first_member = make_member(
        member_id="vocab.statistical_purpose.descriptive",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="descriptive",
    )
    second_member = make_member(
        member_id="vocab.method_family.descriptive",
        vocabulary_id="vocab.definition.method_family",
        value="descriptive",
    )

    repository.register_member(first_member)
    repository.register_member(second_member)

    assert repository.member_count() == 2


def test_get_member_returns_none_for_unknown_valid_id():
    repository, _ = make_repository()

    assert repository.get_member(
        "vocab.statistical_purpose.unknown"
    ) is None


def test_find_member_by_value():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())
    member = make_member()
    repository.register_member(member)

    found = repository.find_member(
        "vocab.definition.statistical_purpose",
        "descriptive",
    )

    assert found == member


def test_find_member_returns_none_when_value_is_unknown():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    assert repository.find_member(
        "vocab.definition.statistical_purpose",
        "unknown",
    ) is None


def test_find_member_rejects_non_string_value():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    with pytest.raises(TypeError, match="value must be a string"):
        repository.find_member(
            "vocab.definition.statistical_purpose",
            123,
        )


def test_list_vocabularies_returns_all_registered_definitions():
    repository, _ = make_repository()

    first = make_vocabulary()
    second = VocabularyDefinition(
        vocabulary_id="vocab.definition.method_family",
        name="Method families",
        description="Defines statistical method families.",
        extensibility="controlled",
        completeness="illustrative",
    )

    repository.register_vocabulary(first)
    repository.register_vocabulary(second)

    result = repository.list_vocabularies()

    assert len(result) == 2
    assert {item.vocabulary_id for item in result} == {
        first.vocabulary_id,
        second.vocabulary_id,
    }


def test_list_members_returns_only_members_of_requested_vocabulary():
    repository, _ = make_repository()

    first_vocabulary = make_vocabulary()
    second_vocabulary = VocabularyDefinition(
        vocabulary_id="vocab.definition.method_family",
        name="Method families",
        description="Defines statistical method families.",
        extensibility="controlled",
        completeness="illustrative",
    )

    repository.register_vocabulary(first_vocabulary)
    repository.register_vocabulary(second_vocabulary)

    first_member = make_member()
    second_member = make_member(
        member_id="vocab.method_family.mean_comparison",
        vocabulary_id="vocab.definition.method_family",
        value="mean_comparison",
    )

    repository.register_member(first_member)
    repository.register_member(second_member)

    result = repository.list_members(
        "vocab.definition.statistical_purpose"
    )

    assert len(result) == 1
    assert result[0] == first_member


def test_list_members_returns_empty_tuple_when_vocabulary_has_no_members():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    assert repository.list_members(
        "vocab.definition.statistical_purpose"
    ) == ()


def test_vocabulary_count_and_member_count():
    repository, _ = make_repository()

    repository.register_vocabulary(make_vocabulary())
    repository.register_member(make_member())

    assert repository.vocabulary_count() == 1
    assert repository.member_count() == 1


def test_vocabulary_exists_returns_false_for_unknown_valid_id():
    repository, _ = make_repository()

    assert repository.vocabulary_exists(
        "vocab.definition.unknown"
    ) is False


def test_member_exists_returns_false_for_unknown_value():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    assert repository.member_exists(
        "vocab.definition.statistical_purpose",
        "unknown",
    ) is False


def test_member_exists_rejects_non_string_value():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    with pytest.raises(TypeError, match="value must be a string"):
        repository.member_exists(
            "vocab.definition.statistical_purpose",
            123,
        )


def test_vocabulary_retrieval_returns_defensive_copy():
    repository, _ = make_repository()
    definition = make_vocabulary()
    repository.register_vocabulary(definition)

    retrieved = repository.get_vocabulary(
        "vocab.definition.statistical_purpose"
    )
    retrieved.name = "Modified externally"

    stored = repository.get_vocabulary(
        "vocab.definition.statistical_purpose"
    )

    assert stored.name == "Statistical purposes"


def test_member_retrieval_returns_defensive_copy():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    member = make_member()
    repository.register_member(member)

    retrieved = repository.get_member(
        "vocab.statistical_purpose.descriptive"
    )
    retrieved.label = "Modified externally"

    stored = repository.get_member(
        "vocab.statistical_purpose.descriptive"
    )

    assert stored.label == "Descriptive"


def test_list_vocabularies_returns_defensive_copies():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    listed = repository.list_vocabularies()
    listed[0].name = "Modified externally"

    stored = repository.get_vocabulary(
        "vocab.definition.statistical_purpose"
    )

    assert stored.name == "Statistical purposes"


def test_list_members_returns_defensive_copies():
    repository, _ = make_repository()
    repository.register_vocabulary(make_vocabulary())

    repository.register_member(make_member())

    listed = repository.list_members(
        "vocab.definition.statistical_purpose"
    )
    listed[0].label = "Modified externally"

    stored = repository.get_member(
        "vocab.statistical_purpose.descriptive"
    )

    assert stored.label == "Descriptive"
