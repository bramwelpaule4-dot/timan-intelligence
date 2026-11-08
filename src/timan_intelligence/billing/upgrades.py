"""Create and fulfil invoices for approved subscription upgrades."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from timan_intelligence.billing.records import BillingError, create_invoice, issue_invoice
from timan_intelligence.database.connection import database_connection, get_database_type


def create_upgrade_invoice(
    request_id: str,
    *,
    amount_minor: int,
    currency: str,
    period_start: str,
    period_end: str,
    due_at: str | None = None,
    actor_user_id: str | None = None,
) -> str:
    """Create and issue an invoice for one approved upgrade.

    Price, currency and service period are explicit trusted inputs. This
    function never chooses a price or billing term.
    """
    if not isinstance(request_id, str) or not request_id.strip():
        raise BillingError("A valid subscription change request ID is required.")
    if not isinstance(period_start, str) or not period_start.strip():
        raise BillingError("A subscription period start is required.")
    if not isinstance(period_end, str) or not period_end.strip():
        raise BillingError("A subscription period end is required.")
    p = "%s" if get_database_type() == "postgresql" else "?"
    with database_connection() as connection:
        request = connection.execute(
            f"SELECT * FROM subscription_change_requests WHERE id = {p}",
            (request_id.strip(),),
        ).fetchone()
    if request is None or request["status"] != "approved_pending_payment":
        raise BillingError("Only an approved upgrade awaiting payment can be invoiced.")
    request = dict(request)
    if request.get("user_id"):
        owner = {"user_id": request["user_id"]}
    else:
        owner = {"organisation_id": request["organisation_id"]}
    invoice_id = create_invoice(
        **owner,
        subscription_change_request_id=request_id.strip(),
        currency=currency,
        due_at=due_at,
        actor_user_id=actor_user_id,
        items=[{
            "description": f"{request['requested_plan_code'].title()} subscription upgrade",
            "plan_code": request["requested_plan_code"],
            "quantity": 1,
            "unit_amount_minor": amount_minor,
            "period_start": period_start,
            "period_end": period_end,
        }],
    )
    issue_invoice(invoice_id, actor_user_id=actor_user_id)
    return invoice_id


def fulfil_paid_upgrade(connection, invoice_id: str, now: str) -> bool:
    """Activate an upgrade in the same transaction that settles its invoice."""
    p = "%s" if get_database_type() == "postgresql" else "?"
    invoice = connection.execute(
        f"SELECT * FROM billing_invoices WHERE id = {p}",
        (invoice_id,),
    ).fetchone()
    if invoice is None or invoice["status"] != "paid":
        return False
    invoice = dict(invoice)
    request_id = invoice.get("subscription_change_request_id")
    if not request_id:
        return False
    request = connection.execute(
        f"SELECT * FROM subscription_change_requests WHERE id = {p}",
        (request_id,),
    ).fetchone()
    if request is None:
        raise BillingError("The invoice's subscription change request was not found.")
    request = dict(request)
    if request["status"] == "completed":
        return True
    if request["status"] != "approved_pending_payment":
        raise BillingError("The linked upgrade request is no longer awaiting payment.")
    owner_column = "user_id" if request.get("user_id") else "organisation_id"
    owner_id = request[owner_column]
    if invoice.get(owner_column) != owner_id:
        raise BillingError("The paid invoice owner does not match the upgrade request.")
    items = connection.execute(
        f"""
        SELECT plan_code, period_start, period_end
        FROM billing_invoice_items
        WHERE invoice_id = {p} AND plan_code = {p}
        ORDER BY line_number, created_at, id
        """,
        (invoice_id, request["requested_plan_code"]),
    ).fetchall()
    if len(items) != 1 or not items[0]["period_start"] or not items[0]["period_end"]:
        raise BillingError("A paid upgrade invoice must contain one requested plan and a defined service period.")
    period = dict(items[0])
    start, end = period["period_start"], period["period_end"]
    current = connection.execute(
        f"""
        SELECT id FROM subscriptions
        WHERE {owner_column} = {p}
          AND status IN ('trialing', 'active', 'past_due')
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (owner_id,),
    ).fetchone()
    if current is not None:
        connection.execute(
            f"""
            UPDATE subscriptions
            SET status = 'expired', updated_at = {p}
            WHERE id = {p} AND status IN ('trialing', 'active', 'past_due')
            """,
            (now, current["id"]),
        )
    subscription_id = str(uuid.uuid4())
    connection.execute(
        f"""
        INSERT INTO subscriptions (
            id, {owner_column}, plan_code, status, started_at,
            current_period_start, current_period_end, cancel_at_period_end
        )
        VALUES ({p}, {p}, {p}, 'active', {p}, {p}, {p}, FALSE)
        """,
        (subscription_id, owner_id, request["requested_plan_code"], now, start, end),
    )
    changed = connection.execute(
        f"""
        UPDATE subscription_change_requests
        SET status = 'completed', updated_at = {p}
        WHERE id = {p} AND status = 'approved_pending_payment'
        """,
        (now, request_id),
    )
    if changed.rowcount != 1:
        raise BillingError("The upgrade request changed while activation was in progress.")
    from timan_intelligence.billing.records import _event
    _event(
        connection,
        event_type="subscription.upgrade_activated",
        invoice_id=invoice_id,
        actor_user_id=None,
        previous_status="approved_pending_payment",
        new_status="completed",
        details=f"subscription_id={subscription_id};plan_code={request['requested_plan_code']}",
    )
    return True
