
"""Method-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class MethodEntity(RegistryEntity):
    """Registry representation of a statistical method.

    A method describes a procedure used to answer a statistical question.
    Its model, design, diagnostics and computational algorithms are
    represented as separate registry entities and linked through
    relationships.
    """

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
