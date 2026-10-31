"""Canonical identifier validation for the TimanStat statistical registry."""

from __future__ import annotations

import re


class IdentifierValidationError(ValueError):
    """Raised when a canonical registry identifier is invalid."""


ENTITY_TYPES = frozenset(
    {
        "method",
        "model",
        "design",
        "diagnostic",
        "algorithm",
        "measure",
        "visualization",
        "theory",
        "distribution",
    }
)

_IDENTIFIER_PATTERN = re.compile(
    r"^(?P<entity_type>[a-z][a-z0-9_]*)"
    r"(?:\.[a-z][a-z0-9_]*){2,}$"
)


def validate_entity_id(
    entity_id: str,
    *,
    expected_entity_type: str | None = None,
) -> str:
    """Validate a canonical identifier and return it unchanged.

    Canonical identifiers must:
    - Be strings.
    - Use lowercase, dot-separated segments.
    - Contain at least three segments.
    - Start with one of the nine registered entity types.
    - Match the expected entity type when one is supplied.

    Legacy identifiers must be resolved through an alias mapping rather
    than accepted as canonical identifiers.
    """
    if not isinstance(entity_id, str):
        raise IdentifierValidationError(
            "Entity identifier must be a string."
        )

    if not _IDENTIFIER_PATTERN.fullmatch(entity_id):
        raise IdentifierValidationError(
            f"Invalid canonical identifier syntax: {entity_id!r}."
        )

    actual_entity_type = entity_id.split(".", maxsplit=1)[0]

    if actual_entity_type not in ENTITY_TYPES:
        raise IdentifierValidationError(
            f"Unknown entity type prefix: {actual_entity_type!r}."
        )

    if expected_entity_type is not None:
        if expected_entity_type not in ENTITY_TYPES:
            raise IdentifierValidationError(
                f"Unknown expected entity type: {expected_entity_type!r}."
            )

        if actual_entity_type != expected_entity_type:
            raise IdentifierValidationError(
                f"Identifier type {actual_entity_type!r} does not match "
                f"expected type {expected_entity_type!r}."
            )

    return entity_id
