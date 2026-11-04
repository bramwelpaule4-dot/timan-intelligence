
"""PostgreSQL concurrency and transaction integrity tests."""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


@pytest.fixture(scope="session")
def postgres_database():
    """Configure and initialise the PostgreSQL integration-test database."""

    database_url = os.getenv(
        "TIMANSTAT_TEST_POSTGRES_URL",
        "",
    ).strip()

    if not database_url:
        pytest.skip(
            "PostgreSQL concurrency tests require "
            "TIMANSTAT_TEST_POSTGRES_URL."
        )

    if not database_url.startswith(
        ("postgresql://", "postgres://")
    ):
        pytest.fail(
            "TIMANSTAT_TEST_POSTGRES_URL must be a PostgreSQL URL."
        )

    os.environ["DATABASE_URL"] = database_url

    initialise_database()

    return database_url


def test_postgresql_prevents_duplicate_memberships_under_concurrency(
    postgres_database,
):
    """
    Concurrent transactions must not create duplicate organisation
    memberships for the same user.
    """

    from psycopg.errors import UniqueViolation

    test_identifier = uuid.uuid4().hex

    user_id = f"concurrent-user-{test_identifier}"
    organisation_id = f"concurrent-org-{test_identifier}"

    username = f"concurrent_user_{test_identifier}"
    email = f"concurrent_user_{test_identifier}@example.com"

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                id,
                username,
                email,
                full_name,
                password_hash
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                username,
                email,
                "Concurrent Membership Test",
                "test-hash",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisations (
                id,
                name
            )
            VALUES (%s, %s)
            """,
            (
                organisation_id,
                f"Concurrent Test Organisation {test_identifier}",
            ),
        )

    barrier = Barrier(2)

    def create_membership(attempt_number):
        """Attempt to create a membership using an independent connection."""

        membership_id = (
            f"concurrent-membership-{test_identifier}-{attempt_number}"
        )

        try:
            with database_connection() as connection:
                # Synchronise both transactions before either attempts
                # the membership insertion.
                barrier.wait(timeout=15)

                connection.execute(
                    """
                    INSERT INTO organisation_memberships (
                        id,
                        organisation_id,
                        user_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        membership_id,
                        organisation_id,
                        user_id,
                    ),
                )

            return "created"

        except UniqueViolation:
            return "rejected_duplicate"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    create_membership,
                    (1, 2),
                )
            )

        assert outcomes.count("created") == 1
        assert outcomes.count("rejected_duplicate") == 1

        with database_connection() as connection:
            result = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM organisation_memberships
                WHERE organisation_id = %s
                  AND user_id = %s
                """,
                (
                    organisation_id,
                    user_id,
                ),
            ).fetchone()

        assert result["total"] == 1

    finally:
        # Remove test records so repeated test runs do not accumulate data.
        with database_connection() as connection:
            connection.execute(
                """
                DELETE FROM organisations
                WHERE id = %s
                """,
                (organisation_id,),
            )

            connection.execute(
                """
                DELETE FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
