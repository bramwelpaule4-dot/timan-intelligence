
"""Distribution-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class DistributionEntity(RegistryEntity):
    """Registry representation of a probability distribution.

    A distribution entity describes the mathematical and probabilistic
    properties of a distribution independently of the statistical
    methods and models that use it.

    It distinguishes distribution definitions from probability
    functions, parameterisations, support, moments and computational
    sampling information.
    """

    entity_type: Literal["distribution"] = field(
        default="distribution",
        init=False,
    )

    distribution_category: str = ""
    distribution_type: str = ""

    distribution_family: str = ""
    dimension: str = ""

    parameters: dict[str, Any] = field(default_factory=dict)

    support: dict[str, Any] = field(default_factory=dict)

    probability_functions: dict[str, Any] = field(
        default_factory=dict
    )

    moments: dict[str, Any] = field(default_factory=dict)

    properties: list[str] = field(default_factory=list)

    characteristic_function: dict[str, Any] = field(
        default_factory=dict
    )

    generating_functions: dict[str, Any] = field(
        default_factory=dict
    )

    sampling_information: dict[str, Any] = field(
        default_factory=dict
    )

    related_distribution_ids: list[str] = field(
        default_factory=list
    )

    related_theory_ids: list[str] = field(default_factory=list)

    related_method_ids: list[str] = field(default_factory=list)

    applications: list[str] = field(default_factory=list)

    limitations: list[str] = field(default_factory=list)

    distribution_references: list[str] = field(
        default_factory=list
    )
