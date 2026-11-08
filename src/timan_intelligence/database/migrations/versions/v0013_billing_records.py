"""Create durable invoices, payment transactions and billing events."""

from __future__ import annotations


VERSION = 13
NAME = "billing_records"


def upgrade(connection) -> None:
    """Create immutable billing records and auditable payment history."""

    connection.execute(
        """
        CREATE TABLE billing_invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT NOT NULL UNIQUE,
            user_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
            organisation_id TEXT
                REFERENCES organisations(id) ON DELETE RESTRICT,
            subscription_id TEXT
                REFERENCES subscriptions(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN (
                    'draft', 'open', 'paid', 'void', 'uncollectible'
                )),
            currency TEXT NOT NULL
                CHECK (
                    length(currency) = 3
                    AND currency = upper(currency)
                ),
            subtotal_minor INTEGER NOT NULL DEFAULT 0
                CHECK (subtotal_minor >= 0),
            tax_minor INTEGER NOT NULL DEFAULT 0
                CHECK (tax_minor >= 0),
            total_minor INTEGER NOT NULL DEFAULT 0
                CHECK (total_minor >= 0),
            amount_paid_minor INTEGER NOT NULL DEFAULT 0
                CHECK (
                    amount_paid_minor >= 0
                    AND amount_paid_minor <= total_minor
                ),
            issued_at TIMESTAMP,
            due_at TIMESTAMP,
            paid_at TIMESTAMP,
            voided_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (user_id IS NOT NULL AND organisation_id IS NULL)
                OR (user_id IS NULL AND organisation_id IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoices_user_created
        ON billing_invoices(user_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoices_org_created
        ON billing_invoices(organisation_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoices_status_due
        ON billing_invoices(status, due_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoices_subscription
        ON billing_invoices(subscription_id)
        """
    )

    connection.execute(
        """
        CREATE TABLE billing_invoice_items (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL
                REFERENCES billing_invoices(id) ON DELETE RESTRICT,
            description TEXT NOT NULL,
            plan_code TEXT,
            quantity INTEGER NOT NULL DEFAULT 1
                CHECK (quantity > 0),
            unit_amount_minor INTEGER NOT NULL
                CHECK (unit_amount_minor >= 0),
            line_total_minor INTEGER NOT NULL
                CHECK (
                    line_total_minor >= 0
                    AND line_total_minor = quantity * unit_amount_minor
                ),
            period_start TIMESTAMP,
            period_end TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                period_start IS NULL
                OR period_end IS NULL
                OR period_end > period_start
            )
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoice_items_invoice
        ON billing_invoice_items(invoice_id)
        """
    )

    connection.execute(
        """
        CREATE TABLE payment_transactions (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL
                REFERENCES billing_invoices(id) ON DELETE RESTRICT,
            provider_code TEXT NOT NULL,
            provider_reference TEXT,
            idempotency_key TEXT UNIQUE,
            payment_method TEXT,
            status TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN (
                    'created', 'pending', 'succeeded', 'failed',
                    'canceled', 'partially_refunded', 'refunded'
                )),
            amount_minor INTEGER NOT NULL
                CHECK (amount_minor > 0),
            currency TEXT NOT NULL
                CHECK (
                    length(currency) = 3
                    AND currency = upper(currency)
                ),
            failure_code TEXT,
            failure_message TEXT,
            initiated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (provider_code, provider_reference)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_payment_transactions_invoice
        ON payment_transactions(invoice_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_payment_transactions_status_created
        ON payment_transactions(status, created_at)
        """
    )

    connection.execute(
        """
        CREATE TABLE billing_events (
            id TEXT PRIMARY KEY,
            invoice_id TEXT
                REFERENCES billing_invoices(id) ON DELETE RESTRICT,
            payment_transaction_id TEXT
                REFERENCES payment_transactions(id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            actor_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            provider_code TEXT,
            provider_event_id TEXT,
            details TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (invoice_id IS NOT NULL AND payment_transaction_id IS NULL)
                OR (invoice_id IS NULL AND payment_transaction_id IS NOT NULL)
            ),
            UNIQUE (provider_code, provider_event_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_events_invoice_created
        ON billing_events(invoice_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_events_payment_created
        ON billing_events(payment_transaction_id, created_at)
        """
    )
