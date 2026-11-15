"""Tests for safe Gmail OAuth diagnostic details."""

from timan_intelligence.identity.email_delivery import EmailDeliveryError


def test_email_delivery_error_retains_allowlisted_oauth_diagnostics():
    error = EmailDeliveryError(
        "Gmail API delivery failed.",
        stage="token_refresh",
        oauth_error="invalid_grant",
        http_status=400,
        api_reason="invalidCredentials",
    )

    assert error.stage == "token_refresh"
    assert error.oauth_error == "invalid_grant"
    assert error.http_status == 400
    assert error.api_reason == "invalidCredentials"


def test_email_delivery_error_rejects_untrusted_diagnostic_values():
    error = EmailDeliveryError(
        "Gmail API delivery failed.",
        stage="token_refresh",
        oauth_error="refresh-token-secret-value",
        http_status=999,
        api_reason="private provider response with token",
    )

    assert error.oauth_error is None
    assert error.http_status is None
    assert error.api_reason is None
