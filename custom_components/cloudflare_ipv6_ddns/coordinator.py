"""Schedule local IPv6 discovery and Cloudflare synchronization."""

import asyncio
import logging
from datetime import datetime, timezone

from homeassistant.const import CONF_API_TOKEN
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CloudflareClient, CloudflareError, InvalidAuth
from .const import CONF_INTERFACE, CONF_PROXIED, CONF_RECORD_NAME, CONF_ZONE_ID, DOMAIN
from .ipv6 import NoIPv6Error, local_candidates

_LOGGER = logging.getLogger(__name__)


class DDNSCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.entry = entry
        self.api = CloudflareClient(async_get_clientsession(hass), entry.data[CONF_API_TOKEN])
        self._sync_lock = asyncio.Lock()
        self.last_changed = None

    async def _async_update_data(self):
        async with self._sync_lock:
            try:
                async with asyncio.timeout(40):
                    interface, candidates = await self.hass.async_add_executor_job(
                        local_candidates, self.entry.options.get(CONF_INTERFACE, "").strip()
                    )
                    address, changed = await self.api.sync(
                        self.entry.data[CONF_ZONE_ID],
                        self.entry.data[CONF_RECORD_NAME],
                        candidates,
                        self.entry.options.get(CONF_PROXIED, False),
                    )
            except InvalidAuth as exc:
                raise ConfigEntryAuthFailed(str(exc)) from exc
            except (CloudflareError, NoIPv6Error, TimeoutError) as exc:
                raise UpdateFailed(str(exc) or "DDNS timed out") from exc
            now = datetime.now(timezone.utc)
            if changed:
                self.last_changed = now
            return {
                "address": address,
                "interface": interface,
                "last_sync": now,
                "last_changed": self.last_changed,
                "result": "updated" if changed else "unchanged",
            }
