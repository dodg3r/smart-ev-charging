from __future__ import annotations

from .const import (
    DEFAULT_PHASES,
    FORCE_OFF_AFTER_STOP_S,
    FULL_LOW_CURRENT_A,
    FULL_LOW_CURRENT_DELAY_S,
    MIN_AMP,
    MODE_AUTOMATIC,
    MODE_CHEAP,
    MODE_MANUAL,
    MODE_OFF,
    MODE_SCHEDULE,
    MODE_SOLAR,
    PHASE_ACTIVE_MIN_A,
    PHASE_DETECT_DELAY_S,
    PHASE_DETECT_MIN_A,
    RATE_STEP_UP_A,
    RATE_STEP_UP_DELAY_S,
    RECONNECT_START_BLOCK_S,
    SOFT_START_S,
    START_AMP,
)
from .models import Decision, InputSnapshot, RuntimeState


def clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def even_floor(v: float) -> float:
    return float(int(v // 2) * 2)


class SmartEVController:
    """Read-only port of the HiBerry Node-RED decision logic.

    It calculates what should happen, but never calls charger services.
    """

    def __init__(self) -> None:
        self.state = RuntimeState()

    def _debug(self, event: str, mapped: str, extra: dict) -> str:
        s = self.state
        parts = [
            event or "-",
            mapped or "-",
            f"BT:{1 if extra.get('cheap_active') else 0}" if "cheap_active" in extra else None,
            f"CH:{extra.get('cheap_plan_hours')}" if "cheap_plan_hours" in extra else None,
            "CW:1" if extra.get("cheap_waiting_for_prices") else None,
            f"CP:{extra.get('cheap_plan_text')}" if extra.get("cheap_plan_text") else None,
            f"AUTO:{extra.get('auto_mode')}" if extra.get("auto_mode") else None,
            f"AS:{round(extra.get('auto_soc'))}" if extra.get("auto_soc") is not None else None,
            f"AT:{round(extra.get('auto_target'))}" if extra.get("auto_target") is not None else None,
            f"N:{round(extra.get('netto'))}" if extra.get("netto") is not None else None,
            f"E:{round(extra.get('export_w'))}" if extra.get("export_w") is not None else None,
            f"BW:{round(extra.get('battery_w'))}" if extra.get("battery_w") is not None else None,
            f"PV:{round(extra.get('pv_power_w'))}" if extra.get("pv_power_w") is not None else None,
            "PR:1" if extra.get("priority_charging") else None,
            f"U:{round(extra.get('priority_available_w'))}" if extra.get("priority_available_w") is not None else None,
            f"H:{round(extra.get('house_limit_a'))}" if extra.get("house_limit_a") is not None else None,
            f"B:{round(extra.get('balance_limit_a'))}" if extra.get("balance_limit_a") is not None else None,
            f"PF:{extra.get('requested_phases')}" if extra.get("requested_phases") is not None else None,
            f"F:{extra.get('detected_phases')}" if extra.get("detected_phases") is not None else None,
            f"L1:{extra.get('l1')}" if extra.get("l1") is not None else None,
            f"L2:{extra.get('l2')}" if extra.get("l2") is not None else None,
            f"L3:{extra.get('l3')}" if extra.get("l3") is not None else None,
            f"T:{round(extra.get('target_a'))}" if extra.get("target_a") is not None else None,
            f"C:{round(extra.get('current_amp_base'))}" if extra.get("current_amp_base") is not None else None,
            f"S:{1 if s.session_active else 0}",
            f"A:{1 if s.awaiting_start_confirm else 0}",
            f"FO:{1 if extra.get('force_off_active') else 0}" if "force_off_active" in extra else None,
            f"AN:{round(extra.get('adjusted_netto'))}" if extra.get("adjusted_netto") is not None else None,
        ]
        return " | ".join(x for x in parts if x)[:255]

    def _decision(
        self,
        inp: InputSnapshot,
        mapped: str,
        event: str,
        status: str,
        info: str = "",
        target: float | None = None,
        command: str | None = None,
        **extra,
    ) -> Decision:
        base = {
            "l1": inp.charger_l1_a,
            "l2": inp.charger_l2_a,
            "l3": inp.charger_l3_a,
            "detected_phases": self.state.detected_phases,
            "cheap_active": inp.cheap_active,
            "cheap_plan_hours": inp.cheap_plan_hours,
            "cheap_waiting_for_prices": inp.cheap_waiting_for_prices,
            "cheap_plan_text": inp.cheap_plan_text,
            **extra,
        }
        return Decision(
            target_current=target,
            command=command,
            status=status,
            info=info,
            event=event,
            debug=self._debug(event, mapped, base),
            attributes=base,
        )

    def _balance(self, inp: InputSnapshot) -> tuple[float, float, str]:
        c1 = inp.grid_l1_w / 230.0
        c2 = inp.grid_l2_w / 230.0
        c3 = inp.grid_l3_w / 230.0

        l1 = (inp.main_fuse - c1 - inp.load_margin) + inp.charger_l1_a
        l2 = (inp.main_fuse - c2 - inp.load_margin) + inp.charger_l2_a
        l3 = (inp.main_fuse - c3 - inp.load_margin) + inp.charger_l3_a

        raw = min(l1, l2, l3)
        bottleneck = "Phase 1" if l1 <= l2 and l1 <= l3 else ("Phase 2" if l2 <= l1 and l2 <= l3 else "Phase 3")
        house = clamp(raw, 0, 999)
        balance = clamp(house, 0, inp.max_current)
        return house, balance, bottleneck

    def _apply_ramp(self, inp: InputSnapshot, target: float) -> float:
        s = self.state
        t = clamp(target, 0, inp.max_current)
        if s.last_set_amp is not None:
            if t > s.last_set_amp:
                can_increase = (inp.now_ms - s.last_increase_at_ms) >= RATE_STEP_UP_DELAY_S * 1000
                if not can_increase:
                    t = s.last_set_amp
                elif t > s.last_set_amp + RATE_STEP_UP_A:
                    t = s.last_set_amp + RATE_STEP_UP_A

        t = even_floor(t)
        if 0 < t < MIN_AMP:
            t = 0
        t = clamp(t, 0, inp.max_current)

        if s.last_set_amp is not None and t > s.last_set_amp:
            s.last_increase_at_ms = inp.now_ms
        return t

    def _stop(self, inp: InputSnapshot) -> None:
        self.state.force_off_until_ms = inp.now_ms + FORCE_OFF_AFTER_STOP_S * 1000
        self.state.session_active = False
        self.state.awaiting_start_confirm = False
        self.state.charger_starting_ms = None
        self.state.cloud_start_ms = None
        self.state.phase_detect_start_ms = None

    def _start(
        self,
        inp: InputSnapshot,
        mapped: str,
        label: str,
        event: str,
        can_start: bool,
        extra: dict,
    ) -> Decision:
        house, balance, bottleneck = self._balance(inp)
        if balance < MIN_AMP:
            self._stop(inp)
            return self._decision(
                inp, mapped, f"{event}_balance_block",
                "⛔ Paused (Low capacity)",
                f"Full load on {bottleneck}",
                command="turn_off",
                target_a=0, house_limit_a=house, balance_limit_a=balance,
                force_off_active=True, **extra
            )
        if not can_start:
            return self._decision(
                inp, mapped, f"{event}_waiting_for_preparing",
                "🔌 Car connected",
                "Waiting for start-ready charger status",
                target_a=0, house_limit_a=house, balance_limit_a=balance, **extra
            )

        self.state.last_set_amp = START_AMP
        self.state.awaiting_start_confirm = True
        self.state.charger_starting_ms = inp.now_ms
        self.state.detected_phases = DEFAULT_PHASES
        return self._decision(
            inp, mapped, f"{event}_start",
            f"{label} ({START_AMP}A, {DEFAULT_PHASES}-phase)",
            "Starting at 6A and waiting for stable charger data",
            target=START_AMP, command="turn_on",
            target_a=START_AMP, house_limit_a=house, balance_limit_a=balance,
            awaiting_start_confirm=True, **extra
        )

    def _load_balanced_mode(
        self,
        inp: InputSnapshot,
        mapped: str,
        label: str,
        event: str,
        can_start: bool,
        charger_active: bool,
        soft_start: bool,
        extra: dict | None = None,
    ) -> Decision:
        extra = extra or {}
        house, balance, bottleneck = self._balance(inp)

        if soft_start:
            self.state.last_set_amp = MIN_AMP
            elapsed = (inp.now_ms - (self.state.charger_starting_ms or inp.now_ms)) // 1000
            remaining = max(0, SOFT_START_S - elapsed)
            return self._decision(
                inp, mapped, f"{event}_softstart",
                f"🔄 Soft start ({remaining}s remaining)",
                f"{label} • Waiting for stable charger data",
                target=MIN_AMP, command="turn_on",
                house_limit_a=house, balance_limit_a=balance,
                target_a=MIN_AMP, **extra
            )

        if not charger_active:
            return self._start(inp, mapped, label, event, can_start, extra)

        if balance < MIN_AMP:
            self._stop(inp)
            return self._decision(
                inp, mapped, f"{event}_balance_block",
                "⛔ Paused (Low capacity)",
                f"Full load on {bottleneck}",
                command="turn_off",
                house_limit_a=house, balance_limit_a=balance,
                target_a=0, force_off_active=True, **extra
            )

        target = self._apply_ramp(inp, balance)
        if target < MIN_AMP:
            self._stop(inp)
            return self._decision(
                inp, mapped, f"{event}_pause",
                "⛔ Paused (Low capacity)",
                f"Full load on {bottleneck}",
                command="turn_off",
                house_limit_a=house, balance_limit_a=balance,
                target_a=0, force_off_active=True, **extra
            )

        self.state.last_set_amp = target
        info = (
            f"Bottleneck: {bottleneck} • House can support {int(house)}A • Limited by max {int(inp.max_current)}A"
            if house > inp.max_current
            else f"Bottleneck: {bottleneck} • Available in house: {int(house)}A"
        )
        return self._decision(
            inp, mapped, f"{event}_run",
            f"{label} ({int(target)}A, {self.state.detected_phases}-phase)",
            info,
            target=target, command="turn_on",
            house_limit_a=house, balance_limit_a=balance,
            current_amp_base=inp.charger_current_a, target_a=target, **extra
        )

    def _solar_mode(
        self,
        inp: InputSnapshot,
        mapped: str,
        can_start: bool,
        charger_active: bool,
        soft_start: bool,
        force_priority: bool = False,
        extra: dict | None = None,
    ) -> Decision:
        extra = extra or {}
        s = self.state
        priority = force_priority or inp.priority_charging
        house, balance, bottleneck = self._balance(inp)

        battery_discharge = abs(inp.battery_power_w) if inp.battery_power_w < 0 else 0
        battery_penalty = battery_discharge if battery_discharge >= inp.battery_support_threshold else 0
        adjusted = inp.grid_net + battery_penalty
        export_w = abs(adjusted) if adjusted < 0 else 0
        requested_phases = 1 if "1" in inp.phase_mode else 3
        start_need_w = MIN_AMP * 230 * requested_phases
        over_cloud = adjusted >= inp.cloud_pause_threshold

        battery_charging = max(0, inp.battery_power_w)
        priority_available = max(0, battery_charging - adjusted)
        priority_grid_ok = adjusted < inp.cloud_pause_threshold
        start_available = priority_available if priority else export_w

        solar_extra = {
            "netto": inp.grid_net,
            "adjusted_netto": adjusted,
            "export_w": export_w,
            "battery_w": inp.battery_power_w,
            "pv_power_w": inp.pv_power_w,
            "priority_charging": priority,
            "priority_available_w": priority_available if priority else None,
            "requested_phases": requested_phases,
            "house_limit_a": house,
            "balance_limit_a": balance,
            "current_amp_base": inp.charger_current_a,
            **extra,
        }

        if balance < MIN_AMP:
            self._stop(inp)
            return self._decision(
                inp, mapped, "solar_balance_block",
                "⛔ Paused (Low capacity)",
                f"Full load on {bottleneck}",
                command="turn_off", target_a=0, force_off_active=True, **solar_extra
            )

        if soft_start:
            s.last_set_amp = MIN_AMP
            return self._decision(
                inp, mapped, "solar_softstart",
                "🔄 Soft start",
                "☀️ Solar • Waiting for stable charger data",
                target=MIN_AMP, command="turn_on", target_a=MIN_AMP, **solar_extra
            )

        solar_session_active = charger_active or s.session_active

        if not solar_session_active:
            s.cloud_start_ms = None
            pv_ok = inp.pv_power_w >= start_need_w
            grid_ok = (not priority) or priority_grid_ok

            if can_start and start_available >= start_need_w and pv_ok and grid_ok and balance >= MIN_AMP:
                s.last_set_amp = START_AMP
                s.awaiting_start_confirm = True
                s.charger_starting_ms = inp.now_ms
                s.detected_phases = DEFAULT_PHASES
                return self._decision(
                    inp, mapped, "solar_priority_start" if priority else "solar_start",
                    f"{'🔋 Priority EV charging' if priority else '☀️ Solar'} ({START_AMP}A, {requested_phases}-phase)",
                    (
                        f"Car before home battery • Available: {round(priority_available)}W • Grid: {round(adjusted)}W"
                        if priority else "Start allowed from solar surplus"
                    ),
                    target=START_AMP, command="turn_on",
                    target_a=START_AMP, awaiting_start_confirm=True, **solar_extra
                )

            if can_start and start_available >= start_need_w and grid_ok and not pv_ok:
                return self._decision(
                    inp, mapped, "solar_wait_for_pv_production",
                    "☀️ Too little solar production",
                    f"Requires at least {round(start_need_w)}W • Now: {round(inp.pv_power_w)}W",
                    target_a=0, **solar_extra
                )

            if not can_start:
                return self._decision(
                    inp, mapped, "solar_waiting_for_preparing",
                    "🔌 Car connected",
                    "Waiting for start-ready charger status",
                    target_a=0, **solar_extra
                )

            return self._decision(
                inp, mapped, "solar_priority_wait" if priority else "solar_wait_for_export",
                "🔋 Waiting for priority start" if priority else "☀️ Too little solar",
                (
                    f"Available: {round(priority_available)}W of {round(start_need_w)}W • Adjusted grid: {round(adjusted)}W"
                    if priority else f"Requires {round(start_need_w)}W export to start"
                ),
                target_a=0, **solar_extra
            )

        if over_cloud:
            if s.cloud_start_ms is None:
                s.cloud_start_ms = inp.now_ms
            elapsed = (inp.now_ms - s.cloud_start_ms) // 1000
            remaining = max(0, inp.cloud_pause_duration - elapsed)

            if elapsed < inp.cloud_pause_duration:
                s.last_set_amp = MIN_AMP
                s.last_increase_at_ms = inp.now_ms
                return self._decision(
                    inp, mapped, "solar_cloud_pause_running",
                    f"☁️ Cloud pause ({remaining}s remaining)",
                    f"Continuing at {MIN_AMP}A despite low solar",
                    target=MIN_AMP, command="turn_on", target_a=MIN_AMP, **solar_extra
                )

            s.cloud_start_ms = None
            self._stop(inp)
            return self._decision(
                inp, mapped, "solar_pause_stop",
                "☀️ Too little solar",
                "Cloud pause ended, charging should stop",
                command="turn_off", target_a=0, force_off_active=True, **solar_extra
            )

        s.cloud_start_ms = None

        if priority:
            s.last_set_amp = MIN_AMP
            return self._decision(
                inp, mapped, "solar_priority_run",
                f"🔋 Priority EV charging ({MIN_AMP}A, {s.detected_phases}-phase)",
                f"Fixed {MIN_AMP}A • Home battery adapts • Grid: {round(adjusted)}W",
                target=MIN_AMP, command="turn_on", target_a=MIN_AMP, **solar_extra
            )

        if adjusted < 0:
            step_w = RATE_STEP_UP_A * 230 * s.detected_phases
            base = even_floor(s.last_set_amp or MIN_AMP)
            if base < MIN_AMP:
                base = MIN_AMP
            if export_w >= step_w:
                base += RATE_STEP_UP_A
            solar_target = even_floor(min(base, balance, inp.max_current))
            target = self._apply_ramp(inp, solar_target)
        else:
            target = self._apply_ramp(inp, MIN_AMP)

        if target < MIN_AMP:
            self._stop(inp)
            return self._decision(
                inp, mapped, "solar_target_below_min",
                "☀️ Too little solar",
                "Solar surplus is below minimum charging current",
                command="turn_off", target_a=0, force_off_active=True, **solar_extra
            )

        s.last_set_amp = target
        return self._decision(
            inp, mapped, "solar_run_incremental",
            f"☀️ Solar ({int(target)}A, {s.detected_phases}-phase)",
            f"Following solar surplus • Available in house: {int(house)}A",
            target=target, command="turn_on", target_a=target, **solar_extra
        )

    def evaluate(self, inp: InputSnapshot) -> Decision:
        s = self.state
        raw = (inp.charger_status or "unknown").strip().lower()
        mapped = {
            "available": "AVAILABLE",
            "unknown": "UNKNOWN",
            "unavailable": "UNAVAILABLE",
            "preparing": "PREPARING",
            "charging": "CHARGING",
            "finishing": "FINISHING",
            "suspendedev": "SUSPENDED_EV",
            "suspendedevse": "SUSPENDED_EVSE",
        }.get(raw, raw.upper())

        # Node-RED explicitly ignores Idle completely.
        if raw == "idle":
            return self._decision(inp, mapped, "idle_ignored", "Idle ignored")

        disconnected = {"available", "unknown", "unavailable", ""}
        car_connected = raw not in disconnected
        can_start = raw == "preparing"

        charger_has_power = inp.charger_current_a > 0.3 or inp.charger_power_w > 100
        holding = raw in {"charging", "suspendedev", "suspendedevse", "finishing"} and car_connected
        charger_active = charger_has_power or holding or s.awaiting_start_confirm or s.session_active

        if raw == "available" and s.last_available_at_ms is None:
            s.last_available_at_ms = inp.now_ms
        elif raw != "available":
            # allow next transition to available to refresh timestamp
            pass

        force_off_active = inp.now_ms < s.force_off_until_ms
        real_charging = raw == "charging" and (
            inp.charger_current_a > PHASE_DETECT_MIN_A or inp.charger_power_w > 500
        )

        soft_start = s.charger_starting_ms is not None and (
            inp.now_ms - s.charger_starting_ms < SOFT_START_S * 1000
        )

        # Phase detection
        if soft_start or not real_charging:
            s.detected_phases = DEFAULT_PHASES
            if not real_charging:
                s.phase_detect_start_ms = None
        else:
            if s.phase_detect_start_ms is None:
                s.phase_detect_start_ms = inp.now_ms
            elapsed = (inp.now_ms - s.phase_detect_start_ms) // 1000
            if elapsed >= PHASE_DETECT_DELAY_S:
                detected = sum(
                    1 for a in (inp.charger_l1_a, inp.charger_l2_a, inp.charger_l3_a)
                    if a > PHASE_ACTIVE_MIN_A
                )
                if detected > 0:
                    s.detected_phases = int(clamp(detected, 1, 3))
                elif inp.charger_current_a > PHASE_DETECT_MIN_A and inp.charger_power_w > 100:
                    est = round(inp.charger_power_w / (inp.charger_current_a * 230))
                    s.detected_phases = int(clamp(est, 1, 3))
                else:
                    s.detected_phases = DEFAULT_PHASES

        if not force_off_active and (real_charging or holding or s.awaiting_start_confirm):
            s.session_active = True

        if soft_start and real_charging:
            s.awaiting_start_confirm = False

        if s.charger_starting_ms is not None and not soft_start:
            s.charger_starting_ms = None
            s.awaiting_start_confirm = False

        if inp.mode == MODE_OFF:
            self.state = RuntimeState()
            return self._decision(inp, mapped, "charging_disabled", "🌑 Charging disabled", command="turn_off")

        if force_off_active:
            s.session_active = False
            return self._decision(
                inp, mapped, "force_off_hold",
                "⏸️ Temporary stop",
                "Stabilising after stop",
                command="turn_off", force_off_active=True
            )

        if not car_connected:
            self.state = RuntimeState()
            return self._decision(inp, mapped, "car_missing", "🔌 Car not connected", command="turn_off")

        if s.last_available_at_ms and can_start and (
            inp.now_ms - s.last_available_at_ms < RECONNECT_START_BLOCK_S * 1000
        ):
            return self._decision(
                inp, mapped, "reconnect_start_block",
                "🔌 Car connected",
                "Waiting for stable charger status after reconnect",
                target_a=0
            )

        # Full/resting detection
        max_phase = max(inp.charger_l1_a, inp.charger_l2_a, inp.charger_l3_a)
        actual_charging_now = raw == "charging" and (
            max_phase >= FULL_LOW_CURRENT_A or inp.charger_power_w > 500
        )
        volvo_done = inp.car_charging_status.strip().lower() in {
            "done", "complete", "completed", "fully charged", "fulladdad", "klar"
        }

        if s.car_resting and actual_charging_now:
            s.car_resting = False
            s.car_resting_reason = None
            s.low_current_since_ms = None

        if volvo_done and not actual_charging_now:
            s.car_resting = True
            s.car_resting_reason = "volvo_done"
            s.session_active = True

        all_low = (
            inp.charger_l1_a < FULL_LOW_CURRENT_A
            and inp.charger_l2_a < FULL_LOW_CURRENT_A
            and inp.charger_l3_a < FULL_LOW_CURRENT_A
        )
        low_candidate = (
            car_connected and s.session_active and raw == "charging"
            and not soft_start and not s.awaiting_start_confirm
            and not force_off_active and all_low
        )

        if low_candidate:
            if s.low_current_since_ms is None:
                s.low_current_since_ms = inp.now_ms
            elif inp.now_ms - s.low_current_since_ms >= FULL_LOW_CURRENT_DELAY_S * 1000:
                s.car_resting = True
                s.car_resting_reason = "low_current_full"
                s.session_active = True
        else:
            s.low_current_since_ms = None

        if raw == "suspendedev" and s.session_active and not actual_charging_now:
            s.car_resting = True
            if s.car_resting_reason not in {"low_current_full", "volvo_done"}:
                s.car_resting_reason = "suspendedev"

        if s.car_resting and not actual_charging_now:
            if s.car_resting_reason == "volvo_done":
                return self._decision(
                    inp, mapped, "session_resting_volvo_done",
                    "✅ Car fully charged",
                    "Vehicle reports fully charged. Session remains resting and is monitored."
                )
            if s.car_resting_reason == "low_current_full":
                return self._decision(
                    inp, mapped, "session_resting_low_current_full",
                    "✅ Car fully charged",
                    f"Charging current below {FULL_LOW_CURRENT_A}A for {FULL_LOW_CURRENT_DELAY_S}s. Session remains resting."
                )
            return self._decision(
                inp, mapped, "session_resting_suspendedev",
                "⏸️ Charging paused",
                "Vehicle has paused charging. Waiting for it to draw current again."
            )

        # Modes
        if inp.mode == MODE_SCHEDULE:
            if not inp.schedule_on:
                s.session_active = False
                return self._decision(inp, mapped, "schema_wait", "⏳ Waiting for schedule", command="turn_off")
            return self._load_balanced_mode(inp, mapped, "📅 Schedule", "schema", can_start, charger_active, soft_start)

        if inp.mode == MODE_MANUAL:
            return self._load_balanced_mode(inp, mapped, "🖐️ Manual", "manual", can_start, charger_active, soft_start)

        if inp.mode == MODE_SOLAR:
            return self._solar_mode(inp, mapped, can_start, charger_active, soft_start)

        if inp.mode == MODE_CHEAP:
            if not inp.cheap_active:
                s.session_active = False
                return self._decision(
                    inp, mapped, "cheap_wait",
                    "💰 Waiting for cheap time",
                    "No planned cheap charging period right now",
                    command="turn_off"
                )
            return self._load_balanced_mode(inp, mapped, "💰 Cheap Time", "cheap", can_start, charger_active, soft_start)

        if inp.mode == MODE_AUTOMATIC:
            auto = {"auto_soc": inp.car_soc, "auto_target": inp.minimum_soc}
            battery_discharge = abs(inp.battery_power_w) if inp.battery_power_w < 0 else 0
            battery_penalty = battery_discharge if battery_discharge >= inp.battery_support_threshold else 0
            adjusted = inp.grid_net + battery_penalty
            export_w = abs(adjusted) if adjusted < 0 else 0
            req_phases = 1 if "1" in inp.phase_mode else 3
            start_need = MIN_AMP * 230 * req_phases
            solar_can_start = inp.pv_power_w >= start_need and export_w >= start_need
            solar_supported_ev = max(0, inp.charger_power_w - adjusted)
            solar_can_take_over = charger_active and inp.pv_power_w >= start_need and solar_supported_ev >= start_need

            if (s.auto_solar_mode_active and (s.session_active or charger_active or soft_start or s.awaiting_start_confirm)) or solar_can_take_over:
                s.auto_solar_mode_active = True
                return self._solar_mode(inp, mapped, can_start, charger_active, soft_start, extra={**auto, "auto_mode": "SOL"})

            if solar_can_start or solar_can_take_over:
                s.auto_solar_mode_active = True
                return self._solar_mode(inp, mapped, can_start, charger_active, soft_start, extra={**auto, "auto_mode": "SOL"})

            s.auto_solar_mode_active = False

            if inp.car_soc >= inp.minimum_soc:
                if charger_active:
                    self._stop(inp)
                    return self._decision(
                        inp, mapped, "automatic_target_reached",
                        "✅ Minimum SOC reached",
                        f"Car has {round(inp.car_soc)}% • Minimum {round(inp.minimum_soc)}% • Waiting for free solar",
                        command="turn_off", target_a=0, auto_mode="TARGET", **auto
                    )
                return self._decision(
                    inp, mapped, "automatic_target_reached",
                    "✅ Minimum SOC reached",
                    f"Car has {round(inp.car_soc)}% • Minimum {round(inp.minimum_soc)}% • Waiting for free solar",
                    target_a=0, auto_mode="TARGET", **auto
                )

            if inp.must_charge_now:
                return self._load_balanced_mode(
                    inp, mapped, "⏱️ Automatic • Must charge", "automatic_deadline",
                    can_start, charger_active, soft_start, {**auto, "auto_mode": "DEADLINE"}
                )

            if inp.cheap_active:
                return self._load_balanced_mode(
                    inp, mapped, "💰 Automatic • Cheap time", "automatic_cheap",
                    can_start, charger_active, soft_start, {**auto, "auto_mode": "CHEAP"}
                )

            if charger_active:
                self._stop(inp)
                return self._decision(
                    inp, mapped, "automatic_wait",
                    "🤖 Automatic • Waiting",
                    "Waiting for cheap time or free solar",
                    command="turn_off", target_a=0, auto_mode="WAIT", **auto
                )

            return self._decision(
                inp, mapped, "automatic_wait",
                "🤖 Automatic • Waiting",
                "Waiting for cheap time or free solar",
                target_a=0, auto_mode="WAIT", **auto
            )

        return self._decision(inp, mapped, "fallback", "Charging disabled", command="turn_off")
