
"""Security tests for TimanStat password hashing and verification."""

import pytest

from timan_intelligence.identity.service import (
    PASSWORD_KEY_BYTES,
    PASSWORD_MAX_BYTES,
    PASSWORD_SALT_BYTES,
    PASSWORD_SCRYPT_N,
    PASSWORD_SCRYPT_P,
    PASSWORD_SCRYPT_R,
    _hash_password,
    _verify_password,
)


VALID_PASSWORD = "SecureTestPassword123!"


def test_password_hash_uses_scrypt():
    """Password hashes should identify the scrypt algorithm."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert password_hash.startswith("scrypt$")


def test_password_hash_contains_expected_parameters():
    """Generated hashes should contain the configured scrypt parameters."""

    password_hash = _hash_password(VALID_PASSWORD)

    algorithm, n, r, p, salt, derived_key = password_hash.split("$")

    assert algorithm == "scrypt"
    assert int(n) == PASSWORD_SCRYPT_N
    assert int(r) == PASSWORD_SCRYPT_R
    assert int(p) == PASSWORD_SCRYPT_P
    assert len(bytes.fromhex(salt)) == PASSWORD_SALT_BYTES
    assert len(bytes.fromhex(derived_key)) == PASSWORD_KEY_BYTES


def test_password_hash_uses_unique_random_salts():
    """Identical passwords should produce different stored hashes."""

    first_hash = _hash_password(VALID_PASSWORD)
    second_hash = _hash_password(VALID_PASSWORD)

    assert first_hash != second_hash


def test_password_verification_accepts_correct_password():
    """The correct password should verify successfully."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert _verify_password(VALID_PASSWORD, password_hash) is True


def test_password_verification_rejects_incorrect_password():
    """An incorrect password should fail verification."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert _verify_password(
        "DifferentSecurePassword123!",
        password_hash,
    ) is False


def test_password_verification_rejects_wrong_algorithm():
    """Unsupported password-hashing algorithms must be rejected."""

    password_hash = _hash_password(VALID_PASSWORD)
    tampered_hash = password_hash.replace("scrypt$", "md5$", 1)

    assert _verify_password(VALID_PASSWORD, tampered_hash) is False


@pytest.mark.parametrize(
    "parameter_index, replacement",
    [
        (1, "2"),
        (2, "16"),
        (3, "2"),
    ],
)
def test_password_verification_rejects_modified_scrypt_parameters(
    parameter_index,
    replacement,
):
    """Untrusted scrypt parameters must not control verification cost."""

    parts = _hash_password(VALID_PASSWORD).split("$")
    parts[parameter_index] = replacement

    tampered_hash = "$".join(parts)

    assert _verify_password(VALID_PASSWORD, tampered_hash) is False


@pytest.mark.parametrize(
    "malformed_hash",
    [
        "",
        "invalid",
        "scrypt",
        "scrypt$",
        "scrypt$16384$8$1",
        "scrypt$16384$8$1$not-hex$not-hex",
        "scrypt$16384$8$1$00$00",
        "scrypt$16384$8$1$" + ("00" * 16) + "$" + ("00" * 64),
        "scrypt$16384$8$1$" + ("00" * 16) + "$" + ("zz" * 64),
    ],
)
def test_password_verification_rejects_malformed_hashes(
    malformed_hash,
):
    """Malformed stored hashes must fail safely."""

    assert _verify_password(VALID_PASSWORD, malformed_hash) is False


@pytest.mark.parametrize(
    "password",
    [
        None,
        12345,
        "",
    ],
)
def test_password_verification_rejects_invalid_password_inputs(password):
    """Invalid password input types and empty values must be rejected."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert _verify_password(password, password_hash) is False


def test_password_hashing_rejects_short_passwords():
    """Registration hashing must reject passwords shorter than 12 characters."""

    with pytest.raises(ValueError, match="at least 12 characters"):
        _hash_password("Short123!")


def test_password_hashing_rejects_passwords_exceeding_byte_limit():
    """Password hashing must enforce the maximum UTF-8 byte length."""

    oversized_password = "a" * (PASSWORD_MAX_BYTES + 1)

    with pytest.raises(ValueError, match="must not exceed"):
        _hash_password(oversized_password)


def test_password_verification_rejects_passwords_exceeding_byte_limit():
    """Verification must reject oversized passwords before hashing."""

    password_hash = _hash_password(VALID_PASSWORD)
    oversized_password = "a" * (PASSWORD_MAX_BYTES + 1)

    assert _verify_password(
        oversized_password,
        password_hash,
    ) is False


def test_password_hashing_supports_unicode_passwords():
    """Valid Unicode passwords should be hashed and verified correctly."""

    password = "TïmanStat-Secure-密码-2026!"

    password_hash = _hash_password(password)

    assert _verify_password(password, password_hash) is True


def test_password_verification_rejects_modified_salt():
    """Changing the stored salt must invalidate password verification."""

    parts = _hash_password(VALID_PASSWORD).split("$")
    parts[4] = ("00" * PASSWORD_SALT_BYTES)

    tampered_hash = "$".join(parts)

    assert _verify_password(VALID_PASSWORD, tampered_hash) is False


def test_password_verification_rejects_modified_derived_key():
    """Changing the derived key must invalidate password verification."""

    parts = _hash_password(VALID_PASSWORD).split("$")
    original_key = bytes.fromhex(parts[5])
    modified_key = bytes([original_key[0] ^ 1]) + original_key[1:]
    parts[5] = modified_key.hex()

    tampered_hash = "$".join(parts)

    assert _verify_password(VALID_PASSWORD, tampered_hash) is False
