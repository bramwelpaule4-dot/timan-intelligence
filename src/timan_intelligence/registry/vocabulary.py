"""Data contracts for the TimanStat controlled vocabulary registry.

This module defines the structures used to represent vocabulary
definitions and their canonical members.

It deliberately contains no repository, identity-registration, or
validation logic. Those responsibilities are implemented in separate
registry modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


VocabularyExtensibility = Literal[
    "closed",
    "controlled",
]

VocabularyCompleteness = Literal[
    "exhaustive",
    "illustrative",
]

VocabularyStatus = Literal[
    "draft",
    "active",
    "deprecated",
]

VocabularyMemberStatus = Literal[
    "active",
    "deprecated",
]


@dataclass
class VocabularyDefinition:
    """Define a controlled vocabulary within the statistical registry."""

    vocabulary_id: str
    name: str
    description: str

    extensibility: VocabularyExtensibility
    completeness: VocabularyCompleteness

    status: VocabularyStatus = "draft"
    version: str = "0.1.0"
    source: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VocabularyMember:
    """Represent a canonical member of a controlled vocabulary."""

    member_id: str
    vocabulary_id: str

    value: str
    label: str
    description: str

    aliases: list[str] = field(default_factory=list)

    status: VocabularyMemberStatus = "active"
    version: str = "0.1.0"

    metadata: dict[str, Any] = field(default_factory=dict)
