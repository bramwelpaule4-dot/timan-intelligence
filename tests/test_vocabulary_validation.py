
"""Tests for TimanStat controlled vocabulary validation."""

import pytest

from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)
from timan_intelligence.registry.vocabulary_repository import (
    VocabularyRepository,
)
from timan_intelligence.registry.vocabulary_validation import (
    DeprecatedVocabularyMemberError,
    DuplicateVocabularyError,
    DuplicateVocabularyMemberError,
    InvalidVocabularyIDError,
    InvalidVocabularyMemberIDError,
    VocabularyCompatibilityError,
    VocabularyMemberNotFoundError,
    VocabularyMembershipError,
    VocabularyNotFoundError,
    validate_classification,
    validate_vocabulary_definition,
    validate_vocabulary_member_structure,
    validate_vocabulary_membership,
)


STATISTICAL_PURPOSE_ID = "vocab.definition.statistical_purpose"
KNOWLEDGE_AREA_ID = "vocab.definition.knowledge_area"

STATISTICAL_PURPOSE_MEMBER_ID = "vocab.statistical_purpose.descriptive"
KNOWLEDGE_AREA_MEMBER_ID = "vocab.knowledge_area.biostatistics"


def make_definition(
    vocabulary_id=STATISTICAL_PURPOSE_ID,
    *,
    status="active",
):
    return VocabularyDefinition(
        vocabulary_id=vocabulary_id,
        name="Statistical Purpose",
        description="Classifies the purpose of a statistical method.",
        extensibility="controlled",
        completeness="exhaustive",
        status=status,
        version="1.0.0",
        source="Catalogue Version 2.1",
    )


def make_member(
    member_id=STATISTICAL_PURPOSE_MEMBER_ID,
    vocabulary_id=STATISTICAL_PURPOSE_ID,
    *,
    value="descriptive",
    status="active",
):
    return VocabularyMember(
        member_id=member_id,
        vocabulary_id=vocabulary_id,
        value=value,
        label=value.replace("_", " ").title(),
        description=f"Description of {value}.",
        status=status,
        version="1.0.0",
    )


def make_repository(
    *,
    definition=None,
    member=None,
):
    repository = VocabularyRepository(RegistryIdentityIndex())
    repository.register_vocabulary(
        definition or make_definition()
    )
    repository.register_member(
        member or make_member()
    )
    return repository


# ---------------------------------------------------------------------
# Vocabulary definition validation
# ---------------------------------------------------------------------


def test_validate_vocabulary_definition_accepts_valid_definition():
    definition = make_definition()

    result = validate_vocabulary_definition(definition)

    assert result is definition


def test_validate_vocabulary_definition_rejects_wrong_object_type():
    with pytest.raises(TypeError):
        validate_vocabulary_definition("not a vocabulary definition")


@pytest.mark.parametrize(
    "vocabulary_id",
    [
        "",
        "invalid",
        "vocab",
        "vocab.definition",
        "vocab.wrong_key.statistical_purpose",
        "vocab.definition.statistical_purpose.extra",
    ],
)
def test_validate_vocabulary_definition_rejects_invalid_ids(
    vocabulary_id,
):
    definition = make_definition(vocabulary_id)

    with pytest.raises(InvalidVocabularyIDError):
        validate_vocabulary_definition(definition)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "   "),
        ("name", None),
        ("description", None),
        ("extensibility", "unrestricted"),
        ("completeness", "unknown"),
        ("status", "published"),
        ("version", ""),
        ("version", "   "),
        ("version", None),
        ("source", None),
        ("metadata", []),
    ],
)
def test_validate_vocabulary_definition_rejects_invalid_fields(
    field,
    value,
):
    definition = make_definition()
    setattr(definition, field, value)

    with pytest.raises(VocabularyCompatibilityError):
        validate_vocabulary_definition(definition)


@pytest.mark.parametrize(
    "extensibility",
    ["closed", "controlled"],
)
def test_validate_vocabulary_definition_accepts_valid_extensibility(
    extensibility,
):
    definition = make_definition()
    definition.extensibility = extensibility

    assert validate_vocabulary_definition(definition) is definition


@pytest.mark.parametrize(
    "completeness",
    ["exhaustive", "illustrative"],
)
def test_validate_vocabulary_definition_accepts_valid_completeness(
    completeness,
):
    definition = make_definition()
    definition.completeness = completeness

    assert validate_vocabulary_definition(definition) is definition


@pytest.mark.parametrize(
    "status",
    ["draft", "active", "deprecated"],
)
def test_validate_vocabulary_definition_accepts_valid_status(status):
    definition = make_definition(status=status)

    assert validate_vocabulary_definition(definition) is definition


# ---------------------------------------------------------------------
# Vocabulary member structure validation
# ---------------------------------------------------------------------


def test_validate_vocabulary_member_structure_accepts_valid_member():
    member = make_member()

    result = validate_vocabulary_member_structure(member)

    assert result is member


def test_validate_vocabulary_member_structure_rejects_wrong_object_type():
    with pytest.raises(TypeError):
        validate_vocabulary_member_structure("not a vocabulary member")


def test_validate_vocabulary_member_structure_rejects_invalid_member_id():
    member = make_member(member_id="invalid")

    with pytest.raises(InvalidVocabularyMemberIDError):
        validate_vocabulary_member_structure(member)


def test_validate_vocabulary_member_structure_rejects_invalid_parent_id():
    member = make_member(vocabulary_id="invalid")

    with pytest.raises(InvalidVocabularyIDError):
        validate_vocabulary_member_structure(member)


def test_validate_vocabulary_member_structure_requires_parent_key_in_member_id():
    member = make_member(
        member_id="vocab.knowledge_area.biostatistics"
    )

    with pytest.raises(InvalidVocabularyMemberIDError):
        validate_vocabulary_member_structure(member)


def test_validate_vocabulary_member_structure_rejects_short_member_id():
    member = make_member(member_id="vocab.statistical_purpose")

    with pytest.raises(InvalidVocabularyMemberIDError):
        validate_vocabulary_member_structure(member)


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", ""),
        ("value", "   "),
        ("value", None),
        ("label", ""),
        ("label", "   "),
        ("label", None),
        ("description", None),
        ("aliases", "not-a-list"),
        ("aliases", None),
        ("status", "draft"),
        ("version", ""),
        ("version", "   "),
        ("version", None),
        ("metadata", []),
    ],
)
def test_validate_vocabulary_member_structure_rejects_invalid_fields(
    field,
    value,
):
    member = make_member()
    setattr(member, field, value)

    with pytest.raises(VocabularyCompatibilityError):
        validate_vocabulary_member_structure(member)


@pytest.mark.parametrize(
    "aliases",
    [
        [""],
        ["   "],
        [None],
        [1],
    ],
)
def test_validate_vocabulary_member_structure_rejects_invalid_aliases(
    aliases,
):
    member = make_member()
    member.aliases = aliases

    with pytest.raises(VocabularyCompatibilityError):
        validate_vocabulary_member_structure(member)


@pytest.mark.parametrize(
    "status",
    ["active", "deprecated"],
)
def test_validate_vocabulary_member_structure_accepts_valid_status(
    status,
):
    member = make_member(status=status)

    assert validate_vocabulary_member_structure(member) is member


def test_validate_vocabulary_member_structure_accepts_valid_aliases():
    member = make_member()
    member.aliases = ["description", "descriptive_analysis"]

    assert validate_vocabulary_member_structure(member) is member


# ---------------------------------------------------------------------
# Vocabulary membership validation
# ---------------------------------------------------------------------


def test_validate_vocabulary_membership_returns_valid_member():
    repository = make_repository()

    result = validate_vocabulary_membership(
        repository,
        STATISTICAL_PURPOSE_MEMBER_ID,
        STATISTICAL_PURPOSE_ID,
    )

    assert result.member_id == STATISTICAL_PURPOSE_MEMBER_ID
    assert result.vocabulary_id == STATISTICAL_PURPOSE_ID


def test_validate_vocabulary_membership_rejects_wrong_repository_type():
    with pytest.raises(TypeError):
        validate_vocabulary_membership(
            "not a repository",
            STATISTICAL_PURPOSE_MEMBER_ID,
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_rejects_invalid_member_id():
    repository = make_repository()

    with pytest.raises(InvalidVocabularyMemberIDError):
        validate_vocabulary_membership(
            repository,
            "invalid",
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_rejects_invalid_vocabulary_id():
    repository = make_repository()

    with pytest.raises(InvalidVocabularyIDError):
        validate_vocabulary_membership(
            repository,
            STATISTICAL_PURPOSE_MEMBER_ID,
            "invalid",
        )


def test_validate_vocabulary_membership_rejects_missing_vocabulary():
    repository = VocabularyRepository(RegistryIdentityIndex())

    with pytest.raises(VocabularyNotFoundError):
        validate_vocabulary_membership(
            repository,
            STATISTICAL_PURPOSE_MEMBER_ID,
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_rejects_inactive_vocabulary():
    definition = make_definition(status="draft")
    repository = make_repository(definition=definition)

    with pytest.raises(VocabularyCompatibilityError):
        validate_vocabulary_membership(
            repository,
            STATISTICAL_PURPOSE_MEMBER_ID,
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_rejects_missing_member():
    repository = make_repository()

    with pytest.raises(VocabularyMemberNotFoundError):
        validate_vocabulary_membership(
            repository,
            "vocab.statistical_purpose.missing",
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_rejects_member_from_another_vocabulary():
    repository = make_repository()

    with pytest.raises(VocabularyMembershipError):
        validate_vocabulary_membership(
            repository,
            STATISTICAL_PURPOSE_MEMBER_ID,
            KNOWLEDGE_AREA_ID,
        )


def test_validate_vocabulary_membership_rejects_deprecated_member_by_default():
    member = make_member(status="deprecated")
    repository = make_repository(member=member)

    with pytest.raises(DeprecatedVocabularyMemberError):
        validate_vocabulary_membership(
            repository,
            STATISTICAL_PURPOSE_MEMBER_ID,
            STATISTICAL_PURPOSE_ID,
        )


def test_validate_vocabulary_membership_allows_deprecated_member_when_requested():
    member = make_member(status="deprecated")
    repository = make_repository(member=member)

    result = validate_vocabulary_membership(
        repository,
        STATISTICAL_PURPOSE_MEMBER_ID,
        STATISTICAL_PURPOSE_ID,
        allow_deprecated=True,
    )

    assert result.member_id == STATISTICAL_PURPOSE_MEMBER_ID
    assert result.status == "deprecated"


# ---------------------------------------------------------------------
# Classification validation
# ---------------------------------------------------------------------


def test_validate_classification_returns_registered_active_member():
    repository = make_repository()

    result = validate_classification(
        repository,
        STATISTICAL_PURPOSE_ID,
        "descriptive",
    )

    assert result.member_id == STATISTICAL_PURPOSE_MEMBER_ID
    assert result.value == "descriptive"


def test_validate_classification_rejects_wrong_repository_type():
    with pytest.raises(TypeError):
        validate_classification(
            "not a repository",
            STATISTICAL_PURPOSE_ID,
            "descriptive",
        )


@pytest.mark.parametrize(
    "vocabulary_id",
    [
        "",
        "invalid",
        "vocab",
    ],
)
def test_validate_classification_rejects_invalid_vocabulary_id(
    vocabulary_id,
):
    repository = make_repository()

    with pytest.raises(InvalidVocabularyIDError):
        validate_classification(
            repository,
            vocabulary_id,
            "descriptive",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_validate_classification_rejects_invalid_values(value):
    repository = make_repository()

    with pytest.raises(VocabularyCompatibilityError):
        validate_classification(
            repository,
            STATISTICAL_PURPOSE_ID,
            value,
        )


def test_validate_classification_rejects_missing_vocabulary():
    repository = VocabularyRepository(RegistryIdentityIndex())

    with pytest.raises(VocabularyNotFoundError):
        validate_classification(
            repository,
            STATISTICAL_PURPOSE_ID,
            "descriptive",
        )


def test_validate_classification_rejects_inactive_vocabulary():
    definition = make_definition(status="deprecated")
    repository = make_repository(definition=definition)

    with pytest.raises(VocabularyCompatibilityError):
        validate_classification(
            repository,
            STATISTICAL_PURPOSE_ID,
            "descriptive",
        )


def test_validate_classification_rejects_unregistered_value():
    repository = make_repository()

    with pytest.raises(VocabularyMemberNotFoundError):
        validate_classification(
            repository,
            STATISTICAL_PURPOSE_ID,
            "predictive",
        )


def test_validate_classification_rejects_deprecated_member():
    member = make_member(status="deprecated")
    repository = make_repository(member=member)

    with pytest.raises(DeprecatedVocabularyMemberError):
        validate_classification(
            repository,
            STATISTICAL_PURPOSE_ID,
            "descriptive",
        )
