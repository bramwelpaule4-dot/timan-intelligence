
"""Central feature implementation and verification registry for TimanStat.

This registry tracks application capabilities separately from the
statistical and software verification evidence supporting them.
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
        """Return a dictionary representation."""
        return asdict(self)


# Initial project baseline.
# These classifications are provisional and should be updated
# as implementation and verification evidence becomes available.

_FEATURES = (
    Feature(
        "DATA-001",
        "CSV file import",
        "Data Management",
        "Import datasets from CSV files.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "DATA-002",
        "Excel file import",
        "Data Management",
        "Import datasets from Excel workbooks.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "DATA-003",
        "Dataset preview",
        "Data Management",
        "Inspect uploaded dataset contents and structure.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "QUAL-001",
        "Initial data-quality profiling",
        "Data Quality",
        "Perform initial checks on dataset completeness and quality.",
        "implemented",
        "not_tested",
        notes="Advanced validity and consistency checks remain outstanding.",
    ),
    Feature(
        "DESC-001",
        "Numeric descriptive statistics",
        "Descriptive Statistics",
        "Generate summary statistics for numeric variables.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "DESC-002",
        "Categorical frequency summaries",
        "Descriptive Statistics",
        "Summarise categorical variables using frequencies.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "DESC-003",
        "Grouped descriptive summaries",
        "Descriptive Statistics",
        "Generate descriptive summaries across selected groups.",
        "in_development",
        "not_tested",
    ),
    Feature(
        "VIZ-001",
        "Basic data visualisations",
        "Visualisations",
        "Produce basic graphical summaries of datasets.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "EXP-001",
        "Selected analytical output exports",
        "Reports and Exports",
        "Export selected analytical outputs.",
        "implemented",
        "not_tested",
    ),
    Feature(
        "INF-001",
        "Statistical hypothesis testing",
        "Statistical Inference",
        "Conduct appropriate statistical hypothesis tests.",
        "planned",
        "not_tested",
    ),
    Feature(
        "SUR-001",
        "Survey analysis workflows",
        "Survey Analysis",
        "Support structured survey analysis.",
        "planned",
        "not_tested",
    ),
    Feature(
        "MOD-001",
        "Research and statistical modelling",
        "Research and Modelling",
        "Provide research-oriented statistical modelling.",
        "planned",
        "not_tested",
    ),
    Feature(
        "MEAL-001",
        "MEAL analytical workflows",
        "MEAL Intelligence",
        "Support monitoring, evaluation, accountability and learning.",
        "planned",
        "not_tested",
    ),
    Feature(
        "BI-001",
        "Business intelligence workflows",
        "Business Intelligence",
        "Support business data analysis and decision-making.",
        "planned",
        "not_tested",
    ),
    Feature(
        "AI-001",
        "Natural-language statistical analyst",
        "AI Analyst",
        "Provide guided analytical assistance using natural language.",
        "planned",
        "not_tested",
    ),
    Feature(
        "ENG-001",
        "Python statistical engine",
        "Statistical Engines",
        "Provide the initial operational statistical computing engine.",
        "in_development",
        "not_tested",
    ),
    Feature(
        "ENG-002",
        "R statistical engine",
        "Statistical Engines",
        "Integrate R as an additional statistical engine.",
        "planned",
        "not_tested",
    ),
    Feature(
        "DESK-001",
        "Desktop application foundation",
        "Desktop Application",
        "Provide the initial branded desktop application shell.",
        "implemented",
        "not_tested",
        notes="Not yet a complete desktop statistical application.",
    ),
    Feature(
        "GOV-001",
        "Centralised branding configuration",
        "Settings and Governance",
        "Maintain shared application identity and branding.",
        "implemented",
        "integration_tested",
        evidence=(
            "GitHub Actions commit #150: Streamlit branding",
            "GitHub Actions commit #151: Desktop branding",
        ),
    ),
    Feature(
        "GOV-002",
        "Automated continuous integration",
        "Settings and Governance",
        "Run automated tests through GitHub Actions.",
        "implemented",
        "integration_tested",
        evidence=(
            "GitHub Actions commit #158: Python 3.11 Tests succeeded",
        ),
        notes="CI success does not establish methodological validity.",
    ),
    Feature(
        "GOV-003",
        "Project implementation dashboard",
        "Settings and Governance",
        "Display implementation and verification progress.",
        "planned",
        "not_tested",
    ),
    Feature(
        "GOV-004",
        "One-click project status reporting",
        "Settings and Governance",
        "Generate project status reports from registry evidence.",
        "planned",
        "not_tested",
    ),
)


def get_all_features() -> list[Feature]:
    """Return all registered features."""
    return list(_FEATURES)


def get_feature(feature_id: str) -> Optional[Feature]:
    """Find a feature by its unique identifier."""
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
    """Return features matching an implementation status."""
    if status not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"Invalid implementation status: {status}")

    return [
        feature
        for feature in _FEATURES
        if feature.implementation_status == status
    ]


def get_features_by_verification_status(
    status: str,
) -> list[Feature]:
    """Return features matching a verification status."""
    if status not in VERIFICATION_STATUSES:
        raise ValueError(f"Invalid verification status: {status}")

    return [
        feature
        for feature in _FEATURES
        if feature.verification_status == status
    ]


def get_registry_summary() -> dict:
    """Return feature counts by implementation and verification status."""
    return {
        "total_features": len(_FEATURES),
        "implementation": {
            status: len(get_features_by_implementation_status(status))
            for status in IMPLEMENTATION_STATUSES
        },
        "verification": {
            status: len(get_features_by_verification_status(status))
            for status in VERIFICATION_STATUSES
        },
    }


def validate_registry() -> list[str]:
    """Return structural registry errors.

    An empty list means structural checks passed. It does not establish
    that the registered statistical procedures are methodologically valid.
    """
    errors: list[str] = []
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
                f"{feature.feature_id}: validated features "
                "must be implemented."
            )

    return errors
