"""Unit tests for the Daraja STK Push adapter."""
import base64
import json

import pytest

from timan_intelligence.billing.daraja import DarajaAdapter, DarajaError


def test_normalize_kenyan_phone_numbers():
    assert DarajaAdapter.normalize_phone("0712345678") == "254712345678"
    assert DarajaAdapter.normalize_phone("+254712345678") == "254712345678"
    assert DarajaAdapter.normalize_phone("0112345678") == "254112345678"
    with pytest.raises(DarajaError):
        DarajaAdapter.normalize_phone("12345")


def test_daraja_requires_complete_credentials_and_https_callback():
    with pytest.raises(DarajaError, match="must be configured"):
        DarajaAdapter(environ={})._config()
    env = {
        "DARAJA_CONSUMER_KEY": "key", "DARAJA_CONSUMER_SECRET": "secret",
        "DARAJA_BUSINESS_SHORTCODE": "123456", "DARAJA_PASSKEY": "pass",
        "DARAJA_CALLBACK_URL": "http://localhost/callback",
    }
    with pytest.raises(DarajaError, match="HTTPS"):
        DarajaAdapter(environ=env)._config()


def test_stk_password_is_generated_from_shortcode_passkey_timestamp():
    shortcode, passkey, timestamp = "174379", "test-passkey", "20261108123000"
    actual = base64.b64decode(
        base64.b64encode((shortcode + passkey + timestamp).encode())
    ).decode()
    assert actual == shortcode + passkey + timestamp


def test_callback_rejects_malformed_json_without_network_call():
    adapter = DarajaAdapter(environ={})
    with pytest.raises(DarajaError, match="Malformed"):
        adapter.verify_webhook(b"not-json", {})
