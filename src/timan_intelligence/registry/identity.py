
"""Registry-wide canonical identity index for TimanStat.

This module provides an in-memory identity index shared across the
statistical knowledge and non-statistical registry namespaces.

It validates identifiers before registration and prevents duplicate
canonical IDs from being assigned to more than one registry record.

Persistence, audit history, alias resolution and duplicate merging are
handled by separate registry components.
"""

from __future__ import annotations

from dataclasses import dataclass

from timan_intelligence.registry.identifiers import (
    IdentifierValidationError,
    validate_entity_id,
)
from timan_intelligence.registry.namespace_identifiers import (
    NamespaceIdentifierValidationError,
    validate_implementation_id,
    validate_reference_id,
    validate_registry_release_id,
    validate_relationship_id,
    validate_vocabulary_id,
)


class RegistryIdentityError(ValueError):
    """Base exception for registry identity errors."""


class DuplicateCanonicalIDError(RegistryIdentityError):
    """Raised when a canonical ID is already registered."""


class UnknownCanonicalIDError(RegistryIdentityError):
    """Raised when a requested canonical ID is not registered."""


class InvalidCanonicalIDError(RegistryIdentityError):
    """Raised when a canonical ID is structurally invalid."""


@dataclass(frozen=True)
class IdentityRecord:
    """Identity index entry for one canonical registry record."""

    canonical_id: str
    namespace: str
    entity_type: str | None = None


class RegistryIdentityIndex:
    """In-memory index enforcing global canonical ID uniqueness."""

    def __init__(self) -> None:
        self._records: dict[str, IdentityRecord] = {}

    @staticmethod
    def _validate_identifier(
        canonical_id: str,
        namespace: str,
        entity_type: str | None = None,
    ) -> IdentityRecord:
        """Validate an ID and construct its identity record."""
        if not isinstance(canonical_id, str):
            raise InvalidCanonicalIDError(
                "Canonical identifier must be a string."
            )

        if not isinstance(namespace, str):
            raise InvalidCanonicalIDError(
                "Namespace must be a string."
            )

        if not namespace:
            raise InvalidCanonicalIDError(
                "Namespace cannot be empty."
            )

        try:
            if namespace == "statistical":
                validated_id = validate_entity_id(
                    canonical_id,
                    expected_entity_type=entity_type,
                )
                resolved_entity_type = validated_id.split(".", maxsplit=1)[0]

            elif namespace == "implementation":
                validated_id = validate_implementation_id(canonical_id)
                resolved_entity_type = None

            elif namespace == "vocab":
                validated_id = validate_vocabulary_id(canonical_id)
                resolved_entity_type = None

            elif namespace == "reference":
                validated_id = validate_reference_id(canonical_id)
                resolved_entity_type = None

            elif namespace == "relationship":
                validated_id = validate_relationship_id(canonical_id)
                resolved_entity_type = None

            elif namespace == "registry_release":
                validated_id = validate_registry_release_id(canonical_id)
                resolved_entity_type = None

            else:
                raise InvalidCanonicalIDError(
                    f"Unsupported registry namespace '{namespace}'."
                )

        except (
            IdentifierValidationError,
            NamespaceIdentifierValidationError,
        ) as exc:
            raise InvalidCanonicalIDError(str(exc)) from exc

        return IdentityRecord(
            canonical_id=validated_id,
            namespace=namespace,
            entity_type=resolved_entity_type,
        )

    def register(
        self,
        canonical_id: str,
        namespace: str,
        entity_type: str | None = None,
    ) -> IdentityRecord:
        """Register a canonical ID without allowing duplicate claims.

        Statistical entity IDs require namespace="statistical".
        Their entity type is inferred from the canonical ID prefix.
        If entity_type is supplied, it must match that prefix.

        Non-statistical IDs use their corresponding namespace name.
        """
        record = self._validate_identifier(
            canonical_id=canonical_id,
            namespace=namespace,
            entity_type=entity_type,
        )

        if record.canonical_id in self._records:
            existing = self._records[record.canonical_id]
            raise DuplicateCanonicalIDError(
                f"Canonical ID '{record.canonical_id}' is already "
                f"registered in namespace '{existing.namespace}'."
            )

        self._records[record.canonical_id] = record
        return record

    def get(self, canonical_id: str) -> IdentityRecord:
        """Return the identity record for a registered canonical ID."""
        if not isinstance(canonical_id, str):
            raise InvalidCanonicalIDError(
                "Canonical identifier must be a string."
            )

        try:
            return self._records[canonical_id]
        except KeyError as exc:
            raise UnknownCanonicalIDError(
                f"Canonical ID '{canonical_id}' is not registered."
            ) from exc

    def contains(self, canonical_id: str) -> bool:
        """Return whether a canonical ID is registered."""
        if not isinstance(canonical_id, str):
            raise InvalidCanonicalIDError(
                "Canonical identifier must be a string."
            )

        return canonical_id in self._records

    def count(self) -> int:
        """Return the number of registered canonical IDs."""
        return len(self._records)

    def all_records(self) -> tuple[IdentityRecord, ...]:
        """Return an immutable snapshot of registered identity records."""
        return tuple(self._records.values())
