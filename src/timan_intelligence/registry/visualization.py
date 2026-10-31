
"""Visualisation-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Any

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class VisualizationEntity(RegistryEntity):
    """Registry representation of a statistical visualisation.

    The entity distinguishes three concepts:

    1. Visualization definition: what the visualisation is and its purpose.
    2. Visualization specification: how it should be configured.
    3. Rendered output: the actual visual output generated from data.

    This separation allows TimanStat to catalogue visualisation types
    independently of particular datasets, configurations or rendered
    chart files.
    """

    entity_type: Literal["visualization"] = field(
        default="visualization",
        init=False,
    )

    visualization_category: str = ""
    visualization_type: str = ""

    visualization_definition: dict[str, Any] = field(
        default_factory=dict
    )

    visualization_specification: dict[str, Any] = field(
        default_factory=dict
    )

    rendered_output: dict[str, Any] = field(
        default_factory=dict
    )

    variables: list[str] = field(default_factory=list)

    encodings: dict[str, Any] = field(default_factory=dict)

    scales: dict[str, Any] = field(default_factory=dict)

    facets: dict[str, Any] = field(default_factory=dict)

    statistical_options: dict[str, Any] = field(
        default_factory=dict
    )

    interactivity: dict[str, Any] = field(default_factory=dict)

    outputs: list[str] = field(default_factory=list)

    related_measure_ids: list[str] = field(default_factory=list)
    related_model_ids: list[str] = field(default_factory=list)
    related_method_ids: list[str] = field(default_factory=list)
    related_diagnostic_ids: list[str] = field(default_factory=list)

    limitations: list[str] = field(default_factory=list)

    visualization_references: list[str] = field(default_factory=list)
