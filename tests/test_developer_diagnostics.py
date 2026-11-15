"""Tests for restricted TimanStat development diagnostics."""

from contextlib import contextmanager
from types import SimpleNamespace

from timan_intelligence.security import developer_diagnostics as diagnostics


class FakeSecrets(dict):
    def get(self, key, default=""):
        return super().get(key, default)


def test_diagnostics_require_development_flag_and_exact_host(monkeypatch):
    secrets = FakeSecrets(
        TIMAN_ENVIRONMENT="development",
        TIMAN_DEV_DIAGNOSTICS_ENABLED="true",
        TIMAN_APP_BASE_URL="https://timanstat-dev.streamlit.app",
    )
    monkeypatch.setattr(diagnostics, "st", SimpleNamespace(secrets=secrets))

    assert diagnostics.diagnostics_enabled() is True

    secrets["TIMAN_APP_BASE_URL"] = "https://timanstat.streamlit.app"
    assert diagnostics.diagnostics_enabled() is False

    secrets["TIMAN_APP_BASE_URL"] = "https://timanstat-dev.streamlit.app"
    secrets["TIMAN_DEV_DIAGNOSTICS_ENABLED"] = "false"
    assert diagnostics.diagnostics_enabled() is False


def test_database_check_uses_read_only_queries(monkeypatch):
    statements = []

    class FakeConnection:
        def execute(self, statement):
            statements.append(statement)
            return self

        def fetchone(self):
            return (1,)

    @contextmanager
    def fake_connection():
        yield FakeConnection()

    monkeypatch.setattr(diagnostics, "database_connection", fake_connection)

    success, message = diagnostics._check_database()

    assert success is True
    assert "identity table is present" in message
    assert statements == [
        "SELECT 1",
        "SELECT id FROM users LIMIT 0",
    ]


def test_email_configuration_rejects_mock_provider(monkeypatch):
    settings = SimpleNamespace(
        provider="mock",
        sender_email="sender@example.com",
    )
    monkeypatch.setattr(
        diagnostics.EmailDeliverySettings,
        "from_environment",
        classmethod(lambda cls: settings),
    )

    success, message, returned_settings = diagnostics._check_email_configuration()

    assert success is False
    assert "mock" in message
    assert returned_settings is settings


def test_controlled_email_test_uses_only_configured_sender(monkeypatch):
    sent = []

    class FakeSender:
        def send(self, message):
            sent.append(message)

    settings = SimpleNamespace(sender_email="configured@example.com")
    monkeypatch.setattr(
        diagnostics,
        "build_email_sender",
        lambda supplied_settings: FakeSender(),
    )

    success, message = diagnostics._send_controlled_test_email(settings)

    assert success is True
    assert "accepted" in message
    assert len(sent) == 1
    assert sent[0].recipient == "configured@example.com"
    assert sent[0].subject == "TimanStat development email-delivery test"
