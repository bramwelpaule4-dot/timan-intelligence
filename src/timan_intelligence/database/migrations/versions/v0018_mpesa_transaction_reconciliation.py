"""Persist independent Safaricom transaction-status reconciliation attempts."""

VERSION = 18
NAME = "mpesa_transaction_reconciliation"


def upgrade(connection) -> None:
    connection.execute(
        """
        CREATE TABLE mpesa_transaction_reconciliations (
            id TEXT PRIMARY KEY,
            payment_transaction_id TEXT NOT NULL
                REFERENCES payment_transactions(id) ON DELETE RESTRICT,
            checkout_request_id TEXT NOT NULL UNIQUE,
            candidate_receipt TEXT NOT NULL UNIQUE,
            candidate_amount_minor INTEGER NOT NULL CHECK (candidate_amount_minor > 0),
            originator_conversation_id TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'verified', 'rejected', 'timeout')),
            verified_receipt TEXT,
            verified_amount_minor INTEGER,
            safaricom_result_code TEXT,
            result_payload_digest TEXT,
            requested_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_mpesa_reconciliation_status
        ON mpesa_transaction_reconciliations(status, created_at)
        """
    )
