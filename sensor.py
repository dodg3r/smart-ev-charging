"""Sensor platform for Smart EV Charging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .controller import SmartEVChargingController
from .entity import SmartEVChargingEntity


@dataclass(frozen=True, kw_only=True)
class SmartSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SmartEVChargingController], object]
    attrs_fn: Callable[[SmartEVChargingController], dict] | None = None


SENSORS = (
    SmartSensorDescription(key="status", translation_key="status", value_fn=lambda c: c.state.status),
    SmartSensorDescription(key="limiting_reason", translation_key="limiting_reason", value_fn=lambda c: c.state.limiting_reason),
    SmartSensorDescription(
        key="debug",
        translation_key="debug",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.state.debug,
        attrs_fn=lambda c: c.state.extra,
    ),
    SmartSensorDescription(
        key="target_current",
        translation_key="target_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda c: c.state.target_current,
    ),
    SmartSensorDescription(
        key="available_current",
        translation_key="available_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda c: round(c.state.available_current, 1),
    ),
    SmartSensorDescription(key="detected_phases", translation_key="detected_phases", value_fn=lambda c: c.state.detected_phases),
    SmartSensorDescription(key="session_state", translation_key="session_state", value_fn=lambda c: c.state.session_state),
    SmartSensorDescription(
        key="last_decision",
        translation_key="last_decision",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.state.last_decision,
    ),
    SmartSensorDescription(
        key="last_command_result",
        translation_key="last_command_result",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.state.last_command_result,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    controller: SmartEVChargingController = entry.runtime_data
    async_add_entities(SmartSensor(entry, controller, description) for description in SENSORS)


class SmartSensor(SmartEVChargingEntity, SensorEntity):
    """Smart EV Charging sensor."""

    entity_description: SmartSensorDescription

    def __init__(self, entry, controller, description: SmartSensorDescription) -> None:
        super().__init__(entry, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.controller)

    @property
    def extra_state_attributes(self):
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.controller)
