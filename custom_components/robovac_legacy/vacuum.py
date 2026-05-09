"""LAN legacy RoboVac vacuum entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_IP_ADDRESS, CONF_MAC, CONF_MODEL, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VACS, DOMAIN
from .coordinator import RobovacLegacyCoordinator

_LOGGER = logging.getLogger(__name__)

FAN_STANDARD = "standard"
FAN_MAX = "max"
FAN_SPEEDS = [FAN_STANDARD, FAN_MAX]

_DRIVE_MAP = {
    "forward": lambda r: r.go_forward(),
    "backward": lambda r: r.go_backward(),
    "left": lambda r: r.go_left(),
    "right": lambda r: r.go_right(),
}


def _activity_from_status(charger_status: int, error_code: int) -> VacuumActivity:
    """Map raw LAN status ints to HA activity (minimal; exposes raw ints as attributes).

    Charging-on-dock heuristic: ``charger_status == 1`` (community practice for RoboVac 11c).
    """
    if error_code:
        return VacuumActivity.ERROR
    if charger_status == 1:
        return VacuumActivity.DOCKED
    return VacuumActivity.IDLE


class RobovacLegacyVacuum(CoordinatorEntity[RobovacLegacyCoordinator], StateVacuumEntity):
    """Home Assistant vacuum for Eufy 11c (lakeside-style LAN protobuf)."""

    _attr_fan_speed_list = FAN_SPEEDS
    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.CLEAN_SPOT
        | VacuumEntityFeature.LOCATE
        | VacuumEntityFeature.SEND_COMMAND
    )

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
        self._attr_unique_id = f"{vacuum_id}_vacuum"
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
    def name(self) -> str | None:
        """Return readable name."""
        name = self._vacuum_config.get(CONF_NAME)
        return name if isinstance(name, str) and name else None

    @property
    def activity(self) -> VacuumActivity | None:
        """Return inferred activity."""
        if not self.coordinator.data:
            return None
        st = self.coordinator.data
        return _activity_from_status(st.charger_status, int(st.error_code))

    @property
    def fan_speed(self) -> str | None:
        """Interpret speed byte."""
        if not self.coordinator.data:
            return None
        if int(self.coordinator.data.speed) == 1:
            return FAN_MAX
        return FAN_STANDARD

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw telemetry for scripting."""
        attrs: dict[str, Any] = {}
        vac = self._vacuum_config
        attrs["lan_ip_address"] = vac.get(CONF_IP_ADDRESS)
        attrs["robovac_device_id"] = vac.get(CONF_ID)
        attrs["robovac_model_code"] = vac.get(CONF_MODEL)
        st = self.coordinator.data
        if st:
            attrs["robovac_mode"] = int(st.mode)
            attrs["robovac_speed_byte"] = int(st.speed)
            attrs["robovac_charger_status"] = int(st.charger_status)
            attrs["robovac_water_tank"] = int(st.water_tank_status)
            attrs["robovac_find_me_flag"] = int(st.find_me)
            attrs["robovac_stop_flag"] = int(st.stop)
            attrs["robovac_error_code"] = int(st.error_code)
        return attrs

    async def async_start(self) -> None:
        """Start auto cleaning."""
        await self.coordinator.async_exec(lambda r: r.start_auto_clean())

    async def async_pause(self) -> None:
        """Pause / stop blade motion (implementation uses STOP_CLEAN).

        Continue by calling ``async_start``.
        """
        await self.coordinator.async_exec(lambda r: r.stop())

    async def async_stop(self, **kwargs: Any) -> None:
        """Alias of pause for vacuums that implement ``stop()`` as cease cleaning."""
        await self.async_pause()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return to dock."""
        await self.coordinator.async_exec(lambda r: r.go_home())

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Spot clean."""
        await self.coordinator.async_exec(lambda r: r.start_spot_clean())

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set suction."""
        lowered = fan_speed.lower()
        if lowered == FAN_MAX:
            await self.coordinator.async_exec(lambda r: r.use_max_speed())
        else:
            await self.coordinator.async_exec(lambda r: r.use_normal_speed())

    async def async_locate(self, **kwargs: Any) -> None:
        """Play find-me tone."""
        await self.coordinator.async_exec(lambda r: r.start_find_me())

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Extras: ``edge_clean``, directional drive when ``command`` maps to movement."""
        lowered = command.lower()
        if lowered == "edge_clean":
            await self.coordinator.async_exec(lambda r: r.start_edge_clean())
            return
        direction = lowered
        if isinstance(params, dict) and params.get("direction"):
            direction = str(params["direction"]).lower()

        mover = _DRIVE_MAP.get(direction)
        if mover is None:
            _LOGGER.warning("Unsupported send_command: %s", command)
            return

        await self.coordinator.async_exec(mover)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Declare vacuum entities for each coordinator."""
    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not entry_data:
        return
    coordinators = entry_data.get("coordinators", {})

    entities: list[RobovacLegacyVacuum] = []
    vacuums_conf = config_entry.data[CONF_VACS]
    for vac_key in vacuums_conf:
        coords = coordinators.get(vac_key)
        if coords is None:
            continue
        entities.append(
            RobovacLegacyVacuum(
                coords,
                vacuum_id=vac_key,
                vacuum_config=vacuums_conf[vac_key],
            )
        )

    async_add_entities(entities)
