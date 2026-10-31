"""Shared data contracts for the TimanStat statistical registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


EntityType = Literal[
    "method",
    "model",
    "design",
    "diagnostic",
    "algorithm",
    "measure",
    "visualization",
    "theory",
    "distribution",
]

RecordMaturity = Literal[
    "draft",
    "catalogued",
    "reviewed",
    "approved",
]

ImplementationStatus = Literal[
    "catalogued",
    "planned",
    "in_development",
    "implemented",
    "deprecated",
]

VerificationStatus = Literal[
    "not_tested",
    "unit_tested",
    "integration_tested",
    "numerically_verified",
    "methodologically_reviewed",
    "validated",
]

ExecutionEligibility = Literal[
    "eligible",
    "ineligible",
    "conditional",
    "not_assessed",
]


@dataclass
class EntityRelationship:
    """A directed relationship between two registry entities."""

    relationship_type: str
    target_entity_id: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityReference:
    """A bibliographic or technical reference supporting an entity."""

    reference_type: str
    citation: str
    url: str | None = None
    doi: str | None = None
    year: int | None = None
    notes: str = ""


@dataclass
class RegistryEntity:
    """Shared core contract for all statistical registry entities."""

    entity_id: str
    name: str
    entity_type: EntityType
    description: str

    knowledge_areas: list[str]
    statistical_purposes: list[str]

    record_maturity: RecordMaturity = "draft"
    implementation_status: ImplementationStatus = "catalogued"
    verification_status: VerificationStatus = "not_tested"

    aliases: list[str] = field(default_factory=list)
    application_domains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    parent_id: str | None = None
    related_entity_ids: list[str] = field(default_factory=list)
    relationships: list[EntityRelationship] = field(default_factory=list)

    inference_paradigms: list[str] = field(default_factory=list)
    method_families: list[str] = field(default_factory=list)

    version: str = "0.1.0"

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    deprecated_at: datetime | None = None
    replacement_entity_id: str | None = None

    references: list[EntityReference] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)
