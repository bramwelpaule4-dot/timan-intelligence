
"""Theory-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class TheoryEntity(RegistryEntity):
    """Registry representation of a mathematical or statistical theory.

    A theory entity captures foundational mathematical knowledge,
    including definitions, propositions, theorems, assumptions,
    conditions and proof information.

    Theoretical entities are distinct from executable statistical
    methods, models and computational algorithms.
    """

    entity_type: Literal["theory"] = field(
        default="theory",
        init=False,
    )

    theory_category: str = ""
    theory_type: str = ""

    formal_definition: dict[str, Any] = field(
        default_factory=dict
    )

    propositions: list[dict[str, Any]] = field(
        default_factory=list
    )

    theorems: list[dict[str, Any]] = field(
        default_factory=list
    )

    assumptions: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    mathematical_notation: dict[str, Any] = field(
        default_factory=dict
    )

    proof_information: dict[str, Any] = field(
        default_factory=dict
    )

    scope: list[str] = field(default_factory=list)
    applicability: list[str] = field(default_factory=list)

    related_theory_ids: list[str] = field(default_factory=list)
    related_distribution_ids: list[str] = field(default_factory=list)
    related_method_ids: list[str] = field(default_factory=list)
    related_model_ids: list[str] = field(default_factory=list)

    implications: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    theory_references: list[str] = field(default_factory=list)
