
"""Measure-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class MeasureEntity(RegistryEntity):
    """Registry representation of a statistical measure.

    Represents statistical quantities including descriptive measures,
    distribution measures, effect sizes, association measures,
    uncertainty measures, test statistics and model-performance
    measures.

    A measure is distinct from the method or model used to estimate
    or calculate it.
    """

    entity_type: Literal["measure"] = field(
        default="measure",
        init=False,
    )

    measure_category: str = ""
    measure_type: str = ""

    purpose: str = ""

    mathematical_definition: dict = field(default_factory=dict)
    formula_components: list[str] = field(default_factory=list)

    measurement_scale: str | None = None
    unit: str | None = None
    valid_range: dict = field(default_factory=dict)

    interpretation_guidance: list[str] = field(default_factory=list)

    directionality: str | None = None
    higher_is_better: bool | None = None
    scope: str | None = None

    estimation_method_ids: list[str] = field(default_factory=list)
    related_model_ids: list[str] = field(default_factory=list)
    related_measure_ids: list[str] = field(default_factory=list)

    visualization_ids: list[str] = field(default_factory=list)

    limitations: list[str] = field(default_factory=list)
    measure_references: list[str] = field(default_factory=list)
