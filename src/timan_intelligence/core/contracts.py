"""Common contracts used by web, desktop, AI orchestration and reports."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisRequest:
    """A structured request for an analysis; no arbitrary code is accepted."""

    question: str
    domain: str = "general"
    dataset_id: str | None = None
    selected_variables: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """A common container for calculated results and their provenance."""

    title: str
    method: str
    status: str = "success"
    tables: dict[str, Any] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
