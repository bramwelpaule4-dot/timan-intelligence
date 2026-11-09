"""Federated identity links for Google and Microsoft OIDC sign-in."""

VERSION = 19
NAME = "federated_identity_links"


def upgrade(connection) -> None:
    """Store provider subject identifiers separately from user credentials."""

    connection.execute(
        """
        CREATE TABLE federated_identities (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL
                CHECK (provider IN ('google', 'microsoft')),
            subject TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (provider, subject),
            UNIQUE (user_id, provider)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_federated_identities_user
        ON federated_identities(user_id)
        """
    )
