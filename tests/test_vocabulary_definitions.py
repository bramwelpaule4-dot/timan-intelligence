
"""Tests for the initial TimanStat controlled vocabulary definitions."""

from timan_intelligence.registry.vocabulary_definitions import (
    APPLICATION_DOMAIN_VOCABULARY,
    ENTITY_TYPE_VOCABULARY,
    INFERENCE_PARADIGM_VOCABULARY,
    INITIAL_VOCABULARIES,
    INITIAL_VOCABULARY_MEMBERS,
    KNOWLEDGE_AREA_VOCABULARY,
    METHOD_FAMILY_VOCABULARY,
    STATISTICAL_PURPOSE_VOCABULARY,
)


EXPECTED_VOCABULARY_IDS = {
    "vocab.definition.statistical_purpose",
    "vocab.definition.knowledge_area",
    "vocab.definition.entity_type",
    "vocab.definition.method_family",
    "vocab.definition.inference_paradigm",
    "vocab.definition.application_domain",
}

EXPECTED_MEMBER_COUNTS = {
    "vocab.definition.statistical_purpose": 8,
    "vocab.definition.knowledge_area": 26,
    "vocab.definition.entity_type": 9,
    "vocab.definition.method_family": 19,
    "vocab.definition.inference_paradigm": 9,
    "vocab.definition.application_domain": 12,
}

EXPECTED_COMPLETENESS = {
    "vocab.definition.statistical_purpose": "exhaustive",
    "vocab.definition.knowledge_area": "illustrative",
    "vocab.definition.entity_type": "exhaustive",
    "vocab.definition.method_family": "illustrative",
    "vocab.definition.inference_paradigm": "exhaustive",
    "vocab.definition.application_domain": "illustrative",
}


def test_all_six_initial_vocabulary_definitions_are_present():
    assert len(INITIAL_VOCABULARIES) == 6

    actual_ids = {
        vocabulary.vocabulary_id
        for vocabulary in INITIAL_VOCABULARIES
    }

    assert actual_ids == EXPECTED_VOCABULARY_IDS


def test_named_vocabulary_constants_match_initial_collection():
    named_vocabulary_ids = {
        STATISTICAL_PURPOSE_VOCABULARY.vocabulary_id,
        KNOWLEDGE_AREA_VOCABULARY.vocabulary_id,
        ENTITY_TYPE_VOCABULARY.vocabulary_id,
        METHOD_FAMILY_VOCABULARY.vocabulary_id,
        INFERENCE_PARADIGM_VOCABULARY.vocabulary_id,
        APPLICATION_DOMAIN_VOCABULARY.vocabulary_id,
    }

    initial_vocabulary_ids = {
        vocabulary.vocabulary_id
        for vocabulary in INITIAL_VOCABULARIES
    }

    assert len(named_vocabulary_ids) == 6
    assert initial_vocabulary_ids == named_vocabulary_ids


def test_vocabulary_definition_ids_are_unique():
    vocabulary_ids = [
        vocabulary.vocabulary_id
        for vocabulary in INITIAL_VOCABULARIES
    ]

    assert len(vocabulary_ids) == len(set(vocabulary_ids))


def test_all_vocabulary_definitions_have_required_descriptive_fields():
    for vocabulary in INITIAL_VOCABULARIES:
        assert vocabulary.name.strip()
        assert vocabulary.description.strip()
        assert vocabulary.extensibility in {
            "closed",
            "controlled",
        }
        assert vocabulary.completeness in {
            "exhaustive",
            "illustrative",
        }


def test_vocabulary_completeness_classifications_are_preserved():
    actual_completeness = {
        vocabulary.vocabulary_id: vocabulary.completeness
        for vocabulary in INITIAL_VOCABULARIES
    }

    assert actual_completeness == EXPECTED_COMPLETENESS


def test_initial_vocabulary_member_count_is_eighty_three():
    assert len(INITIAL_VOCABULARY_MEMBERS) == 83


def test_initial_vocabulary_member_counts_match_catalogue():
    actual_counts = {
        vocabulary.vocabulary_id: sum(
            member.vocabulary_id == vocabulary.vocabulary_id
            for member in INITIAL_VOCABULARY_MEMBERS
        )
        for vocabulary in INITIAL_VOCABULARIES
    }

    assert actual_counts == EXPECTED_MEMBER_COUNTS


def test_all_vocabulary_member_ids_are_unique():
    member_ids = [
        member.member_id
        for member in INITIAL_VOCABULARY_MEMBERS
    ]

    assert len(member_ids) == len(set(member_ids))


def test_all_vocabulary_member_ids_and_values_are_non_empty():
    for member in INITIAL_VOCABULARY_MEMBERS:
        assert member.member_id.strip()
        assert member.value.strip()
        assert member.label.strip()


def test_all_vocabulary_members_reference_existing_definitions():
    vocabulary_ids = {
        vocabulary.vocabulary_id
        for vocabulary in INITIAL_VOCABULARIES
    }

    for member in INITIAL_VOCABULARY_MEMBERS:
        assert member.vocabulary_id in vocabulary_ids


def test_member_values_are_unique_within_each_vocabulary():
    values_by_vocabulary = {}

    for member in INITIAL_VOCABULARY_MEMBERS:
        values = values_by_vocabulary.setdefault(
            member.vocabulary_id,
            [],
        )
        values.append(member.value)

    for vocabulary_id, values in values_by_vocabulary.items():
        assert len(values) == len(set(values)), (
            f"Duplicate member values found in {vocabulary_id}."
        )
