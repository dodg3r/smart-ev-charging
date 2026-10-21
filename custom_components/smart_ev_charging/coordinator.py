from __future__ import annotations

from datetime import timedelta
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_BATTERY_POWER,
    CONF_CAR_CHARGING_STATUS,
    CONF_CAR_SOC,
    CONF_CHARGER_CURRENT,
    CONF_CHARGER_L1,
    CONF_CHARGER_L2,
    CONF_CHARGER_L3,
    CONF_CHARGER_POWER,
    CONF_CHARGER_STATUS,
    CONF_GRID_L1,
    CONF_GRID_L2,
    CONF_GRID_L3,
    CONF_GRID_NET,
    CONF_PV_POWER,
    CONF_SCHEDULE,
    DEFAULTS,
)
from .controller import SmartEVController
from .models import InputSnapshot


def _num(hass: HomeAssistant, entity_id: str | None, fallback: float = 0.0) -> float:
    if not entity_id:
        return fallback
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", None):
        return fallback
    try:
        return float(str(state.state).replace(",", "."))
    except (TypeError, ValueError):
        return fallback


def _str(hass: HomeAssistant, entity_id: str | None, fallback: str = "") -> str:
    if not entity_id:
        return fallback
    state = hass.states.get(entity_id)
    return fallback if state is None else str(state.state)


class SmartEVCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"Smart EV Charging {entry.title}",
            update_interval=timedelta(seconds=5),
        )
        self.entry = entry
        self.controller = SmartEVController()
        self.settings = dict(DEFAULTS)
        self.decision = None
        self._unsub_state = None

    async def async_start(self) -> None:
        entities = {
            value for key, value in self.entry.data.items()
            if isinstance(value, str) and "." in value
        }
        if entities:
            self._unsub_state = async_track_state_change_event(
                self.hass,
                list(entities),
                self._handle_state_change,
            )
        await self.async_config_entry_first_refresh()

    async def _handle_state_change(self, _event) -> None:
        await self.async_request_refresh()

    async def _async_update_data(self):
        d = self.entry.data
        s = self.settings

        # v0.2.0 intentionally does not invent the missing Nordpool planner.
        # The uploaded flow consumes global "nordpool_cheapest_plan", but does
        # not contain the code that creates it.
        cheap_active = False
        waiting_for_prices = True
        must_charge_now = False

        snap = InputSnapshot(
            now_ms=int(time.time() * 1000),
            mode=s["mode"],
            phase_mode=s["phase_mode"],
            schedule_on=_str(self.hass, d.get(CONF_SCHEDULE), "off") == "on",
            priority_charging=bool(s["priority_charging"]),
            main_fuse=float(s["main_fuse"]),
            load_margin=float(s["load_margin"]),
            cloud_pause_duration=int(s["cloud_pause_duration"]),
            max_current=float(s["max_current"]),
            cloud_pause_threshold=float(s["cloud_pause_threshold"]),
            battery_support_threshold=float(s["battery_support_threshold"]),
            grid_net=_num(self.hass, d.get(CONF_GRID_NET)),
            grid_l1_w=_num(self.hass, d.get(CONF_GRID_L1)),
            grid_l2_w=_num(self.hass, d.get(CONF_GRID_L2)),
            grid_l3_w=_num(self.hass, d.get(CONF_GRID_L3)),
            pv_power_w=_num(self.hass, d.get(CONF_PV_POWER)),
            battery_power_w=_num(self.hass, d.get(CONF_BATTERY_POWER)),
            charger_status=_str(self.hass, d.get(CONF_CHARGER_STATUS), "unknown"),
            charger_power_w=_num(self.hass, d.get(CONF_CHARGER_POWER)),
            charger_current_a=_num(self.hass, d.get(CONF_CHARGER_CURRENT)),
            charger_l1_a=_num(self.hass, d.get(CONF_CHARGER_L1)),
            charger_l2_a=_num(self.hass, d.get(CONF_CHARGER_L2)),
            charger_l3_a=_num(self.hass, d.get(CONF_CHARGER_L3)),
            car_soc=_num(self.hass, d.get(CONF_CAR_SOC)),
            minimum_soc=float(s["minimum_soc"]),
            car_charging_status=_str(self.hass, d.get(CONF_CAR_CHARGING_STATUS), ""),
            cheap_active=cheap_active,
            cheap_waiting_for_prices=waiting_for_prices,
            cheap_plan_hours=0,
            cheap_plan_text="missing",
            must_charge_now=must_charge_now,
        )
        self.decision = self.controller.evaluate(snap)
        return {
            "decision": self.decision,
            "snapshot": snap,
        }

    async def async_shutdown(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
