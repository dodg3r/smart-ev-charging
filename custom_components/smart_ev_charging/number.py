from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import SmartEVEntity


NUMBERS = {
    "main_fuse": ("Main fuse", 6, 100, 1, "A"),
    "load_margin": ("Load margin", 0, 20, 0.5, "A"),
    "cloud_pause_duration": ("Cloud pause duration", 0, 1800, 10, "s"),
    "max_current": ("Maximum charging current", 6, 80, 1, "A"),
    "cloud_pause_threshold": ("Cloud pause threshold", 0, 10000, 50, "W"),
    "battery_support_threshold": ("Battery support threshold", 0, 10000, 50, "W"),
    "minimum_soc": ("Minimum SOC", 0, 100, 1, "%"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["smart_ev_charging"][entry.entry_id]
    async_add_entities(
        SmartEVNumber(coordinator, entry, key, *spec)
        for key, spec in NUMBERS.items()
    )


class SmartEVNumber(SmartEVEntity, NumberEntity, RestoreEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, key, name, minimum, maximum, step, unit):
        super().__init__(coordinator, entry, key)
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return float(self.coordinator.settings[self.key])

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old = await self.async_get_last_state()
        if old is not None:
            try:
                self.coordinator.settings[self.key] = float(old.state)
            except (TypeError, ValueError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.settings[self.key] = value
        await self.coordinator.async_request_refresh()
