"""Persist provider checkout sessions and webhook delivery receipts."""

VERSION = 17
NAME = "payment_gateway_sessions"


def upgrade(connection) -> None:
    connection.execute(
        """
        CREATE TABLE payment_checkout_sessions (
            payment_transaction_id TEXT PRIMARY KEY
                REFERENCES payment_transactions(id) ON DELETE RESTRICT,
            provider_code TEXT NOT NULL,
            provider_checkout_id TEXT NOT NULL,
            checkout_url TEXT NOT NULL,
            expires_at TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created', 'completed', 'expired', 'canceled')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (provider_code, provider_checkout_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_payment_checkout_provider
        ON payment_checkout_sessions(provider_code, provider_checkout_id)
        """
    )
    connection.execute(
        """
        CREATE TABLE payment_webhook_events (
            id TEXT PRIMARY KEY,
            provider_code TEXT NOT NULL,
            provider_event_id TEXT NOT NULL,
            payment_transaction_id TEXT
                REFERENCES payment_transactions(id) ON DELETE RESTRICT,
            processing_status TEXT NOT NULL DEFAULT 'received'
                CHECK (processing_status IN ('received', 'processed', 'rejected')),
            payload_digest TEXT NOT NULL,
            error_code TEXT,
            received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            UNIQUE (provider_code, provider_event_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_payment_webhook_status
        ON payment_webhook_events(processing_status, received_at)
        """
    )
