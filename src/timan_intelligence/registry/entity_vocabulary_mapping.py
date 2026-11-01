
"""Canonical mapping between registry entity fields and vocabularies.

This module defines the authoritative relationship between the
classification fields in RegistryEntity and the controlled vocabularies
maintained by the TimanStat vocabulary registry.

It contains mapping definitions only. It does not perform validation,
register entities, or modify vocabulary records.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping


# ---------------------------------------------------------------------
# Canonical vocabulary identifiers
# ---------------------------------------------------------------------

ENTITY_TYPE_VOCABULARY_ID: Final[str] = (
    "vocab.definition.entity_type"
)

KNOWLEDGE_AREA_VOCABULARY_ID: Final[str] = (
    "vocab.definition.knowledge_area"
)

STATISTICAL_PURPOSE_VOCABULARY_ID: Final[str] = (
    "vocab.definition.statistical_purpose"
)

METHOD_FAMILY_VOCABULARY_ID: Final[str] = (
    "vocab.definition.method_family"
)

INFERENCE_PARADIGM_VOCABULARY_ID: Final[str] = (
    "vocab.definition.inference_paradigm"
)

APPLICATION_DOMAIN_VOCABULARY_ID: Final[str] = (
    "vocab.definition.application_domain"
)


# ---------------------------------------------------------------------
# Entity field-to-vocabulary mapping
# ---------------------------------------------------------------------

ENTITY_VOCABULARY_MAPPING: Final[Mapping[str, str]] = (
    MappingProxyType(
        {
            "entity_type": ENTITY_TYPE_VOCABULARY_ID,
            "knowledge_areas": KNOWLEDGE_AREA_VOCABULARY_ID,
            "statistical_purposes": STATISTICAL_PURPOSE_VOCABULARY_ID,
            "method_families": METHOD_FAMILY_VOCABULARY_ID,
            "inference_paradigms": INFERENCE_PARADIGM_VOCABULARY_ID,
            "application_domains": APPLICATION_DOMAIN_VOCABULARY_ID,
        }
    )
)


# ---------------------------------------------------------------------
# Mapping access utilities
# ---------------------------------------------------------------------

def get_vocabulary_id_for_entity_field(
    field_name: str,
) -> str:
    """Return the vocabulary ID associated with an entity field.

    Raises:
        TypeError: If field_name is not a string.
        KeyError: If the entity field has no vocabulary mapping.
    """
    if not isinstance(field_name, str):
        raise TypeError("field_name must be a string.")

    try:
        return ENTITY_VOCABULARY_MAPPING[field_name]
    except KeyError:
        raise KeyError(
            f"No controlled vocabulary is mapped to entity field "
            f"'{field_name}'."
        ) from None


def get_mapped_entity_fields() -> tuple[str, ...]:
    """Return all entity fields mapped to controlled vocabularies."""
    return tuple(ENTITY_VOCABULARY_MAPPING.keys())


def get_mapped_vocabulary_ids() -> tuple[str, ...]:
    """Return all vocabulary IDs referenced by the entity mapping."""
    return tuple(ENTITY_VOCABULARY_MAPPING.values())


def is_vocabulary_mapped_to_entity_field(
    field_name: str,
) -> bool:
    """Check whether an entity field has a controlled vocabulary."""
    if not isinstance(field_name, str):
        raise TypeError("field_name must be a string.")

    return field_name in ENTITY_VOCABULARY_MAPPING
