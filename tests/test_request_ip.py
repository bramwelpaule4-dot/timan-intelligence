"""Tests for trusted-proxy-aware client IP resolution."""

import pytest

from timan_intelligence.security.request_ip import (
    load_trusted_proxy_networks,
    resolve_client_ip,
)


def test_untrusted_peer_cannot_spoof_forwarded_for():
    assert resolve_client_ip(
        "198.51.100.20",
        "203.0.113.99",
        ["10.0.0.0/8"],
    ) == "198.51.100.20"


def test_trusted_proxy_uses_forwarded_client_address():
    assert resolve_client_ip(
        "10.0.0.5",
        "203.0.113.7",
        ["10.0.0.0/8"],
    ) == "203.0.113.7"


def test_trusted_proxy_chain_discards_trusted_hops_from_right():
    assert resolve_client_ip(
        "10.0.0.3",
        "203.0.113.7, 10.0.0.2",
        ["10.0.0.0/8"],
    ) == "203.0.113.7"


def test_trusted_proxy_chain_returns_nearest_untrusted_hop():
    assert resolve_client_ip(
        "10.0.0.3",
        "203.0.113.7, 192.0.2.8, 10.0.0.2",
        ["10.0.0.0/8"],
    ) == "192.0.2.8"


def test_ipv6_peer_and_forwarded_client_are_supported():
    assert resolve_client_ip(
        "2001:db8:ffff::1",
        "2001:db8::25",
        ["2001:db8:ffff::/48"],
    ) == "2001:db8::25"


def test_ipv4_and_ipv6_network_versions_are_not_mixed():
    assert resolve_client_ip(
        "10.0.0.5",
        "2001:db8::25",
        ["10.0.0.0/8"],
    ) == "2001:db8::25"


@pytest.mark.parametrize(
    "peer, forwarded",
    [
        (None, "203.0.113.7"),
        ("not-an-ip", "203.0.113.7"),
        ("10.0.0.5", None),
        ("10.0.0.5", ""),
        ("10.0.0.5", "203.0.113.7, invalid"),
        ("10.0.0.5", "203.0.113.7:1234"),
    ],
)
def test_missing_or_malformed_trusted_request_data_fails_closed(
    peer,
    forwarded,
):
    assert resolve_client_ip(
        peer,
        forwarded,
        ["10.0.0.0/8"],
    ) is None


def test_all_trusted_forwarding_hops_do_not_invent_client():
    assert resolve_client_ip(
        "10.0.0.3",
        "10.0.0.1, 10.0.0.2",
        ["10.0.0.0/8"],
    ) is None


def test_no_trusted_proxy_configuration_uses_peer_only():
    assert resolve_client_ip(
        "192.0.2.10",
        "203.0.113.7",
    ) == "192.0.2.10"


def test_trusted_proxy_cidrs_are_loaded_from_environment(monkeypatch):
    monkeypatch.setenv(
        "TIMANSTAT_TRUSTED_PROXY_CIDRS",
        "10.0.0.0/8, 2001:db8:ffff::/48",
    )

    networks = load_trusted_proxy_networks()

    assert len(networks) == 2
    assert resolve_client_ip(
        "10.0.0.5",
        "203.0.113.7",
        networks,
    ) == "203.0.113.7"


def test_invalid_trusted_proxy_configuration_fails_closed():
    with pytest.raises(RuntimeError, match="Invalid trusted proxy"):
        load_trusted_proxy_networks("10.0.0.0/8,not-a-network")
