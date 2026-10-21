"""Config flow for Smart EV Charging."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_POWER,
    CONF_CHARGE_CONTROL_SWITCH,
    CONF_CHARGER_CURRENT,
    CONF_CHARGER_CURRENT_L1,
    CONF_CHARGER_CURRENT_L2,
    CONF_CHARGER_CURRENT_L3,
    CONF_CHARGER_POWER,
    CONF_CHARGER_STATUS,
    CONF_CURRENT_CONTROL_METHOD,
    CONF_CURRENT_LIMIT_ENTITY,
    CONF_GRID_NET_POWER,
    CONF_GRID_POWER_L1,
    CONF_GRID_POWER_L2,
    CONF_GRID_POWER_L3,
    CONF_PV_POWER,
    CONF_SCHEDULE,
    CONF_SITE_NAME,
    CONF_START_BUTTON,
    CONF_START_STOP_METHOD,
    CONF_STOP_BUTTON,
    CONF_VEHICLE_CHARGING_STATUS,
    CONF_VEHICLE_SOC,
    CURRENT_CONTROL_NONE,
    CURRENT_CONTROL_NUMBER,
    DOMAIN,
    START_STOP_BUTTONS,
    START_STOP_NONE,
    START_STOP_SWITCH,
)


def _entity(domain: str | list[str]) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


class SmartEVChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart EV Charging."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_charger()

        schema = vol.Schema(
            {
                vol.Required(CONF_SITE_NAME, default="HiBerry"): selector.TextSelector(),
                vol.Required(CONF_GRID_POWER_L1): _entity(Platform.SENSOR),
                vol.Required(CONF_GRID_POWER_L2): _entity(Platform.SENSOR),
                vol.Required(CONF_GRID_POWER_L3): _entity(Platform.SENSOR),
                vol.Required(CONF_GRID_NET_POWER): _entity(Platform.SENSOR),
                vol.Required(CONF_PV_POWER): _entity(Platform.SENSOR),
                vol.Optional(CONF_BATTERY_POWER): _entity(Platform.SENSOR),
                vol.Optional(CONF_SCHEDULE): _entity(Platform.SCHEDULE),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_charger(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_START_STOP_METHOD] == START_STOP_SWITCH:
                return await self.async_step_control_switch()
            if user_input[CONF_START_STOP_METHOD] == START_STOP_BUTTONS:
                return await self.async_step_control_buttons()
            return await self.async_step_vehicle()

        schema = vol.Schema(
            {
                vol.Required(CONF_CHARGER_STATUS): _entity(Platform.SENSOR),
                vol.Required(CONF_CHARGER_POWER): _entity(Platform.SENSOR),
                vol.Optional(CONF_CHARGER_CURRENT): _entity(Platform.SENSOR),
                vol.Required(CONF_CHARGER_CURRENT_L1): _entity(Platform.SENSOR),
                vol.Required(CONF_CHARGER_CURRENT_L2): _entity(Platform.SENSOR),
                vol.Required(CONF_CHARGER_CURRENT_L3): _entity(Platform.SENSOR),
                vol.Required(
                    CONF_CURRENT_CONTROL_METHOD,
                    default=CURRENT_CONTROL_NUMBER,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[CURRENT_CONTROL_NUMBER, CURRENT_CONTROL_NONE],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_CURRENT_LIMIT_ENTITY): _entity(Platform.NUMBER),
                vol.Required(
                    CONF_START_STOP_METHOD,
                    default=START_STOP_SWITCH,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[START_STOP_SWITCH, START_STOP_BUTTONS, START_STOP_NONE],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="charger", data_schema=schema)

    async def async_step_control_switch(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_vehicle()

        schema = vol.Schema(
            {vol.Required(CONF_CHARGE_CONTROL_SWITCH): _entity(Platform.SWITCH)}
        )
        return self.async_show_form(step_id="control_switch", data_schema=schema)

    async def async_step_control_buttons(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_vehicle()

        schema = vol.Schema(
            {
                vol.Required(CONF_START_BUTTON): _entity(Platform.BUTTON),
                vol.Required(CONF_STOP_BUTTON): _entity(Platform.BUTTON),
            }
        )
        return self.async_show_form(step_id="control_buttons", data_schema=schema)

    async def async_step_vehicle(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            await self.async_set_unique_id(self._data[CONF_SITE_NAME].strip().lower())
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._data[CONF_SITE_NAME], data=self._data
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_SOC): _entity(Platform.SENSOR),
                vol.Optional(CONF_VEHICLE_CHARGING_STATUS): _entity(Platform.SENSOR),
            }
        )
        return self.async_show_form(step_id="vehicle", data_schema=schema)
