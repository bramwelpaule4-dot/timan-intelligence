"""Safe client-IP resolution for explicitly trusted reverse proxies.

This module deliberately does not read Streamlit's st.context.ip_address.
The caller must supply the transport peer address obtained from a trusted
server-side request adapter. Forwarding headers are ignored unless that peer
is inside an explicitly configured trusted-proxy network.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Iterable


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def _parse_ip(value: str | None) -> IPAddress | None:
    """Parse a plain IPv4 or IPv6 address; reject ports and malformed input."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def load_trusted_proxy_networks(
    value: str | None = None,
) -> tuple[IPNetwork, ...]:
    """Parse trusted proxy CIDRs from explicit configuration.

    When value is omitted, TIMANSTAT_TRUSTED_PROXY_CIDRS is read from the
    process environment. An empty setting means no proxy is trusted.
    Invalid configured networks raise RuntimeError.
    """
    configured = (
        os.getenv("TIMANSTAT_TRUSTED_PROXY_CIDRS", "")
        if value is None
        else value
    )
    if not isinstance(configured, str):
        raise RuntimeError("Trusted proxy CIDRs must be configured as text.")

    networks: list[IPNetwork] = []
    for item in configured.split(","):
        entry = item.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid trusted proxy network: {entry!r}."
            ) from exc
    return tuple(networks)


def resolve_client_ip(
    peer_ip: str | None,
    forwarded_for: str | None,
    trusted_proxy_networks: Iterable[str | IPNetwork] = (),
) -> str | None:
    """Resolve client IP using X-Forwarded-For only from trusted peers.

    peer_ip must be the actual transport peer supplied by trusted server
    infrastructure, not a value copied from a request header or browser.
    An untrusted peer's address is returned and forwarding headers are
    ignored. A trusted peer with a missing or malformed chain fails closed.

    Trusted proxy addresses are removed from the right of the forwarding
    chain. The first untrusted address is the client address.
    """
    peer = _parse_ip(peer_ip)
    if peer is None:
        return None

    networks: list[IPNetwork] = []
    for network in trusted_proxy_networks:
        try:
            parsed = (
                network
                if isinstance(
                    network,
                    (ipaddress.IPv4Network, ipaddress.IPv6Network),
                )
                else ipaddress.ip_network(network, strict=False)
            )
        except (TypeError, ValueError):
            raise ValueError("Trusted proxy network configuration is invalid.")
        networks.append(parsed)

    def is_trusted(address: IPAddress) -> bool:
        return any(
            address.version == network.version and address in network
            for network in networks
        )

    if not is_trusted(peer):
        return str(peer)

    if not isinstance(forwarded_for, str) or not forwarded_for.strip():
        return None

    chain: list[IPAddress] = []
    for raw in forwarded_for.split(","):
        address = _parse_ip(raw)
        if address is None:
            return None
        chain.append(address)

    chain.append(peer)
    while chain and is_trusted(chain[-1]):
        chain.pop()

    return str(chain[-1]) if chain else None
