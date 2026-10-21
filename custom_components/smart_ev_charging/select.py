"""Select platform for Smart EV Charging."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CHARGING_MODES, MODE_OFF
from .controller import SmartEVChargingController
from .entity import SmartEVChargingEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    controller: SmartEVChargingController = entry.runtime_data
    async_add_entities([ChargingModeSelect(entry, controller)])


class ChargingModeSelect(SmartEVChargingEntity, RestoreEntity, SelectEntity):
    """Charging mode selector."""

    _attr_translation_key = "charging_mode"
    _attr_options = CHARGING_MODES

    def __init__(self, entry, controller) -> None:
        super().__init__(entry, controller, "charging_mode")

    @property
    def current_option(self) -> str:
        return self.controller.mode

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous is not None and previous.state in CHARGING_MODES:
            self.controller.mode = previous.state
        else:
            self.controller.mode = MODE_OFF
        self.controller.async_recalculate()

    async def async_select_option(self, option: str) -> None:
        self.controller.mode = option
        self.controller.async_recalculate()
        self.async_write_ha_state()
