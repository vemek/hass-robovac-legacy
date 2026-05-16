"""Data update coordinator for LAN-connected legacy RoboVac vacuums."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import const
from .lan import Robovac, RobovacStatus
from .status_inference import is_battery_report_valid

_LOGGER = logging.getLogger(__name__)


class RobovacLegacyCoordinator(DataUpdateCoordinator[RobovacStatus]):
    """Poll LAN status inside the executor."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        vacuum_id: str,
        lan_ip: str,
        local_code: str,
        update_interval: timedelta,
    ) -> None:
        self._lan_ip = lan_ip
        self._local_code = local_code
        self._last_battery_percent: int | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{const.DOMAIN}_{vacuum_id}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> RobovacStatus:
        def poll() -> RobovacStatus:
            rv = Robovac(self._lan_ip, self._local_code)
            rv.connect()
            try:
                return rv.get_status()
            finally:
                rv.disconnect()

        try:
            status = await self.hass.async_add_executor_job(poll)
        except TimeoutError as err:
            raise UpdateFailed(str(err)) from err
        except OSError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err

        if is_battery_report_valid(status):
            self._last_battery_percent = int(status.battery_capacity)
        return status

    @property
    def battery_percent(self) -> int | None:
        """Battery % for entities: live reading or last valid value while in sleep."""

        if not self.data:
            return None
        if is_battery_report_valid(self.data):
            return int(self.data.battery_capacity)
        return self._last_battery_percent

    async def async_exec(self, actor: Callable[[Robovac], None]) -> None:
        """Run ``actor(robovac)`` on executor with fresh connect/disconnect."""

        def run() -> None:
            rv = Robovac(self._lan_ip, self._local_code)
            rv.connect()
            try:
                actor(rv)
            finally:
                rv.disconnect()

        await self.hass.async_add_executor_job(run)
        await self.async_request_refresh()
