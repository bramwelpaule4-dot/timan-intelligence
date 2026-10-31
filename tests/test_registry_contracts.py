"""Tests for the TimanStat shared registry entity contracts."""

from datetime import datetime, timezone

import pytest

from timan_intelligence.registry.contracts import (
    EntityReference,
    EntityRelationship,
    RegistryEntity,
)


def create_entity(**overrides):
    data = {
        "entity_id": "method.inference.anova.one_way",
        "name": "One-way ANOVA",
        "entity_type": "method",
        "description": "Compares the means of three or more independent groups.",
        "knowledge_areas": ["frequentist_inference"],
        "statistical_purposes": ["inferential"],
    }
    data.update(overrides)
    return RegistryEntity(**data)


def test_creates_registry_entity():
    entity = create_entity()

    assert entity.entity_id == "method.inference.anova.one_way"
    assert entity.entity_type == "method"
    assert entity.record_maturity == "draft"
    assert entity.implementation_status == "catalogued"
    assert entity.verification_status == "not_tested"


def test_default_collections_are_independent():
    first = create_entity()
    second = create_entity(
        entity_id="method.inference.t_test.independent.welch",
        name="Welch independent-samples t-test",
    )

    first.aliases.append("legacy.anova.one_way")

    assert second.aliases == []


def test_entity_supports_relationships():
    relationship = EntityRelationship(
        relationship_type="has_diagnostic",
        target_entity_id="diagnostic.distribution.normality.shapiro_wilk",
    )

    entity = create_entity(relationships=[relationship])

    assert len(entity.relationships) == 1
    assert entity.relationships[0].relationship_type == "has_diagnostic"


def test_entity_supports_references():
    reference = EntityReference(
        reference_type="textbook",
        citation="Statistical Methods Reference",
        year=2024,
    )

    entity = create_entity(references=[reference])

    assert entity.references[0].citation == "Statistical Methods Reference"
    assert entity.references[0].year == 2024


def test_entity_has_timezone_aware_timestamps():
    entity = create_entity()

    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)
    assert entity.created_at.tzinfo is not None
    assert entity.updated_at.tzinfo is not None


def test_entity_accepts_lifecycle_metadata():
    entity = create_entity(
        record_maturity="reviewed",
        implementation_status="implemented",
        verification_status="unit_tested",
        version="1.0.0",
    )

    assert entity.record_maturity == "reviewed"
    assert entity.implementation_status == "implemented"
    assert entity.verification_status == "unit_tested"
    assert entity.version == "1.0.0"


def test_entity_supports_provenance():
    entity = create_entity(
        provenance={"created_by": "registry_team", "source_version": "2.1"}
    )

    assert entity.provenance["source_version"] == "2.1"


def test_entity_supports_replacement_reference():
    entity = create_entity(
        implementation_status="deprecated",
        replacement_entity_id="method.inference.anova.one_way",
    )

    assert entity.replacement_entity_id == "method.inference.anova.one_way"


def test_entity_rejects_missing_required_fields():
    with pytest.raises(TypeError):
        RegistryEntity()
