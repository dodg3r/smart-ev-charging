from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import *


def ent(domain: str, multiple: bool = False):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=multiple)
    )


class SmartEVChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            title = user_input.pop(CONF_SITE_NAME)
            await self.async_set_unique_id(title.lower().replace(" ", "_"))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_SITE_NAME, default="HiBerry"): str,

            vol.Required(CONF_SCHEDULE): ent("schedule"),

            vol.Required(CONF_GRID_NET): ent("sensor"),
            vol.Required(CONF_GRID_L1): ent("sensor"),
            vol.Required(CONF_GRID_L2): ent("sensor"),
            vol.Required(CONF_GRID_L3): ent("sensor"),
            vol.Required(CONF_PV_POWER): ent("sensor"),
            vol.Required(CONF_BATTERY_POWER): ent("sensor"),

            vol.Required(CONF_CHARGER_STATUS): ent("sensor"),
            vol.Required(CONF_CHARGER_POWER): ent("sensor"),
            vol.Required(CONF_CHARGER_CURRENT): ent("sensor"),
            vol.Required(CONF_CHARGER_L1): ent("sensor"),
            vol.Required(CONF_CHARGER_L2): ent("sensor"),
            vol.Required(CONF_CHARGER_L3): ent("sensor"),

            vol.Required(CONF_CAR_SOC): ent("sensor"),
            vol.Required(CONF_CAR_CHARGING_STATUS): ent("sensor"),

            # Stored now for later control-enabled releases. v0.2.0 never writes.
            vol.Optional(CONF_CURRENT_CONTROL): ent("number"),
            vol.Optional(CONF_START_CONTROL): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "button"])
            ),
            vol.Optional(CONF_STOP_CONTROL): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "button"])
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "note": "v0.2.0 is read-only and will not control the charger."
            },
        )
