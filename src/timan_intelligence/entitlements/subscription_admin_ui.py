"""Platform administrator interface for subscription assignment."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from timan_intelligence.administration.audit import record_audit_event
from timan_intelligence.administration.user_service import list_users
from timan_intelligence.database.connection import database_connection
from timan_intelligence.entitlements.plans import PLAN_CATALOG
from timan_intelligence.entitlements.subscriptions import (
    SUBSCRIPTION_STATUSES,
    assign_subscription,
    get_subscription,
    get_subscription_history,
)


def _list_organisations() -> list[dict]:
    """Return organisation identifiers and names for platform administrators."""
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, status, created_at
            FROM organisations
            ORDER BY name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _owner_label(owner: dict, scope: str) -> str:
    if scope == "Individual":
        name = owner.get("full_name") or owner.get("username") or owner["email"]
        return f"{name} — {owner['email']}"
    return f"{owner['name']} — {owner['status']}"


def render_subscription_administration(
    *,
    actor_user_id: str | None,
    actor_role: str | None,
) -> None:
    """Render the restricted platform subscription administration interface."""
    st.title("Subscription Administration")
    st.caption(
        "Assign plans to individual accounts and organisations. "
        "Every assignment preserves the previous subscription record."
    )

    if actor_role not in {"admin", "super_admin"}:
        st.error("You do not have permission to administer platform subscriptions.")
        return
    if not isinstance(actor_user_id, str) or not actor_user_id.strip():
        st.error("The administrator account could not be verified.")
        return

    try:
        users = list_users(actor_role, limit=1000)
        organisations = _list_organisations()
    except Exception:
        st.error("Platform account and organisation records could not be loaded.")
        return

    scope = st.radio(
        "Subscription owner",
        ["Individual", "Organisation"],
        horizontal=True,
        key="subscription_admin_scope",
    )

    if scope == "Individual":
        if not users:
            st.info("There are no user accounts to manage.")
            return
        owners = users
        labels = {
            _owner_label(user, scope): user
            for user in users
        }
    else:
        if not organisations:
            st.info("There are no organisations to manage.")
            return
        owners = organisations
        labels = {
            _owner_label(organisation, scope): organisation
            for organisation in organisations
        }

    selected_label = st.selectbox(
        "Select account or organisation",
        list(labels),
        key="subscription_admin_owner",
    )
    owner = labels[selected_label]
    owner_kwargs = (
        {"user_id": owner["id"]}
        if scope == "Individual"
        else {"organisation_id": owner["id"]}
    )

    try:
        current = get_subscription(**owner_kwargs)
        history = get_subscription_history(**owner_kwargs)
    except Exception:
        st.error("The selected subscription records could not be loaded.")
        return

    st.subheader("Current subscription")
    if current:
        st.write(
            f"**Plan:** {PLAN_CATALOG[current['plan_code']].name}  
"
            f"**Status:** {current['status'].replace('_', ' ').title()}  
"
            f"**Started:** {current.get('started_at') or 'Not recorded'}  
"
            f"**Period ends:** {current.get('current_period_end') or 'Not specified'}"
        )
        if current.get("cancel_at_period_end"):
            st.warning("This subscription is scheduled to cancel at period end.")
    else:
        st.info("No current paid subscription. The owner receives the Free plan unless an inherited plan applies.")

    st.subheader("Assign or replace subscription")
    st.warning(
        "Assigning a new subscription will mark any current subscription for this owner "
        "as canceled and create a new historical record. This action does not charge the customer."
    )

    with st.form("subscription_assignment_form"):
        plan_code = st.selectbox(
            "Plan",
            options=list(PLAN_CATALOG),
            format_func=lambda code: PLAN_CATALOG[code].name,
        )
        status = st.selectbox(
            "Initial status",
            options=sorted(SUBSCRIPTION_STATUSES),
            index=sorted(SUBSCRIPTION_STATUSES).index("active"),
        )
        period_start = st.text_input(
            "Current period start (optional ISO date/time)",
            placeholder="2026-11-08T00:00:00Z",
        )
        period_end = st.text_input(
            "Current period end (optional ISO date/time)",
            placeholder="2026-12-08T00:00:00Z",
        )
        cancel_at_period_end = st.checkbox("Schedule cancellation at period end")
        confirmed = st.checkbox(
            "I confirm that this plan assignment is authorised."
        )
        submitted = st.form_submit_button("Assign subscription", type="primary")

    if submitted:
        if not confirmed:
            st.error("Confirm that this assignment is authorised before proceeding.")
        else:
            try:
                subscription_id = assign_subscription(
                    plan_code=plan_code,
                    status=status,
                    current_period_start=period_start.strip() or None,
                    current_period_end=period_end.strip() or None,
                    cancel_at_period_end=cancel_at_period_end,
                    **owner_kwargs,
                )
                record_audit_event(
                    action="subscription.assigned",
                    user_id=actor_user_id,
                    organisation_id=(
                        owner["id"] if scope == "Organisation" else None
                    ),
                    resource_type="subscription",
                    resource_id=subscription_id,
                    details={
                        "owner_scope": scope.lower(),
                        "owner_id": owner["id"],
                        "plan_code": plan_code,
                        "status": status,
                        "cancel_at_period_end": cancel_at_period_end,
                    },
                )
                st.success(
                    f"{PLAN_CATALOG[plan_code].name} subscription assigned successfully."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Subscription assignment failed: {exc}")

    st.subheader("Subscription history")
    if history:
        rows = [
            {
                "Plan": PLAN_CATALOG[item["plan_code"]].name,
                "Status": item["status"].replace("_", " ").title(),
                "Started": item.get("started_at"),
                "Period start": item.get("current_period_start"),
                "Period end": item.get("current_period_end"),
                "Cancel at period end": bool(item.get("cancel_at_period_end")),
                "Subscription ID": item["id"],
            }
            for item in history
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.caption("No subscription records exist for this owner.")
