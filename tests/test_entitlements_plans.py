"""Tests for TimanStat subscription plan entitlement policies."""

import pytest

from timan_intelligence.entitlements.plans import (
    PLAN_CATALOG,
    PLAN_CODES,
    EntitlementError,
    get_limit,
    get_plan,
    has_feature,
    is_within_limit,
)


def test_catalog_contains_the_three_initial_plans():
    assert PLAN_CODES == {"free", "professional", "enterprise"}


def test_free_plan_includes_core_data_workflows():
    for feature in (
        "dataset_inspection",
        "essential_data_quality",
        "descriptive_statistics",
        "frequency_tables",
        "crosstabs",
        "basic_visualisations",
        "basic_exports",
    ):
        assert has_feature("free", feature)


def test_free_plan_does_not_include_inferential_features():
    for feature in (
        "hypothesis_testing",
        "confidence_intervals",
        "regression_analysis",
        "anova",
        "ai_analysis_recommendations",
    ):
        assert not has_feature("free", feature)


def test_professional_includes_inferential_and_ai_features():
    for feature in (
        "hypothesis_testing",
        "confidence_intervals",
        "correlation_analysis",
        "regression_analysis",
        "anova",
        "statistical_diagnostics",
        "ai_analysis_recommendations",
        "advanced_reports",
    ):
        assert has_feature("professional", feature)


def test_enterprise_includes_professional_and_organisation_features():
    for feature in (
        "hypothesis_testing",
        "team_collaboration",
        "organisation_dashboards",
        "advanced_workflows",
        "custom_reports",
        "institutional_branding",
        "priority_support",
        "api_integrations",
    ):
        assert has_feature("enterprise", feature)


def test_plan_feature_sets_are_cumulative():
    assert PLAN_CATALOG["free"].features <= PLAN_CATALOG["professional"].features
    assert (
        PLAN_CATALOG["professional"].features
        <= PLAN_CATALOG["enterprise"].features
    )


def test_free_and_professional_limits_are_explicit():
    assert get_limit("free", "max_projects") == 3
    assert get_limit("free", "max_dataset_rows") == 10_000
    assert get_limit("professional", "max_projects") == 25
    assert get_limit("professional", "max_dataset_rows") == 250_000


def test_enterprise_none_limit_means_unlimited():
    assert get_limit("enterprise", "max_projects") is None
    assert get_limit("enterprise", "monthly_analyses") is None


def test_limit_check_accepts_usage_at_limit():
    assert is_within_limit("free", "max_projects", 2, 1)


def test_limit_check_rejects_usage_over_limit():
    assert not is_within_limit("free", "max_projects", 3, 1)


def test_limit_check_supports_multi_unit_requests():
    assert is_within_limit("free", "max_projects", 1, 2)
    assert not is_within_limit("free", "max_projects", 2, 2)


def test_unlimited_plan_allows_any_non_negative_usage():
    assert is_within_limit("enterprise", "max_projects", 10**12, 10**12)


@pytest.mark.parametrize("invalid_plan", ["", "unknown", None, 123])
def test_unknown_plan_is_rejected(invalid_plan):
    with pytest.raises(EntitlementError):
        get_plan(invalid_plan)


def test_unknown_feature_is_not_granted():
    assert not has_feature("free", "feature_not_registered")


def test_unknown_limit_is_rejected_not_treated_as_unlimited():
    with pytest.raises(EntitlementError):
        get_limit("enterprise", "unregistered_limit")


@pytest.mark.parametrize(
    ("usage", "requested"),
    [(-1, 1), (0, -1), (True, 1), (1, False), (1.5, 1)],
)
def test_invalid_usage_values_are_rejected(usage, requested):
    with pytest.raises(ValueError):
        is_within_limit("free", "max_projects", usage, requested)


def test_plan_definitions_and_limits_are_immutable():
    with pytest.raises(TypeError):
        PLAN_CATALOG["starter"] = PLAN_CATALOG["free"]

    with pytest.raises(TypeError):
        PLAN_CATALOG["free"].limits["max_projects"] = 999
