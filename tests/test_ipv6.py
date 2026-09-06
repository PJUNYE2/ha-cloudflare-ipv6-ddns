from ipaddress import IPv6Address

import pytest


def row(ip, flags=0, interface="eth0", scope=0):
    return f"{int(IPv6Address(ip)):032x} 02 40 {scope:02x} {flags:x} {interface}"


@pytest.mark.parametrize("flags", [1, 4, 8, 32, 64, 65])
def test_excludes_unusable_flags(ipv6, flags):
    addresses = ipv6.parse_addresses(row("240e::1", flags))
    assert not addresses[0].eligible


@pytest.mark.parametrize(
    "ip", ["fe80::1", "fd00::1", "fc00::1", "::1", "::", "ff02::1", "2001:db8::1"]
)
def test_excludes_non_public(ipv6, ip):
    assert not ipv6.parse_addresses(row(ip))[0].eligible


def test_stable_privacy_and_temporary_route_source(ipv6):
    addresses = ipv6.parse_addresses(
        "\n".join(
            [
                row("240e::1", 0x800),
                row("240e::2", 1),
                row("240e:1::1", 0, "eth1"),
            ]
        )
    )
    assert ipv6.select_addresses(addresses, source="240e::2") == ("eth0", ["240e::1"])


def test_explicit_interface(ipv6):
    addresses = ipv6.parse_addresses(row("240e:1::1", 0x80, "enp0s18"))
    assert ipv6.select_addresses(addresses, "enp0s18") == ("enp0s18", ["240e:1::1"])
    with pytest.raises(ipv6.NoIPv6Error):
        ipv6.select_addresses(addresses, "vmbr0")


def test_no_route_never_guesses_other_interface(ipv6):
    addresses = ipv6.parse_addresses(row("240e::1"))
    with pytest.raises(ipv6.NoIPv6Error):
        ipv6.select_addresses(addresses, source="240e::2")


def test_proc_unavailable(ipv6, monkeypatch):
    def fail(self):
        raise FileNotFoundError()

    monkeypatch.setattr(ipv6.Path, "read_text", fail)
    with pytest.raises(ipv6.NoIPv6Error):
        ipv6.local_candidates()
