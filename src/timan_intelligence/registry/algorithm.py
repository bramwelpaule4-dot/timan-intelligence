
"""Algorithm-specific entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class AlgorithmEntity(RegistryEntity):
    """Registry representation of a computational algorithm.

    An algorithm is a computational procedure used to perform
    statistical calculations, simulation, optimisation, numerical
    approximation or other computational tasks.

    Algorithms are distinct from statistical methods and models.
    """

    entity_type: Literal["algorithm"] = field(
        default="algorithm",
        init=False,
    )

    algorithm_category: str = ""
    algorithm_type: str = ""

    purpose: str = ""

    input_requirements: list[str] = field(default_factory=list)
    output_specification: dict = field(default_factory=dict)

    parameters: dict = field(default_factory=dict)
    default_parameters: dict = field(default_factory=dict)
    parameter_constraints: dict = field(default_factory=dict)

    computational_complexity: dict = field(default_factory=dict)

    convergence_requirements: list[str] = field(default_factory=list)
    stopping_criteria: list[str] = field(default_factory=list)

    randomness_requirements: dict = field(default_factory=dict)
    reproducibility: dict = field(default_factory=dict)

    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    validation_requirements: list[str] = field(default_factory=list)

    implementation_languages: list[str] = field(default_factory=list)
    software_dependencies: list[str] = field(default_factory=list)

    related_method_ids: list[str] = field(default_factory=list)
    related_model_ids: list[str] = field(default_factory=list)
    related_algorithm_ids: list[str] = field(default_factory=list)

    algorithm_references: list[str] = field(default_factory=list)
