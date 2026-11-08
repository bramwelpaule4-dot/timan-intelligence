"""Streamlit interface for platform user administration."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from timan_intelligence.administration.audit import list_audit_events
from timan_intelligence.administration.user_service import (
    change_user_role,
    list_users,
    set_user_active_status,
)


PLATFORM_ROLES = ("user", "developer", "admin", "super_admin")


def _format_timestamp(value) -> str:
    if value is None:
        return "—"
    return str(value)


def render_user_administration(
    actor_user_id: str | None,
    actor_role: str | None,
) -> None:
    """Render the user directory and super-admin account controls."""

    if actor_role not in {"admin", "super_admin"}:
        st.error("You do not have permission to access user administration.")
        return

    if not isinstance(actor_user_id, str) or not actor_user_id.strip():
        st.error("Your account could not be verified. Sign in again.")
        return

    st.title("User Administration")
    st.caption(
        "Review platform accounts, verification status and access. "
        "Administrative changes are recorded in the audit log."
    )

    try:
        users = list_users(actor_role=actor_role, limit=1000)
    except Exception:
        st.error("The platform user directory is temporarily unavailable.")
        return

    if not users:
        st.info("No user accounts have been registered yet.")
        return

    total = len(users)
    active = sum(bool(user["is_active"]) for user in users)
    verified = sum(bool(user["email_verified"]) for user in users)
    super_admins = sum(user["role"] == "super_admin" for user in users)

    metrics = st.columns(4)
    metrics[0].metric("Accounts", total)
    metrics[1].metric("Active", active)
    metrics[2].metric("Email verified", verified)
    metrics[3].metric("Super admins", super_admins)

    st.divider()
    st.subheader("Platform user directory")

    filters = st.columns([2, 1, 1])
    search_text = filters[0].text_input(
        "Search name, username or email",
        key="user_admin_search",
    ).strip().casefold()
    role_filter = filters[1].selectbox(
        "Platform role",
        options=["All", *PLATFORM_ROLES],
        key="user_admin_role_filter",
    )
    status_filter = filters[2].selectbox(
        "Account status",
        options=["All", "Active", "Inactive", "Verified", "Unverified"],
        key="user_admin_status_filter",
    )

    filtered_users = []
    for user in users:
        searchable = " ".join(
            str(user.get(field) or "")
            for field in ("full_name", "username", "email")
        ).casefold()
        if search_text and search_text not in searchable:
            continue
        if role_filter != "All" and user["role"] != role_filter:
            continue
        if status_filter == "Active" and not bool(user["is_active"]):
            continue
        if status_filter == "Inactive" and bool(user["is_active"]):
            continue
        if status_filter == "Verified" and not bool(user["email_verified"]):
            continue
        if status_filter == "Unverified" and bool(user["email_verified"]):
            continue
        filtered_users.append(user)

    display_rows = [
        {
            "Name": user["full_name"],
            "Username": user["username"],
            "Email": user["email"],
            "Role": user["role"],
            "Active": bool(user["is_active"]),
            "Email verified": bool(user["email_verified"]),
            "Created": _format_timestamp(user["created_at"]),
            "Last updated": _format_timestamp(user["updated_at"]),
        }
        for user in filtered_users
    ]
    st.dataframe(
        pd.DataFrame(display_rows),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"Showing {len(filtered_users)} of {total} accounts. "
        "The directory is limited to the 1,000 most recently created accounts."
    )

    st.divider()
    st.subheader("Account details and access controls")
    user_options = [user["id"] for user in filtered_users]
    if not user_options:
        st.info("No accounts match the current filters.")
    else:
        selected_user_id = st.selectbox(
            "Select an account",
            options=user_options,
            format_func=lambda user_id: next(
                (
                    f"{user['full_name']} · {user['username']} · {user['role']}"
                    for user in filtered_users
                    if user["id"] == user_id
                ),
                user_id,
            ),
            key="user_admin_selected_id",
        )
        selected = next(
            user for user in filtered_users if user["id"] == selected_user_id
        )

        detail_cols = st.columns(3)
        detail_cols[0].write(f"**Full name**\n\n{selected['full_name']}")
        detail_cols[1].write(f"**Email**\n\n{selected['email']}")
        detail_cols[2].write(
            f"**Email verification**\n\n"
            f"{'Verified' if selected['email_verified'] else 'Not verified'}"
        )

        if actor_role == "super_admin":
            st.markdown("**Change platform role**")
            with st.form("user_admin_role_form"):
                selected_role = st.selectbox(
                    "New role",
                    options=PLATFORM_ROLES,
                    index=PLATFORM_ROLES.index(selected["role"]),
                )
                role_submitted = st.form_submit_button(
                    "Save role",
                    type="primary",
                )
            if role_submitted:
                try:
                    change_user_role(
                        actor_role=actor_role,
                        actor_user_id=actor_user_id,
                        target_user_id=selected_user_id,
                        new_role=selected_role,
                    )
                    st.success("Account role updated. Existing sessions were revoked.")
                    st.rerun()
                except (PermissionError, ValueError) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The role change could not be completed.")

            st.markdown("**Account access**")
            with st.form("user_admin_status_form"):
                desired_active = st.checkbox(
                    "Account is active",
                    value=bool(selected["is_active"]),
                    help="Deactivating an account revokes its existing sessions.",
                )
                status_submitted = st.form_submit_button("Save account status")
            if status_submitted:
                try:
                    set_user_active_status(
                        actor_role=actor_role,
                        actor_user_id=actor_user_id,
                        target_user_id=selected_user_id,
                        is_active=desired_active,
                    )
                    st.success("Account status updated. Existing sessions were revoked.")
                    st.rerun()
                except (PermissionError, ValueError) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The account status change could not be completed.")
        else:
            st.info(
                "Your administrator role allows you to review accounts. "
                "Only a super administrator can change platform roles or account status."
            )

    st.divider()
    st.subheader("Recent administrative activity")
    try:
        events = list_audit_events(
            requested_by_role=actor_role,
            limit=100,
        )
        if events:
            audit_rows = []
            for event in events:
                details = event.get("details")
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except (TypeError, ValueError):
                        pass
                audit_rows.append(
                    {
                        "Date": _format_timestamp(event.get("created_at")),
                        "Action": event.get("action"),
                        "Actor user ID": event.get("user_id"),
                        "Target user ID": event.get("resource_id"),
                        "Details": (
                            json.dumps(details, ensure_ascii=False)
                            if isinstance(details, (dict, list))
                            else details
                        ),
                    }
                )
            st.dataframe(
                pd.DataFrame(audit_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No audit events have been recorded yet.")
    except Exception:
        st.warning("Audit history is temporarily unavailable.")
