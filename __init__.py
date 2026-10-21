"""Smart EV Charging integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .controller import SmartEVChargingController


type SmartEVChargingConfigEntry = ConfigEntry[SmartEVChargingController]


async def async_setup_entry(hass: HomeAssistant, entry: SmartEVChargingConfigEntry) -> bool:
    """Set up Smart EV Charging from a config entry."""
    controller = SmartEVChargingController(hass, dict(entry.data))
    entry.runtime_data = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartEVChargingConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
