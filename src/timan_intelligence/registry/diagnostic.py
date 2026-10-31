
"""Diagnostic-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class DiagnosticEntity(RegistryEntity):
    """Registry representation of a statistical diagnostic.

    Diagnostics assess data quality, distributions, assumptions,
    model adequacy, residual behaviour, influence and predictive
    performance.

    A diagnostic provides evidence and guidance. It does not
    automatically determine or change the statistical method.
    """

    entity_type: Literal["diagnostic"] = field(
        default="diagnostic",
        init=False,
    )

    diagnostic_category: str = ""
    diagnostic_type: str = ""

    purpose: str = ""

    data_requirements: list[str] = field(default_factory=list)
    applicable_variables: list[str] = field(default_factory=list)

    test_statistic: dict = field(default_factory=dict)
    null_hypothesis: str | None = None
    alternative_hypothesis: str | None = None

    produces_p_value: bool = False
    thresholds: dict = field(default_factory=dict)

    interpretation_guidance: list[str] = field(default_factory=list)

    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    applicable_model_ids: list[str] = field(default_factory=list)
    applicable_method_ids: list[str] = field(default_factory=list)
    related_diagnostic_ids: list[str] = field(default_factory=list)

    outputs: list[str] = field(default_factory=list)
    visualization_ids: list[str] = field(default_factory=list)

    diagnostic_references: list[str] = field(default_factory=list)
