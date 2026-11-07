"""Subscription entitlement policies and server-side enforcement."""

from timan_intelligence.entitlements.plans import (
    PLAN_CATALOG,
    PLAN_CODES,
    EntitlementError,
    PlanDefinition,
    get_limit,
    get_plan,
    has_feature,
    is_within_limit,
)
from timan_intelligence.entitlements.service import (
    FeatureAccessDenied,
    UsageLimitExceeded,
    consume_monthly_usage,
    get_effective_entitlements,
    get_monthly_usage,
    require_feature,
)

__all__ = [
    "PLAN_CATALOG",
    "PLAN_CODES",
    "EntitlementError",
    "PlanDefinition",
    "FeatureAccessDenied",
    "UsageLimitExceeded",
    "get_limit",
    "get_plan",
    "has_feature",
    "is_within_limit",
    "get_effective_entitlements",
    "require_feature",
    "get_monthly_usage",
    "consume_monthly_usage",
]
