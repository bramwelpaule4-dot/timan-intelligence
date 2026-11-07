
"""Tests for TimanStat password-reset email notifications."""

from urllib.parse import parse_qs, urlsplit

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.email_notifications import (
    PASSWORD_RESET_REQUEST_LIMITER,
    request_password_reset,
    send_password_reset_email,
)
from timan_intelligence.identity.password_reset import (
    reset_password_with_token,
)
from timan_intelligence.identity.service import (
    _verify_password,
    register_user,
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_password_reset_notifications.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )
    monkeypatch.setenv("TIMANSTAT_RATE_LIMIT_HMAC_KEY", "test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")

    initialise_database()

    return database_file


@pytest.fixture
def test_user(test_database):
    """Register a test user."""

    return register_user(
        username="resetmailuser",
        email="resetmail@example.com",
        full_name="Reset Mail User",
        password="OriginalSecurePassword123!",
    )


class RecordingEmailSender:
    """Capture outgoing emails without using an SMTP server."""

    def __init__(self):
        self.sent_messages = []

    def send(self, message):
        self.sent_messages.append(message)


def _extract_reset_token(message):
    """Extract the password-reset token from an outgoing email."""

    url_line = next(
        line
        for line in message.body.splitlines()
        if "reset_password=" in line
    )

    return parse_qs(
        urlsplit(url_line.strip()).query
    )["reset_password"][0]


def _expire_previous_reset_cooldown(user_id):
    """Move existing reset-token timestamps outside the cooldown."""

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE password_reset_tokens
            SET created_at = ?
            WHERE user_id = ?
            """,
            ("2000-01-01 00:00:00", user_id),
        )

    PASSWORD_RESET_REQUEST_LIMITER.record_success(
        "resetmail@example.com"
    )


def test_direct_reset_email_contains_valid_reset_link(test_user):
    sender = RecordingEmailSender()

    send_password_reset_email(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert len(sender.sent_messages) == 1

    message = sender.sent_messages[0]

    assert message.recipient == "resetmail@example.com"
    assert message.subject == "Reset your TimanStat password"
    assert "expires in 30 minutes" in message.body

    token = _extract_reset_token(message)

    assert token

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is True

    # Verify the new password hash directly. Login must remain blocked
    # because this test account has not completed email verification.
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert _verify_password(
        "NewSecurePassword456!",
        row["password_hash"],
    )


def test_direct_reset_email_rejects_unknown_user(test_database):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError):
        send_password_reset_email(
            user_id="unknown-user-id",
            base_url="https://timanstat.example.com",
            sender=sender,
        )

    assert sender.sent_messages == []


def test_request_password_reset_sends_email_for_active_account(
    test_user,
):
    sender = RecordingEmailSender()

    result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 1

    message = sender.sent_messages[0]

    assert message.recipient == "resetmail@example.com"
    assert message.subject == "Reset your TimanStat password"


def test_password_reset_request_allows_unverified_email(test_user):
    """Password recovery must not require email verification."""

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT email_verified
            FROM users
            WHERE id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert not bool(row["email_verified"])

    sender = RecordingEmailSender()

    result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 1

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT email_verified
            FROM users
            WHERE id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert not bool(row["email_verified"])


def test_unknown_email_returns_false_without_sending(test_database):
    sender = RecordingEmailSender()

    result = request_password_reset(
        email="unknown@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert sender.sent_messages == []


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "invalid-email",
        "missing-domain@",
        "@example.com",
        None,
    ],
)
def test_invalid_email_returns_false(email, test_database):
    sender = RecordingEmailSender()

    result = request_password_reset(
        email=email,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert sender.sent_messages == []


def test_request_normalises_email_address(test_user):
    sender = RecordingEmailSender()

    result = request_password_reset(
        email="  RESETMAIL@EXAMPLE.COM  ",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 1


def test_recent_password_reset_request_is_blocked(test_user):
    sender = RecordingEmailSender()

    first_result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    second_result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert first_result is True
    assert second_result is False
    assert len(sender.sent_messages) == 1


def test_password_reset_request_succeeds_after_cooldown(test_user):
    sender = RecordingEmailSender()

    first_result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert first_result is True

    _expire_previous_reset_cooldown(test_user)

    second_result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert second_result is True
    assert len(sender.sent_messages) == 2


def test_new_reset_email_invalidates_previous_token(test_user):
    sender = RecordingEmailSender()

    request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    first_token = _extract_reset_token(
        sender.sent_messages[0]
    )

    _expire_previous_reset_cooldown(test_user)

    request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    second_token = _extract_reset_token(
        sender.sent_messages[1]
    )

    assert first_token != second_token

    assert reset_password_with_token(
        first_token,
        "FirstNewSecurePassword123!",
    ) is False

    assert reset_password_with_token(
        second_token,
        "SecondNewSecurePassword456!",
    ) is True


def test_inactive_account_cannot_request_password_reset(test_user):
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET is_active = FALSE
            WHERE id = ?
            """,
            (test_user,),
        )

    sender = RecordingEmailSender()

    result = request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert sender.sent_messages == []


@pytest.mark.parametrize(
    "cooldown",
    [
        0,
        -1,
        3601,
        True,
        1.5,
        "60",
    ],
)
def test_invalid_password_reset_cooldown_raises_value_error(
    test_user,
    cooldown,
):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError, match="cooldown"):
        request_password_reset(
            email="resetmail@example.com",
            base_url="https://timanstat.example.com",
            sender=sender,
            cooldown_seconds=cooldown,
        )

    assert sender.sent_messages == []


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "not-a-url",
        "http://example.com",
        "https://example.com?unexpected=value",
        "https://user:password@example.com",
    ],
)
def test_invalid_base_url_is_rejected(
    test_user,
    base_url,
):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError):
        request_password_reset(
            email="resetmail@example.com",
            base_url=base_url,
            sender=sender,
        )

    assert sender.sent_messages == []



def test_repeated_password_reset_request_is_throttled(test_user):
    sender = RecordingEmailSender()

    assert request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    ) is True

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE password_reset_tokens
            SET created_at = ?
            WHERE user_id = ?
            """,
            ("2000-01-01 00:00:00", test_user),
        )

    assert request_password_reset(
        email="resetmail@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    ) is False
    assert len(sender.sent_messages) == 1
