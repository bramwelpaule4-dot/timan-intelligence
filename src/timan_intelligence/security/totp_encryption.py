
"""Authenticated encryption for TimanStat TOTP secrets."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTION_KEY_ENV = "TIMANSTAT_TOTP_ENCRYPTION_KEY"
CIPHERTEXT_PREFIX = "fernet:v1:"


class SecretEncryptionError(Exception):
    """Raised when TOTP secret encryption or decryption fails."""


def generate_totp_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Generate this key once and store it securely outside the database.
    Do not call this automatically during application startup.
    """

    return Fernet.generate_key().decode("ascii")


def _get_encryption_key() -> str:
    """Retrieve the encryption key from the environment or Streamlit Secrets."""

    environment_key = os.getenv(ENCRYPTION_KEY_ENV, "").strip()

    if environment_key:
        return environment_key

    try:
        import streamlit as st

        streamlit_key = st.secrets.get(ENCRYPTION_KEY_ENV, "")

        if isinstance(streamlit_key, str) and streamlit_key.strip():
            return streamlit_key.strip()

    except Exception:
        # Streamlit may be unavailable outside a configured web deployment.
        pass

    raise SecretEncryptionError(
        f"Encryption key is not configured. Set {ENCRYPTION_KEY_ENV} "
        "or configure it in Streamlit Secrets."
    )


def _get_fernet(encryption_key: str | None = None) -> Fernet:
    """Create a Fernet instance using a validated encryption key."""

    if encryption_key is None:
        encryption_key = _get_encryption_key()

    if not isinstance(encryption_key, str) or not encryption_key.strip():
        raise SecretEncryptionError("Encryption key must be a non-empty string.")

    try:
        key_bytes = encryption_key.encode("ascii")
        return Fernet(key_bytes)

    except (UnicodeEncodeError, ValueError, TypeError) as exc:
        raise SecretEncryptionError(
            "The configured encryption key is invalid."
        ) from exc


def encrypt_totp_secret(
    secret: str,
    encryption_key: str | None = None,
) -> str:
    """Encrypt a TOTP secret and return versioned ciphertext."""

    if not isinstance(secret, str) or not secret:
        raise SecretEncryptionError(
            "TOTP secret must be a non-empty string."
        )

    fernet = _get_fernet(encryption_key)

    try:
        encrypted = fernet.encrypt(secret.encode("utf-8"))
        return CIPHERTEXT_PREFIX + encrypted.decode("ascii")

    except (UnicodeEncodeError, ValueError, TypeError) as exc:
        raise SecretEncryptionError(
            "Unable to encrypt the TOTP secret."
        ) from exc


def decrypt_totp_secret(
    encrypted_secret: str,
    encryption_key: str | None = None,
) -> str:
    """Decrypt a versioned TOTP ciphertext."""

    if not isinstance(encrypted_secret, str) or not encrypted_secret:
        raise SecretEncryptionError(
            "Encrypted TOTP secret must be a non-empty string."
        )

    if not encrypted_secret.startswith(CIPHERTEXT_PREFIX):
        raise SecretEncryptionError(
            "Unsupported or unrecognised encrypted-secret format."
        )

    token = encrypted_secret[len(CIPHERTEXT_PREFIX):]

    if not token:
        raise SecretEncryptionError(
            "Encrypted TOTP secret contains no ciphertext."
        )

    fernet = _get_fernet(encryption_key)

    try:
        decrypted = fernet.decrypt(token.encode("ascii"))
        return decrypted.decode("utf-8")

    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError, ValueError) as exc:
        raise SecretEncryptionError(
            "Unable to decrypt the TOTP secret. The ciphertext may be "
            "corrupted or the encryption key may be incorrect."
        ) from exc
