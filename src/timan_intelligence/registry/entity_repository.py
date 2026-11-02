```python
"""In-memory repository for TimanStat registry entities.

The repository stores complete RegistryEntity records while delegating
canonical identity uniqueness to the shared RegistryIdentityIndex.

Entity classifications are validated against controlled vocabularies
before canonical identity registration.
"""

from __future__ import annotations

import copy

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.entity_vocabulary_validation import (
    validate_entity_classifications,
)
from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.vocabulary_repository import (
    VocabularyRepository,
)


class EntityRepository:
    """Store and retrieve validated statistical registry entities."""

    def __init__(
        self,
        identity_index: RegistryIdentityIndex,
        vocabulary_repository: VocabularyRepository,
    ) -> None:
        """Initialise the repository with shared registry dependencies."""
        if not isinstance(identity_index, RegistryIdentityIndex):
            raise TypeError(
                "identity_index must be a RegistryIdentityIndex instance."
            )

        if not isinstance(vocabulary_repository, VocabularyRepository):
            raise TypeError(
                "vocabulary_repository must be a VocabularyRepository instance."
            )

        self._identity_index = identity_index
        self._vocabulary_repository = vocabulary_repository
        self._entities: dict[str, RegistryEntity] = {}

    def register(self, entity: RegistryEntity) -> RegistryEntity:
        """Validate and register an entity.

        Classification validation occurs before canonical identity
        registration. This prevents invalid entities from claiming
        canonical IDs in the shared identity index.

        The stored record is a deep copy, preventing callers from
        mutating repository state through the original object.

        Args:
            entity: A RegistryEntity instance or subclass.

        Returns:
            A defensive copy of the registered entity.

        Raises:
            TypeError: If entity is not a RegistryEntity instance.
            ValueError: If the entity is already registered locally.
            VocabularyCompatibilityError: If its classification
                structure is invalid.
            VocabularyError: If a classification is not valid
                against its controlled vocabulary.
            RegistryIdentityError: If its canonical ID is invalid
                or already registered globally.
        """
        if not isinstance(entity, RegistryEntity):
            raise TypeError(
                "entity must be a RegistryEntity instance."
            )

        entity_id = entity.entity_id

        if entity_id in self._entities:
            raise ValueError(
                f"Entity '{entity_id}' is already registered "
                "in this repository."
            )

        # Validate all controlled classifications before claiming
        # the canonical identity.
        validate_entity_classifications(
            entity,
            self._vocabulary_repository,
        )

        stored_entity = copy.deepcopy(entity)

        # RegistryIdentityIndex derives and verifies the entity type
        # from the canonical statistical entity ID.
        self._identity_index.register(
            canonical_id=entity_id,
            namespace="statistical",
            entity_type=entity.entity_type,
        )

        self._entities[entity_id] = stored_entity

        return copy.deepcopy(stored_entity)

    def get(self, entity_id: str) -> RegistryEntity | None:
        """Return an entity by canonical ID, if present."""
        entity = self._entities.get(entity_id)

        if entity is None:
            return None

        return copy.deepcopy(entity)

    def list_all(self) -> tuple[RegistryEntity, ...]:
        """Return all registered entities as defensive copies."""
        return tuple(
            copy.deepcopy(entity)
            for entity in self._entities.values()
        )

    def exists(self, entity_id: str) -> bool:
        """Return whether an entity exists in this repository."""
        return entity_id in self._entities

    def count(self) -> int:
        """Return the number of stored entities."""
        return len(self._entities)
```
