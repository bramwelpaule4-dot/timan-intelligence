"""Preserve invoice line-item ordering across database backends."""

from __future__ import annotations


VERSION = 14
NAME = "billing_invoice_item_order"


def upgrade(connection) -> None:
    """Add a stable caller-defined position to each invoice line."""

    connection.execute(
        """
        ALTER TABLE billing_invoice_items
        ADD COLUMN line_number INTEGER NOT NULL DEFAULT 0
            CHECK (line_number >= 0)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_billing_invoice_items_order
        ON billing_invoice_items(invoice_id, line_number, created_at, id)
        """
    )
