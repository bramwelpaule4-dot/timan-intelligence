
"""Tests for TimanStat RFC 6238 TOTP security."""

import base64
import urllib.parse

import pytest

from timan_intelligence.security.totp import (
    TOTPError,
    build_totp_provisioning_uri,
    generate_totp_code,
    generate_totp_secret,
    verify_totp_code,
)


# RFC 6238 test secret:
# ASCII: 12345678901234567890
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_generated_totp_secret_is_valid_base32():
    """Generated secrets must be valid Base32 values."""

    secret = generate_totp_secret()

    decoded = base64.b32decode(
        secret + "=" * (-len(secret) % 8)
    )

    assert len(decoded) == 20
    assert secret == secret.upper()


def test_generated_totp_secrets_are_unique():
    """Independent secret generations must produce different values."""

    secrets = {
        generate_totp_secret()
        for _ in range(100)
    }

    assert len(secrets) == 100


@pytest.mark.parametrize(
    "secret_bytes",
    [
        15,
        65,
        0,
        -1,
        True,
        20.5,
        "20",
    ],
)
def test_secret_generation_rejects_invalid_lengths(secret_bytes):
    """Secret generation must reject invalid byte lengths."""

    with pytest.raises(TOTPError):
        generate_totp_secret(secret_bytes)


@pytest.mark.parametrize(
    ("timestamp", "expected_code"),
    [
        (59, "287082"),
        (1111111109, "081804"),
        (1111111111, "050471"),
        (1234567890, "005924"),
        (2000000000, "279037"),
    ],
)
def test_totp_matches_rfc_6238_sha1_vectors(timestamp, expected_code):
    """Generated codes must match RFC 6238 SHA1 test vectors."""

    assert generate_totp_code(
        RFC_SECRET,
        at_time=timestamp,
    ) == expected_code


def test_totp_code_changes_after_period_boundary():
    """TOTP codes must be based on 30-second time periods."""

    first_code = generate_totp_code(
        RFC_SECRET,
        at_time=59,
    )

    next_code = generate_totp_code(
        RFC_SECRET,
        at_time=60,
    )

    assert first_code != next_code


def test_totp_verification_accepts_valid_code():
    """A valid code for the current time must be accepted."""

    code = generate_totp_code(
        RFC_SECRET,
        at_time=90,
    )

    counter = verify_totp_code(
        RFC_SECRET,
        code,
        at_time=90,
    )

    assert counter == 3


def test_totp_verification_rejects_incorrect_code():
    """An incorrect code must not be accepted."""

    assert verify_totp_code(
        RFC_SECRET,
        "000000",
        at_time=90,
        window=0,
    ) is None


@pytest.mark.parametrize(
    "code",
    [
        "",
        "12345",
        "1234567",
        "abcdef",
        "12345a",
        "１２３４５６",
        "123 456",
        None,
        123456,
    ],
)
def test_totp_verification_rejects_invalid_code_formats(code):
    """Codes must contain exactly six ASCII digits."""

    assert verify_totp_code(
        RFC_SECRET,
        code,
        at_time=90,
    ) is None


def test_totp_verification_accepts_previous_period_within_window():
    """The configured window should allow one previous time period."""

    previous_code = generate_totp_code(
        RFC_SECRET,
        at_time=59,
    )

    assert verify_totp_code(
        RFC_SECRET,
        previous_code,
        at_time=60,
        window=1,
    ) == 1


def test_totp_verification_accepts_next_period_within_window():
    """The configured window should allow one future time period."""

    next_code = generate_totp_code(
        RFC_SECRET,
        at_time=60,
    )

    assert verify_totp_code(
        RFC_SECRET,
        next_code,
        at_time=59,
        window=1,
    ) == 2


def test_totp_verification_rejects_code_outside_window():
    """Codes outside the permitted time window must be rejected."""

    previous_code = generate_totp_code(
        RFC_SECRET,
        at_time=30,
    )

    assert verify_totp_code(
        RFC_SECRET,
        previous_code,
        at_time=90,
        window=1,
    ) is None


def test_totp_verification_rejects_replayed_counter():
    """A previously accepted counter must not be accepted again."""

    code = generate_totp_code(
        RFC_SECRET,
        at_time=90,
    )

    first_result = verify_totp_code(
        RFC_SECRET,
        code,
        at_time=90,
    )

    assert first_result == 3

    second_result = verify_totp_code(
        RFC_SECRET,
        code,
        at_time=90,
        last_accepted_counter=first_result,
    )

    assert second_result is None


def test_totp_verification_accepts_newer_counter():
    """A newer time counter must remain acceptable."""

    previous_code = generate_totp_code(
        RFC_SECRET,
        at_time=90,
    )

    previous_counter = verify_totp_code(
        RFC_SECRET,
        previous_code,
        at_time=90,
    )

    next_code = generate_totp_code(
        RFC_SECRET,
        at_time=120,
    )

    next_counter = verify_totp_code(
        RFC_SECRET,
        next_code,
        at_time=120,
        last_accepted_counter=previous_counter,
    )

    assert previous_counter == 3
    assert next_counter == 4


def test_totp_verification_rejects_replayed_previous_window_counter():
    """Replay protection must also apply to accepted previous-window codes."""

    previous_code = generate_totp_code(
        RFC_SECRET,
        at_time=59,
    )

    first_result = verify_totp_code(
        RFC_SECRET,
        previous_code,
        at_time=60,
        window=1,
    )

    assert first_result == 1

    second_result = verify_totp_code(
        RFC_SECRET,
        previous_code,
        at_time=60,
        window=1,
        last_accepted_counter=first_result,
    )

    assert second_result is None


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "INVALID!",
        "ABC",
        None,
        12345,
    ],
)
def test_totp_generation_rejects_invalid_secrets(secret):
    """Invalid or undersized secrets must not generate codes."""

    with pytest.raises(TOTPError):
        generate_totp_code(
            secret,
            at_time=90,
        )


@pytest.mark.parametrize(
    ("digits", "period_seconds"),
    [
        (8, 30),
        (5, 30),
        (6, 0),
        (6, -1),
        (True, 30),
        (6, True),
    ],
)
def test_totp_generation_rejects_invalid_configuration(
    digits,
    period_seconds,
):
    """Unsupported TOTP configuration must be rejected."""

    with pytest.raises(TOTPError):
        generate_totp_code(
            RFC_SECRET,
            at_time=90,
            digits=digits,
            period_seconds=period_seconds,
        )


@pytest.mark.parametrize(
    "window",
    [
        -1,
        11,
        True,
        1.5,
        "1",
    ],
)
def test_totp_verification_rejects_invalid_window(window):
    """Verification must reject invalid clock-drift windows."""

    with pytest.raises(TOTPError):
        verify_totp_code(
            RFC_SECRET,
            "123456",
            at_time=90,
            window=window,
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
        "90",
    ],
)
def test_totp_generation_rejects_invalid_timestamps(timestamp):
    """TOTP generation must reject invalid timestamps."""

    with pytest.raises(TOTPError):
        generate_totp_code(
            RFC_SECRET,
            at_time=timestamp,
        )


def test_totp_provisioning_uri_has_correct_parameters():
    """Provisioning URI must contain standard authenticator parameters."""

    uri = build_totp_provisioning_uri(
        RFC_SECRET,
        account_name="user@example.com",
        issuer="TimanStat",
    )

    parsed = urllib.parse.urlparse(uri)
    parameters = urllib.parse.parse_qs(parsed.query)

    assert parsed.scheme == "otpauth"
    assert parsed.netloc == "totp"
    assert parsed.path == "/TimanStat%3Auser%40example.com"

    assert parameters["secret"] == [RFC_SECRET]
    assert parameters["issuer"] == ["TimanStat"]
    assert parameters["algorithm"] == ["SHA1"]
    assert parameters["digits"] == ["6"]
    assert parameters["period"] == ["30"]


@pytest.mark.parametrize(
    ("account_name", "issuer"),
    [
        ("", "TimanStat"),
        ("   ", "TimanStat"),
        ("user@example.com", ""),
        ("user@example.com", "   "),
        (None, "TimanStat"),
        ("user@example.com", None),
    ],
)
def test_provisioning_uri_rejects_invalid_identity(
    account_name,
    issuer,
):
    """Provisioning requires a valid account name and issuer."""

    with pytest.raises(TOTPError):
        build_totp_provisioning_uri(
            RFC_SECRET,
            account_name=account_name,
            issuer=issuer,
        )
