"""Finalize pending payment attempts after trusted backend confirmation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from timan_intelligence.billing.records import BillingError, _event, _p
from timan_intelligence.database.connection import database_connection


def finalize_payment_transaction(
    payment_id: str,
    *,
    status: str,
    provider_reference: str | None = None,
    failure_code: str | None = None,
    failure_message: str | None = None,
    actor_user_id: str | None = None,
) -> bool:
    """Finalize a created/pending attempt and update invoice balance atomically.

    This is a trusted backend operation. A future gateway adapter/webhook must
    authenticate provider notifications before invoking it.
    """
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise BillingError("A valid payment transaction ID is required.")
    if status not in {"succeeded", "failed", "canceled"}:
        raise BillingError("Final status must be succeeded, failed, or canceled.")
    for value, field, maximum in (
        (provider_reference, "provider_reference", 200),
        (failure_code, "failure_code", 100),
        (failure_message, "failure_message", 500),
    ):
        if value is not None and (not isinstance(value, str) or len(value) > maximum):
            raise BillingError(f"{field} must not exceed {maximum} characters.")

    p = _p()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_connection() as connection:
        payment = connection.execute(
            f"SELECT * FROM payment_transactions WHERE id = {p}",
            (payment_id.strip(),),
        ).fetchone()
        if payment is None:
            raise BillingError("Payment transaction was not found.")
        payment = dict(payment)
        if payment["status"] not in {"created", "pending"}:
            if payment["status"] == status:
                return True
            raise BillingError("A finalized payment cannot be changed.")

        invoice = connection.execute(
            f"SELECT * FROM billing_invoices WHERE id = {p}",
            (payment["invoice_id"],),
        ).fetchone()
        if invoice is None or invoice["status"] != "open":
            raise BillingError("The related invoice is not open.")

        paid_after = int(invoice["amount_paid_minor"])
        if status == "succeeded":
            paid_after += int(payment["amount_minor"])
            if paid_after > int(invoice["total_minor"]):
                raise BillingError("Payment exceeds the invoice's outstanding balance.")

        changed = connection.execute(
            f"""
            UPDATE payment_transactions
            SET status = {p}, provider_reference = COALESCE({p}, provider_reference),
                failure_code = {p}, failure_message = {p},
                completed_at = {p}, updated_at = {p}
            WHERE id = {p} AND status IN ('created', 'pending')
            """,
            (
                status, provider_reference, failure_code, failure_message,
                now, now, payment_id.strip(),
            ),
        )
        if changed.rowcount != 1:
            raise BillingError("Payment changed while finalization was in progress.")

        _event(
            connection, event_type=f"payment.{status}",
            payment_id=payment_id.strip(), actor_user_id=actor_user_id,
            provider_code=payment["provider_code"],
            provider_event_id=provider_reference,
            previous_status=payment["status"], new_status=status,
        )
        if status == "succeeded":
            invoice_status = "paid" if paid_after == int(invoice["total_minor"]) else "open"
            connection.execute(
                f"""
                UPDATE billing_invoices
                SET amount_paid_minor = {p}, status = {p},
                    paid_at = CASE WHEN {p} = 'paid' THEN {p} ELSE paid_at END,
                    updated_at = {p}
                WHERE id = {p} AND status = 'open'
                """,
                (paid_after, invoice_status, invoice_status, invoice_status, now, payment["invoice_id"]),
            )
    return True
