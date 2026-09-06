"""Manually request a synchronized update."""

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import DDNSEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SyncButton(entry.runtime_data)])


class SyncButton(DDNSEntity, ButtonEntity):
    _attr_translation_key = "sync_now"
    _attr_icon = "mdi:cloud-sync"

    def __init__(self, coordinator):
        super().__init__(coordinator, "sync_now")

    @property
    def available(self):
        # Keep retries accessible after a transient failure.
        return True

    async def async_press(self):
        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            raise HomeAssistantError("DDNS sync failed; check integration status and logs")
