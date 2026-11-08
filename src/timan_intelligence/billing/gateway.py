"""Provider-neutral payment gateway contracts and orchestration.

Adapters own provider API calls and webhook signature verification. Browser
redirects are never accepted as proof of payment.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol
from urllib.parse import urlparse

from timan_intelligence.billing.records import BillingError, _p, get_invoice, record_payment_transaction
from timan_intelligence.billing.settlement import finalize_payment_transaction
from timan_intelligence.database.connection import database_connection


@dataclass(frozen=True)
class CheckoutRequest:
    payment_transaction_id: str
    invoice_number: str
    amount_minor: int
    currency: str
    idempotency_key: str
    return_url: str
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class CheckoutResponse:
    provider_checkout_id: str
    checkout_url: str
    expires_at: str | None = None


@dataclass(frozen=True)
class PaymentNotification:
    provider_event_id: str
    payment_transaction_id: str
    status: str
    amount_minor: int
    currency: str
    provider_reference: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class PaymentGatewayAdapter(Protocol):
    provider_code: str

    def create_checkout(self, request: CheckoutRequest) -> CheckoutResponse:
        """Create a hosted checkout session using provider APIs."""

    def verify_webhook(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> PaymentNotification:
        """Verify authenticity and return a normalized payment notification."""


_ADAPTERS: dict[str, PaymentGatewayAdapter] = {}


def register_gateway(adapter: PaymentGatewayAdapter) -> None:
    code = getattr(adapter, "provider_code", None)
    if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_-]{2,40}", code):
        raise BillingError("Gateway provider_code must be a lowercase identifier.")
    if not callable(getattr(adapter, "create_checkout", None)) or not callable(
        getattr(adapter, "verify_webhook", None)
    ):
        raise BillingError("Gateway adapter must implement checkout and webhook verification.")
    _ADAPTERS[code] = adapter


def get_gateway(provider_code: str) -> PaymentGatewayAdapter:
    adapter = _ADAPTERS.get(str(provider_code).strip().lower())
    if adapter is None:
        raise BillingError("Payment gateway is not configured.")
    return adapter


def initiate_checkout(
    invoice_id: str,
    *,
    user_id: str | None = None,
    organisation_id: str | None = None,
    provider_code: str,
    return_url: str,
) -> dict[str, str | None]:
    """Create a pending ledger attempt and a hosted checkout session."""
    if not isinstance(return_url, str) or urlparse(return_url).scheme != "https":
        raise BillingError("Checkout return_url must use HTTPS.")
    provider = provider_code.strip().lower()
    adapter = get_gateway(provider)
    invoice = get_invoice(
        invoice_id, user_id=user_id, organisation_id=organisation_id
    )
    if invoice is None:
        raise BillingError("Invoice was not found for this account.")
    if invoice["status"] != "open":
        raise BillingError("Only open invoices can be checked out.")
    balance = int(invoice["total_minor"]) - int(invoice["amount_paid_minor"])
    if balance <= 0:
        raise BillingError("Invoice has no outstanding balance.")
    payment_idempotency = f"checkout-{uuid.uuid4().hex}"
    payment_id = record_payment_transaction(
        invoice_id,
        amount_minor=balance,
        currency=invoice["currency"],
        provider_code=provider,
        status="pending",
        idempotency_key=payment_idempotency,
        payment_method="hosted_checkout",
    )
    request = CheckoutRequest(
        payment_transaction_id=payment_id,
        invoice_number=invoice["invoice_number"],
        amount_minor=balance,
        currency=invoice["currency"],
        idempotency_key=payment_idempotency,
        return_url=return_url,
        metadata={"payment_transaction_id": payment_id, "invoice_id": invoice_id},
    )
    try:
        response = adapter.create_checkout(request)
        if (
            not isinstance(response, CheckoutResponse)
            or not response.provider_checkout_id
            or len(response.provider_checkout_id) > 200
            or not isinstance(response.checkout_url, str)
            or urlparse(response.checkout_url).scheme != "https"
            or not urlparse(response.checkout_url).netloc
        ):
            raise BillingError("Gateway returned an invalid hosted checkout response.")
        p = _p()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with database_connection() as connection:
            connection.execute(
                f"""INSERT INTO payment_checkout_sessions
                (payment_transaction_id, provider_code, provider_checkout_id,
                 checkout_url, expires_at, status, created_at, updated_at)
                VALUES ({p}, {p}, {p}, {p}, {p}, 'created', {p}, {p})""",
                (payment_id, provider, response.provider_checkout_id,
                 response.checkout_url, response.expires_at, now, now),
            )
        return {
            "payment_transaction_id": payment_id,
            "checkout_url": response.checkout_url,
            "expires_at": response.expires_at,
        }
    except Exception:
        # Keep the attempt in the ledger; reconciliation can identify a
        # provider-side checkout that was created before a local failure.
        raise


def process_webhook(
    provider_code: str,
    *,
    raw_body: bytes,
    headers: Mapping[str, str],
) -> dict[str, object]:
    """Verify, deduplicate, reconcile and settle one provider notification."""
    provider = provider_code.strip().lower()
    adapter = get_gateway(provider)
    if not isinstance(raw_body, bytes) or not raw_body:
        raise BillingError("Webhook body must be non-empty bytes.")
    notification = adapter.verify_webhook(raw_body, headers)
    if not isinstance(notification, PaymentNotification):
        raise BillingError("Gateway returned an invalid payment notification.")
    if (
        not notification.provider_event_id
        or not notification.payment_transaction_id
        or notification.status not in {"succeeded", "failed", "canceled"}
        or isinstance(notification.amount_minor, bool)
        or not isinstance(notification.amount_minor, int)
        or notification.amount_minor <= 0
        or not re.fullmatch(r"[A-Za-z]{3}", notification.currency or "")
    ):
        raise BillingError("Gateway notification failed normalized field validation.")

    digest = hashlib.sha256(raw_body).hexdigest()
    p = _p()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    event_row_id = str(uuid.uuid4())
    with database_connection() as connection:
        payment = connection.execute(
            f"""SELECT * FROM payment_transactions
                WHERE id = {p} AND provider_code = {p}""",
            (notification.payment_transaction_id, provider),
        ).fetchone()
        if payment is None:
            raise BillingError("Webhook payment transaction was not found for this provider.")
        payment = dict(payment)
        if (
            int(payment["amount_minor"]) != notification.amount_minor
            or payment["currency"] != notification.currency.upper()
        ):
            raise BillingError("Webhook amount or currency does not match the payment attempt.")
        existing = connection.execute(
            f"""SELECT processing_status FROM payment_webhook_events
                WHERE provider_code = {p} AND provider_event_id = {p}""",
            (provider, notification.provider_event_id),
        ).fetchone()
        if existing is not None and existing["processing_status"] == "processed":
            return {"processed": True, "duplicate": True}
        if existing is None:
            connection.execute(
                f"""INSERT INTO payment_webhook_events
                (id, provider_code, provider_event_id, payment_transaction_id,
                 processing_status, payload_digest, received_at)
                VALUES ({p}, {p}, {p}, {p}, 'received', {p}, {p})""",
                (event_row_id, provider, notification.provider_event_id,
                 notification.payment_transaction_id, digest, now),
            )
    try:
        finalize_payment_transaction(
            notification.payment_transaction_id,
            status=notification.status,
            provider_reference=notification.provider_reference,
            failure_code=notification.failure_code,
            failure_message=notification.failure_message,
        )
    except Exception:
        with database_connection() as connection:
            connection.execute(
                f"""UPDATE payment_webhook_events SET processing_status = 'rejected',
                    error_code = 'SETTLEMENT_REJECTED'
                    WHERE provider_code = {p} AND provider_event_id = {p}""",
                (provider, notification.provider_event_id),
            )
        raise
    with database_connection() as connection:
        connection.execute(
            f"""UPDATE payment_webhook_events SET processing_status = 'processed',
                processed_at = {p}, error_code = NULL
                WHERE provider_code = {p} AND provider_event_id = {p}""",
            (now, provider, notification.provider_event_id),
        )
        connection.execute(
            f"""UPDATE payment_checkout_sessions SET status = 'completed',
                updated_at = {p} WHERE payment_transaction_id = {p}""",
            (now, notification.payment_transaction_id),
        )
    return {"processed": True, "duplicate": False}
