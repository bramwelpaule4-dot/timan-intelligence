
"""In-memory repository for statistical method registry records.

The repository stores complete MethodEntity records while delegating
canonical identity uniqueness to the shared RegistryIdentityIndex.
"""

from __future__ import annotations

import copy

from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.method import MethodEntity


class MethodRepository:
    """Store and retrieve statistical method records."""

    def __init__(self, identity_index: RegistryIdentityIndex) -> None:
        """Initialise the repository with a shared identity index."""
        if not isinstance(identity_index, RegistryIdentityIndex):
            raise TypeError(
                "identity_index must be a RegistryIdentityIndex instance."
            )

        self._identity_index = identity_index
        self._methods: dict[str, MethodEntity] = {}

    def register(self, method: MethodEntity) -> MethodEntity:
        """Register a method record and return a defensive copy.

        The complete record is copied before identity registration.
        This prevents callers from mutating repository state through
        the original object supplied during registration.
        """
        if not isinstance(method, MethodEntity):
            raise TypeError("method must be a MethodEntity instance.")

        method_id = method.entity_id

        if method_id in self._methods:
            raise ValueError(
                f"Method '{method_id}' is already registered "
                "in this repository."
            )

        stored_method = copy.deepcopy(method)

        self._identity_index.register(
            method_id,
            namespace="statistical",
            entity_type="method",
        )

        self._methods[method_id] = stored_method

        return copy.deepcopy(stored_method)

    def get(self, method_id: str) -> MethodEntity | None:
        """Return a method record by canonical ID, if present."""
        method = self._methods.get(method_id)

        if method is None:
            return None

        return copy.deepcopy(method)

    def list_all(self) -> tuple[MethodEntity, ...]:
        """Return all registered method records."""
        return tuple(
            copy.deepcopy(method)
            for method in self._methods.values()
        )

    def find(
        self,
        *,
        use_case: str | None = None,
        record_maturity: str | None = None,
        execution_eligibility: str | None = None,
    ) -> tuple[MethodEntity, ...]:
        """Return method records matching all supplied filters."""
        matches = []

        for method in self._methods.values():
            if (
                use_case is not None
                and use_case not in method.use_cases
            ):
                continue

            if (
                record_maturity is not None
                and method.record_maturity != record_maturity
            ):
                continue

            if (
                execution_eligibility is not None
                and method.execution_eligibility
                != execution_eligibility
            ):
                continue

            matches.append(copy.deepcopy(method))

        return tuple(matches)

    def exists(self, method_id: str) -> bool:
        """Return whether a method record exists in this repository."""
        return method_id in self._methods

    def count(self) -> int:
        """Return the number of stored method records."""
        return len(self._methods)
