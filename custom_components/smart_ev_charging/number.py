"""Number platform for Smart EV Charging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DEFAULT_BATTERY_SUPPORT_THRESHOLD,
    DEFAULT_CLOUD_PAUSE_DURATION,
    DEFAULT_CLOUD_PAUSE_THRESHOLD,
    DEFAULT_LOAD_MARGIN,
    DEFAULT_MAIN_FUSE,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MINIMUM_SOC,
)
from .controller import SmartEVChargingController
from .entity import SmartEVChargingEntity


@dataclass(frozen=True, kw_only=True)
class SmartNumberDescription(NumberEntityDescription):
    default: float
    getter: Callable[[SmartEVChargingController], float]
    setter: Callable[[SmartEVChargingController, float], None]


def _set(name: str):
    def setter(controller: SmartEVChargingController, value: float) -> None:
        setattr(controller, name, value)
        controller.async_recalculate()
    return setter


NUMBERS = (
    SmartNumberDescription(key="main_fuse", translation_key="main_fuse", default=DEFAULT_MAIN_FUSE, native_min_value=6, native_max_value=100, native_step=1, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, mode=NumberMode.BOX, getter=lambda c: c.main_fuse_a, setter=_set("main_fuse_a")),
    SmartNumberDescription(key="load_margin", translation_key="load_margin", default=DEFAULT_LOAD_MARGIN, native_min_value=0, native_max_value=20, native_step=0.5, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, mode=NumberMode.BOX, getter=lambda c: c.load_margin_a, setter=_set("load_margin_a")),
    SmartNumberDescription(key="max_current", translation_key="max_current", default=DEFAULT_MAX_CURRENT, native_min_value=6, native_max_value=80, native_step=1, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, mode=NumberMode.BOX, getter=lambda c: c.max_current_a, setter=_set("max_current_a")),
    SmartNumberDescription(key="minimum_soc", translation_key="minimum_soc", default=DEFAULT_MINIMUM_SOC, native_min_value=0, native_max_value=100, native_step=1, native_unit_of_measurement=PERCENTAGE, mode=NumberMode.SLIDER, getter=lambda c: c.minimum_soc, setter=_set("minimum_soc")),
    SmartNumberDescription(key="cloud_pause_duration", translation_key="cloud_pause_duration", default=DEFAULT_CLOUD_PAUSE_DURATION, native_min_value=0, native_max_value=1800, native_step=10, native_unit_of_measurement=UnitOfTime.SECONDS, mode=NumberMode.BOX, getter=lambda c: c.cloud_pause_duration_s, setter=_set("cloud_pause_duration_s")),
    SmartNumberDescription(key="cloud_pause_threshold", translation_key="cloud_pause_threshold", default=DEFAULT_CLOUD_PAUSE_THRESHOLD, native_min_value=0, native_max_value=10000, native_step=50, native_unit_of_measurement=UnitOfPower.WATT, mode=NumberMode.BOX, getter=lambda c: c.cloud_pause_threshold_w, setter=_set("cloud_pause_threshold_w")),
    SmartNumberDescription(key="battery_support_threshold", translation_key="battery_support_threshold", default=DEFAULT_BATTERY_SUPPORT_THRESHOLD, native_min_value=0, native_max_value=10000, native_step=50, native_unit_of_measurement=UnitOfPower.WATT, mode=NumberMode.BOX, getter=lambda c: c.battery_support_threshold_w, setter=_set("battery_support_threshold_w")),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    controller: SmartEVChargingController = entry.runtime_data
    async_add_entities(SmartNumber(entry, controller, description) for description in NUMBERS)


class SmartNumber(SmartEVChargingEntity, RestoreEntity, NumberEntity):
    """Integration-owned setting."""

    entity_description: SmartNumberDescription

    def __init__(self, entry, controller, description: SmartNumberDescription) -> None:
        super().__init__(entry, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        return self.entity_description.getter(self.controller)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous is not None:
            try:
                self.entity_description.setter(self.controller, float(previous.state))
            except (TypeError, ValueError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        self.entity_description.setter(self.controller, value)
        self.async_write_ha_state()
