
"""Tests for TimanStat email-verification resend workflows."""

from urllib.parse import parse_qs, urlsplit

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.email_notifications import (
    resend_email_verification,
    send_email_verification,
)
from timan_intelligence.identity.email_verification import (
    verify_email_token,
)
from timan_intelligence.identity.service import register_user


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_email_resend.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


@pytest.fixture
def test_user(test_database):
    """Register an unverified test user."""

    return register_user(
        username="resenduser",
        email="resend@example.com",
        full_name="Resend User",
        password="SecureTestPassword123!",
    )


class RecordingEmailSender:
    """Capture outgoing emails without using an SMTP server."""

    def __init__(self):
        self.sent_messages = []

    def send(self, message):
        self.sent_messages.append(message)


def _extract_token(message):
    """Extract the verification token from an outgoing email."""

    url_line = next(
        line
        for line in message.body.splitlines()
        if "verify_email=" in line
    )

    return parse_qs(
        urlsplit(url_line.strip()).query
    )["verify_email"][0]


def _make_previous_token_expired_from_cooldown(user_id):
    """Move existing verification-token timestamps outside the cooldown."""

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE email_verification_tokens
            SET created_at = ?
            WHERE user_id = ?
            """,
            ("2000-01-01 00:00:00", user_id),
        )


def test_resends_verification_email_after_cooldown(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    _make_previous_token_expired_from_cooldown(test_user)

    result = resend_email_verification(
        email="resend@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 2
    assert sender.sent_messages[1].recipient == "resend@example.com"


def test_successful_resend_invalidates_previous_token(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    previous_token = _extract_token(sender.sent_messages[0])

    _make_previous_token_expired_from_cooldown(test_user)

    result = resend_email_verification(
        email="resend@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 2

    replacement_token = _extract_token(sender.sent_messages[1])

    assert replacement_token != previous_token
    assert verify_email_token(previous_token) is False
    assert verify_email_token(replacement_token) is True


def test_recent_verification_request_is_blocked(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    result = resend_email_verification(
        email="resend@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert len(sender.sent_messages) == 1


def test_unknown_email_returns_false_without_sending(test_database):
    sender = RecordingEmailSender()

    result = resend_email_verification(
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

    result = resend_email_verification(
        email=email,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert sender.sent_messages == []


def test_resend_normalises_email_address(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    _make_previous_token_expired_from_cooldown(test_user)

    result = resend_email_verification(
        email="  RESEND@EXAMPLE.COM  ",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is True
    assert len(sender.sent_messages) == 2


def test_already_verified_account_cannot_resend(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    token = _extract_token(sender.sent_messages[0])

    assert verify_email_token(token) is True

    result = resend_email_verification(
        email="resend@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert result is False
    assert len(sender.sent_messages) == 1


def test_inactive_account_cannot_resend(test_user):
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

    result = resend_email_verification(
        email="resend@example.com",
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
def test_invalid_cooldown_raises_value_error(
    test_user,
    cooldown,
):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError, match="cooldown"):
        resend_email_verification(
            email="resend@example.com",
            base_url="https://timanstat.example.com",
            sender=sender,
            cooldown_seconds=cooldown,
        )

    assert sender.sent_messages == []
