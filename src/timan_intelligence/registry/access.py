
"""Read-only access layer for the TimanStat statistical method registry."""

from __future__ import annotations

from timan_intelligence.registry.identifiers import (
    IdentifierValidationError,
    validate_entity_id,
)
from timan_intelligence.registry.method import MethodEntity
from timan_intelligence.registry.method_repository import MethodRepository


class RegistryAccessError(Exception):
    """Base exception for registry access operations."""


class InvalidMethodIDError(RegistryAccessError, ValueError):
    """Raised when an identifier is invalid or is not a method ID."""


class MethodRegistryAccess:
    """Provide validated, read-only access to registered methods."""

    def __init__(self, repository: MethodRepository) -> None:
        """Initialise access using an explicitly supplied repository."""
        if not isinstance(repository, MethodRepository):
            raise TypeError(
                "repository must be a MethodRepository instance."
            )

        self._repository = repository

    @staticmethod
    def _validate_method_id(method_id: str) -> str:
        """Validate an identifier as a canonical statistical method ID."""
        try:
            return validate_entity_id(
                method_id,
                expected_entity_type="method",
            )
        except IdentifierValidationError as exc:
            raise InvalidMethodIDError(str(exc)) from exc

    def get_method(self, method_id: str) -> MethodEntity | None:
        """Return a registered method, or None if it is not registered."""
        validated_id = self._validate_method_id(method_id)
        return self._repository.get(validated_id)

    def find_methods(
        self,
        *,
        use_case: str | None = None,
        record_maturity: str | None = None,
        execution_eligibility: str | None = None,
    ) -> tuple[MethodEntity, ...]:
        """Find methods matching all supplied structured filters."""
        return self._repository.find(
            use_case=use_case,
            record_maturity=record_maturity,
            execution_eligibility=execution_eligibility,
        )

    def list_methods(self) -> tuple[MethodEntity, ...]:
        """Return all registered method records."""
        return self._repository.list_all()

    def method_exists(self, method_id: str) -> bool:
        """Check whether a valid canonical method ID is registered."""
        validated_id = self._validate_method_id(method_id)
        return self._repository.exists(validated_id)

    def get_methods_by_ids(
        self,
        method_ids: list[str],
    ) -> dict[str, MethodEntity]:
        """Resolve multiple method IDs, omitting valid unknown IDs.

        Duplicate requested IDs are resolved only once. Invalid IDs
        cause the operation to fail rather than returning a partial map.
        """
        if not isinstance(method_ids, list):
            raise TypeError("method_ids must be a list of strings.")

        validated_ids = [
            self._validate_method_id(method_id)
            for method_id in method_ids
        ]

        resolved: dict[str, MethodEntity] = {}

        for method_id in dict.fromkeys(validated_ids):
            method = self._repository.get(method_id)

            if method is not None:
                resolved[method_id] = method

        return resolved
