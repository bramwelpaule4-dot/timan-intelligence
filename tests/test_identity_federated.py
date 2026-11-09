"""Tests for federated identity validation and account provisioning."""

from timan_intelligence.identity.federated import (
    authenticate_federated_identity,
)


def test_unverified_provider_email_is_rejected_before_database_access():
    assert authenticate_federated_identity(
        provider="google",
        subject="google-subject-1",
        email="tester@example.com",
        email_verified=False,
        full_name="Test User",
    ) is None


def test_unsupported_provider_is_rejected():
    assert authenticate_federated_identity(
        provider="github",
        subject="github-subject-1",
        email="tester@example.com",
        email_verified=True,
        full_name="Test User",
    ) is None


def test_malformed_email_is_rejected():
    assert authenticate_federated_identity(
        provider="google",
        subject="google-subject-1",
        email="not-an-email",
        email_verified=True,
        full_name="Test User",
    ) is None


def test_empty_subject_is_rejected():
    assert authenticate_federated_identity(
        provider="microsoft",
        subject="",
        email="tester@example.com",
        email_verified=True,
        full_name="Test User",
    ) is None
