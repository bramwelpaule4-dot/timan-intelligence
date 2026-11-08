"""Link billing invoices to approved subscription change requests."""

VERSION = 15
NAME = "billing_subscription_change_requests"


def upgrade(connection) -> None:
    connection.execute(
        """
        ALTER TABLE billing_invoices
        ADD COLUMN subscription_change_request_id TEXT
            REFERENCES subscription_change_requests(id) ON DELETE RESTRICT
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoices_change_request
        ON billing_invoices(subscription_change_request_id)
        """
    )
