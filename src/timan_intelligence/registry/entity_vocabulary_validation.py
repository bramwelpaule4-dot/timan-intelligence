
"""Validation of RegistryEntity classifications against controlled vocabularies.

This module ensures that classification values assigned to registry
entities are registered, active members of their corresponding
controlled vocabularies.

It preserves the existing RegistryEntity contract and does not modify
entities, vocabulary definitions, or repository records.
"""

from __future__ import annotations

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.entity_vocabulary_mapping import (
    ENTITY_VOCABULARY_MAPPING,
)
from timan_intelligence.registry.vocabulary_repository import (
    VocabularyRepository,
)
from timan_intelligence.registry.vocabulary_validation import (
    VocabularyCompatibilityError,
    validate_classification,
)


# ---------------------------------------------------------------------
# Entity classification validation
# ---------------------------------------------------------------------

def validate_entity_classifications(
    entity: RegistryEntity,
    vocabulary_repository: VocabularyRepository,
) -> RegistryEntity:
    """Validate all controlled-vocabulary classifications on an entity.

    The entity's classification fields are checked against their
    corresponding registered vocabularies.

    The entity_type field is a single classification value.
    The remaining mapped fields are lists of classification values.

    Empty classification lists are permitted. Every supplied value
    must exist as an active member of the corresponding vocabulary.

    Args:
        entity: Registry entity whose classifications are to be checked.
        vocabulary_repository: Repository containing vocabulary
            definitions and members.

    Returns:
        The original entity, unchanged, if all classifications are valid.

    Raises:
        TypeError: If entity or vocabulary_repository has the wrong type.
        VocabularyCompatibilityError: If a classification field has
            an invalid structure or contains an invalid value.
        VocabularyNotFoundError: If a required vocabulary is missing.
        VocabularyMemberNotFoundError: If a classification value is
            not registered.
        DeprecatedVocabularyMemberError: If a classification value
            refers to a deprecated vocabulary member.
    """
    if not isinstance(entity, RegistryEntity):
        raise TypeError(
            "entity must be a RegistryEntity instance."
        )

    if not isinstance(vocabulary_repository, VocabularyRepository):
        raise TypeError(
            "vocabulary_repository must be a VocabularyRepository instance."
        )

    for field_name, vocabulary_id in ENTITY_VOCABULARY_MAPPING.items():
        classification_values = getattr(entity, field_name)

        if field_name == "entity_type":
            validate_classification(
                vocabulary_repository,
                vocabulary_id,
                classification_values,
            )
            continue

        if not isinstance(classification_values, list):
            raise VocabularyCompatibilityError(
                f"Entity classification field '{field_name}' "
                "must be a list."
            )

        for value in classification_values:
            validate_classification(
                vocabulary_repository,
                vocabulary_id,
                value,
            )

    return entity
