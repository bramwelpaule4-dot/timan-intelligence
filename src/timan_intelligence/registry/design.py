
"""Design-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class DesignEntity(RegistryEntity):
    """Registry representation of a statistical study design.

    Represents experimental, observational and sampling designs.

    Sampling, allocation, observation and analysis units are
    represented separately because they may differ within a study.
    """

    entity_type: Literal["design"] = field(
        default="design",
        init=False,
    )

    design_category: str = ""
    design_type: str = ""

    sampling_unit: str | None = None
    allocation_unit: str | None = None
    observation_unit: str | None = None
    analysis_unit: str | None = None

    randomization_method: str | None = None
    sampling_method: str | None = None

    control_group: dict[str, Any] = field(default_factory=dict)
    treatment_arms: list[dict[str, Any]] = field(default_factory=list)
    blinding: dict[str, Any] = field(default_factory=dict)

    repeated_measures: bool = False
    measurement_occasions: list[str] = field(default_factory=list)

    clustering: dict[str, Any] = field(default_factory=dict)
    stratification_variables: list[str] = field(default_factory=list)

    design_structure: dict[str, Any] = field(default_factory=dict)

    assumptions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    analysis_implications: list[str] = field(default_factory=list)

    related_method_ids: list[str] = field(default_factory=list)
    related_model_ids: list[str] = field(default_factory=list)

    design_references: list[str] = field(default_factory=list)
