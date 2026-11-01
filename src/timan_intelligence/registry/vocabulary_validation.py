
"""Validation utilities for the TimanStat controlled vocabulary registry.

This module validates vocabulary definitions, member identifiers,
vocabulary membership and classification eligibility.

It does not register records or modify the repository.
"""

from __future__ import annotations

from timan_intelligence.registry.namespace_identifiers import (
    validate_vocabulary_id,
)
from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)
from timan_intelligence.registry.vocabulary_repository import (
    VocabularyRepository,
)


class VocabularyError(ValueError):
    """Base exception for vocabulary validation errors."""


class InvalidVocabularyIDError(VocabularyError):
    """Raised when a vocabulary definition ID is invalid."""


class InvalidVocabularyMemberIDError(VocabularyError):
    """Raised when a vocabulary member ID is invalid."""


class VocabularyNotFoundError(VocabularyError):
    """Raised when a required vocabulary definition does not exist."""


class VocabularyMemberNotFoundError(VocabularyError):
    """Raised when a required vocabulary member does not exist."""


class DuplicateVocabularyError(VocabularyError):
    """Raised when a vocabulary definition is duplicated."""


class DuplicateVocabularyMemberError(VocabularyError):
    """Raised when a vocabulary member is duplicated."""


class VocabularyMembershipError(VocabularyError):
    """Raised when a member does not belong to the expected vocabulary."""


class DeprecatedVocabularyMemberError(VocabularyError):
    """Raised when a deprecated member is used for a new classification."""


class VocabularyCompatibilityError(VocabularyError):
    """Raised when vocabulary records are structurally incompatible."""


def validate_vocabulary_definition(
    definition: VocabularyDefinition,
) -> VocabularyDefinition:
    """Validate the structure and permitted values of a definition."""
    if not isinstance(definition, VocabularyDefinition):
        raise TypeError(
            "definition must be a VocabularyDefinition instance."
        )

    try:
        validate_vocabulary_id(definition.vocabulary_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyIDError(
            f"Invalid vocabulary ID: {definition.vocabulary_id!r}."
        ) from exc

    segments = definition.vocabulary_id.split(".")

    if len(segments) != 3 or segments[1] != "definition":
        raise InvalidVocabularyIDError(
            "A vocabulary definition ID must follow the format "
            "'vocab.definition.<vocabulary_key>'."
        )

    if not isinstance(definition.name, str) or not definition.name.strip():
        raise VocabularyCompatibilityError(
            "Vocabulary definition name must be a non-empty string."
        )

    if not isinstance(definition.description, str):
        raise VocabularyCompatibilityError(
            "Vocabulary definition description must be a string."
        )

    if definition.extensibility not in ("closed", "controlled"):
        raise VocabularyCompatibilityError(
            "Vocabulary extensibility must be 'closed' or 'controlled'."
        )

    if definition.completeness not in ("exhaustive", "illustrative"):
        raise VocabularyCompatibilityError(
            "Vocabulary completeness must be 'exhaustive' "
            "or 'illustrative'."
        )

    if definition.status not in ("draft", "active", "deprecated"):
        raise VocabularyCompatibilityError(
            "Vocabulary status must be 'draft', 'active' or 'deprecated'."
        )

    if not isinstance(definition.version, str) or not definition.version.strip():
        raise VocabularyCompatibilityError(
            "Vocabulary version must be a non-empty string."
        )

    if not isinstance(definition.source, str):
        raise VocabularyCompatibilityError(
            "Vocabulary source must be a string."
        )

    if not isinstance(definition.metadata, dict):
        raise VocabularyCompatibilityError(
            "Vocabulary metadata must be a dictionary."
        )

    return definition


def validate_vocabulary_member_structure(
    member: VocabularyMember,
) -> VocabularyMember:
    """Validate a member's structure and canonical identifiers."""
    if not isinstance(member, VocabularyMember):
        raise TypeError(
            "member must be a VocabularyMember instance."
        )

    try:
        validate_vocabulary_id(member.member_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyMemberIDError(
            f"Invalid vocabulary member ID: {member.member_id!r}."
        ) from exc

    try:
        validate_vocabulary_id(member.vocabulary_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyIDError(
            f"Invalid parent vocabulary ID: {member.vocabulary_id!r}."
        ) from exc

    parent_segments = member.vocabulary_id.split(".")
    member_segments = member.member_id.split(".")

    if (
        len(parent_segments) != 3
        or parent_segments[1] != "definition"
    ):
        raise InvalidVocabularyIDError(
            "A member's parent ID must follow the format "
            "'vocab.definition.<vocabulary_key>'."
        )

    if (
        len(member_segments) < 3
        or member_segments[1] != parent_segments[2]
    ):
        raise InvalidVocabularyMemberIDError(
            "A member ID must use the parent vocabulary key. "
            "Expected the format "
            "'vocab.<vocabulary_key>.<member_value>'."
        )

    if not isinstance(member.value, str) or not member.value.strip():
        raise VocabularyCompatibilityError(
            "Vocabulary member value must be a non-empty string."
        )

    if not isinstance(member.label, str) or not member.label.strip():
        raise VocabularyCompatibilityError(
            "Vocabulary member label must be a non-empty string."
        )

    if not isinstance(member.description, str):
        raise VocabularyCompatibilityError(
            "Vocabulary member description must be a string."
        )

    if not isinstance(member.aliases, list):
        raise VocabularyCompatibilityError(
            "Vocabulary member aliases must be a list."
        )

    if any(
        not isinstance(alias, str) or not alias.strip()
        for alias in member.aliases
    ):
        raise VocabularyCompatibilityError(
            "Every vocabulary member alias must be a non-empty string."
        )

    if member.status not in ("active", "deprecated"):
        raise VocabularyCompatibilityError(
            "Vocabulary member status must be 'active' or 'deprecated'."
        )

    if not isinstance(member.version, str) or not member.version.strip():
        raise VocabularyCompatibilityError(
            "Vocabulary member version must be a non-empty string."
        )

    if not isinstance(member.metadata, dict):
        raise VocabularyCompatibilityError(
            "Vocabulary member metadata must be a dictionary."
        )

    return member


def validate_vocabulary_membership(
    repository: VocabularyRepository,
    member_id: str,
    expected_vocabulary_id: str,
    *,
    allow_deprecated: bool = False,
) -> VocabularyMember:
    """Validate that a member exists and belongs to an expected vocabulary.

    Deprecated members are rejected by default for new classifications.
    They can be retrieved for historical or administrative purposes by
    setting allow_deprecated=True.
    """
    if not isinstance(repository, VocabularyRepository):
        raise TypeError(
            "repository must be a VocabularyRepository instance."
        )

    try:
        validated_member_id = validate_vocabulary_id(member_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyMemberIDError(
            f"Invalid vocabulary member ID: {member_id!r}."
        ) from exc

    try:
        validated_vocabulary_id = validate_vocabulary_id(
            expected_vocabulary_id
        )
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyIDError(
            f"Invalid expected vocabulary ID: "
            f"{expected_vocabulary_id!r}."
        ) from exc

    definition = repository.get_vocabulary(validated_vocabulary_id)

    if definition is None:
        raise VocabularyNotFoundError(
            f"Vocabulary '{validated_vocabulary_id}' does not exist."
        )

    if definition.status != "active":
        raise VocabularyCompatibilityError(
            f"Vocabulary '{validated_vocabulary_id}' is not active."
        )

    member = repository.get_member(validated_member_id)

    if member is None:
        raise VocabularyMemberNotFoundError(
            f"Vocabulary member '{validated_member_id}' does not exist."
        )

    validate_vocabulary_member_structure(member)

    if member.vocabulary_id != validated_vocabulary_id:
        raise VocabularyMembershipError(
            f"Member '{validated_member_id}' belongs to "
            f"'{member.vocabulary_id}', not "
            f"'{validated_vocabulary_id}'."
        )

    if member.status == "deprecated" and not allow_deprecated:
        raise DeprecatedVocabularyMemberError(
            f"Member '{validated_member_id}' is deprecated and "
            "cannot be used for a new classification."
        )

    return member


def validate_classification(
    repository: VocabularyRepository,
    vocabulary_id: str,
    value: str,
) -> VocabularyMember:
    """Validate a canonical value for use in a new classification."""
    if not isinstance(repository, VocabularyRepository):
        raise TypeError(
            "repository must be a VocabularyRepository instance."
        )

    try:
        validated_vocabulary_id = validate_vocabulary_id(vocabulary_id)
    except (TypeError, ValueError) as exc:
        raise InvalidVocabularyIDError(
            f"Invalid vocabulary ID: {vocabulary_id!r}."
        ) from exc

    if not isinstance(value, str) or not value.strip():
        raise VocabularyCompatibilityError(
            "Classification value must be a non-empty string."
        )

    definition = repository.get_vocabulary(validated_vocabulary_id)

    if definition is None:
        raise VocabularyNotFoundError(
            f"Vocabulary '{validated_vocabulary_id}' does not exist."
        )

    if definition.status != "active":
        raise VocabularyCompatibilityError(
            f"Vocabulary '{validated_vocabulary_id}' is not active."
        )

    member = repository.find_member(validated_vocabulary_id, value)

    if member is None:
        raise VocabularyMemberNotFoundError(
            f"Value '{value}' is not registered in vocabulary "
            f"'{validated_vocabulary_id}'."
        )

    if member.status == "deprecated":
        raise DeprecatedVocabularyMemberError(
            f"Value '{value}' is deprecated in vocabulary "
            f"'{validated_vocabulary_id}'."
        )

    return member
