"""Current address and last successful synchronization."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory

from .entity import DDNSEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AddressSensor(entry.runtime_data), LastSyncSensor(entry.runtime_data)])


class AddressSensor(DDNSEntity, SensorEntity):
    _attr_translation_key = "ipv6_address"
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator):
        super().__init__(coordinator, "ipv6_address")

    @property
    def native_value(self):
        return self.coordinator.data["address"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "interface": data["interface"],
            "result": data["result"],
            "last_changed": data["last_changed"],
        }


class LastSyncSensor(DDNSEntity, SensorEntity):
    _attr_translation_key = "last_sync"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_sync")

    @property
    def native_value(self):
        return self.coordinator.data["last_sync"]
