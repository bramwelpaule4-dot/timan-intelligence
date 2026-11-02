
"""Tests for the shared TimanStat entity repository."""

from __future__ import annotations

import copy

import pytest

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.entity_repository import EntityRepository
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
from timan_intelligence.registry.vocabulary_validation import (
    DeprecatedVocabularyMemberError,
    VocabularyCompatibilityError,
    VocabularyMemberNotFoundError,
)


ENTITY_ID = "method.test.entity"


def build_dependencies():
    """Create shared identity and vocabulary repositories."""
    identity_index = RegistryIdentityIndex()
    vocabulary_repository = VocabularyRepository(identity_index)

    vocabulary_definitions = [
        VocabularyDefinition(
            vocabulary_id="vocab.definition.entity_type",
            name="Entity types",
            description="Statistical registry entity types.",
            extensibility="closed",
            completeness="exhaustive",
            status="active",
        ),
        VocabularyDefinition(
            vocabulary_id="vocab.definition.knowledge_area",
            name="Knowledge areas",
            description="Statistical knowledge areas.",
            extensibility="controlled",
            completeness="illustrative",
            status="active",
        ),
        VocabularyDefinition(
            vocabulary_id="vocab.definition.statistical_purpose",
            name="Statistical purposes",
            description="Statistical purposes.",
            extensibility="closed",
            completeness="exhaustive",
            status="active",
        ),
        VocabularyDefinition(
            vocabulary_id="vocab.definition.method_family",
            name="Method families",
            description="Families of statistical methods.",
            extensibility="controlled",
            completeness="illustrative",
            status="active",
        ),
        VocabularyDefinition(
            vocabulary_id="vocab.definition.inference_paradigm",
            name="Inference paradigms",
            description="Statistical inference paradigms.",
            extensibility="closed",
            completeness="exhaustive",
            status="active",
        ),
        VocabularyDefinition(
            vocabulary_id="vocab.definition.application_domain",
            name="Application domains",
            description="Domains where statistics are applied.",
            extensibility="controlled",
            completeness="illustrative",
            status="active",
        ),
    ]

    for definition in vocabulary_definitions:
        vocabulary_repository.register_vocabulary(definition)

    vocabulary_values = {
        "vocab.definition.entity_type": [
            "method",
            "model",
            "design",
            "diagnostic",
            "algorithm",
            "measure",
            "visualization",
            "theory",
            "distribution",
        ],
        "vocab.definition.knowledge_area": [
            "probability",
            "descriptive_statistics",
        ],
        "vocab.definition.statistical_purpose": [
            "description",
            "inference",
        ],
        "vocab.definition.method_family": [
            "regression",
            "hypothesis_testing",
        ],
        "vocab.definition.inference_paradigm": [
            "frequentist",
            "bayesian",
        ],
        "vocab.definition.application_domain": [
            "health",
            "education",
        ],
    }

    for vocabulary_id, values in vocabulary_values.items():
        vocabulary_name = vocabulary_id.removeprefix(
            "vocab.definition."
        )

        for value in values:
            member_id = f"vocab.{vocabulary_name}.{value}"

            vocabulary_repository.register_member(
                VocabularyMember(
                    member_id=member_id,
                    vocabulary_id=vocabulary_id,
                    value=value,
                    label=value.replace("_", " ").title(),
                    description=f"Test vocabulary member: {value}.",
                    status="active",
                )
            )

    return identity_index, vocabulary_repository


def build_entity(
    *,
    entity_id: str = ENTITY_ID,
    knowledge_areas: list[str] | None = None,
    statistical_purposes: list[str] | None = None,
    application_domains: list[str] | None = None,
    inference_paradigms: list[str] | None = None,
    method_families: list[str] | None = None,
) -> RegistryEntity:
    """Build a valid RegistryEntity for repository tests."""
    return RegistryEntity(
        entity_id=entity_id,
        name="Test statistical method",
        entity_type="method",
        description="A test registry entity.",
        knowledge_areas=(
            ["probability"]
            if knowledge_areas is None
            else knowledge_areas
        ),
        statistical_purposes=(
            ["description"]
            if statistical_purposes is None
            else statistical_purposes
        ),
        application_domains=(
            ["health"]
            if application_domains is None
            else application_domains
        ),
        inference_paradigms=(
            ["frequentist"]
            if inference_paradigms is None
            else inference_paradigms
        ),
        method_families=(
            ["regression"]
            if method_families is None
            else method_families
        ),
    )


def build_repository():
    """Create a repository with registered test vocabularies."""
    identity_index, vocabulary_repository = build_dependencies()

    repository = EntityRepository(
        identity_index=identity_index,
        vocabulary_repository=vocabulary_repository,
    )

    return repository, identity_index, vocabulary_repository


def test_repository_requires_identity_index():
    """The repository requires a RegistryIdentityIndex."""
    _, vocabulary_repository = build_dependencies()

    with pytest.raises(TypeError):
        EntityRepository(
            identity_index=object(),
            vocabulary_repository=vocabulary_repository,
        )


def test_repository_requires_vocabulary_repository():
    """The repository requires a VocabularyRepository."""
    identity_index, _ = build_dependencies()

    with pytest.raises(TypeError):
        EntityRepository(
            identity_index=identity_index,
            vocabulary_repository=object(),
        )


def test_register_requires_registry_entity():
    """Only RegistryEntity instances can be registered."""
    repository, _, _ = build_repository()

    with pytest.raises(TypeError):
        repository.register(object())


def test_register_valid_entity():
    """A valid entity is registered and returned."""
    repository, identity_index, _ = build_repository()
    entity = build_entity()

    registered = repository.register(entity)

    assert registered == entity
    assert registered is not entity
    assert repository.exists(ENTITY_ID)
    assert repository.count() == 1
    assert identity_index.contains(ENTITY_ID)


def test_register_preserves_entity_subclass():
    """A valid RegistryEntity subclass retains its concrete type."""
    from timan_intelligence.registry.method import MethodEntity

    repository, _, _ = build_repository()

    method = MethodEntity(
        entity_id="method.test.subclass",
        name="Test method subclass",
        description="A test method entity.",
        knowledge_areas=["probability"],
        statistical_purposes=["description"],
    )

    registered = repository.register(method)

    assert isinstance(registered, MethodEntity)
    assert registered.entity_type == "method"


def test_get_returns_registered_entity():
    """The get method retrieves an entity by canonical ID."""
    repository, _, _ = build_repository()
    entity = build_entity()

    repository.register(entity)

    retrieved = repository.get(ENTITY_ID)

    assert retrieved == entity
    assert retrieved is not entity


def test_get_returns_none_for_unknown_entity():
    """Unknown entity IDs return None."""
    repository, _, _ = build_repository()

    assert repository.get("method.unknown.entity") is None


def test_list_all_returns_registered_entities():
    """The list method returns all stored entities."""
    repository, _, _ = build_repository()

    first = build_entity()
    second = build_entity(entity_id="method.test.second_entity")

    repository.register(first)
    repository.register(second)

    entities = repository.list_all()

    assert len(entities) == 2
    assert first in entities
    assert second in entities


def test_list_all_returns_defensive_copies():
    """Changing returned entities cannot mutate repository state."""
    repository, _, _ = build_repository()

    repository.register(build_entity())

    entities = repository.list_all()
    entities[0].name = "Modified outside repository"

    stored = repository.get(ENTITY_ID)

    assert stored is not None
    assert stored.name == "Test statistical method"


def test_register_returns_defensive_copy():
    """Changing the returned entity cannot mutate stored state."""
    repository, _, _ = build_repository()

    registered = repository.register(build_entity())
    registered.name = "Changed returned object"

    stored = repository.get(ENTITY_ID)

    assert stored is not None
    assert stored.name == "Test statistical method"


def test_register_does_not_store_original_object():
    """Changing the original entity cannot mutate stored state."""
    repository, _, _ = build_repository()

    entity = build_entity()
    repository.register(entity)

    entity.name = "Changed original object"

    stored = repository.get(ENTITY_ID)

    assert stored is not None
    assert stored.name == "Test statistical method"


def test_register_rejects_duplicate_local_entity():
    """An entity cannot be registered twice in the same repository."""
    repository, _, _ = build_repository()

    repository.register(build_entity())

    with pytest.raises(ValueError, match="already registered"):
        repository.register(build_entity())


@pytest.mark.parametrize(
    ("field_name", "invalid_values"),
    [
        ("knowledge_areas", ["unknown_area"]),
        ("statistical_purposes", ["unknown_purpose"]),
        ("application_domains", ["unknown_domain"]),
        ("inference_paradigms", ["unknown_paradigm"]),
        ("method_families", ["unknown_family"]),
    ],
)
def test_register_rejects_unregistered_classification_values(
    field_name,
    invalid_values,
):
    """Unregistered classification values must be rejected."""
    repository, identity_index, _ = build_repository()

    entity = build_entity(**{field_name: invalid_values})

    with pytest.raises(VocabularyMemberNotFoundError):
        repository.register(entity)

    assert not repository.exists(ENTITY_ID)
    assert not identity_index.contains(ENTITY_ID)


def test_register_rejects_invalid_entity_type():
    """An entity type absent from its vocabulary must be rejected."""
    repository, identity_index, _ = build_repository()

    entity = build_entity()
    entity.entity_type = "unknown_type"

    with pytest.raises(VocabularyMemberNotFoundError):
        repository.register(entity)

    assert not identity_index.contains(ENTITY_ID)


def test_register_rejects_invalid_classification_structure():
    """Classification fields must preserve their declared list type."""
    repository, identity_index, _ = build_repository()

    entity = build_entity()
    entity.knowledge_areas = "probability"

    with pytest.raises(VocabularyCompatibilityError):
        repository.register(entity)

    assert not identity_index.contains(ENTITY_ID)


def test_register_rejects_deprecated_vocabulary_member():
    """Deprecated classification members cannot be newly registered."""
    repository, identity_index, vocabulary_repository = (
        build_repository()
    )

    deprecated_member = VocabularyMember(
        member_id="vocab.knowledge_area.deprecated_area",
        vocabulary_id="vocab.definition.knowledge_area",
        value="deprecated_area",
        label="Deprecated area",
        description="A deprecated test classification.",
        status="deprecated",
    )

    vocabulary_repository.register_member(deprecated_member)

    entity = build_entity(
        knowledge_areas=["deprecated_area"]
    )

    with pytest.raises(DeprecatedVocabularyMemberError):
        repository.register(entity)

    assert not identity_index.contains(ENTITY_ID)


def test_register_rejects_inactive_vocabulary():
    """Classifications cannot use a vocabulary that is not active."""
    repository, identity_index, _ = build_repository()

    # Use a separate identity index and vocabulary repository so that
    # the entity-type vocabulary can be registered in draft status.
    identity_index_2 = RegistryIdentityIndex()
    inactive_repository = VocabularyRepository(identity_index_2)

    inactive_repository.register_vocabulary(
        VocabularyDefinition(
            vocabulary_id="vocab.definition.entity_type",
            name="Entity types",
            description="Inactive test vocabulary.",
            extensibility="closed",
            completeness="exhaustive",
            status="draft",
        )
    )

    entity_type_member = VocabularyMember(
        member_id="vocab.entity_type.method",
        vocabulary_id="vocab.definition.entity_type",
        value="method",
        label="Method",
        description="Statistical method.",
    )

    inactive_repository.register_member(entity_type_member)

    repository = EntityRepository(
        identity_index=identity_index,
        vocabulary_repository=inactive_repository,
    )

    with pytest.raises(Exception):
        repository.register(build_entity())

    assert not identity_index.contains(ENTITY_ID)


def test_failed_validation_does_not_claim_canonical_identity():
    """Failed classification validation must not register an ID."""
    repository, identity_index, _ = build_repository()

    entity = build_entity(
        knowledge_areas=["not_registered"]
    )

    with pytest.raises(VocabularyMemberNotFoundError):
        repository.register(entity)

    assert not identity_index.contains(ENTITY_ID)

    # The same ID can subsequently be used by a valid entity.
    valid_entity = build_entity()
    registered = repository.register(valid_entity)

    assert registered.entity_id == ENTITY_ID
    assert identity_index.contains(ENTITY_ID)


def test_register_rejects_globally_duplicate_canonical_id():
    """An ID already claimed elsewhere cannot be registered."""
    repository, identity_index, _ = build_repository()

    identity_index.register(
        canonical_id=ENTITY_ID,
        namespace="statistical",
        entity_type="method",
    )

    with pytest.raises(DuplicateCanonicalIDError):
        repository.register(build_entity())

    assert not repository.exists(ENTITY_ID)


def test_register_rejects_invalid_canonical_entity_id():
    """Malformed canonical entity IDs must be rejected."""
    repository, identity_index, _ = build_repository()

    entity = build_entity(entity_id="invalid_id")

    with pytest.raises(ValueError):
        repository.register(entity)

    assert not identity_index.contains("invalid_id")


def test_exists_returns_false_for_unknown_entity():
    """The exists method returns False for unknown IDs."""
    repository, _, _ = build_repository()

    assert not repository.exists("method.unknown.entity")


def test_exists_returns_true_for_registered_entity():
    """The exists method returns True for registered IDs."""
    repository, _, _ = build_repository()

    repository.register(build_entity())

    assert repository.exists(ENTITY_ID)


def test_count_returns_zero_for_empty_repository():
    """An empty repository has a count of zero."""
    repository, _, _ = build_repository()

    assert repository.count() == 0


def test_count_returns_number_of_registered_entities():
    """The count method reflects successful registrations."""
    repository, _, _ = build_repository()

    repository.register(build_entity())
    repository.register(
        build_entity(entity_id="method.test.second_entity")
    )

    assert repository.count() == 2


def test_register_does_not_change_input_entity():
    """Registration leaves the supplied entity unchanged."""
    repository, _, _ = build_repository()

    entity = build_entity()
    original = copy.deepcopy(entity)

    repository.register(entity)

    assert entity == original


def test_empty_optional_classification_lists_are_allowed():
    """Empty optional classification lists remain permitted."""
    repository, _, _ = build_repository()

    entity = build_entity(
        knowledge_areas=[],
        statistical_purposes=[],
        application_domains=[],
        inference_paradigms=[],
        method_families=[],
    )

    registered = repository.register(entity)

    assert registered.knowledge_areas == []
    assert registered.statistical_purposes == []
    assert registered.application_domains == []
    assert registered.inference_paradigms == []
    assert registered.method_families == []
