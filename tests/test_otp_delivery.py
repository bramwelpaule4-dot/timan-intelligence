"""Tests for provider-neutral TimanStat OTP delivery."""

import pytest

from timan_intelligence.identity.email_delivery import MockEmailSender
from timan_intelligence.security.otp_delivery import (
    OTPDeliveryError,
    OutboundSMS,
    send_email_otp,
    send_sms_otp,
)


class RecordingSMSSender:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)


def test_email_otp_uses_existing_email_sender():
    sender = MockEmailSender()

    send_email_otp(
        "recovery@example.com",
        "123456",
        "verify_recovery_email",
        sender=sender,
    )

    assert len(sender.sent_messages) == 1
    message = sender.sent_messages[0]
    assert message.recipient == "recovery@example.com"
    assert message.subject == "Verify your TimanStat recovery email"
    assert "123456" in message.body
    assert "5 minutes" in message.body
    assert "Never share this code" in message.body


@pytest.mark.parametrize(
    ("recipient", "code", "purpose"),
    [
        ("", "123456", "verify_recovery_email"),
        ("recovery@example.com", "12345", "verify_recovery_email"),
        ("recovery@example.com", "123456", ""),
    ],
)
def test_email_otp_rejects_invalid_inputs(recipient, code, purpose):
    with pytest.raises(OTPDeliveryError):
        send_email_otp(
            recipient,
            code,
            purpose,
            sender=MockEmailSender(),
        )


def test_sms_otp_fails_closed_without_provider():
    with pytest.raises(OTPDeliveryError, match="SMS delivery is not configured"):
        send_sms_otp("+254712345678", "123456", "verify_phone")


def test_sms_otp_uses_supplied_provider_adapter():
    sender = RecordingSMSSender()

    send_sms_otp(
        "+254712345678",
        "123456",
        "verify_phone",
        sender=sender,
    )

    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert isinstance(message, OutboundSMS)
    assert message.recipient == "+254712345678"
    assert "123456" in message.body
    assert "5 minutes" in message.body


def test_sms_otp_rejects_non_international_destination():
    with pytest.raises(OTPDeliveryError, match="E.164"):
        send_sms_otp(
            "0712345678",
            "123456",
            "verify_phone",
            sender=RecordingSMSSender(),
        )
