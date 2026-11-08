"""Enforce one invoice per subscription upgrade request."""

VERSION = 16
NAME = "unique_subscription_upgrade_invoice"


def upgrade(connection) -> None:
    connection.execute(
        """
        CREATE UNIQUE INDEX uq_billing_invoices_subscription_change_request
        ON billing_invoices(subscription_change_request_id)
        WHERE subscription_change_request_id IS NOT NULL
        """
    )
