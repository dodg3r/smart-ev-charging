from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import MODES, PHASE_MODES
from .entity import SmartEVEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["smart_ev_charging"][entry.entry_id]
    async_add_entities([
        SmartEVSelect(coordinator, entry, "mode", "Charging mode", MODES),
        SmartEVSelect(coordinator, entry, "phase_mode", "Phase mode", PHASE_MODES),
    ])


class SmartEVSelect(SmartEVEntity, SelectEntity, RestoreEntity):
    def __init__(self, coordinator, entry, key, name, options):
        super().__init__(coordinator, entry, key)
        self._attr_name = name
        self._attr_options = options

    @property
    def current_option(self):
        return self.coordinator.settings[self.key]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old = await self.async_get_last_state()
        if old is not None and old.state in self.options:
            self.coordinator.settings[self.key] = old.state

    async def async_select_option(self, option: str) -> None:
        self.coordinator.settings[self.key] = option
        await self.coordinator.async_request_refresh()
