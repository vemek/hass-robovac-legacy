"""Config + options flows (pytest-homeassistant-custom-component harness)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_legacy.const import (
    CONF_DEVICE_IDS,
    CONF_LOCAL_CODE,
    CONF_REFRESH_FROM_CLOUD,
    CONF_VACS,
    DOMAIN,
)
from custom_components.robovac_legacy.config_flow import ConfigFlow, validate_login
from custom_components.robovac_legacy.eufynet import EufyLegacyError, LegacyVacuumCandidate


def _vac_entry(username: str = "alice@example.com") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=username.strip().lower(),
        title="RoboVac",
        data={
            CONF_USERNAME: username,
            CONF_PASSWORD: "pwd",
            CONF_VACS: {
                "d1": {
                    "id": "d1",
                    "name": "Kitchen Vac",
                    "description": "",
                    "model": "T2103",
                    "mac": "",
                    CONF_IP_ADDRESS: "192.168.1.10",
                    CONF_LOCAL_CODE: "A" * 16,
                }
            },
        },
    )


def _candidate() -> LegacyVacuumCandidate:
    return LegacyVacuumCandidate(
        device_id="d1",
        alias="Kitchen",
        model_name="RoboVac 11c",
        lan_ip="192.168.1.10",
        local_code="A" * 16,
        mac="AA:BB:CC:DD:EE:FF",
        product_code="T2103",
    )


@pytest.mark.asyncio
async def test_config_flow_abort_no_candidates(hass):  # type: ignore[no-untyped-def]
    """User step succeeds but empty picker -> abort."""

    await async_setup_component(hass, DOMAIN, {})

    with patch(
        "custom_components.robovac_legacy.config_flow.validate_login",
        new=AsyncMock(return_value=[]),
    ):
        start = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert start["step_id"] == "user"
        cont = await hass.config_entries.flow.async_configure(
            start["flow_id"],
            {CONF_USERNAME: "alice@example.com", CONF_PASSWORD: "x"},
        )
        assert cont["type"] == "abort"
        assert cont["reason"] == "no_devices"


@pytest.mark.asyncio
async def test_config_flow_invalid_auth(hass):  # type: ignore[no-untyped-def]
    """Eufy auth errors map to translation keys."""

    await async_setup_component(hass, DOMAIN, {})

    with patch(
        "custom_components.robovac_legacy.config_flow.validate_login",
        new=AsyncMock(
            side_effect=EufyLegacyError("invalid_auth"),
        ),
    ):
        start = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        bad = await hass.config_entries.flow.async_configure(
            start["flow_id"],
            {CONF_USERNAME: "alice@example.com", CONF_PASSWORD: "x"},
        )
        assert bad["type"] == "form"
        assert bad["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_config_flow_duplicate_unique_id(hass):  # type: ignore[no-untyped-def]
    """Second flow with same account aborts as already configured."""

    await async_setup_component(hass, DOMAIN, {})
    cand = [_candidate()]
    validate = AsyncMock(return_value=cand)

    with patch("custom_components.robovac_legacy.config_flow.validate_login", validate):
        r1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        step2 = await hass.config_entries.flow.async_configure(
            r1["flow_id"],
            {CONF_USERNAME: "bob@example.com", CONF_PASSWORD: "x"},
        )
        ok = await hass.config_entries.flow.async_configure(
            step2["flow_id"],
            {CONF_DEVICE_IDS: ["d1"]},
        )
        assert ok["type"] == "create_entry"

        restart = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        select = await hass.config_entries.flow.async_configure(
            restart["flow_id"],
            {CONF_USERNAME: "Bob@Example.com", CONF_PASSWORD: "other"},
        )
        assert select["step_id"] == "devices"
        dup = await hass.config_entries.flow.async_configure(
            select["flow_id"],
            {CONF_DEVICE_IDS: ["d1"]},
        )
        assert dup["type"] == "abort"
        assert dup["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_config_flow_unknown_exception_maps_unknown(hass):  # type: ignore[no-untyped-def]
    await async_setup_component(hass, DOMAIN, {})

    async def explode(*_a, **_k):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    with patch(
        "custom_components.robovac_legacy.config_flow.validate_login",
        new=explode,
    ):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        frm = await hass.config_entries.flow.async_configure(
            r["flow_id"],
            {CONF_USERNAME: "alice@example.com", CONF_PASSWORD: "x"},
        )
        assert frm["errors"]["base"] == "unknown"


@pytest.mark.asyncio
async def test_config_flow_devices_no_selection_error(hass):  # type: ignore[no-untyped-def]
    await async_setup_component(hass, DOMAIN, {})
    cand = [_candidate()]
    validate = AsyncMock(return_value=cand)

    with patch("custom_components.robovac_legacy.config_flow.validate_login", validate):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        step2 = await hass.config_entries.flow.async_configure(
            r["flow_id"],
            {CONF_USERNAME: "u@example.com", CONF_PASSWORD: "x"},
        )
        frm = await hass.config_entries.flow.async_configure(
            step2["flow_id"],
            {CONF_DEVICE_IDS: []},
        )
        assert frm["type"] == "form"
        assert frm["errors"]["base"] == "no_devices_selected"


@pytest.mark.asyncio
async def test_validate_login_executor_invokes_cloud(hass):  # type: ignore[no-untyped-def]
    with patch(
        "custom_components.robovac_legacy.config_flow.fetch_legacy_candidates",
        return_value=[_candidate()],
    ):
        picked = await validate_login(hass, " u@example.com ", "pwd")
        assert len(picked) == 1
        assert picked[0].device_id == "d1"


@pytest.mark.asyncio
async def test_devices_step_filters_unknown_candidate_ids(hass):  # type: ignore[no-untyped-def]
    """When every selected id disappears from ``candidate_map``, fail closed."""
    handler = ConfigFlow()
    handler.hass = hass  # noqa: SLF001
    handler._legacy_username = "u@example.com"  # noqa: SLF001
    handler._legacy_password = "p"  # noqa: SLF001
    handler._legacy_candidates = [_candidate()]  # noqa: SLF001

    out = await handler.async_step_devices({CONF_DEVICE_IDS: ["missing-id"]})

    assert out["type"] == "form"
    assert out["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_options_manual_ip(hass):  # type: ignore[no-untyped-def]
    """Manual LAN IP update writes merged entry data."""

    await async_setup_component(hass, DOMAIN, {})
    entry = _vac_entry()
    entry.add_to_hass(hass)

    opts = await hass.config_entries.options.async_init(entry.entry_id)
    pick = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"selected_vacuum": "d1"}
    )
    finish = await hass.config_entries.options.async_configure(
        pick["flow_id"],
        {CONF_REFRESH_FROM_CLOUD: False, CONF_IP_ADDRESS: "10.10.10.42"},
    )
    assert finish["type"] == "create_entry"
    refreshed = hass.config_entries.async_get_entry(entry.entry_id)
    assert refreshed is not None
    assert refreshed.data["vacs"]["d1"][CONF_IP_ADDRESS] == "10.10.10.42"


@pytest.mark.asyncio
async def test_options_no_change_raises_no_change(hass):  # type: ignore[no-untyped-def]
    await async_setup_component(hass, DOMAIN, {})
    entry = _vac_entry()
    entry.add_to_hass(hass)

    opts = await hass.config_entries.options.async_init(entry.entry_id)
    pick = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"selected_vacuum": "d1"}
    )
    same = await hass.config_entries.options.async_configure(
        pick["flow_id"],
        {CONF_REFRESH_FROM_CLOUD: False, CONF_IP_ADDRESS: "192.168.1.10"},
    )
    assert same["type"] == "form"
    assert same["errors"]["base"] == "no_change"


@pytest.mark.asyncio
async def test_options_cloud_refresh_updates_ip(hass):  # type: ignore[no-untyped-def]
    entry = _vac_entry()
    await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.robovac_legacy.config_flow.refresh_lan_ip",
        return_value="192.168.7.77",
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
        pick = await hass.config_entries.options.async_configure(
            opts["flow_id"], {"selected_vacuum": "d1"}
        )
        finish = await hass.config_entries.options.async_configure(
            pick["flow_id"],
            {CONF_REFRESH_FROM_CLOUD: True, CONF_IP_ADDRESS: ""},
        )
    assert finish["type"] == "create_entry"
    refreshed = hass.config_entries.async_get_entry(entry.entry_id)
    assert refreshed is not None
    assert refreshed.data["vacs"]["d1"][CONF_IP_ADDRESS] == "192.168.7.77"


@pytest.mark.asyncio
async def test_options_cloud_fail_manual_salvage(hass):  # type: ignore[no-untyped-def]
    entry = _vac_entry()
    await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.robovac_legacy.config_flow.refresh_lan_ip",
        return_value=None,
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
        pick = await hass.config_entries.options.async_configure(
            opts["flow_id"], {"selected_vacuum": "d1"}
        )
        finish = await hass.config_entries.options.async_configure(
            pick["flow_id"],
            {
                CONF_REFRESH_FROM_CLOUD: True,
                CONF_IP_ADDRESS: "192.168.9.9",
            },
        )
    assert finish["type"] == "create_entry"
    refreshed = hass.config_entries.async_get_entry(entry.entry_id)
    assert refreshed is not None
    assert refreshed.data["vacs"]["d1"][CONF_IP_ADDRESS] == "192.168.9.9"


@pytest.mark.asyncio
async def test_options_missing_credentials_on_refresh(hass):  # type: ignore[no-untyped-def]
    entry_data = dict(_vac_entry().data)
    entry_data.pop(CONF_PASSWORD, None)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="carol@example.com",
        title="RoboVac",
        data={
            CONF_USERNAME: "carol@example.com",
            **{k: v for k, v in entry_data.items() if k != CONF_USERNAME},
        },
    )

    await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)

    opts = await hass.config_entries.options.async_init(entry.entry_id)
    pick = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"selected_vacuum": "d1"}
    )
    cont = await hass.config_entries.options.async_configure(
        pick["flow_id"],
        {CONF_REFRESH_FROM_CLOUD: True, CONF_IP_ADDRESS: ""},
    )
    assert cont["type"] == "form"
    assert cont["errors"]["base"] == "cannot_connect"
