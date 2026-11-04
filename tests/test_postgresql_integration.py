def test_postgresql_migrations_are_recorded(postgres_database):
    """All registered schema migrations should be recorded correctly."""

    with database_connection() as connection:
        history = connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

    assert [(row["version"], row["name"]) for row in history] == [
        (1, "initial_schema"),
        (2, "totp_enrolment"),
    ]

    assert history[-1]["version"] == LATEST_SCHEMA_VERSION

    with database_connection() as connection:
        columns = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'users'
            """
        ).fetchall()

    actual_columns = {row["column_name"] for row in columns}

    expected_totp_columns = {
        "totp_enabled",
        "totp_secret_encrypted",
        "totp_pending_secret_encrypted",
        "totp_last_accepted_counter",
        "totp_enrolled_at",
        "totp_pending_created_at",
    }

    assert expected_totp_columns.issubset(actual_columns)
