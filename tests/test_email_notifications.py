
"""Tests for TimanStat email verification notifications."""

from urllib.parse import parse_qs, urlsplit

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.email_delivery import OutboundEmail
from timan_intelligence.identity.email_notifications import (
    EMAIL_VERIFICATION_SUBJECT,
    send_email_verification,
)
from timan_intelligence.identity.email_verification import (
    verify_email_token,
)
from timan_intelligence.identity.service import (
    get_user_by_id,
    register_user,
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_email_notifications.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


@pytest.fixture
def test_user(test_database):
    """Register and return a test user ID."""

    return register_user(
        username="notificationuser",
        email="notification@example.com",
        full_name="Notification User",
        password="SecureTestPassword123!",
    )


class RecordingEmailSender:
    """Capture outgoing messages without sending real emails."""

    def __init__(self):
        self.sent_messages = []

    def send(self, message):
        self.sent_messages.append(message)


def test_sends_verification_email_to_registered_user(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert len(sender.sent_messages) == 1

    message = sender.sent_messages[0]

    assert isinstance(message, OutboundEmail)
    assert message.recipient == "notification@example.com"
    assert message.subject == EMAIL_VERIFICATION_SUBJECT
    assert "Notification User" in message.body
    assert "TimanStat" in message.body


def test_verification_link_contains_valid_token(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    message = sender.sent_messages[0]

    url_line = next(
        line
        for line in message.body.splitlines()
        if "verify_email=" in line
    )

    parsed_url = urlsplit(url_line.strip())

    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "timanstat.example.com"

    query = parse_qs(parsed_url.query)

    assert "verify_email" in query
    assert len(query["verify_email"]) == 1

    token = query["verify_email"][0]

    assert verify_email_token(token) is True

    user = get_user_by_id(test_user)

    assert user is not None
    assert bool(user["email_verified"]) is True


def test_verification_link_supports_application_path(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://example.com/timanstat",
        sender=sender,
    )

    message = sender.sent_messages[0]

    url_line = next(
        line
        for line in message.body.splitlines()
        if "verify_email=" in line
    )

    parsed_url = urlsplit(url_line.strip())

    assert parsed_url.path == "/timanstat/"


def test_custom_token_expiry_is_included_in_email(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
        expiry_minutes=60,
    )

    message = sender.sent_messages[0]

    assert "expires in 60 minutes" in message.body


def test_default_token_expiry_is_included_in_email(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    message = sender.sent_messages[0]

    assert "expires in 30 minutes" in message.body


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "   ",
        "timanstat.example.com",
        "ftp://timanstat.example.com",
        "https://",
        "https://example.com?existing=value",
        "https://example.com#fragment",
        "https://user:password@example.com",
        "http://timanstat.example.com",
    ],
)
def test_rejects_invalid_application_urls(test_user, base_url):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError):
        send_email_verification(
            user_id=test_user,
            base_url=base_url,
            sender=sender,
        )

    assert sender.sent_messages == []


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "https://timanstat.example.com",
    ],
)
def test_accepts_valid_application_urls(test_user, base_url):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url=base_url,
        sender=sender,
    )

    assert len(sender.sent_messages) == 1


def test_rejects_unknown_user(test_database):
    """Unknown-user checks must run against an initialised database."""

    sender = RecordingEmailSender()

    with pytest.raises(ValueError, match="does not exist"):
        send_email_verification(
            user_id="unknown-user",
            base_url="https://timanstat.example.com",
            sender=sender,
        )

    assert sender.sent_messages == []


def test_rejects_already_verified_user(test_user):
    sender = RecordingEmailSender()

    send_email_verification(
        user_id=test_user,
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    message = sender.sent_messages[0]

    url_line = next(
        line
        for line in message.body.splitlines()
        if "verify_email=" in line
    )

    token = parse_qs(
        urlsplit(url_line.strip()).query
    )["verify_email"][0]

    assert verify_email_token(token) is True

    with pytest.raises(ValueError, match="already verified"):
        send_email_verification(
            user_id=test_user,
            base_url="https://timanstat.example.com",
            sender=sender,
        )

    assert len(sender.sent_messages) == 1


def test_rejects_invalid_token_expiry(test_user):
    sender = RecordingEmailSender()

    with pytest.raises(ValueError):
        send_email_verification(
            user_id=test_user,
            base_url="https://timanstat.example.com",
            sender=sender,
            expiry_minutes=0,
        )

    assert sender.sent_messages == []


def test_rejects_inactive_user(test_user):
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

    with pytest.raises(ValueError):
        send_email_verification(
            user_id=test_user,
            base_url="https://timanstat.example.com",
            sender=sender,
        )

    assert sender.sent_messages == []
