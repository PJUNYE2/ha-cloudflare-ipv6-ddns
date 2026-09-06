"""Cloudflare IPv6 DDNS, configured entirely through the Home Assistant UI."""

from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_INTERVAL, DEFAULT_INTERVAL
from .coordinator import DDNSCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass, entry):
    coordinator = DDNSCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def scheduled_sync(now):
        await coordinator.async_request_refresh()

    # Keep DDNS running even if the user disables every sensor entity.
    entry.async_on_unload(
        async_track_time_interval(
            hass,
            scheduled_sync,
            timedelta(minutes=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
    )
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
