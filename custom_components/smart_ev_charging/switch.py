"""Switch platform for Smart EV Charging."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .controller import SmartEVChargingController
from .entity import SmartEVChargingEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    controller: SmartEVChargingController = entry.runtime_data
    async_add_entities([PriorityChargingSwitch(entry, controller)])


class PriorityChargingSwitch(SmartEVChargingEntity, RestoreEntity, SwitchEntity):
    """Priority charging toggle."""

    _attr_translation_key = "priority_charging"

    def __init__(self, entry, controller) -> None:
        super().__init__(entry, controller, "priority_charging")

    @property
    def is_on(self) -> bool:
        return self.controller.priority_charging

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        self.controller.priority_charging = previous is not None and previous.state == "on"
        self.controller.async_recalculate()

    async def async_turn_on(self, **kwargs) -> None:
        self.controller.priority_charging = True
        self.controller.async_recalculate()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.controller.priority_charging = False
        self.controller.async_recalculate()
        self.async_write_ha_state()
