"""Unit tests for LAN status heuristics (activity + battery)."""

from __future__ import annotations

import pytest
from homeassistant.components.vacuum import VacuumActivity

from custom_components.robovac_legacy.lan import RobovacStatus
from custom_components.robovac_legacy.status_inference import (
    MODE_CLEANING,
    MODE_GO_HOME,
    MODE_IDLE,
    MODE_SLEEP,
    effective_battery_percent,
    infer_activity,
    infer_activity_key,
    is_battery_report_valid,
)


def _status(**kwargs):  # type: ignore[no-untyped-def]
    base = dict(
        find_me=0,
        water_tank_status=0,
        mode=MODE_IDLE,
        speed=0,
        charger_status=0,
        battery_capacity=99,
        error_code=0,
        stop=1,
    )
    base.update(kwargs)
    return RobovacStatus(**base)


@pytest.mark.parametrize(
    ("status_kwargs", "expected_key", "expected_activity"),
    [
        (
            dict(mode=MODE_GO_HOME, stop=1, charger_status=1, battery_capacity=100),
            "docked",
            VacuumActivity.DOCKED,
        ),
        (
            dict(mode=MODE_IDLE, stop=1, charger_status=0, battery_capacity=99),
            "idle",
            VacuumActivity.IDLE,
        ),
        (
            dict(mode=MODE_CLEANING, stop=0, charger_status=0, battery_capacity=99),
            "cleaning",
            VacuumActivity.CLEANING,
        ),
        (
            dict(mode=MODE_GO_HOME, stop=0, charger_status=0, battery_capacity=80),
            "returning",
            VacuumActivity.RETURNING,
        ),
        (
            dict(mode=MODE_SLEEP, stop=0, charger_status=0, battery_capacity=0),
            "idle",
            VacuumActivity.IDLE,
        ),
        (
            dict(error_code=4, charger_status=1),
            "error",
            VacuumActivity.ERROR,
        ),
    ],
    ids=["docked", "idle", "cleaning", "returning", "sleep", "error"],
)
def test_infer_activity_matrix(status_kwargs, expected_key, expected_activity):  # type: ignore[no-untyped-def]
    st = _status(**status_kwargs)
    assert infer_activity_key(st) == expected_key
    assert infer_activity(st) == expected_activity


def test_battery_valid_and_sleep_withhold():  # type: ignore[no-untyped-def]
    awake = _status(battery_capacity=99)
    assert is_battery_report_valid(awake) is True
    assert effective_battery_percent(awake, last_valid=50) == 99

    asleep = _status(mode=MODE_SLEEP, battery_capacity=0, stop=0)
    assert is_battery_report_valid(asleep) is False
    assert effective_battery_percent(asleep, last_valid=99) == 99
    assert effective_battery_percent(asleep, last_valid=None) is None
