
"""Security tests for the TimanStat development email simulator."""

import pytest

from timan_intelligence.security import auth_ui


class FakeSecrets(dict):
    """Minimal Streamlit Secrets test double."""


@pytest.fixture
def configure_secrets(monkeypatch):
    """Configure isolated Streamlit secrets for each test."""

    secrets = FakeSecrets(
        {
            "TIMAN_ENVIRONMENT": "development",
            "TIMAN_DEV_EMAIL_SIMULATOR": "true",
            "TIMAN_DEV_ALLOWED_HOSTS": "timanstat-dev.example.com",
        }
    )

    monkeypatch.setattr(
        auth_ui,
        "st",
        type("FakeStreamlit", (), {"secrets": secrets})(),
    )

    for name in (
        "TIMAN_ENVIRONMENT",
        "TIMAN_DEV_EMAIL_SIMULATOR",
        "TIMAN_DEV_ALLOWED_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)

    return secrets


def test_simulator_is_enabled_for_authorised_development_host(
    configure_secrets,
):
    sender = auth_ui._development_email_sender(
        "https://timanstat-dev.example.com"
    )

    assert isinstance(sender, auth_ui.MockEmailSender)


def test_simulator_is_disabled_in_production(
    configure_secrets,
):
    configure_secrets["TIMAN_ENVIRONMENT"] = "production"

    sender = auth_ui._development_email_sender(
        "https://timanstat-dev.example.com"
    )

    assert sender is None


def test_simulator_is_disabled_when_flag_is_false(
    configure_secrets,
):
    configure_secrets["TIMAN_DEV_EMAIL_SIMULATOR"] = "false"

    sender = auth_ui._development_email_sender(
        "https://timanstat-dev.example.com"
    )

    assert sender is None


def test_simulator_is_disabled_when_environment_is_missing(
    configure_secrets,
):
    del configure_secrets["TIMAN_ENVIRONMENT"]

    sender = auth_ui._development_email_sender(
        "https://timanstat-dev.example.com"
    )

    assert sender is None


def test_simulator_rejects_unauthorised_hostname(
    configure_secrets,
):
    with pytest.raises(
        ValueError,
        match="not authorised",
    ):
        auth_ui._development_email_sender(
            "https://unapproved.example.com"
        )


def test_simulator_allows_localhost_for_development(
    configure_secrets,
):
    sender = auth_ui._development_email_sender(
        "http://localhost:8501"
    )

    assert isinstance(sender, auth_ui.MockEmailSender)


def test_simulator_rejects_invalid_application_url(
    configure_secrets,
):
    with pytest.raises(ValueError):
        auth_ui._development_email_sender(
            "not-a-valid-url"
        )


def test_verification_url_extraction_returns_link():
    body = (
        "Hello,\n\n"
        "Please verify your email:\n\n"
        "https://timanstat-dev.example.com/"
        "?verify_email=test-token\n"
    )

    result = auth_ui._extract_verification_url(body)

    assert result == (
        "https://timanstat-dev.example.com/"
        "?verify_email=test-token"
    )


def test_verification_url_extraction_returns_none_without_link():
    body = "Hello. Your account has been created."

    assert auth_ui._extract_verification_url(body) is None
