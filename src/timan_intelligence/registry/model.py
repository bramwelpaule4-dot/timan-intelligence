
"""Statistical model entity contract for the TimanStat registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from timan_intelligence.registry.contracts import RegistryEntity


@dataclass
class StatisticalModelEntity(RegistryEntity):
    """Registry representation of a statistical model.

    A statistical model describes the mathematical or probabilistic
    structure used to represent a data-generating process or relationship.

    Estimation and inference methods are represented separately from
    the model itself. This allows one model to support multiple
    estimation and inference procedures.
    """

    entity_type: Literal["model"] = field(
        default="model",
        init=False,
    )

    model_family: str = ""

    model_class: str = ""

    response_variable: dict[str, Any] = field(
        default_factory=dict
    )

    predictor_variables: list[dict[str, Any]] = field(
        default_factory=list
    )

    mathematical_formulation: dict[str, Any] = field(
        default_factory=dict
    )

    parameter_definitions: dict[str, str] = field(
        default_factory=dict
    )

    estimation_methods: list[str] = field(
        default_factory=list
    )

    inference_methods: list[str] = field(
        default_factory=list
    )

    assumptions: list[str] = field(
        default_factory=list
    )

    diagnostics: list[str] = field(
        default_factory=list
    )

    outputs: list[str] = field(
        default_factory=list
    )

    limitations: list[str] = field(
        default_factory=list
    )
