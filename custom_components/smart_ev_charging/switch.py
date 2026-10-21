from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import SmartEVEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["smart_ev_charging"][entry.entry_id]
    async_add_entities([
        SmartEVPrioritySwitch(coordinator, entry),
    ])


class SmartEVPrioritySwitch(SmartEVEntity, SwitchEntity, RestoreEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "priority_charging")
        self._attr_name = "Priority charging"

    @property
    def is_on(self):
        return bool(self.coordinator.settings["priority_charging"])

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old = await self.async_get_last_state()
        if old is not None:
            self.coordinator.settings["priority_charging"] = old.state == "on"

    async def async_turn_on(self, **kwargs):
        self.coordinator.settings["priority_charging"] = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        self.coordinator.settings["priority_charging"] = False
        await self.coordinator.async_request_refresh()
