
"""Registry-driven implementation and verification status reporting.

This module reads the central TimanStat feature registry and produces
a structured project status report.

It does not maintain separate, manually updated progress totals.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from timan_intelligence.registry.feature_registry import (
    IMPLEMENTATION_STATUSES,
    VERIFICATION_STATUSES,
    get_all_features,
    validate_registry,
)


def _percentage(numerator: int, denominator: int) -> float:
    """Calculate a percentage safely."""
    if denominator == 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def build_project_status() -> dict[str, Any]:
    """Generate a project status report from the feature registry.

    Returns:
        A dictionary containing:
        - Report generation timestamp.
        - Overall feature counts.
        - Implementation status distribution.
        - Verification status distribution.
        - Implementation and validation rates.
        - Individual feature records.
        - Registry validation errors.
    """
    features = list(get_all_features())

    implementation_counts = Counter(
        feature.implementation_status for feature in features
    )

    verification_counts = Counter(
        feature.verification_status for feature in features
    )

    implementation_summary = {
        status: implementation_counts.get(status, 0)
        for status in IMPLEMENTATION_STATUSES
    }

    verification_summary = {
        status: verification_counts.get(status, 0)
        for status in VERIFICATION_STATUSES
    }

    total_features = len(features)

    deprecated_count = implementation_summary.get("deprecated", 0)
    active_features = total_features - deprecated_count

    implemented_count = implementation_summary.get("implemented", 0)

    implementation_rate = _percentage(
        implemented_count,
        active_features,
    )

    validated_count = sum(
        1
        for feature in features
        if (
            feature.implementation_status == "implemented"
            and feature.verification_status == "validated"
        )
    )

    implemented_not_fully_validated = sum(
        1
        for feature in features
        if (
            feature.implementation_status == "implemented"
            and feature.verification_status != "validated"
        )
    )

    validation_rate = _percentage(
        validated_count,
        implemented_count,
    )

    feature_records = [
        {
            "feature_id": feature.feature_id,
            "name": feature.name,
            "module": feature.module,
            "description": feature.description,
            "implementation_status": feature.implementation_status,
            "verification_status": feature.verification_status,
            "evidence": list(feature.evidence),
            "notes": feature.notes,
        }
        for feature in features
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_features": total_features,
            "active_features": active_features,
            "deprecated_features": deprecated_count,
            "implemented_features": implemented_count,
            "implementation_rate_percent": implementation_rate,
            "validated_features": validated_count,
            "implemented_not_fully_validated": (
                implemented_not_fully_validated
            ),
            "validation_rate_percent": validation_rate,
        },
        "implementation_status": implementation_summary,
        "verification_status": verification_summary,
        "features": feature_records,
        "registry_validation_errors": validate_registry(),
    }
