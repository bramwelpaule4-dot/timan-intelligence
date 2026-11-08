"""Read-only subscription and plan overview for TimanStat users."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from timan_intelligence.entitlements.plans import PLAN_CATALOG
from timan_intelligence.billing.records import BillingError, get_invoice, list_invoices
from timan_intelligence.billing.daraja import DarajaError, initiate_mpesa_payment
from timan_intelligence.billing.invoice_pdf import build_invoice_pdf
from timan_intelligence.entitlements.service import (
    get_effective_entitlements,
    get_monthly_usage,
)
from timan_intelligence.entitlements.subscriptions import (
    get_subscription,
    get_subscription_history,
    request_plan_change,
    list_plan_change_requests,
    cancel_plan_change_request,
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

    st.subheader("Change your plan")
    st.caption(
        "Submit an upgrade or downgrade request for administrator review. "
        "Approvals do not activate a paid plan until payment is confirmed."
    )
    available_plans = [
        code for code in PLAN_CATALOG
        if code != plan_code
    ]
    with st.form("customer_plan_change_form"):
        requested_plan = st.selectbox(
            "Requested plan",
            options=available_plans,
            format_func=lambda code: PLAN_CATALOG[code].name,
        )
        request_confirmed = st.checkbox(
            "I understand this is a request and my current access will not change immediately."
        )
        request_submitted = st.form_submit_button("Submit plan-change request")
    if request_submitted:
        if not request_confirmed:
            st.error("Confirm that you understand the plan-change process.")
        else:
            try:
                request_plan_change(
                    requested_by=user_id,
                    requested_plan_code=requested_plan,
                    user_id=user_id if not organisation_id else None,
                    organisation_id=organisation_id,
                )
                st.success("Your plan-change request has been submitted for review.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    try:
        change_requests = list_plan_change_requests(
            user_id=user_id if not organisation_id else None,
            organisation_id=organisation_id,
            limit=50,
        )
    except Exception:
        change_requests = []
        st.warning("Plan-change requests could not be loaded.")
    if change_requests:
        st.subheader("Plan-change requests")
        request_rows = [
            {
                "Requested plan": PLAN_CATALOG[item["requested_plan_code"]].name,
                "Change": item["change_type"].title(),
                "Status": item["status"].replace("_", " ").title(),
                "Submitted": item.get("created_at"),
                "Effective date": item.get("effective_at") or "To be determined",
            }
            for item in change_requests
        ]
        st.dataframe(pd.DataFrame(request_rows), hide_index=True, use_container_width=True)
        for item in change_requests:
            if item["status"] == "pending" and item["requested_by"] == user_id:
                if st.button(
                    "Withdraw pending request",
                    key=f"withdraw_plan_change_{item['id']}",
                ):
                    if cancel_plan_change_request(item["id"], requested_by=user_id):
                        st.success("The pending request was withdrawn.")
                        st.rerun()
                    else:
                        st.error("The request could not be withdrawn.")

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

    st.subheader("Invoices & payment history")
    st.caption(
        "Review invoices issued to this account or workspace, outstanding balances, "
        "and recorded payment attempts. Payment confirmation is handled by trusted "
        "billing services; this page cannot mark an invoice as paid."
    )
    try:
        invoices = list_invoices(
            user_id=user_id if not organisation_id else None,
            organisation_id=organisation_id,
            limit=100,
        )
    except BillingError:
        invoices = []
        st.error("Billing records could not be loaded for this workspace.")
    except Exception:
        invoices = []
        st.error("Billing information is temporarily unavailable.")

    if invoices:
        outstanding_minor = sum(
            max(0, int(item["total_minor"]) - int(item["amount_paid_minor"]))
            for item in invoices
            if item["status"] in {"open", "overdue"}
        )
        unpaid_count = sum(
            item["status"] in {"open", "overdue"} for item in invoices
        )
        invoice_metrics = st.columns(3)
        invoice_metrics[0].metric("Invoices", f"{len(invoices):,}")
        invoice_metrics[1].metric("Outstanding invoices", f"{unpaid_count:,}")
        invoice_metrics[2].metric(
            "Outstanding balance (minor units)",
            f"{outstanding_minor:,}",
        )
        invoice_rows = [
            {
                "Invoice": item["invoice_number"],
                "Issued": _format_timestamp(item.get("issued_at")),
                "Due": _format_timestamp(item.get("due_at")),
                "Currency": item["currency"],
                "Total (minor units)": int(item["total_minor"]),
                "Paid (minor units)": int(item["amount_paid_minor"]),
                "Balance (minor units)": max(
                    0, int(item["total_minor"]) - int(item["amount_paid_minor"])
                ),
                "Status": str(item["status"]).replace("_", " ").title(),
            }
            for item in invoices
        ]
        st.dataframe(
            pd.DataFrame(invoice_rows),
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "Amounts are shown in the invoice currency's minor units "
            "(for example, cents). No currency conversion is performed."
        )
        for summary in invoices:
            with st.expander(
                f"{summary['invoice_number']} · {summary['currency']} "
                f"{int(summary['total_minor']):,} · {str(summary['status']).title()}"
            ):
                try:
                    detail = get_invoice(
                        summary["id"],
                        user_id=user_id if not organisation_id else None,
                        organisation_id=organisation_id,
                    )
                except Exception:
                    detail = None
                if detail is None:
                    st.warning("Invoice details are temporarily unavailable.")
                    continue

                try:
                    pdf_bytes = build_invoice_pdf(detail)
                    st.download_button(
                        "Download invoice (PDF)",
                        data=pdf_bytes,
                        file_name=f"{detail['invoice_number']}.pdf",
                        mime="application/pdf",
                        key=f"download_invoice_pdf_{detail['id']}",
                    )
                except Exception:
                    st.warning("The invoice PDF could not be generated. Please try again later.")

                # Kenyan M-Pesa checkout is available only for open KES invoices.
                outstanding_minor = max(
                    0, int(detail["total_minor"]) - int(detail["amount_paid_minor"])
                )
                if detail["status"] == "open" and detail["currency"] == "KES" and outstanding_minor > 0 and outstanding_minor % 100 == 0:
                    st.markdown("**Pay this invoice with M-Pesa**")
                    st.caption(
                        "Enter the Kenyan mobile number that should receive the "
                        "STK Push prompt. The outstanding balance is requested in KES."
                    )
                    with st.form(f"mpesa_checkout_form_{detail['id']}"):
                        mpesa_phone = st.text_input(
                            "M-Pesa phone number",
                            placeholder="0712345678 or 254712345678",
                            key=f"mpesa_phone_{detail['id']}",
                            max_chars=20,
                        )
                        mpesa_submitted = st.form_submit_button(
                            f"Pay KES {outstanding_minor // 100:,} with M-Pesa",
                            type="primary",
                            use_container_width=True,
                        )
                    if mpesa_submitted:
                        if not mpesa_phone.strip():
                            st.error("Enter the phone number to receive the M-Pesa prompt.")
                        else:
                            try:
                                with st.spinner("Sending the M-Pesa payment prompt..."):
                                    checkout = initiate_mpesa_payment(
                                        detail["id"],
                                        mpesa_phone.strip(),
                                        user_id=user_id if not organisation_id else None,
                                        organisation_id=organisation_id,
                                    )
                                st.success(
                                    "M-Pesa prompt accepted. Check the phone and enter "
                                    "your M-Pesa PIN to authorise payment."
                                )
                                st.info(
                                    "Payment status: Pending. The invoice will update "
                                    "only after the payment is confirmed by the billing service."
                                )
                                st.caption(
                                    f"Checkout reference: {checkout['checkout_request_id']}"
                                )
                            except DarajaError as exc:
                                st.error(str(exc))
                            except BillingError as exc:
                                st.error(str(exc))
                            except Exception:
                                st.error(
                                    "The M-Pesa request could not be completed. "
                                    "Check the billing service configuration and try again."
                                )
                elif detail["status"] == "open" and detail["currency"] == "KES" and outstanding_minor > 0:
                    st.info(
                        "M-Pesa requires a whole-shilling balance. Use another "
                        "available payment method for this invoice."
                    )

                st.markdown("**Invoice items**")
                item_rows = [
                    {
                        "Description": line["description"],
                        "Quantity": int(line["quantity"]),
                        "Unit amount (minor units)": int(line["unit_amount_minor"]),
                        "Line total (minor units)": int(line["line_total_minor"]),
                        "Service period start": _format_timestamp(line.get("period_start")),
                        "Service period end": _format_timestamp(line.get("period_end")),
                    }
                    for line in detail["items"]
                ]
                st.dataframe(
                    pd.DataFrame(item_rows),
                    hide_index=True,
                    use_container_width=True,
                )

                st.markdown("**Payment attempts**")
                if detail["payments"]:
                    payment_rows = [
                        {
                            "Date": _format_timestamp(payment.get("created_at")),
                            "Provider": payment["provider_code"],
                            "Method": payment.get("payment_method") or "Not specified",
                            "Amount (minor units)": int(payment["amount_minor"]),
                            "Currency": payment["currency"],
                            "Status": str(payment["status"]).title(),
                            "Reference": payment.get("provider_reference") or "Not available",
                        }
                        for payment in detail["payments"]
                    ]
                    st.dataframe(
                        pd.DataFrame(payment_rows),
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.caption("No payment attempts have been recorded.")

                st.markdown("**Billing activity**")
                if detail["events"]:
                    event_rows = [
                        {
                            "Date": _format_timestamp(event.get("created_at")),
                            "Event": str(event["event_type"]).replace(".", " ").replace("_", " ").title(),
                            "Previous status": event.get("previous_status") or "—",
                            "New status": event.get("new_status") or "—",
                        }
                        for event in detail["events"]
                    ]
                    st.dataframe(
                        pd.DataFrame(event_rows),
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.caption("No additional billing activity is recorded.")
    else:
        st.info("No invoices or payment attempts are recorded for this account or workspace.")

    st.caption(
        "Plan upgrades are activated only after full payment is confirmed by a trusted "
        "backend payment process. This page is read-only and does not accept or verify payments."
    )
