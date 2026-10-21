from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .entity import SmartEVEntity


SENSORS = {
    "status": "Status",
    "info": "Limiting reason",
    "debug": "Debug",
    "target_current": "Target current",
    "available_current": "Available current",
    "detected_phases": "Detected phases",
    "session_state": "Session state",
    "last_decision": "Last decision",
    "planner_status": "Planner status",
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["smart_ev_charging"][entry.entry_id]
    async_add_entities(
        SmartEVSensor(coordinator, entry, key, name)
        for key, name in SENSORS.items()
    )


class SmartEVSensor(SmartEVEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry, key)
        self._attr_name = name

    @property
    def native_value(self):
        decision = self.coordinator.decision
        if decision is None:
            return None

        if self.key == "status":
            return decision.status
        if self.key == "info":
            return decision.info or "-"
        if self.key == "debug":
            return decision.debug
        if self.key == "target_current":
            return decision.target_current if decision.target_current is not None else 0
        if self.key == "available_current":
            return decision.attributes.get("balance_limit_a", 0)
        if self.key == "detected_phases":
            return decision.attributes.get("detected_phases", 3)
        if self.key == "session_state":
            return "active" if self.coordinator.controller.state.session_active else "inactive"
        if self.key == "last_decision":
            return decision.event
        if self.key == "planner_status":
            return "not_ported"
        return None

    @property
    def extra_state_attributes(self):
        decision = self.coordinator.decision
        if decision is None:
            return {}
        if self.key == "debug":
            return {
                "event": decision.event,
                "command_preview": decision.command,
                **decision.attributes,
            }
        if self.key == "planner_status":
            return {
                "reason": "The uploaded Node-RED flow consumes nordpool_cheapest_plan but does not contain the code that builds that plan."
            }
        return {}

    @property
    def native_unit_of_measurement(self):
        if self.key in {"target_current", "available_current"}:
            return "A"
        return None
