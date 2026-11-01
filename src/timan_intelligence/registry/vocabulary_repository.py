
"""In-memory repository for TimanStat controlled vocabularies.

The repository manages vocabulary definitions and their canonical members.
It delegates global canonical ID uniqueness to RegistryIdentityIndex.

Validation of vocabulary semantics is kept separate so that this module
remains focused on storage, retrieval and repository-level integrity.
"""

from __future__ import annotations

import copy

from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.namespace_identifiers import (
    validate_vocabulary_id,
)
from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)


class VocabularyRepository:
    """Manage controlled vocabulary definitions and members."""

    def __init__(self, identity_index: RegistryIdentityIndex) -> None:
        if not isinstance(identity_index, RegistryIdentityIndex):
            raise TypeError(
                "identity_index must be a RegistryIdentityIndex instance."
            )

        self._identity_index = identity_index

        self._vocabularies: dict[str, VocabularyDefinition] = {}
        self._members: dict[str, VocabularyMember] = {}

        self._members_by_value: dict[tuple[str, str], str] = {}

    def register_vocabulary(
        self,
        definition: VocabularyDefinition,
    ) -> None:
        """Register a vocabulary definition and its canonical identity."""
        if not isinstance(definition, VocabularyDefinition):
            raise TypeError(
                "definition must be a VocabularyDefinition instance."
            )

        vocabulary_id = validate_vocabulary_id(definition.vocabulary_id)

        if vocabulary_id in self._vocabularies:
            raise ValueError(
                f"Vocabulary '{vocabulary_id}' is already registered."
            )

        if self._identity_index.contains(vocabulary_id):
            raise ValueError(
                f"Canonical ID '{vocabulary_id}' is already registered "
                "in the global identity index."
            )

        stored_definition = copy.deepcopy(definition)

        self._identity_index.register(
            canonical_id=vocabulary_id,
            namespace="vocab",
        )

        self._vocabularies[vocabulary_id] = stored_definition

    def register_member(
        self,
        member: VocabularyMember,
    ) -> None:
        """Register a canonical member under an existing vocabulary."""
        if not isinstance(member, VocabularyMember):
            raise TypeError(
                "member must be a VocabularyMember instance."
            )

        member_id = validate_vocabulary_id(member.member_id)
        vocabulary_id = validate_vocabulary_id(member.vocabulary_id)

        if vocabulary_id not in self._vocabularies:
            raise ValueError(
                f"Parent vocabulary '{vocabulary_id}' is not registered."
            )

        if member_id in self._members:
            raise ValueError(
                f"Vocabulary member '{member_id}' is already registered."
            )

        if self._identity_index.contains(member_id):
            raise ValueError(
                f"Canonical ID '{member_id}' is already registered "
                "in the global identity index."
            )

        if not isinstance(member.value, str) or not member.value.strip():
            raise ValueError(
                "Vocabulary member value must be a non-empty string."
            )

        value_key = (vocabulary_id, member.value)

        if value_key in self._members_by_value:
            raise ValueError(
                f"Value '{member.value}' already exists in vocabulary "
                f"'{vocabulary_id}'."
            )

        if not isinstance(member.label, str) or not member.label.strip():
            raise ValueError(
                "Vocabulary member label must be a non-empty string."
            )

        stored_member = copy.deepcopy(member)

        self._identity_index.register(
            canonical_id=member_id,
            namespace="vocab",
        )

        self._members[member_id] = stored_member
        self._members_by_value[value_key] = member_id

    def get_vocabulary(
        self,
        vocabulary_id: str,
    ) -> VocabularyDefinition | None:
        """Retrieve a vocabulary definition by canonical ID."""
        validated_id = validate_vocabulary_id(vocabulary_id)
        definition = self._vocabularies.get(validated_id)

        if definition is None:
            return None

        return copy.deepcopy(definition)

    def get_member(
        self,
        member_id: str,
    ) -> VocabularyMember | None:
        """Retrieve a vocabulary member by canonical ID."""
        validated_id = validate_vocabulary_id(member_id)
        member = self._members.get(validated_id)

        if member is None:
            return None

        return copy.deepcopy(member)

    def find_member(
        self,
        vocabulary_id: str,
        value: str,
    ) -> VocabularyMember | None:
        """Find a member by its canonical value within a vocabulary."""
        validated_id = validate_vocabulary_id(vocabulary_id)

        if not isinstance(value, str):
            raise TypeError("value must be a string.")

        member_id = self._members_by_value.get(
            (validated_id, value)
        )

        if member_id is None:
            return None

        return self.get_member(member_id)

    def list_vocabularies(
        self,
    ) -> tuple[VocabularyDefinition, ...]:
        """Return all registered vocabulary definitions."""
        return tuple(
            copy.deepcopy(definition)
            for definition in self._vocabularies.values()
        )

    def list_members(
        self,
        vocabulary_id: str,
    ) -> tuple[VocabularyMember, ...]:
        """Return all members registered under a vocabulary."""
        validated_id = validate_vocabulary_id(vocabulary_id)

        return tuple(
            copy.deepcopy(member)
            for member in self._members.values()
            if member.vocabulary_id == validated_id
        )

    def member_exists(
        self,
        vocabulary_id: str,
        value: str,
    ) -> bool:
        """Check whether a canonical value exists in a vocabulary."""
        validated_id = validate_vocabulary_id(vocabulary_id)

        if not isinstance(value, str):
            raise TypeError("value must be a string.")

        return (validated_id, value) in self._members_by_value

    def vocabulary_exists(self, vocabulary_id: str) -> bool:
        """Check whether a vocabulary definition is registered."""
        validated_id = validate_vocabulary_id(vocabulary_id)
        return validated_id in self._vocabularies

    def vocabulary_count(self) -> int:
        """Return the number of registered vocabulary definitions."""
        return len(self._vocabularies)

    def member_count(self) -> int:
        """Return the total number of registered vocabulary members."""
        return len(self._members)
