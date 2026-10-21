from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InputSnapshot:
    now_ms: int
    mode: str
    phase_mode: str
    schedule_on: bool
    priority_charging: bool

    main_fuse: float
    load_margin: float
    cloud_pause_duration: int
    max_current: float
    cloud_pause_threshold: float
    battery_support_threshold: float

    grid_net: float
    grid_l1_w: float
    grid_l2_w: float
    grid_l3_w: float
    pv_power_w: float
    battery_power_w: float

    charger_status: str
    charger_power_w: float
    charger_current_a: float
    charger_l1_a: float
    charger_l2_a: float
    charger_l3_a: float

    car_soc: float
    minimum_soc: float
    car_charging_status: str

    cheap_active: bool = False
    cheap_waiting_for_prices: bool = True
    cheap_plan_hours: float = 0
    cheap_plan_text: str = "missing"
    must_charge_now: bool = False


@dataclass(slots=True)
class RuntimeState:
    session_active: bool = False
    car_resting: bool = False
    car_resting_reason: str | None = None
    low_current_since_ms: int | None = None
    awaiting_start_confirm: bool = False
    charger_starting_ms: int | None = None
    last_available_at_ms: int | None = None
    force_off_until_ms: int = 0
    cloud_start_ms: int | None = None
    detected_phases: int = 3
    phase_detect_start_ms: int | None = None
    last_set_amp: float | None = None
    last_increase_at_ms: int = 0
    auto_solar_mode_active: bool = False


@dataclass(slots=True)
class Decision:
    target_current: float | None
    command: str | None
    status: str
    info: str
    event: str
    debug: str
    attributes: dict[str, Any] = field(default_factory=dict)
