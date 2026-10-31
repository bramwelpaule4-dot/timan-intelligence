
"""Method-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class MethodEntity(RegistryEntity):
    """Registry representation of a statistical method."""

    entity_type: Literal["method"] = field(
        default="method",
        init=False,
    )

    use_cases: list[str] = field(default_factory=list)

    data_requirements: list[str] = field(default_factory=list)

    statistical_specification: dict[str, Any] = field(
        default_factory=dict
    )

    assumptions: list[str] = field(default_factory=list)

    estimands: list[str] = field(default_factory=list)

    hypotheses: list[str] = field(default_factory=list)

    outputs: list[str] = field(default_factory=list)

    computational_requirements: list[str] = field(
        default_factory=list
    )

    validation_requirements: list[str] = field(
        default_factory=list
    )

    limitations: list[str] = field(default_factory=list)
