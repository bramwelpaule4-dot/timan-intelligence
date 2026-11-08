"""Safaricom transaction-status reconciliation persistence and validation.

The result callback is correlated to a server-created request and its receipt,
then checked against the expected ledger amount before any settlement.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from timan_intelligence.billing.records import _p
from timan_intelligence.database.connection import database_connection


class ReconciliationError(ValueError):
    """Invalid or unmatched Safaricom reconciliation result."""


def create_attempt(payment_transaction_id, checkout_request_id, receipt, amount_minor):
    if not all(isinstance(value, str) and value for value in (
        payment_transaction_id, checkout_request_id, receipt
    )):
        raise ReconciliationError("A payment, checkout and receipt reference are required.")
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
        raise ReconciliationError("The expected payment amount is invalid.")
    p = _p()
    attempt_id = str(uuid.uuid4())
    with database_connection() as connection:
        connection.execute(
            f"""INSERT INTO mpesa_transaction_reconciliations
            (id, payment_transaction_id, checkout_request_id, candidate_receipt,
             candidate_amount_minor, status)
            VALUES ({p}, {p}, {p}, {p}, {p}, 'pending')""",
            (attempt_id, payment_transaction_id, checkout_request_id, receipt, amount_minor),
        )
    return attempt_id


def attach_originator(checkout_request_id, originator_conversation_id):
    if not isinstance(originator_conversation_id, str) or not originator_conversation_id.strip():
        raise ReconciliationError("Safaricom did not return an originator conversation ID.")
    p = _p()
    with database_connection() as connection:
        result = connection.execute(
            f"""UPDATE mpesa_transaction_reconciliations
            SET originator_conversation_id = {p}, requested_at = {p},
                updated_at = {p}
            WHERE checkout_request_id = {p} AND status = 'pending'""",
            (
                originator_conversation_id.strip(),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                checkout_request_id,
            ),
        )
        if result.rowcount != 1:
            raise ReconciliationError("Unable to link Safaricom's reconciliation request.")


def _parameters(result):
    block = result.get("ResultParameters") or {}
    items = block.get("ResultParameter", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ReconciliationError("Safaricom result parameters are malformed.")
    values = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("Key"), str):
            values[item["Key"]] = item.get("Value")
    return values


def verify_result(raw_body: bytes):
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        result = payload["Result"]
        originator = result["OriginatorConversationID"]
        result_code = str(result["ResultCode"])
        result_type = int(result["ResultType"])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ReconciliationError("Malformed Safaricom transaction-status result.") from exc
    if not isinstance(originator, str) or not originator:
        raise ReconciliationError("Transaction-status result has no originator reference.")
    p = _p()
    with database_connection() as connection:
        row = connection.execute(
            f"""SELECT * FROM mpesa_transaction_reconciliations
            WHERE originator_conversation_id = {p}""",
            (originator,),
        ).fetchone()
    if row is None:
        raise ReconciliationError("Unknown Safaricom reconciliation request.")
    attempt = dict(row)
    if attempt["status"] not in {"pending", "verified"}:
        raise ReconciliationError("Safaricom reconciliation attempt is no longer pending.")
    if result_code != "0" or result_type != 0:
        raise ReconciliationError("Safaricom has not confirmed a completed transaction.")
    values = _parameters(result)
    receipt = values.get("ReceiptNo")
    status = values.get("TransactionStatus")
    try:
        amount = Decimal(str(values.get("Amount")))
        minor = amount * 100
        if not amount.is_finite() or minor != minor.to_integral_value():
            raise InvalidOperation
        amount_minor = int(minor)
    except (InvalidOperation, TypeError, ValueError, OverflowError) as exc:
        raise ReconciliationError("Safaricom result has no valid whole-shilling amount.") from exc
    if (
        not isinstance(receipt, str)
        or receipt != attempt["candidate_receipt"]
        or status != "Completed"
        or amount_minor != int(attempt["candidate_amount_minor"])
    ):
        raise ReconciliationError("Safaricom receipt, status or amount does not match the payment attempt.")
    digest = hashlib.sha256(raw_body).hexdigest()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_connection() as connection:
        connection.execute(
            f"""UPDATE mpesa_transaction_reconciliations
            SET status = 'verified', verified_receipt = {p},
                verified_amount_minor = {p}, safaricom_result_code = {p},
                result_payload_digest = {p}, completed_at = {p},
                updated_at = {p}
            WHERE id = {p} AND status IN ('pending', 'verified')""",
            (receipt, amount_minor, result_code, digest, now, now, attempt["id"]),
        )
    return {
        "payment_transaction_id": attempt["payment_transaction_id"],
        "checkout_request_id": attempt["checkout_request_id"],
        "receipt": receipt,
        "amount_minor": amount_minor,
    }


def mark_timeout(raw_body: bytes):
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        result = payload.get("Result", payload)
        originator = result["OriginatorConversationID"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ReconciliationError("Malformed Safaricom transaction-status timeout.") from exc
    if not isinstance(originator, str) or not originator:
        raise ReconciliationError("Timeout has no originator reference.")
    p = _p()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_connection() as connection:
        updated = connection.execute(
            f"""UPDATE mpesa_transaction_reconciliations
            SET status = 'timeout', completed_at = {p}, updated_at = {p}
            WHERE originator_conversation_id = {p} AND status = 'pending'""",
            (now, now, originator),
        )
    return updated.rowcount == 1
