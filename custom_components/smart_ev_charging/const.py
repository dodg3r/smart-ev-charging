from __future__ import annotations

DOMAIN = "smart_ev_charging"
PLATFORMS = ["sensor", "number", "select", "switch"]

CONF_SITE_NAME = "site_name"

CONF_SCHEDULE = "schedule"
CONF_GRID_NET = "grid_net"
CONF_GRID_L1 = "grid_l1"
CONF_GRID_L2 = "grid_l2"
CONF_GRID_L3 = "grid_l3"
CONF_PV_POWER = "pv_power"
CONF_BATTERY_POWER = "battery_power"

CONF_CHARGER_STATUS = "charger_status"
CONF_CHARGER_POWER = "charger_power"
CONF_CHARGER_CURRENT = "charger_current"
CONF_CHARGER_L1 = "charger_l1"
CONF_CHARGER_L2 = "charger_l2"
CONF_CHARGER_L3 = "charger_l3"

CONF_CAR_SOC = "car_soc"
CONF_CAR_CHARGING_STATUS = "car_charging_status"
CONF_BATTERY_CAPACITY = "battery_capacity"

CONF_CURRENT_CONTROL = "current_control"
CONF_START_CONTROL = "start_control"
CONF_STOP_CONTROL = "stop_control"

MODE_OFF = "Off"
MODE_CHEAP = "Cheap Time"
MODE_SCHEDULE = "Schedule"
MODE_SOLAR = "Solar Only"
MODE_AUTOMATIC = "Automatic"
MODE_MANUAL = "Manual"

MODES = [
    MODE_OFF,
    MODE_CHEAP,
    MODE_SCHEDULE,
    MODE_SOLAR,
    MODE_AUTOMATIC,
    MODE_MANUAL,
]

PHASE_1 = "1 phase"
PHASE_3 = "3 phase"
PHASE_MODES = [PHASE_1, PHASE_3]

DEFAULTS = {
    "mode": MODE_SCHEDULE,
    "phase_mode": PHASE_3,
    "main_fuse": 20.0,
    "load_margin": 2.0,
    "cloud_pause_duration": 180.0,
    "max_current": 16.0,
    "cloud_pause_threshold": 500.0,
    "battery_support_threshold": 300.0,
    "minimum_soc": 80.0,
    "priority_charging": False,
}

MIN_AMP = 6
START_AMP = 6
SOFT_START_S = 60
RECONNECT_START_BLOCK_S = 30
RATE_STEP_UP_A = 2
RATE_STEP_UP_DELAY_S = 20
PHASE_DETECT_MIN_A = 0.5
PHASE_ACTIVE_MIN_A = 1.0
DEFAULT_PHASES = 3
PHASE_DETECT_DELAY_S = 10
FORCE_OFF_AFTER_STOP_S = 120
FULL_LOW_CURRENT_A = 2
FULL_LOW_CURRENT_DELAY_S = 60
