"""Configure Eufy RoboVac legacy."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_DESCRIPTION,
    CONF_ID,
    CONF_IP_ADDRESS,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_IDS,
    CONF_LOCAL_CODE,
    CONF_REFRESH_FROM_CLOUD,
    CONF_VACS,
    DOMAIN,
    SUPPORTED_LEGACY_PRODUCT_CODES,
)
from .eufynet import (
    EufyLegacyError,
    LegacyVacuumCandidate,
    fetch_legacy_candidates,
    refresh_lan_ip,
)

_LOGGER = logging.getLogger(__package__)


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


async def validate_login(
    hass: HomeAssistant,
    username: str,
    password: str,
) -> list[LegacyVacuumCandidate]:
    """Return supported candidates or raise."""

    def job() -> list[LegacyVacuumCandidate]:
        return fetch_legacy_candidates(
            username.strip(),
            password,
            supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES,
        )

    return await hass.async_add_executor_job(job)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[misc,call-arg]
    """OAuth-less Eufy credential + device picker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gather Eufy account credentials."""

        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                candidates = await validate_login(self.hass, username, password)
            except EufyLegacyError as exc:
                _LOGGER.warning("Eufy legacy login failed (%s)", exc.translation_key)
                if exc.translation_key == "invalid_auth":
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during credential validation")
                errors["base"] = "unknown"
            else:
                if not candidates:
                    return self.async_abort(reason="no_devices")

                self._legacy_username = username
                self._legacy_password = password
                self._legacy_candidates = candidates
                return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select which supported vacuums to import."""

        errors: dict[str, str] = {}
        candidates: list[LegacyVacuumCandidate] = self._legacy_candidates

        options = [
            {
                "value": candidate.device_id,
                "label": f"{candidate.alias} ({candidate.product_code}) • {candidate.lan_ip}",
            }
            for candidate in candidates
        ]
        selector_field = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            ),
        )

        devices_schema = vol.Schema({vol.Required(CONF_DEVICE_IDS): selector_field})

        if user_input is not None:
            selected_ids: list[str] = [
                sid for sid in user_input.get(CONF_DEVICE_IDS, []) if isinstance(sid, str)
            ]
            if not selected_ids:
                errors["base"] = "no_devices_selected"
            else:
                candidate_map = {c.device_id: c for c in candidates}
                vacs: dict[str, dict[str, Any]] = {}
                for device_id in selected_ids:
                    candidate = candidate_map.get(device_id)
                    if candidate is None:
                        continue
                    vacs[device_id] = {
                        CONF_ID: candidate.device_id,
                        CONF_NAME: candidate.alias,
                        CONF_DESCRIPTION: candidate.model_name,
                        CONF_MODEL: candidate.product_code,
                        CONF_MAC: candidate.mac or "",
                        CONF_IP_ADDRESS: candidate.lan_ip,
                        CONF_LOCAL_CODE: candidate.local_code,
                    }

                if not vacs:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(self._legacy_username.strip().lower())
                    self._abort_if_unique_id_configured()
                    title = self._legacy_username.strip()
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_USERNAME: self._legacy_username,
                            CONF_PASSWORD: self._legacy_password,
                            CONF_VACS: vacs,
                        },
                    )

        return self.async_show_form(
            step_id="devices",
            data_schema=self.add_suggested_values_to_schema(
                devices_schema, user_input or {}
            ),
            errors=errors,
        )

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Expose options UI."""
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Allow IP refresh/manual adjustments."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._config_entry = entry
        self._selected_device: str | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick which vacuum slot to tweak."""

        if user_input is not None:
            self._selected_device = user_input["selected_vacuum"]
            return await self.async_step_adjust()

        vacuum_list = {
            device_id: data.get(CONF_NAME, device_id)
            for device_id, data in self._config_entry.data[CONF_VACS].items()
        }
        schema = vol.Schema(
            {"selected_vacuum": vol.In(vacuum_list)},
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_adjust(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Refresh IP via Eufy or type a LAN address."""

        assert self._selected_device is not None
        vacuums = self._config_entry.data[CONF_VACS]
        target = vacuums[self._selected_device]
        username = self._config_entry.data.get(CONF_USERNAME, "")
        password = self._config_entry.data.get(CONF_PASSWORD, "")
        prior_ip = (target.get(CONF_IP_ADDRESS, "") or "").strip()

        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Optional(CONF_REFRESH_FROM_CLOUD, default=False): bool,
                vol.Optional(
                    CONF_IP_ADDRESS,
                    default=target.get(CONF_IP_ADDRESS, ""),
                ): str,
            }
        )

        if user_input is not None:
            refresh_requested = bool(user_input.get(CONF_REFRESH_FROM_CLOUD))
            manual_ip = (user_input.get(CONF_IP_ADDRESS) or "").strip()

            merged: dict[str, Any] = {
                key: val
                for key, val in self._config_entry.data.items()
                if key != CONF_VACS
            }
            merged[CONF_VACS] = {
                vac_key: dict(vac_blob)
                for vac_key, vac_blob in self._config_entry.data[CONF_VACS].items()
            }
            merged_target = merged[CONF_VACS][self._selected_device]

            cloud_ip: str | None = None
            if refresh_requested:
                if not username or not password:
                    errors["base"] = "cannot_connect"
                else:
                    cloud_candidate = await self.hass.async_add_executor_job(
                        refresh_lan_ip,
                        username,
                        password,
                        self._selected_device,
                    )
                    if cloud_candidate:
                        cloud_ip = cloud_candidate.strip()

            chosen_ip = prior_ip
            if manual_ip:
                chosen_ip = manual_ip
            elif cloud_ip:
                chosen_ip = cloud_ip
            elif refresh_requested and errors:
                pass  # Already recorded cannot_connect errors.
            elif refresh_requested:
                errors["base"] = "cannot_refresh"
            elif not manual_ip:
                errors["base"] = "no_change"

            # Manual IP salvage when cloud lookup fails but form provided an address.
            if errors.get("base") in {"cannot_refresh", "cannot_connect"} and manual_ip:
                errors.pop("base", None)
                chosen_ip = manual_ip

            if not errors and chosen_ip.strip() == prior_ip:
                errors["base"] = "no_change"

            if not errors:
                merged_target[CONF_IP_ADDRESS] = chosen_ip.strip()
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=merged,
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="adjust",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                {
                    CONF_REFRESH_FROM_CLOUD: False,
                    CONF_IP_ADDRESS: prior_ip or target.get(CONF_IP_ADDRESS, ""),
                },
            ),
            errors=errors,
        )
