"""Safaricom Daraja STK Push integration for Kenyan KES invoices.

Daraja callbacks are not cryptographically signed. This adapter therefore
correlates the CheckoutRequestID to a pending ledger attempt and queries
Safaricom's STK status API before accepting a successful callback.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Mapping
from zoneinfo import ZoneInfo

from timan_intelligence.billing.gateway import (
    PaymentNotification, get_gateway, process_webhook, register_gateway,
)
from timan_intelligence.billing.mpesa_reconciliation import (
    ReconciliationError, attach_originator, create_attempt, mark_timeout, verify_result,
)
from timan_intelligence.billing.records import (
    BillingError, _p, get_invoice, record_payment_transaction,
)
from timan_intelligence.database.connection import database_connection


class DarajaError(BillingError):
    """Daraja configuration, transport, or response error."""


class DarajaAdapter:
    provider_code = "mpesa"

    def __init__(self, *, environ=None, opener=None):
        self.environ = os.environ if environ is None else environ
        self.opener = opener or urllib.request.urlopen

    def _config(self):
        mode = self.environ.get("DARAJA_ENVIRONMENT", "sandbox").strip().lower()
        if mode not in {"sandbox", "production"}:
            raise DarajaError("DARAJA_ENVIRONMENT must be sandbox or production.")
        if mode == "production":
            raise DarajaError(
                "Production M-Pesa payments remain disabled pending sandbox end-to-end "
                "validation, callback hardening and operational reconciliation controls."
            )
        prefix = "https://sandbox.safaricom.co.ke" if mode == "sandbox" else "https://api.safaricom.co.ke"
        values = {
            "consumer_key": self.environ.get("DARAJA_CONSUMER_KEY", "").strip(),
            "consumer_secret": self.environ.get("DARAJA_CONSUMER_SECRET", "").strip(),
            "shortcode": self.environ.get("DARAJA_BUSINESS_SHORTCODE", "").strip(),
            "passkey": self.environ.get("DARAJA_PASSKEY", "").strip(),
            "callback_url": self.environ.get("DARAJA_CALLBACK_URL", "").strip(),
        }
        if not all(values.values()):
            raise DarajaError("Daraja credentials, shortcode, passkey and callback URL must be configured.")
        parsed = urllib.parse.urlparse(values["callback_url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise DarajaError("DARAJA_CALLBACK_URL must be a public HTTPS URL.")
        if not values["shortcode"].isdigit():
            raise DarajaError("DARAJA_BUSINESS_SHORTCODE must contain digits only.")
        return prefix, values

    def _request(self, url, *, method="GET", headers=None, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with self.opener(request, timeout=15) as response:
                body = response.read()
                status = getattr(response, "status", 200)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DarajaError("Daraja could not be reached; payment remains pending.") from exc
        if status < 200 or status >= 300:
            raise DarajaError(f"Daraja returned HTTP {status}.")
        try:
            result = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DarajaError("Daraja returned an invalid response.") from exc
        if not isinstance(result, dict):
            raise DarajaError("Daraja returned an unexpected response.")
        return result

    def _token(self):
        base, cfg = self._config()
        auth = base64.b64encode(
            f"{cfg['consumer_key']}:{cfg['consumer_secret']}".encode()
        ).decode("ascii")
        result = self._request(
            base + "/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": "Basic " + auth},
        )
        token = result.get("access_token")
        if not isinstance(token, str) or not token:
            raise DarajaError("Daraja OAuth did not return an access token.")
        return base, cfg, token

    @staticmethod
    def _timestamp():
        return datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def normalize_phone(phone):
        if not isinstance(phone, str):
            raise DarajaError("Enter a valid Kenyan M-Pesa phone number.")
        digits = re.sub(r"[\s+()-]", "", phone)
        if digits.startswith("0"):
            digits = "254" + digits[1:]
        elif digits.startswith("7") or digits.startswith("1"):
            digits = "254" + digits
        if not re.fullmatch(r"254[17][0-9]{8}", digits):
            raise DarajaError("Phone number must be a valid Kenyan 07/01 or 2547/2541 number.")
        return digits

    def initiate(self, invoice_id, phone, *, user_id=None, organisation_id=None):
        invoice = get_invoice(invoice_id, user_id=user_id, organisation_id=organisation_id)
        if invoice is None:
            raise DarajaError("Invoice was not found for this account.")
        if invoice["status"] != "open":
            raise DarajaError("Only open invoices can be paid.")
        if invoice["currency"] != "KES":
            raise DarajaError("M-Pesa checkout is available only for KES invoices.")
        balance = int(invoice["total_minor"]) - int(invoice["amount_paid_minor"])
        if balance <= 0 or balance % 100:
            raise DarajaError("The outstanding KES balance must be a positive whole shilling amount.")
        msisdn = self.normalize_phone(phone)
        payment_id = record_payment_transaction(
            invoice_id, amount_minor=balance, currency="KES", provider_code="mpesa",
            status="pending", idempotency_key="mpesa-" + uuid.uuid4().hex,
            payment_method="mpesa_stk_push",
        )
        base, cfg, token = self._token()
        timestamp = self._timestamp()
        password = base64.b64encode(
            (cfg["shortcode"] + cfg["passkey"] + timestamp).encode()
        ).decode("ascii")
        amount_shillings = balance // 100
        payload = {
            "BusinessShortCode": cfg["shortcode"], "Password": password,
            "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline",
            "Amount": amount_shillings, "PartyA": msisdn,
            "PartyB": cfg["shortcode"], "PhoneNumber": msisdn,
            "CallBackURL": cfg["callback_url"],
            "AccountReference": invoice["invoice_number"][:12],
            "TransactionDesc": "TimanStat invoice " + invoice["invoice_number"][:20],
        }
        result = self._request(
            base + "/mpesa/stkpush/v1/processrequest", method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            payload=payload,
        )
        checkout_id = result.get("CheckoutRequestID")
        response_code = str(result.get("ResponseCode", ""))
        if response_code != "0" or not isinstance(checkout_id, str) or not checkout_id:
            raise DarajaError(str(result.get("ResponseDescription") or "Daraja did not accept the STK Push request."))
        p = _p()
        with database_connection() as connection:
            connection.execute(
                f"UPDATE payment_transactions SET provider_reference = {p}, updated_at = CURRENT_TIMESTAMP WHERE id = {p} AND status = 'pending'",
                (checkout_id, payment_id),
            )
        return {"payment_transaction_id": payment_id, "checkout_request_id": checkout_id, "status": "pending"}

    def _query(self, checkout_id):
        base, cfg, token = self._token()
        timestamp = self._timestamp()
        password = base64.b64encode(
            (cfg["shortcode"] + cfg["passkey"] + timestamp).encode()
        ).decode("ascii")
        return self._request(
            base + "/mpesa/stkpushquery/v1/query", method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            payload={
                "BusinessShortCode": cfg["shortcode"], "Password": password,
                "Timestamp": timestamp, "CheckoutRequestID": checkout_id,
            },
        )

    def _request_transaction_status(self, payment, checkout_id, receipt, amount_minor, *, create_record=True):
        base, cfg, token = self._token()
        initiator = self.environ.get("DARAJA_INITIATOR_NAME", "").strip()
        credential = self.environ.get("DARAJA_SECURITY_CREDENTIAL", "").strip()
        result_url = self.environ.get("DARAJA_TRANSACTION_STATUS_RESULT_URL", "").strip()
        timeout_url = self.environ.get("DARAJA_TRANSACTION_STATUS_TIMEOUT_URL", "").strip()
        if not initiator or not credential or not result_url or not timeout_url:
            raise DarajaError(
                "Transaction-status initiator, security credential and HTTPS result/timeout URLs must be configured."
            )
        for callback_url in (result_url, timeout_url):
            parsed = urllib.parse.urlparse(callback_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise DarajaError("Transaction-status callback URLs must use public HTTPS.")
        if create_record:
            create_attempt(payment["id"], checkout_id, receipt, amount_minor)
        response = self._request(
            base + "/mpesa/transactionstatus/v1/query",
            method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            payload={
                "Initiator": initiator,
                "SecurityCredential": credential,
                "CommandID": "TransactionStatusQuery",
                "TransactionID": receipt,
                "PartyA": cfg["shortcode"],
                "IdentifierType": self.environ.get("DARAJA_IDENTIFIER_TYPE", "4").strip(),
                "ResultURL": result_url,
                "QueueTimeOutURL": timeout_url,
                "Remarks": "TimanStat payment reconciliation",
                "Occasion": "Invoice payment",
            },
        )
        originator = response.get("OriginatorConversationID")
        if str(response.get("ResponseCode", "")) != "0" or not isinstance(originator, str) or not originator:
            raise DarajaError(
                str(response.get("ResponseDescription") or "Safaricom did not accept transaction-status query.")
            )
        attach_originator(checkout_id, originator)
        return {"status": "reconciliation_pending", "originator_conversation_id": originator}

    def start_reconciliation(self, raw_body: bytes):
        try:
            data = json.loads(raw_body.decode("utf-8"))
            callback = data["Body"]["stkCallback"]
            checkout_id = callback["CheckoutRequestID"]
            callback_code = int(callback["ResultCode"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Malformed Daraja STK callback.") from exc
        if not isinstance(checkout_id, str) or not checkout_id:
            raise DarajaError("Daraja callback is missing CheckoutRequestID.")
        configure_daraja(self)
        query = self._query(checkout_id)
        try:
            confirmed_code = int(query["ResultCode"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Safaricom status query did not return a transaction result.") from exc
        if confirmed_code != callback_code:
            raise DarajaError("Callback result does not match Safaricom's transaction status.")
        if callback_code != 0:
            return process_webhook("mpesa", raw_body=raw_body, headers={})
        if str(query.get("ResponseCode", "")) != "0":
            raise DarajaError("Safaricom has not confirmed successful payment.")
        p = _p()
        with database_connection() as connection:
            payment = connection.execute(
                f"""SELECT DISTINCT p.id, p.amount_minor, p.currency
                FROM payment_transactions AS p
                LEFT JOIN mpesa_transaction_reconciliations AS r
                  ON r.payment_transaction_id = p.id
                 AND r.checkout_request_id = {p}
                WHERE p.provider_code = 'mpesa'
                  AND (p.provider_reference = {p} OR r.checkout_request_id = {p})""",
                (checkout_id, checkout_id, checkout_id),
            ).fetchone()
            existing = connection.execute(
                f"""SELECT status, originator_conversation_id
                FROM mpesa_transaction_reconciliations WHERE checkout_request_id = {p}""",
                (checkout_id,),
            ).fetchone()
        if payment is None:
            raise DarajaError("Unknown Daraja CheckoutRequestID.")
        payment = dict(payment)
        if payment["currency"] != "KES":
            raise DarajaError("M-Pesa payment ledger currency is invalid.")
        if existing is not None and existing["status"] == "verified":
            return {"status": "already_reconciled"}
        if existing is not None and existing["status"] != "pending":
            raise DarajaError("This M-Pesa payment reconciliation requires manual review.")
        if existing is not None and existing["originator_conversation_id"]:
            return {
                "status": "reconciliation_pending",
                "originator_conversation_id": existing["originator_conversation_id"],
            }
        metadata = callback.get("CallbackMetadata", {}).get("Item", [])
        if not isinstance(metadata, list):
            raise DarajaError("Successful callback metadata is malformed.")
        fields = {
            item.get("Name"): item.get("Value")
            for item in metadata if isinstance(item, dict)
        }
        try:
            callback_amount = int(fields["Amount"])
            receipt = str(fields["MpesaReceiptNumber"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Successful callback is missing amount or M-Pesa receipt.") from exc
        if (
            callback_amount * 100 != int(payment["amount_minor"])
            or not re.fullmatch(r"[A-Z0-9]{8,20}", receipt)
        ):
            raise DarajaError("Callback amount or receipt does not match the expected payment.")
        try:
            return self._request_transaction_status(
                payment, checkout_id, receipt, callback_amount * 100,
                create_record=existing is None,
            )
        except ReconciliationError as exc:
            raise DarajaError("Unable to create Safaricom reconciliation attempt.") from exc

    def handle_transaction_status_result(self, raw_body: bytes):
        configure_daraja(self)
        try:
            verified = verify_result(raw_body)
        except ReconciliationError as exc:
            raise DarajaError(str(exc)) from exc
        # Re-run the STK status query and pass only the independently
        # reconciled amount and receipt into the existing idempotent ledger.
        synthetic = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": verified["checkout_request_id"],
                    "ResultCode": 0,
                    "ResultDesc": "Independently reconciled by Safaricom Transaction Status API",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": verified["amount_minor"] // 100},
                            {"Name": "MpesaReceiptNumber", "Value": verified["receipt"]},
                        ]
                    },
                }
            }
        }
        return process_webhook(
            "mpesa", raw_body=json.dumps(synthetic).encode("utf-8"), headers={}
        )

    def create_checkout(self, request):
        raise DarajaError("Daraja uses phone-based STK Push, not hosted checkout.")

    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]):
        try:
            data = json.loads(raw_body.decode("utf-8"))
            callback = data["Body"]["stkCallback"]
            checkout_id = callback["CheckoutRequestID"]
            result_code = int(callback["ResultCode"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Malformed Daraja STK callback.") from exc
        if not isinstance(checkout_id, str) or not checkout_id:
            raise DarajaError("Daraja callback is missing CheckoutRequestID.")
        p = _p()
        with database_connection() as connection:
            payment = connection.execute(
                f"SELECT id, amount_minor, currency FROM payment_transactions WHERE provider_code = 'mpesa' AND provider_reference = {p}",
                (checkout_id,),
            ).fetchone()
        if payment is None:
            raise DarajaError("Unknown Daraja CheckoutRequestID.")
        payment = dict(payment)
        if payment["currency"] != "KES":
            raise DarajaError("M-Pesa payment ledger currency is invalid.")

        # Daraja callbacks are unsigned. Query Safaricom for every outcome,
        # including failures, so a forged callback cannot cancel a live attempt.
        query = self._query(checkout_id)
        try:
            confirmed_code = int(query["ResultCode"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Safaricom status query did not return a transaction result.") from exc
        if confirmed_code != result_code:
            raise DarajaError("Callback result does not match Safaricom's transaction status.")
        if result_code != 0:
            return PaymentNotification(
                provider_event_id=checkout_id, payment_transaction_id=payment["id"],
                status="canceled" if result_code in {1032, 1037} else "failed",
                amount_minor=int(payment["amount_minor"]), currency="KES",
                failure_code=str(result_code),
                failure_message=str(callback.get("ResultDesc", "M-Pesa payment failed"))[:500],
            )
        if str(query.get("ResponseCode", "")) != "0":
            raise DarajaError("Safaricom status query has not confirmed successful payment.")
        metadata = callback.get("CallbackMetadata", {}).get("Item", [])
        fields = {item.get("Name"): item.get("Value") for item in metadata if isinstance(item, dict)}
        try:
            callback_amount = int(fields["Amount"])
            receipt = str(fields["MpesaReceiptNumber"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DarajaError("Successful callback is missing amount or M-Pesa receipt.") from exc
        if callback_amount * 100 != int(payment["amount_minor"]) or not re.fullmatch(r"[A-Z0-9]{8,20}", receipt):
            raise DarajaError("Callback amount or receipt does not match expected payment details.")
        return PaymentNotification(
            provider_event_id=checkout_id, payment_transaction_id=payment["id"],
            status="succeeded", amount_minor=int(payment["amount_minor"]),
            currency="KES", provider_reference=receipt,
        )

def configure_daraja(adapter=None):
    """Register the configured Daraja adapter for webhook processing."""
    instance = adapter or DarajaAdapter()
    register_gateway(instance)
    return instance


def initiate_mpesa_payment(invoice_id, phone, *, user_id=None, organisation_id=None):
    """Start an M-Pesa STK Push for an owner-scoped KES invoice."""
    return DarajaAdapter().initiate(
        invoice_id, phone, user_id=user_id, organisation_id=organisation_id
    )


def handle_mpesa_callback(raw_body: bytes):
    """Verify STK status and start independent Safaricom transaction reconciliation."""
    return DarajaAdapter().start_reconciliation(raw_body)


def handle_mpesa_transaction_status_callback(raw_body: bytes):
    """Verify Safaricom's asynchronous transaction-status result before settlement."""
    return DarajaAdapter().handle_transaction_status_result(raw_body)


def handle_mpesa_transaction_status_timeout(raw_body: bytes):
    """Record a Safaricom transaction-status query timeout without settling payment."""
    try:
        return mark_timeout(raw_body)
    except ReconciliationError as exc:
        raise DarajaError(str(exc)) from exc
