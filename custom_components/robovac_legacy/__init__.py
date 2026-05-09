"""Eufy RoboVac LAN legacy integration (PyRobovac lakeside protocol)."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LOCAL_CODE, CONF_VACS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import RobovacLegacyCoordinator

PLATFORMS: list[str] = [Platform.VACUUM]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Bootstrap integration discovery-only components (unused)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Prepare coordinators and vacuum platform."""
    interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    coordinators: dict[str, RobovacLegacyCoordinator] = {}

    for vac_key, vacuum in entry.data[CONF_VACS].items():
        coord = RobovacLegacyCoordinator(
            hass,
            vacuum_id=vac_key,
            lan_ip=vacuum[CONF_IP_ADDRESS],
            local_code=vacuum[CONF_LOCAL_CODE],
            update_interval=interval,
        )
        await coord.async_config_entry_first_refresh()
        coordinators[vac_key] = coord

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinators": coordinators}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def reload_listener(hass_inst: HomeAssistant, config_entry: ConfigEntry) -> None:
        await hass_inst.config_entries.async_reload(config_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(reload_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and coordinators."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
