
"""Central feature implementation and verification registry.

This module records the development status of TimanStat capabilities.

Implementation status and verification status are deliberately separate.
A feature may be implemented without having undergone numerical or
methodological verification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


IMPLEMENTATION_STATUSES = (
    "planned",
    "in_development",
    "implemented",
    "deprecated",
)

VERIFICATION_STATUSES = (
    "not_tested",
    "unit_tested",
    "integration_tested",
    "numerically_verified",
    "methodologically_reviewed",
    "validated",
)


@dataclass(frozen=True)
class Feature:
    """Represent one TimanStat capability."""

    feature_id: str
    name: str
    module: str
    description: str
    implementation_status: str
    verification_status: str
    evidence: tuple[str, ...] = ()
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Return a serialisable representation of the feature."""
        return asdict(self)


# Initial registry baseline.
#
# Statuses below are conservative starting classifications based on the
# documented prototype and development history. They must be updated when
# implementation or verification evidence changes.

_FEATURES = (
    Feature(
        feature_id="DATA-001",
        name="CSV file import",
        module="Data Management",
        description="Import datasets from CSV files.",
        implementation_status="implemented",
        verification_status="not_tested",
        notes="Prototype capability; dedicated verification evidence "
              "must be recorded.",
    ),
    Feature(
        feature_id="DATA-002",
        name="Excel file import",
        module="Data Management",
        description="Import datasets from Excel workbooks.",
        implementation_status="implemented",
        verification_status="not_tested",
        notes="Workbook and worksheet handling require further testing.",
    ),
    Feature(
        feature_id="DATA-003",
        name="Dataset preview",
        module="Data Management",
        description="Inspect uploaded dataset contents and structure.",
        implementation_status="implemented",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="QUAL-001",
        name="Initial data-quality profiling",
        module="Data Quality",
        description="Perform initial checks on dataset completeness "
                    "and variable quality.",
        implementation_status="implemented",
        verification_status="not_tested",
        notes="Advanced validity, consistency and programme-specific "
              "checks remain outstanding.",
    ),
    Feature(
        feature_id="DESC-001",
        name="Numeric descriptive statistics",
        module="Descriptive Statistics",
        description="Generate summary statistics for numeric variables.",
        implementation_status="implemented",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="DESC-002",
        name="Categorical frequency summaries",
        module="Descriptive Statistics",
        description="Summarise categorical variables using frequencies.",
        implementation_status="implemented",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="DESC-003",
        name="Grouped descriptive summaries",
        module="Descriptive Statistics",
        description="Explore descriptive summaries across selected groups.",
        implementation_status="in_development",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="VIZ-001",
        name="Basic data visualisations",
        module="Visualisations",
        description="Produce basic graphical summaries of datasets.",
        implementation_status="implemented",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="EXP-001",
        name="Selected analytical output exports",
        module="Reports and Exports",
        description="Export selected analytical outputs.",
        implementation_status="implemented",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="INF-001",
        name="Statistical hypothesis testing",
        module="Statistical Inference",
        description="Conduct appropriate statistical hypothesis tests.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="SUR-001",
        name="Survey analysis workflows",
        module="Survey Analysis",
        description="Support structured survey analysis, including "
                    "appropriate survey design considerations.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="MOD-001",
        name="Research and statistical modelling",
        module="Research and Modelling",
        description="Provide research-oriented statistical modelling.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="MEAL-001",
        name="MEAL analytical workflows",
        module="MEAL Intelligence",
        description="Support monitoring, evaluation, accountability "
                    "and learning analysis.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="BI-001",
        name="Business intelligence workflows",
        module="Business Intelligence",
        description="Support business data analysis and decision-making.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="AI-001",
        name="Natural-language statistical analyst",
        module="AI Analyst",
        description="Provide guided analytical assistance through "
                    "natural-language interaction.",
        implementation_status="planned",
        verification_status="not_tested",
        notes="AI-assisted recommendations must use validated "
              "statistical procedures.",
    ),
    Feature(
        feature_id="ENG-001",
        name="Python statistical engine",
        module="Statistical Engines",
        description="Provide the initial operational statistical "
                    "computing engine.",
        implementation_status="in_development",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="ENG-002",
        name="R statistical engine",
        module="Statistical Engines",
        description="Integrate R as an additional statistical engine.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="DESK-001",
        name="Desktop application foundation",
        module="Desktop Application",
        description="Provide the initial branded desktop application shell.",
        implementation_status="implemented",
        verification_status="not_tested",
        notes="The desktop shell is not yet a complete statistical "
              "analysis application.",
    ),
    Feature(
        feature_id="GOV-001",
        name="Centralised branding configuration",
        module="Settings and Governance",
        description="Maintain shared application identity and branding.",
        implementation_status="implemented",
        verification_status="integration_tested",
        evidence=(
            "GitHub Actions commit #150: Streamlit branding",
            "GitHub Actions commit #151: Desktop branding",
        ),
    ),
    Feature(
        feature_id="GOV-002",
        name="Automated continuous integration",
        module="Settings and Governance",
        description="Run automated tests through GitHub Actions.",
        implementation_status="implemented",
        verification_status="integration_tested",
        evidence=(
            "GitHub Actions commit #158: Python 3.11 Tests succeeded",
        ),
        notes="CI success does not establish methodological validity.",
    ),
    Feature(
        feature_id="GOV-003",
        name="Project implementation dashboard",
        module="Settings and Governance",
        description="Display implementation and verification progress.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
    Feature(
        feature_id="GOV-004",
        name="One-click project status reporting",
        module="Settings and Governance",
        description="Generate an updated project status report from "
                    "registry data and verification evidence.",
        implementation_status="planned",
        verification_status="not_tested",
    ),
)


def get_all_features() -> list[Feature]:
    """Return all registered features."""
    return list(_FEATURES)


def get_feature(feature_id: str) -> Optional[Feature]:
    """Find a feature using its unique identifier."""
    return next(
        (
            feature
            for feature in _FEATURES
            if feature.feature_id == feature_id
        ),
        None,
    )


def get_features_by_implementation_status(
    status: str,
) -> list[Feature]:
    """Filter features by implementation status."""
    if status not in IMPLEMENTATION_STATUSES:
        raise ValueError(
            f"Invalid implementation status: {status}"
        )

    return [
        feature
        for feature in _FEATURES
        if feature.implementation_status == status
    ]


def get_features_by_verification_status(
    status: str,
) -> list[Feature]:
    """Filter features by verification status."""
    if status not in VERIFICATION_STATUSES:
        raise ValueError(
            f"Invalid verification status: {status}"
        )

    return [
        feature
        for feature in _FEATURES
        if feature.verification_status == status
    ]


def get_registry_summary() -> dict:
    """Return implementation and verification counts."""
    implementation_counts = {
        status: len(
            get_features_by_implementation_status(status)
        )
        for status in IMPLEMENTATION_STATUSES
    }

    verification_counts = {
        status: len(
            get_features_by_verification_status(status)
        )
        for status in VERIFICATION_STATUSES
    }

    return {
        "total_features": len(_FEATURES),
        "implementation": implementation_counts,
        "verification": verification_counts,
    }


def validate_registry() -> list[str]:
    """Return registry integrity errors.

    An empty list means the registry passed these structural checks.
    It does not mean the registered features have been methodologically
    validated.
    """
    errors = []
    identifiers = [feature.feature_id for feature in _FEATURES]

    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate feature identifiers found.")

    for feature in _FEATURES:
        if not feature.feature_id.strip():
            errors.append("A feature has an empty identifier.")

        if not feature.name.strip():
            errors.append(
                f"{feature.feature_id}: feature name is empty."
            )

        if not feature.module.strip():
            errors.append(
                f"{feature.feature_id}: module is empty."
            )

        if feature.implementation_status not in IMPLEMENTATION_STATUSES:
            errors.append(
                f"{feature.feature_id}: invalid implementation status."
            )

        if feature.verification_status not in VERIFICATION_STATUSES:
            errors.append(
                f"{feature.feature_id}: invalid verification status."
            )

        if (
            feature.verification_status == "validated"
            and feature.implementation_status != "implemented"
        ):
            errors.append(
                f"{feature.feature_id}: a validated feature "
                "must be implemented."
            )

    return errors
