"""Read-only Smart EV Charging controller."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import (
    CONF_BATTERY_POWER,
    CONF_CHARGER_CURRENT,
    CONF_CHARGER_CURRENT_L1,
    CONF_CHARGER_CURRENT_L2,
    CONF_CHARGER_CURRENT_L3,
    CONF_CHARGER_POWER,
    CONF_CHARGER_STATUS,
    CONF_GRID_NET_POWER,
    CONF_GRID_POWER_L1,
    CONF_GRID_POWER_L2,
    CONF_GRID_POWER_L3,
    CONF_PV_POWER,
    CONF_VEHICLE_CHARGING_STATUS,
    DEFAULT_BATTERY_SUPPORT_THRESHOLD,
    DEFAULT_CLOUD_PAUSE_DURATION,
    DEFAULT_CLOUD_PAUSE_THRESHOLD,
    DEFAULT_LOAD_MARGIN,
    DEFAULT_MAIN_FUSE,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MINIMUM_SOC,
    MODE_OFF,
    UPDATE_INTERVAL_SECONDS,
)
from .models import SmartChargingState

_LOGGER = logging.getLogger(__name__)


class SmartEVChargingController:
    """Calculate charging decisions without controlling the charger."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self.hass = hass
        self.config = config
        self.state = SmartChargingState()
        self.listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []

        # Integration-owned controls. Entities update these values.
        self.mode = MODE_OFF
        self.main_fuse_a = DEFAULT_MAIN_FUSE
        self.load_margin_a = DEFAULT_LOAD_MARGIN
        self.max_current_a = DEFAULT_MAX_CURRENT
        self.minimum_soc = DEFAULT_MINIMUM_SOC
        self.cloud_pause_duration_s = DEFAULT_CLOUD_PAUSE_DURATION
        self.cloud_pause_threshold_w = DEFAULT_CLOUD_PAUSE_THRESHOLD
        self.battery_support_threshold_w = DEFAULT_BATTERY_SUPPORT_THRESHOLD
        self.priority_charging = False

    async def async_start(self) -> None:
        entity_ids = [
            self.config.get(CONF_GRID_POWER_L1),
            self.config.get(CONF_GRID_POWER_L2),
            self.config.get(CONF_GRID_POWER_L3),
            self.config.get(CONF_GRID_NET_POWER),
            self.config.get(CONF_PV_POWER),
            self.config.get(CONF_BATTERY_POWER),
            self.config.get(CONF_CHARGER_STATUS),
            self.config.get(CONF_CHARGER_POWER),
            self.config.get(CONF_CHARGER_CURRENT),
            self.config.get(CONF_CHARGER_CURRENT_L1),
            self.config.get(CONF_CHARGER_CURRENT_L2),
            self.config.get(CONF_CHARGER_CURRENT_L3),
            self.config.get(CONF_VEHICLE_CHARGING_STATUS),
        ]
        entity_ids = [entity_id for entity_id in entity_ids if entity_id]

        if entity_ids:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, entity_ids, self._async_source_changed
                )
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._async_periodic_update, timedelta(seconds=UPDATE_INTERVAL_SECONDS)
            )
        )
        self.async_recalculate()

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def _async_source_changed(self, event: Event) -> None:
        self.async_recalculate()

    @callback
    def _async_periodic_update(self, _now) -> None:
        self.async_recalculate()

    @callback
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(listener)

        @callback
        def remove_listener() -> None:
            if listener in self.listeners:
                self.listeners.remove(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self.listeners):
            listener()

    def _str(self, key: str, default: str = "unknown") -> str:
        entity_id = self.config.get(key)
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none"}:
            return default
        return str(state.state).strip()

    def _num(self, key: str, default: float = 0.0) -> float:
        entity_id = self.config.get(key)
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none"}:
            return default
        try:
            return float(str(state.state).replace(",", "."))
        except (TypeError, ValueError):
            return default

    @callback
    def async_recalculate(self) -> None:
        s = SmartChargingState()
        s.charger_status = self._str(CONF_CHARGER_STATUS).lower()
        s.charger_power_w = self._num(CONF_CHARGER_POWER)
        s.charger_current_a = self._num(CONF_CHARGER_CURRENT)
        s.current_l1_a = self._num(CONF_CHARGER_CURRENT_L1)
        s.current_l2_a = self._num(CONF_CHARGER_CURRENT_L2)
        s.current_l3_a = self._num(CONF_CHARGER_CURRENT_L3)

        s.grid_l1_w = self._num(CONF_GRID_POWER_L1)
        s.grid_l2_w = self._num(CONF_GRID_POWER_L2)
        s.grid_l3_w = self._num(CONF_GRID_POWER_L3)
        s.grid_power_w = self._num(CONF_GRID_NET_POWER)
        s.pv_power_w = self._num(CONF_PV_POWER)
        s.battery_power_w = self._num(CONF_BATTERY_POWER)

        # Phase detection from actual EVSE phase current.
        phase_currents = [s.current_l1_a, s.current_l2_a, s.current_l3_a]
        active_phases = sum(current > 1.0 for current in phase_currents)
        s.detected_phases = active_phases if active_phases else 3

        # Per-phase load balancing. This mirrors the corrected logic used in the project:
        # available EV current on each phase = main fuse - house load - margin + EV current.
        grid_a = [s.grid_l1_w / 230.0, s.grid_l2_w / 230.0, s.grid_l3_w / 230.0]
        ev_a = [s.current_l1_a, s.current_l2_a, s.current_l3_a]
        limits = [
            (self.main_fuse_a - grid_a[i] - self.load_margin_a) + ev_a[i]
            for i in range(3)
        ]
        min_limit = min(limits)
        bottleneck_index = limits.index(min_limit)
        s.bottleneck_phase = f"L{bottleneck_index + 1}"
        s.house_limit_a = max(0.0, min_limit)
        s.balance_limit_a = max(0.0, min(s.house_limit_a, self.max_current_a))
        s.available_current = s.balance_limit_a

        if self.mode == MODE_OFF:
            s.target_current = 0.0
            s.status = "off"
            s.session_state = "idle"
            s.limiting_reason = "Charging mode is Off"
            s.last_decision = "Target current 0 A because charging mode is Off"
        else:
            target = int(s.balance_limit_a // 2) * 2
            if 0 < target < 6:
                target = 0
            s.target_current = float(target)
            s.status = "ready" if target >= 6 else "limited"
            s.session_state = "charging" if s.charger_status == "charging" else s.charger_status
            if target < 6:
                s.limiting_reason = f"Insufficient headroom on {s.bottleneck_phase}"
                s.last_decision = f"No charge: available current {s.balance_limit_a:.1f} A"
            else:
                s.limiting_reason = f"Load balancing limited by {s.bottleneck_phase}"
                s.last_decision = f"Read-only target {target} A"

        s.last_command_result = "Read-only mode: no command sent"
        s.debug = (
            f"preview | {s.charger_status.upper()} | N:{round(s.grid_power_w)} | "
            f"PV:{round(s.pv_power_w)} | BW:{round(s.battery_power_w)} | "
            f"H:{round(s.house_limit_a)} | B:{round(s.balance_limit_a)} | "
            f"F:{s.detected_phases} | L1:{s.current_l1_a:.1f} | "
            f"L2:{s.current_l2_a:.1f} | L3:{s.current_l3_a:.1f} | "
            f"T:{round(s.target_current)}"
        )[:255]

        s.extra = {
            "mode": self.mode,
            "bottleneck_phase": s.bottleneck_phase,
            "grid_power_w": s.grid_power_w,
            "pv_power_w": s.pv_power_w,
            "battery_power_w": s.battery_power_w,
            "house_limit_a": round(s.house_limit_a, 2),
            "balance_limit_a": round(s.balance_limit_a, 2),
            "detected_phases": s.detected_phases,
            "current_l1_a": s.current_l1_a,
            "current_l2_a": s.current_l2_a,
            "current_l3_a": s.current_l3_a,
            "target_current_a": s.target_current,
        }

        self.state = s
        self._notify_listeners()
