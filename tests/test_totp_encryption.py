
"""Security tests for TimanStat TOTP secret encryption."""

import sys
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from timan_intelligence.security.totp_encryption import (
    CIPHERTEXT_PREFIX,
    ENCRYPTION_KEY_ENV,
    SecretEncryptionError,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_encryption_key,
)


@pytest.fixture
def encryption_key():
    """Provide an independent Fernet key for each test."""

    return generate_totp_encryption_key()


def test_generated_encryption_key_is_valid_fernet_key():
    """Generated keys must be accepted by Fernet."""

    key = generate_totp_encryption_key()

    assert isinstance(key, str)
    assert len(key) == 44

    fernet = Fernet(key.encode("ascii"))

    assert fernet is not None


def test_generated_encryption_keys_are_unique():
    """Independent key generations must produce different keys."""

    keys = {
        generate_totp_encryption_key()
        for _ in range(100)
    }

    assert len(keys) == 100


def test_encrypt_and_decrypt_totp_secret(encryption_key):
    """An encrypted secret must decrypt to its original value."""

    secret = "GEZDGNBVGYTQOJQGEZDGNBVGYTQOJQ"

    encrypted = encrypt_totp_secret(
        secret,
        encryption_key=encryption_key,
    )

    decrypted = decrypt_totp_secret(
        encrypted,
        encryption_key=encryption_key,
    )

    assert decrypted == secret


def test_encrypted_secret_has_version_prefix(encryption_key):
    """Encrypted values must identify their encryption format."""

    encrypted = encrypt_totp_secret(
        "TESTSECRET123456",
        encryption_key=encryption_key,
    )

    assert encrypted.startswith(CIPHERTEXT_PREFIX)


def test_encrypted_secret_does_not_expose_plaintext(encryption_key):
    """Ciphertext must not contain the original secret."""

    secret = "MYPRIVATEAUTHENTICATORSECRET"

    encrypted = encrypt_totp_secret(
        secret,
        encryption_key=encryption_key,
    )

    assert secret not in encrypted
    assert encrypted != secret


def test_encryption_uses_randomised_ciphertext(encryption_key):
    """Encrypting the same secret twice must produce different ciphertexts."""

    secret = "TESTSECRET123456"

    first = encrypt_totp_secret(
        secret,
        encryption_key=encryption_key,
    )

    second = encrypt_totp_secret(
        secret,
        encryption_key=encryption_key,
    )

    assert first != second

    assert decrypt_totp_secret(
        first,
        encryption_key=encryption_key,
    ) == secret

    assert decrypt_totp_secret(
        second,
        encryption_key=encryption_key,
    ) == secret


def test_encryption_supports_unicode_secrets(encryption_key):
    """UTF-8 secret values must survive encryption and decryption."""

    secret = "TimanStat-秘密-🔐-123456"

    encrypted = encrypt_totp_secret(
        secret,
        encryption_key=encryption_key,
    )

    assert decrypt_totp_secret(
        encrypted,
        encryption_key=encryption_key,
    ) == secret


def test_encryption_rejects_empty_secret(encryption_key):
    """An empty plaintext secret must not be encrypted."""

    with pytest.raises(SecretEncryptionError):
        encrypt_totp_secret(
            "",
            encryption_key=encryption_key,
        )


@pytest.mark.parametrize(
    "secret",
    [
        None,
        123456,
        b"secret",
        [],
        {},
    ],
)
def test_encryption_rejects_invalid_secret_types(
    secret,
    encryption_key,
):
    """Only non-empty string secrets may be encrypted."""

    with pytest.raises(SecretEncryptionError):
        encrypt_totp_secret(
            secret,
            encryption_key=encryption_key,
        )


def test_decryption_rejects_wrong_encryption_key(encryption_key):
    """Ciphertext must not decrypt with a different key."""

    encrypted = encrypt_totp_secret(
        "TESTSECRET123456",
        encryption_key=encryption_key,
    )

    wrong_key = generate_totp_encryption_key()

    with pytest.raises(SecretEncryptionError):
        decrypt_totp_secret(
            encrypted,
            encryption_key=wrong_key,
        )


def test_decryption_rejects_tampered_ciphertext(encryption_key):
    """Modified ciphertext must fail authenticated decryption."""

    encrypted = encrypt_totp_secret(
        "TESTSECRET123456",
        encryption_key=encryption_key,
    )

    token = encrypted[len(CIPHERTEXT_PREFIX):]

    replacement = "A" if token[-1] != "A" else "B"

    tampered = (
        CIPHERTEXT_PREFIX
        + token[:-1]
        + replacement
    )

    with pytest.raises(SecretEncryptionError):
        decrypt_totp_secret(
            tampered,
            encryption_key=encryption_key,
        )


@pytest.mark.parametrize(
    "encrypted_secret",
    [
        "",
        None,
        123456,
        b"encrypted",
        "unsupported-format",
        "plaintext-secret",
        CIPHERTEXT_PREFIX,
        CIPHERTEXT_PREFIX + "invalid-token",
    ],
)
def test_decryption_rejects_invalid_encrypted_values(
    encrypted_secret,
    encryption_key,
):
    """Invalid or unrecognised ciphertext must never be accepted."""

    with pytest.raises(SecretEncryptionError):
        decrypt_totp_secret(
            encrypted_secret,
            encryption_key=encryption_key,
        )


@pytest.mark.parametrize(
    "encryption_key_value",
    [
        "",
        "   ",
        "invalid-key",
        "not-a-valid-fernet-key",
        "秘密",
        None,
        12345,
    ],
)
def test_encryption_rejects_invalid_keys(encryption_key_value):
    """Invalid encryption keys must cause explicit errors."""

    with pytest.raises(SecretEncryptionError):
        encrypt_totp_secret(
            "TESTSECRET123456",
            encryption_key=encryption_key_value,
        )


def test_encryption_key_can_be_loaded_from_environment(
    encryption_key,
    monkeypatch,
):
    """Environment configuration must supply the encryption key."""

    monkeypatch.setenv(
        ENCRYPTION_KEY_ENV,
        encryption_key,
    )

    encrypted = encrypt_totp_secret("TESTSECRET123456")

    assert decrypt_totp_secret(encrypted) == "TESTSECRET123456"


def test_streamlit_secrets_can_supply_encryption_key(
    encryption_key,
    monkeypatch,
):
    """Streamlit Secrets must be supported when environment key is absent."""

    monkeypatch.delenv(
        ENCRYPTION_KEY_ENV,
        raising=False,
    )

    fake_streamlit = SimpleNamespace(
        secrets={
            ENCRYPTION_KEY_ENV: encryption_key,
        }
    )

    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        fake_streamlit,
    )

    encrypted = encrypt_totp_secret("TESTSECRET123456")

    assert decrypt_totp_secret(encrypted) == "TESTSECRET123456"


def test_missing_encryption_key_fails_closed(monkeypatch):
    """The encryption module must not generate or assume a missing key."""

    monkeypatch.delenv(
        ENCRYPTION_KEY_ENV,
        raising=False,
    )

    fake_streamlit = SimpleNamespace(secrets={})

    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        fake_streamlit,
    )

    with pytest.raises(SecretEncryptionError):
        encrypt_totp_secret("TESTSECRET123456")


def test_existing_ciphertext_cannot_be_decrypted_after_key_rotation(
    encryption_key,
):
    """Changing the encryption key must invalidate old ciphertext."""

    encrypted = encrypt_totp_secret(
        "TESTSECRET123456",
        encryption_key=encryption_key,
    )

    rotated_key = generate_totp_encryption_key()

    with pytest.raises(SecretEncryptionError):
        decrypt_totp_secret(
            encrypted,
            encryption_key=rotated_key,
        )
