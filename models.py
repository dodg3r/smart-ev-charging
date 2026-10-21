"""Runtime models for Smart EV Charging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SmartChargingState:
    """Calculated controller state."""

    status: str = "initializing"
    limiting_reason: str = ""
    debug: str = "initializing"
    session_state: str = "idle"
    last_decision: str = "No decision yet"
    last_command_result: str = "Read-only mode"

    target_current: float = 0.0
    available_current: float = 0.0
    detected_phases: int = 3

    charger_status: str = "unknown"
    charger_power_w: float = 0.0
    charger_current_a: float = 0.0
    current_l1_a: float = 0.0
    current_l2_a: float = 0.0
    current_l3_a: float = 0.0

    grid_power_w: float = 0.0
    grid_l1_w: float = 0.0
    grid_l2_w: float = 0.0
    grid_l3_w: float = 0.0
    pv_power_w: float = 0.0
    battery_power_w: float = 0.0

    house_limit_a: float = 0.0
    balance_limit_a: float = 0.0
    bottleneck_phase: str = "L1"

    extra: dict[str, Any] = field(default_factory=dict)
