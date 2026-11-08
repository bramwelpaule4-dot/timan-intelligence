"""Read-only subscription and plan overview for TimanStat users."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from timan_intelligence.entitlements.plans import PLAN_CATALOG
from timan_intelligence.entitlements.service import (
    get_effective_entitlements,
    get_monthly_usage,
)
from timan_intelligence.entitlements.subscriptions import (
    get_subscription,
    get_subscription_history,
)


def _format_limit(value: int | None) -> str:
    """Format a finite or unlimited plan allowance."""
    return "Unlimited" if value is None else f"{value:,}"


def _format_timestamp(value: Any) -> str:
    """Format an optional persisted timestamp for display."""
    return str(value) if value else "Not specified"


def render_subscription_page(
    *,
    user_id: str | None,
    organisation_id: str | None = None,
) -> None:
    """Render the effective plan, allowances, usage and subscription history."""
    st.title("Subscription & Plans")
    st.caption("Review the plan and limits applied to your current workspace.")

    if not isinstance(user_id, str) or not user_id.strip():
        st.error("Your authenticated account could not be verified. Please sign in again.")
        return

    if organisation_id:
        workspace_label = "Organisation workspace"
        usage_owner = {"organisation_id": organisation_id}
        organisation_record = get_subscription(organisation_id=organisation_id)
        organisation_history = get_subscription_history(organisation_id=organisation_id)
        personal_record = get_subscription(user_id=user_id)
        personal_history = get_subscription_history(user_id=user_id)

        # Effective entitlements use the organisation plan when active,
        # otherwise they fall back to the signed-in user's personal plan.
        current_record = organisation_record or personal_record
        history = sorted(
            organisation_history + personal_history,
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        subscription_owner_label = (
            "Organisation subscription"
            if organisation_record
            else "Personal subscription applied to this workspace"
            if personal_record
            else "No active paid subscription"
        )
    else:
        workspace_label = "Personal account"
        usage_owner = {"user_id": user_id}
        current_record = get_subscription(user_id=user_id)
        history = get_subscription_history(user_id=user_id)
        subscription_owner_label = "Personal subscription"

    try:
        entitlements = get_effective_entitlements(
            user_id=user_id,
            organisation_id=organisation_id,
        )
        analysis_used = get_monthly_usage("monthly_analyses", **usage_owner)
        exports_used = get_monthly_usage("monthly_exports", **usage_owner)
    except Exception:
        st.error("Subscription information could not be loaded. Please refresh and try again.")
        return

    plan_code = entitlements["plan_code"]
    limits = entitlements["limits"]

    st.subheader(workspace_label)
    st.caption(subscription_owner_label)

    metric_columns = st.columns(4)
    metric_columns[0].metric("Current plan", entitlements["plan_name"])
    metric_columns[1].metric(
        "Subscription status",
        current_record["status"].replace("_", " ").title()
        if current_record else "Free access",
    )
    metric_columns[2].metric(
        "Monthly analyses",
        f"{analysis_used:,} / {_format_limit(limits['monthly_analyses'])}",
    )
    metric_columns[3].metric(
        "Monthly exports",
        f"{exports_used:,} / {_format_limit(limits['monthly_exports'])}",
    )

    if current_record and current_record.get("cancel_at_period_end"):
        st.warning(
            "This subscription is scheduled to end at the close of its current period. "
            "Your current plan remains effective until then."
        )
    elif current_record is None and plan_code == "free":
        st.info(
            "This workspace is currently using the Free plan. "
            "No paid subscription is recorded."
        )

    st.subheader("Current plan allowances")
    allowance_rows = [
        {"Allowance": "Projects", "Plan limit": _format_limit(limits["max_projects"])},
        {"Allowance": "Dataset rows", "Plan limit": _format_limit(limits["max_dataset_rows"])},
        {"Allowance": "Upload size (MB)", "Plan limit": _format_limit(limits["max_upload_size_mb"])},
        {"Allowance": "Monthly analyses", "Plan limit": _format_limit(limits["monthly_analyses"])},
        {"Allowance": "Monthly exports", "Plan limit": _format_limit(limits["monthly_exports"])},
        {"Allowance": "Team members", "Plan limit": _format_limit(limits["max_team_members"])},
    ]
    st.dataframe(pd.DataFrame(allowance_rows), hide_index=True, use_container_width=True)

    st.subheader("Included capabilities")
    feature_names = {
        "dataset_inspection": "Dataset inspection",
        "essential_data_quality": "Essential data-quality checks",
        "descriptive_statistics": "Descriptive statistics",
        "frequency_tables": "Frequency tables",
        "crosstabs": "Cross-tabulations",
        "basic_visualisations": "Basic visualisations",
        "basic_exports": "Basic data exports",
        "hypothesis_testing": "Hypothesis testing",
        "confidence_intervals": "Confidence intervals",
        "correlation_analysis": "Correlation analysis",
        "regression_analysis": "Regression analysis",
        "anova": "Analysis of variance (ANOVA)",
        "statistical_diagnostics": "Statistical diagnostics",
        "ai_analysis_recommendations": "AI analysis recommendations",
        "advanced_reports": "Advanced reports",
        "team_collaboration": "Team collaboration",
        "organisation_dashboards": "Organisation dashboards",
        "advanced_workflows": "Advanced analytical workflows",
        "custom_reports": "Custom reports",
        "institutional_branding": "Institutional branding",
        "priority_support": "Priority support",
        "api_integrations": "API integrations",
    }
    included = set(entitlements["features"])
    feature_rows = [
        {
            "Capability": label,
            "Included": "Included" if code in included else "Not included",
        }
        for code, label in feature_names.items()
    ]
    st.dataframe(pd.DataFrame(feature_rows), hide_index=True, use_container_width=True)

    st.subheader("Plan comparison")
    comparison_rows = []
    for code, plan in PLAN_CATALOG.items():
        comparison_rows.append(
            {
                "Plan": plan.name,
                "Projects": _format_limit(plan.limits["max_projects"]),
                "Dataset rows": _format_limit(plan.limits["max_dataset_rows"]),
                "Upload (MB)": _format_limit(plan.limits["max_upload_size_mb"]),
                "Analyses / month": _format_limit(plan.limits["monthly_analyses"]),
                "Exports / month": _format_limit(plan.limits["monthly_exports"]),
                "Team members": _format_limit(plan.limits["max_team_members"]),
                "Current plan": "Yes" if code == plan_code else "",
            }
        )
    st.dataframe(
        pd.DataFrame(comparison_rows),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Subscription history")
    if history:
        history_rows = [
            {
                "Scope": (
                    "Organisation"
                    if item.get("organisation_id")
                    else "Personal"
                ),
                "Plan": str(item["plan_code"]).title(),
                "Status": str(item["status"]).replace("_", " ").title(),
                "Started": _format_timestamp(item.get("started_at")),
                "Period starts": _format_timestamp(item.get("current_period_start")),
                "Period ends": _format_timestamp(item.get("current_period_end")),
                "Cancel at period end": "Yes" if item.get("cancel_at_period_end") else "No",
            }
            for item in history
        ]
        st.dataframe(
            pd.DataFrame(history_rows),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("No subscription history is recorded for this account or workspace.")

    st.caption(
        "Plan upgrades, renewals and payments are not yet processed in the application. "
        "Contact the TimanStat platform administrator to discuss a plan change."
    )
