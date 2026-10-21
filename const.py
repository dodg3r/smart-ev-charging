"""Constants for Smart EV Charging."""

from __future__ import annotations

DOMAIN = "smart_ev_charging"
PLATFORMS = ["sensor", "number", "select", "switch"]

CONF_SITE_NAME = "site_name"
CONF_GRID_POWER_L1 = "grid_power_l1"
CONF_GRID_POWER_L2 = "grid_power_l2"
CONF_GRID_POWER_L3 = "grid_power_l3"
CONF_GRID_NET_POWER = "grid_net_power"
CONF_PV_POWER = "pv_power"
CONF_BATTERY_POWER = "battery_power"
CONF_SCHEDULE = "schedule"

CONF_CHARGER_STATUS = "charger_status"
CONF_CHARGER_POWER = "charger_power"
CONF_CHARGER_CURRENT = "charger_current"
CONF_CHARGER_CURRENT_L1 = "charger_current_l1"
CONF_CHARGER_CURRENT_L2 = "charger_current_l2"
CONF_CHARGER_CURRENT_L3 = "charger_current_l3"

CONF_CURRENT_CONTROL_METHOD = "current_control_method"
CONF_CURRENT_LIMIT_ENTITY = "current_limit_entity"
CURRENT_CONTROL_NUMBER = "number"
CURRENT_CONTROL_NONE = "none"

CONF_START_STOP_METHOD = "start_stop_method"
START_STOP_SWITCH = "switch"
START_STOP_BUTTONS = "buttons"
START_STOP_NONE = "none"
CONF_CHARGE_CONTROL_SWITCH = "charge_control_switch"
CONF_START_BUTTON = "start_button"
CONF_STOP_BUTTON = "stop_button"

CONF_VEHICLE_SOC = "vehicle_soc"
CONF_VEHICLE_CHARGING_STATUS = "vehicle_charging_status"

MODE_OFF = "off"
MODE_SCHEDULE = "schedule"
MODE_CHEAP_TIME = "cheap_time"
MODE_SOLAR_ONLY = "solar_only"
MODE_AUTOMATIC = "automatic"
MODE_MANUAL = "manual"
CHARGING_MODES = [
    MODE_OFF,
    MODE_SCHEDULE,
    MODE_CHEAP_TIME,
    MODE_SOLAR_ONLY,
    MODE_AUTOMATIC,
    MODE_MANUAL,
]

DEFAULT_MAIN_FUSE = 20.0
DEFAULT_LOAD_MARGIN = 2.0
DEFAULT_MAX_CURRENT = 16.0
DEFAULT_MINIMUM_SOC = 80.0
DEFAULT_CLOUD_PAUSE_DURATION = 180.0
DEFAULT_CLOUD_PAUSE_THRESHOLD = 500.0
DEFAULT_BATTERY_SUPPORT_THRESHOLD = 300.0

UPDATE_INTERVAL_SECONDS = 5
