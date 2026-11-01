"""Tests for TimanStat controlled vocabulary data contracts."""

from dataclasses import fields, is_dataclass

from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)


def test_vocabulary_definition_is_dataclass():
    """VocabularyDefinition should be a dataclass."""
    assert is_dataclass(VocabularyDefinition)


def test_vocabulary_member_is_dataclass():
    """VocabularyMember should be a dataclass."""
    assert is_dataclass(VocabularyMember)


def test_vocabulary_definition_accepts_required_fields():
    """A definition should preserve all supplied required fields."""
    definition = VocabularyDefinition(
        vocabulary_id="vocab.definition.statistical_purpose",
        name="Statistical purposes",
        description="Defines the purposes of statistical analysis.",
        extensibility="controlled",
        completeness="exhaustive",
    )

    assert definition.vocabulary_id == (
        "vocab.definition.statistical_purpose"
    )
    assert definition.name == "Statistical purposes"
    assert definition.description == (
        "Defines the purposes of statistical analysis."
    )
    assert definition.extensibility == "controlled"
    assert definition.completeness == "exhaustive"


def test_vocabulary_definition_default_values():
    """A definition should use the specified default values."""
    definition = VocabularyDefinition(
        vocabulary_id="vocab.definition.knowledge_area",
        name="Knowledge areas",
        description="Statistical knowledge areas.",
        extensibility="controlled",
        completeness="illustrative",
    )

    assert definition.status == "draft"
    assert definition.version == "0.1.0"
    assert definition.source == ""
    assert definition.metadata == {}


def test_vocabulary_definition_accepts_explicit_optional_values():
    """A definition should preserve explicitly supplied optional values."""
    metadata = {
        "catalogue_section": "37.1",
        "approval_required": True,
    }

    definition = VocabularyDefinition(
        vocabulary_id="vocab.definition.statistical_purpose",
        name="Statistical purposes",
        description="Defines statistical purposes.",
        extensibility="controlled",
        completeness="exhaustive",
        status="active",
        version="1.0.0",
        source="TimanStat Statistical Methods Catalogue, Version 2.1",
        metadata=metadata,
    )

    assert definition.status == "active"
    assert definition.version == "1.0.0"
    assert definition.source == (
        "TimanStat Statistical Methods Catalogue, Version 2.1"
    )
    assert definition.metadata == metadata


def test_vocabulary_definition_metadata_is_independent_between_instances():
    """Definitions should not share mutable metadata defaults."""
    first = VocabularyDefinition(
        vocabulary_id="vocab.definition.statistical_purpose",
        name="Statistical purposes",
        description="Defines statistical purposes.",
        extensibility="controlled",
        completeness="exhaustive",
    )

    second = VocabularyDefinition(
        vocabulary_id="vocab.definition.knowledge_area",
        name="Knowledge areas",
        description="Defines knowledge areas.",
        extensibility="controlled",
        completeness="illustrative",
    )

    first.metadata["source_section"] = "37.1"

    assert first.metadata == {"source_section": "37.1"}
    assert second.metadata == {}


def test_vocabulary_member_accepts_required_fields():
    """A member should preserve all supplied required fields."""
    member = VocabularyMember(
        member_id="vocab.statistical_purpose.descriptive",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="descriptive",
        label="Descriptive",
        description="",
    )

    assert member.member_id == (
        "vocab.statistical_purpose.descriptive"
    )
    assert member.vocabulary_id == (
        "vocab.definition.statistical_purpose"
    )
    assert member.value == "descriptive"
    assert member.label == "Descriptive"
    assert member.description == ""


def test_vocabulary_member_default_values():
    """A member should use the specified default values."""
    member = VocabularyMember(
        member_id="vocab.statistical_purpose.inferential",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="inferential",
        label="Inferential",
        description="",
    )

    assert member.aliases == []
    assert member.status == "active"
    assert member.version == "0.1.0"
    assert member.metadata == {}


def test_vocabulary_member_accepts_explicit_optional_values():
    """A member should preserve explicitly supplied optional values."""
    aliases = ["summary_statistics"]
    metadata = {"catalogue_section": "37.1"}

    member = VocabularyMember(
        member_id="vocab.statistical_purpose.descriptive",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="descriptive",
        label="Descriptive",
        description="A purpose focused on describing data.",
        aliases=aliases,
        status="deprecated",
        version="1.2.0",
        metadata=metadata,
    )

    assert member.aliases == aliases
    assert member.status == "deprecated"
    assert member.version == "1.2.0"
    assert member.metadata == metadata


def test_vocabulary_member_mutable_defaults_are_independent():
    """Members should not share mutable aliases or metadata defaults."""
    first = VocabularyMember(
        member_id="vocab.statistical_purpose.descriptive",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="descriptive",
        label="Descriptive",
        description="",
    )

    second = VocabularyMember(
        member_id="vocab.statistical_purpose.inferential",
        vocabulary_id="vocab.definition.statistical_purpose",
        value="inferential",
        label="Inferential",
        description="",
    )

    first.aliases.append("summary_statistics")
    first.metadata["source_section"] = "37.1"

    assert first.aliases == ["summary_statistics"]
    assert first.metadata == {"source_section": "37.1"}

    assert second.aliases == []
    assert second.metadata == {}


def test_vocabulary_definition_and_member_have_expected_fields():
    """The contracts should expose the approved field structure."""
    definition_field_names = {
        item.name for item in fields(VocabularyDefinition)
    }

    member_field_names = {
        item.name for item in fields(VocabularyMember)
    }

    assert definition_field_names == {
        "vocabulary_id",
        "name",
        "description",
        "extensibility",
        "completeness",
        "status",
        "version",
        "source",
        "metadata",
    }

    assert member_field_names == {
        "member_id",
        "vocabulary_id",
        "value",
        "label",
        "description",
        "aliases",
        "status",
        "version",
        "metadata",
    }


def test_vocabulary_contracts_preserve_canonical_values():
    """Contract construction should not normalise canonical values."""
    member = VocabularyMember(
        member_id="vocab.method_family.mean_comparison",
        vocabulary_id="vocab.definition.method_family",
        value="mean_comparison",
        label="Mean Comparison",
        description="",
    )

    assert member.value == "mean_comparison"
    assert member.member_id.endswith(".mean_comparison")
