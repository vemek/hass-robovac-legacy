"""Sensors exposing coordinator telemetry as first-class HA entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_MAC, CONF_MODEL, CONF_NAME, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VACS, DOMAIN
from .coordinator import RobovacLegacyCoordinator


class RobovacLegacyBatterySensor(CoordinatorEntity[RobovacLegacyCoordinator], SensorEntity):
    """Battery percentage mirrored from LAN status polls (vacuum entities no longer report it)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: RobovacLegacyCoordinator,
        *,
        vacuum_id: str,
        vacuum_config: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._vacuum_id = vacuum_id
        self._vacuum_config = vacuum_config
        self._attr_unique_id = f"{vacuum_id}_battery"
        mac = vacuum_config.get(CONF_MAC)
        connections = set()
        if isinstance(mac, str) and mac:
            formatted = dr.format_mac(mac)
            if formatted:
                connections.add((dr.CONNECTION_NETWORK_MAC, formatted))
        dev_id_stored = vacuum_config.get(CONF_ID) or vacuum_id
        assert isinstance(dev_id_stored, str)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev_id_stored)},
            name=vacuum_config.get(CONF_NAME) or vacuum_id,
            manufacturer="Anker/Eufy",
            model=vacuum_config.get(CONF_MODEL),
            connections=connections if connections else None,
        )

    @property
    def native_value(self) -> int | None:
        """Return battery percentage parsed from telemetry."""

        return self.coordinator.battery_percent


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Battery sensor per vacuum/coordinator."""

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not entry_data:
        return
    coordinators = entry_data.get("coordinators", {})

    entities: list[RobovacLegacyBatterySensor] = []
    vacuums_conf = config_entry.data[CONF_VACS]
    for vac_key in vacuums_conf:
        coords = coordinators.get(vac_key)
        if coords is None:
            continue
        entities.append(
            RobovacLegacyBatterySensor(
                coords,
                vacuum_id=vac_key,
                vacuum_config=vacuums_conf[vac_key],
            )
        )

    async_add_entities(entities)
