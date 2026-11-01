
"""Canonical identifier validation for non-statistical registry namespaces.

Statistical knowledge entity identifiers are handled separately by
registry.identifiers. This module validates the other shared-registry
identifier namespaces without changing or normalising supplied identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class NamespaceIdentifierValidationError(ValueError):
    """Raised when a non-statistical namespace identifier is invalid."""


@dataclass(frozen=True)
class ParsedNamespaceIdentifier:
    """Parsed representation of a non-statistical namespace identifier."""

    canonical_id: str
    namespace: str
    segments: tuple[str, ...]


# Shared segment syntax:
# - starts with a lowercase letter
# - continues with lowercase letters, digits, or underscores
_SEGMENT_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Implementation and vocabulary identifiers have variable depth.
_VARIABLE_DEPTH_NAMESPACES = {"implementation", "vocab"}

# Statistical entity types are included here only because relationship
# identifiers identify the source entity type in their second segment.
_RELATIONSHIP_SOURCE_TYPES = {
    "method",
    "model",
    "design",
    "diagnostic",
    "algorithm",
    "measure",
    "visualization",
    "theory",
    "distribution",
    "implementation",
    "vocab",
}

# Reference identifiers use a registered reference-kind segment.
_REFERENCE_TYPES = {"doi", "url", "bibliography"}

# A relationship identifier has the form:
# relationship.<source_type>.<relationship_type>.<six_digit_sequence>
_RELATIONSHIP_SEQUENCE_PATTERN = re.compile(r"^[0-9]{6}$")

# Registry releases use semantic versioning with numeric components.
_REGISTRY_RELEASE_PATTERN = re.compile(
    r"^registry_release\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)$"
)


def _validate_segments(
    identifier: str,
    *,
    expected_namespace: str,
    minimum_segments: int,
) -> tuple[str, ...]:
    """Validate common namespace syntax and return its segments."""
    if not isinstance(identifier, str):
        raise NamespaceIdentifierValidationError(
            "Namespace identifier must be a string."
        )

    if not identifier:
        raise NamespaceIdentifierValidationError(
            "Namespace identifier cannot be empty."
        )

    if identifier != identifier.strip():
        raise NamespaceIdentifierValidationError(
            "Namespace identifier cannot have leading or trailing whitespace."
        )

    segments = tuple(identifier.split("."))

    if len(segments) < minimum_segments:
        raise NamespaceIdentifierValidationError(
            f"{expected_namespace} identifiers must contain at least "
            f"{minimum_segments} dot-separated segments."
        )

    if segments[0] != expected_namespace:
        raise NamespaceIdentifierValidationError(
            f"Expected namespace prefix '{expected_namespace}'."
        )

    for segment in segments:
        if not _SEGMENT_PATTERN.fullmatch(segment):
            raise NamespaceIdentifierValidationError(
                f"Invalid identifier segment: '{segment}'."
            )

    return segments


def validate_implementation_id(identifier: str) -> str:
    """Validate a variable-depth implementation identifier.

    Examples:
        implementation.scipy.welch_t_test
        implementation.scipy.stats.welch_t_test
    """
    _validate_segments(
        identifier,
        expected_namespace="implementation",
        minimum_segments=3,
    )
    return identifier


def validate_vocabulary_id(identifier: str) -> str:
    """Validate a variable-depth controlled-vocabulary identifier.

    Examples:
        vocab.method_family.regression
        vocab.statistical_method.family.regression
    """
    _validate_segments(
        identifier,
        expected_namespace="vocab",
        minimum_segments=3,
    )
    return identifier


def validate_reference_id(identifier: str) -> str:
    """Validate the structure of a shared reference identifier.

    This function validates the namespace and reference-kind structure.
    It deliberately does not normalise DOI, URL, or bibliographic values.
    Reference-specific normalisation and duplicate detection are separate
    responsibilities.
    """
    segments = _validate_segments(
        identifier,
        expected_namespace="reference",
        minimum_segments=3,
    )

    if segments[1] not in _REFERENCE_TYPES:
        allowed = ", ".join(sorted(_REFERENCE_TYPES))
        raise NamespaceIdentifierValidationError(
            f"Unknown reference type '{segments[1]}'. "
            f"Expected one of: {allowed}."
        )

    return identifier


def validate_relationship_id(identifier: str) -> str:
    """Validate a relationship identifier with a six-digit sequence.

    Example:
        relationship.method.supported_by.000001

    Global uniqueness of the complete identifier is enforced by the
    registry-wide identity service, not by this structural validator.
    """
    if not isinstance(identifier, str):
        raise NamespaceIdentifierValidationError(
            "Namespace identifier must be a string."
        )

    segments = tuple(identifier.split("."))

    if len(segments) != 4:
        raise NamespaceIdentifierValidationError(
            "Relationship identifiers must contain exactly four segments."
        )

    if segments[0] != "relationship":
        raise NamespaceIdentifierValidationError(
            "Expected namespace prefix 'relationship'."
        )

    if segments[1] not in _RELATIONSHIP_SOURCE_TYPES:
        raise NamespaceIdentifierValidationError(
            f"Unknown relationship source type '{segments[1]}'."
        )

    if not _SEGMENT_PATTERN.fullmatch(segments[2]):
        raise NamespaceIdentifierValidationError(
            f"Invalid relationship type segment: '{segments[2]}'."
        )

    if not _RELATIONSHIP_SEQUENCE_PATTERN.fullmatch(segments[3]):
        raise NamespaceIdentifierValidationError(
            "Relationship sequence must contain exactly six digits."
        )

    return identifier


def validate_registry_release_id(identifier: str) -> str:
    """Validate a registry release identifier using semantic versioning.

    Examples:
        registry_release.1.0.0
        registry_release.2.3.1
    """
    if not isinstance(identifier, str):
        raise NamespaceIdentifierValidationError(
            "Namespace identifier must be a string."
        )

    if not _REGISTRY_RELEASE_PATTERN.fullmatch(identifier):
        raise NamespaceIdentifierValidationError(
            "Registry release identifier must use the format "
            "'registry_release.MAJOR.MINOR.PATCH' with non-negative "
            "integers and no leading zeroes except for zero itself."
        )

    return identifier


def parse_namespace_identifier(identifier: str) -> ParsedNamespaceIdentifier:
    """Parse a structurally valid non-statistical namespace identifier."""
    if not isinstance(identifier, str):
        raise NamespaceIdentifierValidationError(
            "Namespace identifier must be a string."
        )

    if not identifier:
        raise NamespaceIdentifierValidationError(
            "Namespace identifier cannot be empty."
        )

    namespace = identifier.split(".", maxsplit=1)[0]

    validators = {
        "implementation": validate_implementation_id,
        "vocab": validate_vocabulary_id,
        "reference": validate_reference_id,
        "relationship": validate_relationship_id,
        "registry_release": validate_registry_release_id,
    }

    validator = validators.get(namespace)
    if validator is None:
        raise NamespaceIdentifierValidationError(
            f"Unsupported namespace '{namespace}'."
        )

    canonical_id = validator(identifier)
    segments = tuple(canonical_id.split("."))

    return ParsedNamespaceIdentifier(
        canonical_id=canonical_id,
        namespace=namespace,
        segments=segments,
    )

