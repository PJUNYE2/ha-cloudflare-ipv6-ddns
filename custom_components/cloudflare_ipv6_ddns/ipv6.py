"""Read stable IPv6 addresses from the local Linux network namespace."""

import socket
from dataclasses import dataclass
from ipaddress import IPv6Address, IPv6Network
from pathlib import Path

PUBLIC_RANGE = IPv6Network("2000::/3")
UNUSABLE_FLAGS = 0x01 | 0x04 | 0x08 | 0x20 | 0x40


class NoIPv6Error(Exception):
    """No suitable local IPv6 address or interface."""


@dataclass(frozen=True)
class Address:
    interface: str
    ip: str
    scope: int
    flags: int

    @property
    def eligible(self):
        address = IPv6Address(self.ip)
        return (
            self.scope == 0
            and not self.flags & UNUSABLE_FLAGS
            and address.is_global
            and address in PUBLIC_RANGE
        )


def parse_addresses(text):
    """Parse /proc/net/if_inet6; retain temporary addresses for route matching."""
    result = []
    for line in text.splitlines():
        raw, _, _, scope, flags, interface = line.split()
        result.append(
            Address(interface, str(IPv6Address(int(raw, 16))), int(scope, 16), int(flags, 16))
        )
    return result


def route_source():
    """Ask the kernel for an IPv6 route without transmitting a packet."""
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
        sock.connect(("2606:4700:4700::1111", 443))
        return str(IPv6Address(sock.getsockname()[0]))


def select_addresses(addresses, interface="", source=None):
    """Only choose addresses on the selected/default-route interface."""
    if not interface:
        interfaces = {a.interface for a in addresses if a.ip == source}
        if len(interfaces) != 1:
            raise NoIPv6Error("Cannot identify IPv6 egress; select the HAOS interface in options")
        interface = interfaces.pop()
    eligible = sorted({a.ip for a in addresses if a.interface == interface and a.eligible})
    if not eligible:
        raise NoIPv6Error(f"No stable public IPv6 on {interface}; existing DNS is preserved")
    return interface, eligible


def local_candidates(interface=""):
    """Called only in an executor; HAOS Core shares its VM's network."""
    try:
        addresses = parse_addresses(Path("/proc/net/if_inet6").read_text())
        source = None if interface else route_source()
        return select_addresses(addresses, interface, source)
    except (OSError, ValueError) as exc:
        raise NoIPv6Error("Cannot read local IPv6; check HAOS IPv6 networking") from exc
