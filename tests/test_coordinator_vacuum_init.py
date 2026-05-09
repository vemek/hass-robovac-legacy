"""Coordinator lifecycle, mocked LAN I/O, vacuum helpers, setup/unload."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.components.vacuum import VacuumActivity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components import robovac_legacy
from custom_components.robovac_legacy.lan import RobovacStatus
from custom_components.robovac_legacy.const import CONF_LOCAL_CODE, CONF_VACS, DOMAIN
from custom_components.robovac_legacy.coordinator import RobovacLegacyCoordinator, UpdateFailed
from custom_components.robovac_legacy.vacuum import (
    FAN_MAX,
    FAN_STANDARD,
    RobovacLegacyVacuum,
    async_setup_entry as vacuum_async_setup_entry,
)


def _status(**kwargs):  # type: ignore[no-untyped-def]
    base = dict(
        find_me=0,
        water_tank_status=0,
        mode=3,
        speed=0,
        charger_status=1,
        battery_capacity=80,
        error_code=0,
        stop=0,
    )
    base.update(kwargs)
    return RobovacStatus(**base)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="RoboVac Legacy",
        unique_id="u@example.com",
        data={
            "username": "u@example.com",
            "password": "p",
            CONF_VACS: {
                "d1": {
                    "id": "d1",
                    "name": "Vac",
                    "description": "",
                    "model": "T2103",
                    "mac": "aa-bb-cc-dd-ee-ff",
                    CONF_IP_ADDRESS: "192.168.1.2",
                    CONF_LOCAL_CODE: "BCDEFGHIJKLMNOP",
                }
            },
        },
    )


def _vac_conf() -> dict:
    return dict(_entry().data[CONF_VACS]["d1"])


def _make_ro_mock(status_fn: Callable[[], RobovacStatus]) -> MagicMock:
    stub = MagicMock()
    stub.connect.return_value = None
    stub.disconnect.return_value = None
    stub.get_status.side_effect = status_fn

    stub.start_auto_clean.return_value = None
    stub.stop.return_value = None
    stub.go_forward.return_value = None
    stub.go_backward.return_value = None
    stub.go_left.return_value = None
    stub.go_right.return_value = None
    stub.start_edge_clean.return_value = None
    stub.use_max_speed.return_value = None
    stub.use_normal_speed.return_value = None
    stub.start_find_me.return_value = None
    stub.go_home.return_value = None
    stub.start_spot_clean.return_value = None
    return stub


@pytest.mark.asyncio
async def test_async_setup_registers_domain_bucket(hass):  # type: ignore[no-untyped-def]
    hass.data.pop(DOMAIN, None)
    assert await robovac_legacy.async_setup(hass, {})
    assert isinstance(hass.data[DOMAIN], dict)


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_typ,msg", [(TimeoutError, "slow"), (OSError, "lan"), (RuntimeError, "weird")])
async def test_coordinator_wraps_executor_errors(  # type: ignore[no-untyped-def]
    hass, exc_typ, msg
) -> None:
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="192.168.1.2",
        local_code="A" * 16,
        update_interval=timedelta(seconds=1),
    )

    def boom() -> RobovacStatus:
        raise exc_typ(msg)

    with patch(
        "custom_components.robovac_legacy.coordinator.Robovac",
        return_value=MagicMock(
            connect=lambda: None,
            disconnect=lambda: None,
            get_status=boom,
        ),
    ):
        await coordinator.async_refresh()

    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert msg in str(coordinator.last_exception)


@pytest.mark.asyncio
async def test_coordinator_async_exec_requests_refresh(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="192.168.1.2",
        local_code="A" * 16,
        update_interval=timedelta(seconds=1),
    )
    statuses = [_status()]
    stub = _make_ro_mock(lambda: statuses[0])

    with patch(
        "custom_components.robovac_legacy.coordinator.Robovac",
        return_value=stub,
    ):
        await coordinator.async_refresh()
        coordinator.async_request_refresh = AsyncMock()
        await coordinator.async_exec(lambda r: r.start_auto_clean())
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_entry_unloads_and_drops(hass):  # type: ignore[no-untyped-def]
    await async_setup_component(hass, DOMAIN, {})
    entry = _entry()

    statuses = [_status()]
    stub = _make_ro_mock(lambda: statuses[0])

    with patch("custom_components.robovac_legacy.coordinator.Robovac", return_value=stub):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        assert entry.entry_id in hass.data.get(DOMAIN, {})

        assert await hass.config_entries.async_unload(entry.entry_id)
        stash = hass.data.get(DOMAIN, {})
        assert entry.entry_id not in stash


@pytest.mark.asyncio
async def test_platform_registers_vacuum_state(hass):  # type: ignore[no-untyped-def]
    await async_setup_component(hass, DOMAIN, {})
    registry = er.async_get(hass)

    statuses = [_status()]
    stub = _make_ro_mock(lambda: statuses[0])

    entry = _entry()
    entry.add_to_hass(hass)

    with patch("custom_components.robovac_legacy.coordinator.Robovac", return_value=stub):
        assert await hass.config_entries.async_setup(entry.entry_id)

    vac_ids_before = hass.states.async_entity_ids("vacuum")
    assert len(vac_ids_before) == 1

    assert len(er.async_entries_for_config_entry(registry, entry.entry_id)) == 1

    unload_ok = await hass.config_entries.async_unload(entry.entry_id)
    assert unload_ok
    await hass.async_block_till_done()

    stash = hass.data.get(DOMAIN)
    assert stash is None or entry.entry_id not in stash


@pytest.mark.asyncio
async def test_vacuum_activity_speed_battery(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="192.168.4.5",
        local_code="C" * 16,
        update_interval=timedelta(seconds=1),
    )
    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())

    coordinator.async_set_updated_data(
        _status(
            charger_status=2,
            battery_capacity="oops",
            speed=1,
            mode=9,
            water_tank_status=7,
            find_me=1,
            stop=5,
            error_code=0,
        )
    )
    assert vacuum.battery_level is None
    assert vacuum.fan_speed == FAN_MAX
    assert vacuum.activity == VacuumActivity.IDLE

    attrs = vacuum.extra_state_attributes
    assert attrs["robovac_mode"] == 9
    assert attrs["robovac_water_tank"] == 7
    assert attrs["robovac_find_me_flag"] == 1
    assert attrs["robovac_stop_flag"] == 5

    coordinator.async_set_updated_data(_status(error_code=4, charger_status=1))
    assert vacuum.activity == VacuumActivity.ERROR

    coordinator.async_set_updated_data(_status(error_code=0, charger_status=1))
    assert vacuum.activity == VacuumActivity.DOCKED

    coordinator.async_set_updated_data(None)  # type: ignore[arg-type]
    assert vacuum.activity is None


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd,signal", [("FoRwArD", "go_forward"), ("left", "go_left")])
async def test_send_command_direction(hass, cmd, signal):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.0.44",
        local_code="D" * 16,
        update_interval=timedelta(seconds=1),
    )

    hits: list[str] = []

    async def recorder(actor):  # type: ignore[no-untyped-def]
        rob = MagicMock()
        setattr(
            rob,
            signal,
            MagicMock(side_effect=lambda: hits.append(signal)),
        )
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_send_command(cmd)
    assert signal in hits


@pytest.mark.asyncio
async def test_send_command_edge_clean(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.0.45",
        local_code="E" * 16,
        update_interval=timedelta(seconds=1),
    )

    invoked = False

    async def recorder(actor):  # type: ignore[no-untyped-def]
        nonlocal invoked
        rob = MagicMock()

        def _edge() -> None:
            nonlocal invoked
            invoked = True

        rob.start_edge_clean.side_effect = _edge
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_send_command("edge_clean")

    assert invoked


@pytest.mark.asyncio
async def test_send_command_params_direction(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.0.46",
        local_code="F" * 16,
        update_interval=timedelta(seconds=1),
    )

    hits: list[str] = []

    async def recorder(actor):  # type: ignore[no-untyped-def]
        rob = MagicMock()
        rob.go_backward.side_effect = lambda: hits.append("backward")
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_send_command("noop", {"direction": "backward"})
    assert hits == ["backward"]


@pytest.mark.asyncio
async def test_send_command_unknown_warns(hass, caplog):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.0.47",
        local_code="0" * 16,
        update_interval=timedelta(seconds=1),
    )

    coordinator.async_exec = AsyncMock()

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_send_command("teleport")
    coordinator.async_exec.assert_not_called()
    assert any("unsupported" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_fan_speed_standard(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="192.168.1.88",
        local_code="1" * 16,
        update_interval=timedelta(seconds=1),
    )

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    coordinator.async_set_updated_data(_status(speed=2))
    assert vacuum.fan_speed == FAN_STANDARD


@pytest.mark.parametrize(
    ("method_name", "attr"),
    [
        ("async_start", "start_auto_clean"),
        ("async_pause", "stop"),
        ("async_stop", "stop"),
        ("async_clean_spot", "start_spot_clean"),
        ("async_locate", "start_find_me"),
        ("async_return_to_base", "go_home"),
    ],
)
@pytest.mark.asyncio
async def test_vacuum_service_wrappers_invoke_exec(hass, method_name, attr):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.11.11.99",
        local_code="Z" * 16,
        update_interval=timedelta(seconds=1),
    )

    calls: list[str] = []

    async def recorder(actor):  # type: ignore[no-untyped-def]
        rob = MagicMock()
        getattr(rob, attr).side_effect = lambda: calls.append(attr)
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await getattr(vacuum, method_name)()
    assert attr in calls


@pytest.mark.asyncio
async def test_set_fan_speed_routes_through_exec(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.99.99",
        local_code="Y" * 16,
        update_interval=timedelta(seconds=1),
    )

    recorded: dict[str, str] = {}

    async def recorder(actor):  # type: ignore[no-untyped-def]
        rob = MagicMock()
        rob.use_max_speed.side_effect = lambda: recorded.setdefault("mode", "max")
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_set_fan_speed(FAN_MAX)
    assert recorded["mode"] == "max"


@pytest.mark.asyncio
async def test_set_fan_speed_normal(hass):  # type: ignore[no-untyped-def]
    coordinator = RobovacLegacyCoordinator(
        hass,
        vacuum_id="d1",
        lan_ip="10.0.99.100",
        local_code="Y" * 16,
        update_interval=timedelta(seconds=1),
    )

    recorded: dict[str, str] = {}

    async def recorder(actor):  # type: ignore[no-untyped-def]
        rob = MagicMock()
        rob.use_normal_speed.side_effect = lambda: recorded.setdefault("mode", "std")
        actor(rob)

    coordinator.async_exec = recorder  # type: ignore[method-assign]

    vacuum = RobovacLegacyVacuum(coordinator, vacuum_id="d1", vacuum_config=_vac_conf())
    await vacuum.async_set_fan_speed("Standard")
    assert recorded["mode"] == "std"


@pytest.mark.asyncio
async def test_vacuum_platform_early_exit(hass):  # type: ignore[no-untyped-def]
    hass.data.setdefault(DOMAIN, {})
    entry = Mock()
    entry.entry_id = "missing-runtime"
    entry.data = {
        CONF_VACS: {"d1": {CONF_LOCAL_CODE: "A" * 16, CONF_IP_ADDRESS: "1.1.1.1"}},
    }
    spy = MagicMock()

    await vacuum_async_setup_entry(hass, entry, spy)
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_vacuum_platform_skips_missing_coordinator(hass):  # type: ignore[no-untyped-def]
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["half"] = {"coordinators": {}}
    entry = Mock()
    entry.entry_id = "half"
    entry.data = {
        CONF_VACS: {"d1": {CONF_LOCAL_CODE: "Z" * 16, CONF_IP_ADDRESS: "8.8.8.8"}},
    }
    spy = MagicMock()

    await vacuum_async_setup_entry(hass, entry, spy)
    spy.assert_called_once_with([])
