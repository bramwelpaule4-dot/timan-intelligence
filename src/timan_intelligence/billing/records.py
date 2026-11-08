"""Provider-neutral invoice and payment ledger operations for TimanStat.

This module persists billing facts. It does not contact a payment gateway,
store payment credentials, or grant subscription entitlements.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from timan_intelligence.database.connection import database_connection, get_database_type


class BillingError(ValueError):
    """Raised when a billing ledger operation is invalid."""


def _p() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


def _owner(user_id: str | None, organisation_id: str | None) -> tuple[str, str]:
    has_user = isinstance(user_id, str) and bool(user_id.strip())
    has_org = isinstance(organisation_id, str) and bool(organisation_id.strip())
    if has_user == has_org:
        raise BillingError("Provide exactly one user ID or organisation ID.")
    return ("user_id", user_id.strip()) if has_user else ("organisation_id", organisation_id.strip())


def _currency(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        raise BillingError("Currency must be a three-letter ISO currency code.")
    return value.strip().upper()


def _amount(value: Any, field: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BillingError(f"{field} must be an integer in minor currency units.")
    if value < 0 or (positive and value == 0):
        raise BillingError(f"{field} must be {'positive' if positive else 'non-negative'}.")
    return value


def _time(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise BillingError(f"{field} must be an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise BillingError(f"{field} must be an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _event(
    connection,
    *,
    event_type: str,
    invoice_id: str | None = None,
    payment_id: str | None = None,
    actor_user_id: str | None = None,
    provider_code: str | None = None,
    provider_event_id: str | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    details: str | None = None,
) -> None:
    p = _p()
    connection.execute(
        f"""
        INSERT INTO billing_events (
            id, invoice_id, payment_transaction_id, event_type,
            previous_status, new_status, actor_user_id,
            provider_code, provider_event_id, details
        )
        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
        """,
        (
            str(uuid.uuid4()), invoice_id, payment_id, event_type,
            previous_status, new_status, actor_user_id,
            provider_code, provider_event_id, details,
        ),
    )


def create_invoice(
    *,
    items: list[dict[str, Any]],
    user_id: str | None = None,
    organisation_id: str | None = None,
    subscription_id: str | None = None,
    subscription_change_request_id: str | None = None,
    currency: str = "USD",
    tax_minor: int = 0,
    due_at: str | None = None,
    actor_user_id: str | None = None,
) -> str:
    """Create a draft invoice and its line items atomically."""
    owner_column, owner_id = _owner(user_id, organisation_id)
    if not isinstance(items, list) or not items:
        raise BillingError("At least one invoice item is required.")
    currency_code = _currency(currency)
    tax = _amount(tax_minor, "tax_minor")
    due = _time(due_at, "due_at")
    if actor_user_id is not None and (
        not isinstance(actor_user_id, str) or not actor_user_id.strip()
    ):
        raise BillingError("actor_user_id must be a valid user ID.")

    normalized = []
    subtotal = 0
    for item in items:
        if not isinstance(item, dict):
            raise BillingError("Each invoice item must be a mapping.")
        label = item.get("description")
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 500:
            raise BillingError("Each invoice item needs a description of 1–500 characters.")
        quantity = item.get("quantity", 1)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise BillingError("Item quantity must be a positive integer.")
        unit = _amount(item.get("unit_amount_minor"), "unit_amount_minor")
        line_total = quantity * unit
        subtotal += line_total
        if subtotal > 9_000_000_000_000_000:
            raise BillingError("Invoice amount exceeds the supported range.")
        plan_code = item.get("plan_code")
        if plan_code is not None and (
            not isinstance(plan_code, str) or len(plan_code) > 50
        ):
            raise BillingError("plan_code must not exceed 50 characters.")
        start = _time(item.get("period_start"), "period_start")
        end = _time(item.get("period_end"), "period_end")
        if start and end and datetime.fromisoformat(end) <= datetime.fromisoformat(start):
            raise BillingError("Invoice item period_end must follow period_start.")
        normalized.append((label.strip(), plan_code, quantity, unit, line_total, start, end))

    total = subtotal + tax
    if total > 9_000_000_000_000_000:
        raise BillingError("Invoice total exceeds the supported range.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    invoice_id = str(uuid.uuid4())
    invoice_number = f"TS-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"
    p = _p()

    with database_connection() as connection:
        owner_table = "users" if owner_column == "user_id" else "organisations"
        owner_active = "is_active = TRUE" if owner_column == "user_id" else "status = 'active'"
        exists = connection.execute(
            f"SELECT id FROM {owner_table} WHERE id = {p} AND {owner_active}",
            (owner_id,),
        ).fetchone()
        if exists is None:
            raise BillingError("Invoice owner does not exist or is inactive.")
        if actor_user_id:
            actor = connection.execute(
                f"SELECT id FROM users WHERE id = {p} AND is_active = TRUE",
                (actor_user_id.strip(),),
            ).fetchone()
            if actor is None:
                raise BillingError("The acting user does not exist or is inactive.")
        if subscription_id:
            subscription = connection.execute(
                f"""
                SELECT id FROM subscriptions
                WHERE id = {p} AND {owner_column} = {p}
                """,
                (subscription_id, owner_id),
            ).fetchone()
            if subscription is None:
                raise BillingError("Subscription does not belong to the invoice owner.")
        if subscription_change_request_id:
            request = connection.execute(
                f"""
                SELECT id, requested_plan_code, status, user_id, organisation_id
                FROM subscription_change_requests
                WHERE id = {p}
                """,
                (subscription_change_request_id.strip(),),
            ).fetchone()
            if (
                request is None
                or request["status"] != "approved_pending_payment"
                or request[owner_column] != owner_id
            ):
                raise BillingError("Invoice must reference an approved upgrade request for the same owner.")
            if not any(item[1] == request["requested_plan_code"] for item in normalized):
                raise BillingError("Invoice items must include the requested subscription plan.")
        connection.execute(
            f"""
            INSERT INTO billing_invoices (
                id, invoice_number, {owner_column}, subscription_id,
                subscription_change_request_id, status, currency,
                subtotal_minor, tax_minor, total_minor, due_at,
                created_at, updated_at
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, 'draft', {p}, {p}, {p}, {p}, {p}, {p}, {p})
            """,
            (
                invoice_id, invoice_number, owner_id, subscription_id,
                subscription_change_request_id.strip() if subscription_change_request_id else None,
                currency_code, subtotal, tax, total, due, now, now,
            ),
        )
        for line_number, (label, plan, quantity, unit, line_total, start, end) in enumerate(normalized, start=1):
            connection.execute(
                f"""
                INSERT INTO billing_invoice_items (
                    id, invoice_id, description, plan_code, quantity,
                    unit_amount_minor, line_total_minor, period_start, period_end,
                    line_number
                )
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """,
                (
                    str(uuid.uuid4()), invoice_id, label, plan, quantity,
                    unit, line_total, start, end, line_number,
                ),
            )
        _event(
            connection, event_type="invoice.created", invoice_id=invoice_id,
            actor_user_id=actor_user_id.strip() if actor_user_id else None,
            previous_status=None, new_status="draft",
        )
    return invoice_id


def issue_invoice(invoice_id: str, *, actor_user_id: str | None = None) -> bool:
    """Issue a draft invoice, making it eligible for payment attempts."""
    if not isinstance(invoice_id, str) or not invoice_id.strip():
        raise BillingError("A valid invoice ID is required.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p = _p()
    with database_connection() as connection:
        result = connection.execute(
            f"""
            UPDATE billing_invoices
            SET status = 'open', issued_at = {p}, updated_at = {p}
            WHERE id = {p} AND status = 'draft'
            """,
            (now, now, invoice_id.strip()),
        )
        if result.rowcount != 1:
            raise BillingError("Only a draft invoice can be issued.")
        _event(
            connection, event_type="invoice.issued", invoice_id=invoice_id.strip(),
            actor_user_id=actor_user_id, previous_status="draft", new_status="open",
        )
    return True


def record_payment_transaction(
    invoice_id: str,
    *,
    amount_minor: int,
    currency: str,
    provider_code: str,
    status: str = "pending",
    idempotency_key: str | None = None,
    provider_reference: str | None = None,
    payment_method: str | None = None,
    actor_user_id: str | None = None,
    failure_code: str | None = None,
    failure_message: str | None = None,
) -> str:
    """Record a payment attempt. Successful payments update the invoice ledger."""
    amount = _amount(amount_minor, "amount_minor", positive=True)
    currency_code = _currency(currency)
    if status not in {"created", "pending", "succeeded", "failed", "canceled"}:
        raise BillingError("Unsupported initial payment status.")
    if not isinstance(provider_code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", provider_code.strip()):
        raise BillingError("provider_code must be a 2–40 character identifier.")
    if idempotency_key is not None and (
        not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key.strip()) <= 128
    ):
        raise BillingError("Idempotency key must contain 8–128 characters.")
    if provider_reference is not None and len(provider_reference) > 200:
        raise BillingError("Provider reference must not exceed 200 characters.")
    if failure_code is not None and len(failure_code) > 100:
        raise BillingError("Failure code must not exceed 100 characters.")
    if failure_message is not None and len(failure_message) > 500:
        raise BillingError("Failure message must not exceed 500 characters.")

    p = _p()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payment_id = str(uuid.uuid4())
    provider = provider_code.strip().lower()
    with database_connection() as connection:
        if idempotency_key:
            existing = connection.execute(
                f"SELECT * FROM payment_transactions WHERE idempotency_key = {p}",
                (idempotency_key.strip(),),
            ).fetchone()
            if existing is not None:
                existing = dict(existing)
                if (
                    existing["invoice_id"] == invoice_id.strip()
                    and int(existing["amount_minor"]) == amount
                    and existing["currency"] == currency_code
                    and existing["provider_code"] == provider
                ):
                    return existing["id"]
                raise BillingError("Idempotency key was already used for another payment.")
        invoice = connection.execute(
            f"SELECT * FROM billing_invoices WHERE id = {p}",
            (invoice_id.strip(),),
        ).fetchone()
        if invoice is None or invoice["status"] != "open":
            raise BillingError("Payments require an open invoice.")
        if invoice["currency"] != currency_code:
            raise BillingError("Payment currency must match the invoice currency.")
        if status == "succeeded" and int(invoice["amount_paid_minor"]) + amount > int(invoice["total_minor"]):
            raise BillingError("Payment exceeds the invoice's outstanding balance.")
        connection.execute(
            f"""
            INSERT INTO payment_transactions (
                id, invoice_id, provider_code, provider_reference,
                idempotency_key, payment_method, status, amount_minor,
                currency, failure_code, failure_message, completed_at,
                created_at, updated_at
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            """,
            (
                payment_id, invoice_id.strip(), provider,
                provider_reference, idempotency_key.strip() if idempotency_key else None,
                payment_method, status, amount, currency_code, failure_code,
                failure_message, now if status in {"succeeded", "failed", "canceled"} else None,
                now, now,
            ),
        )
        _event(
            connection, event_type=f"payment.{status}", payment_id=payment_id,
            actor_user_id=actor_user_id, provider_code=provider,
            provider_event_id=provider_reference,
            previous_status=None, new_status=status,
        )
        if status == "succeeded":
            paid_after = int(invoice["amount_paid_minor"]) + amount
            new_status = "paid" if paid_after == int(invoice["total_minor"]) else "open"
            connection.execute(
                f"""
                UPDATE billing_invoices
                SET amount_paid_minor = {p}, status = {p},
                    paid_at = CASE WHEN {p} = 'paid' THEN {p} ELSE paid_at END,
                    updated_at = {p}
                WHERE id = {p} AND status = 'open'
                """,
                (paid_after, new_status, new_status, now, now, invoice_id.strip()),
            )
    return payment_id


def get_invoice(invoice_id: str) -> dict[str, Any] | None:
    """Fetch invoice, itemised charges, and payment attempts."""
    if not isinstance(invoice_id, str) or not invoice_id.strip():
        raise BillingError("A valid invoice ID is required.")
    p = _p()
    with database_connection() as connection:
        invoice = connection.execute(
            f"SELECT * FROM billing_invoices WHERE id = {p}", (invoice_id.strip(),)
        ).fetchone()
        if invoice is None:
            return None
        items = connection.execute(
            f"SELECT * FROM billing_invoice_items WHERE invoice_id = {p} ORDER BY line_number, created_at, id",
            (invoice_id.strip(),),
        ).fetchall()
        payments = connection.execute(
            f"SELECT * FROM payment_transactions WHERE invoice_id = {p} ORDER BY created_at, id",
            (invoice_id.strip(),),
        ).fetchall()
        events = connection.execute(
            f"""
            SELECT * FROM billing_events
            WHERE invoice_id = {p}
               OR payment_transaction_id IN (
                   SELECT id FROM payment_transactions WHERE invoice_id = {p}
               )
            ORDER BY created_at, id
            """,
            (invoice_id.strip(), invoice_id.strip()),
        ).fetchall()
    result = dict(invoice)
    result["items"] = [dict(row) for row in items]
    result["payments"] = [dict(row) for row in payments]
    result["events"] = [dict(row) for row in events]
    return result


def list_invoices(
    *,
    user_id: str | None = None,
    organisation_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List invoices for one account owner."""
    owner_column, owner_id = _owner(user_id, organisation_id)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise BillingError("limit must be between 1 and 1000.")
    p = _p()
    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM billing_invoices
            WHERE {owner_column} = {p}
            ORDER BY created_at DESC, id DESC
            LIMIT {p}
            """,
            (owner_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]
