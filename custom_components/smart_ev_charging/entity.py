"""Base entities for Smart EV Charging."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .controller import SmartEVChargingController


class SmartEVChargingEntity(Entity):
    """Base entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, controller: SmartEVChargingController, key: str) -> None:
        self.entry = entry
        self.controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart EV Charging",
            model="Smart EV Charging Controller",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.controller.add_listener(self.async_write_ha_state))
