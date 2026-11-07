"""Canonical subscription plans and feature-entitlement policy.

This module defines product access policy only. It deliberately does not
manage subscriptions, payments, user roles, or database persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


class EntitlementError(ValueError):
    """Raised when a plan or entitlement identifier is invalid."""


@dataclass(frozen=True)
class PlanDefinition:
    """Immutable feature and usage limits for a subscription plan."""

    code: str
    name: str
    features: frozenset[str]
    limits: Mapping[str, int | None]


_COMMON_FEATURES = frozenset(
    {
        "dataset_inspection",
        "essential_data_quality",
        "descriptive_statistics",
        "frequency_tables",
        "crosstabs",
        "basic_visualisations",
        "basic_exports",
    }
)

_PROFESSIONAL_FEATURES = _COMMON_FEATURES | frozenset(
    {
        "hypothesis_testing",
        "confidence_intervals",
        "correlation_analysis",
        "regression_analysis",
        "anova",
        "statistical_diagnostics",
        "ai_analysis_recommendations",
        "advanced_reports",
    }
)

_ENTERPRISE_FEATURES = _PROFESSIONAL_FEATURES | frozenset(
    {
        "team_collaboration",
        "organisation_dashboards",
        "advanced_workflows",
        "custom_reports",
        "institutional_branding",
        "priority_support",
        "api_integrations",
    }
)


def _limits(**values: int | None) -> Mapping[str, int | None]:
    """Create a read-only limits mapping."""
    return MappingProxyType(dict(values))


PLAN_CATALOG: Mapping[str, PlanDefinition] = MappingProxyType(
    {
        "free": PlanDefinition(
            code="free",
            name="Free",
            features=_COMMON_FEATURES,
            limits=_limits(
                max_projects=3,
                max_dataset_rows=10_000,
                max_upload_size_mb=25,
                monthly_analyses=100,
                monthly_exports=10,
                max_team_members=1,
            ),
        ),
        "professional": PlanDefinition(
            code="professional",
            name="Professional",
            features=_PROFESSIONAL_FEATURES,
            limits=_limits(
                max_projects=25,
                max_dataset_rows=250_000,
                max_upload_size_mb=250,
                monthly_analyses=2_000,
                monthly_exports=250,
                max_team_members=1,
            ),
        ),
        "enterprise": PlanDefinition(
            code="enterprise",
            name="Enterprise",
            features=_ENTERPRISE_FEATURES,
            limits=_limits(
                max_projects=None,
                max_dataset_rows=None,
                max_upload_size_mb=None,
                monthly_analyses=None,
                monthly_exports=None,
                max_team_members=None,
            ),
        ),
    }
)

PLAN_CODES = frozenset(PLAN_CATALOG)


def _normalise_code(plan_code: str) -> str:
    """Validate and normalise a plan code."""
    if not isinstance(plan_code, str):
        raise EntitlementError("Subscription plan code must be text.")

    code = plan_code.strip().lower()
    if code not in PLAN_CATALOG:
        raise EntitlementError("Unrecognised subscription plan.")

    return code


def get_plan(plan_code: str) -> PlanDefinition:
    """Return the immutable definition for a recognised plan."""
    return PLAN_CATALOG[_normalise_code(plan_code)]


def has_feature(plan_code: str, feature: str) -> bool:
    """Return whether a plan explicitly includes a feature."""
    plan = get_plan(plan_code)

    if not isinstance(feature, str) or not feature.strip():
        return False

    return feature.strip().lower() in plan.features


def get_limit(plan_code: str, limit_name: str) -> int | None:
    """Return a configured limit; None means unlimited.

    Unknown limits are rejected rather than treated as unlimited.
    """
    plan = get_plan(plan_code)

    if not isinstance(limit_name, str) or not limit_name.strip():
        raise EntitlementError("Usage limit name must be text.")

    key = limit_name.strip().lower()
    if key not in plan.limits:
        raise EntitlementError("Unrecognised subscription usage limit.")

    return plan.limits[key]


def is_within_limit(
    plan_code: str,
    limit_name: str,
    current_usage: int,
    requested_amount: int = 1,
) -> bool:
    """Check whether a proposed usage increment stays within its plan limit."""
    if (
        isinstance(current_usage, bool)
        or not isinstance(current_usage, int)
        or current_usage < 0
    ):
        raise ValueError("Current usage must be a non-negative integer.")

    if (
        isinstance(requested_amount, bool)
        or not isinstance(requested_amount, int)
        or requested_amount < 0
    ):
        raise ValueError("Requested amount must be a non-negative integer.")

    limit = get_limit(plan_code, limit_name)
    return limit is None or current_usage + requested_amount <= limit
