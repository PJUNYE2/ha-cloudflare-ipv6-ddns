"""Small asynchronous Cloudflare client; never log credentials or response bodies."""

import asyncio
import re
from ipaddress import IPv6Address

import aiohttp

BASE_URL = "https://api.cloudflare.com/client/v4"
LABEL = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$")


class CloudflareError(Exception):
    """An API or DNS conflict error."""


class InvalidAuth(CloudflareError):
    """Token is invalid or lacks required permissions."""


class CannotConnect(CloudflareError):
    """Network, rate limit or service failure."""


class RecordConflict(CloudflareError):
    """Multiple AAAA records or a CNAME exist for this name."""


class ZoneNotFound(CloudflareError):
    """Token has no visible zone matching the requested hostname."""


def normalize_hostname(value):
    """Accept an exact fully qualified DNS hostname, not a URL/wildcard."""
    name = value.strip().rstrip(".").encode("idna").decode().lower()
    if len(name) > 253 or "." not in name or any(not LABEL.fullmatch(x) for x in name.split(".")):
        raise ValueError("Enter a full hostname such as ha.example.com")
    return name


class CloudflareClient:
    def __init__(self, session, token):
        self.session = session
        self.token = token.strip()

    async def request(self, method, path, *, params=None, payload=None):
        try:
            async with self.session.request(
                method,
                BASE_URL + path,
                headers={"Authorization": f"Bearer {self.token}"},
                params=params,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise InvalidAuth("Check token and Zone Read / DNS Edit permissions")
                if response.status == 429 or response.status >= 500:
                    raise CannotConnect(
                        f"Cloudflare is temporarily unavailable (HTTP {response.status})"
                    )
                if response.status >= 300:
                    raise CloudflareError(f"Cloudflare request failed (HTTP {response.status})")
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise CannotConnect("Cannot reach Cloudflare") from exc
        if data.get("success") is not True:
            codes = {error.get("code") for error in data.get("errors", [])}
            if codes & {10000, 9103, 9106, 9109}:
                raise InvalidAuth("Cloudflare rejected token")
            raise CloudflareError("Cloudflare rejected the DNS request")
        return data

    async def find_zone(self, name):
        """Resolve the most specific matching zone, including delegated subzones."""
        labels = name.split(".")
        async with asyncio.timeout(45):
            for index in range(len(labels) - 1):
                data = await self.request(
                    "GET", "/zones", params={"name": ".".join(labels[index:]), "per_page": 50}
                )
                if data["result"]:
                    return data["result"][0]["id"]
        raise ZoneNotFound("No matching zone; grant Zone Read and DNS Edit for this domain")

    async def record(self, zone, name):
        data = await self.request(
            "GET", f"/zones/{zone}/dns_records", params={"name": name, "per_page": 100}
        )
        records = data["result"]
        if data.get("result_info", {}).get("total_pages", 1) > 1:
            raise RecordConflict("Too many records for this name")
        if any(r["type"] == "CNAME" for r in records):
            raise RecordConflict("A CNAME exists for this name")
        matches = [r for r in records if r["type"] == "AAAA"]
        if len(matches) > 1:
            raise RecordConflict("More than one AAAA exists; use a dedicated DDNS hostname")
        return matches[0] if matches else None

    async def sync(self, zone, name, candidates, proxied=False):
        """Read before each sync to repair external changes; PATCH preserves metadata."""
        if not candidates:
            raise ValueError("No IPv6 candidates; refusing to alter DNS")
        record = await self.record(zone, name)
        old = str(IPv6Address(record["content"])) if record else None
        target = old if old in candidates else candidates[0]
        changed = not record or old != target or record.get("proxied", False) != proxied
        if changed:
            payload = {"content": target, "proxied": proxied}
            if record:
                await self.request(
                    "PATCH", f"/zones/{zone}/dns_records/{record['id']}", payload=payload
                )
            else:
                payload.update(type="AAAA", name=name, ttl=1 if proxied else 300)
                await self.request("POST", f"/zones/{zone}/dns_records", payload=payload)
        return target, changed
