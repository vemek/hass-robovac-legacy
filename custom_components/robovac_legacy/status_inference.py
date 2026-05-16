"""Map raw LAN ``RobovacStatus`` fields to Home Assistant activity and battery semantics.

Observed on T2103 (see ``state_heuristics.txt`` at repo root):

| Scenario              | mode | stop | charger | battery |
|-----------------------|------|------|---------|---------|
| Docked                | 3    | 1    | 1       | 100     |
| Go home               | 3    | *    | 0       | *       |
| Idle (undocked)       | 0    | 1    | 0       | 99      |
| Cleaning              | 2    | 0    | 0       | 99      |
| Sleep (power-save)    | 240  | 0    | 0       | 0       |
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lan import RobovacStatus

if TYPE_CHECKING:
    from homeassistant.components.vacuum import VacuumActivity

MODE_IDLE = 0
MODE_CLEANING = 2
MODE_GO_HOME = 3
MODE_SLEEP = 240

ACTIVITY_ERROR = "error"
ACTIVITY_DOCKED = "docked"
ACTIVITY_CLEANING = "cleaning"
ACTIVITY_RETURNING = "returning"
ACTIVITY_IDLE = "idle"


def infer_activity_key(status: RobovacStatus) -> str:
    """Derive activity id from raw LAN status (no Home Assistant dependency)."""

    if int(status.error_code):
        return ACTIVITY_ERROR
    if int(status.charger_status) == 1:
        return ACTIVITY_DOCKED
    if int(status.mode) == MODE_CLEANING and int(status.stop) == 0:
        return ACTIVITY_CLEANING
    if int(status.mode) == MODE_GO_HOME:
        return ACTIVITY_RETURNING
    return ACTIVITY_IDLE


def infer_activity(status: RobovacStatus) -> VacuumActivity:
    """Derive HA vacuum activity from raw LAN status bytes."""

    from homeassistant.components.vacuum import VacuumActivity

    return {
        ACTIVITY_ERROR: VacuumActivity.ERROR,
        ACTIVITY_DOCKED: VacuumActivity.DOCKED,
        ACTIVITY_CLEANING: VacuumActivity.CLEANING,
        ACTIVITY_RETURNING: VacuumActivity.RETURNING,
        ACTIVITY_IDLE: VacuumActivity.IDLE,
    }[infer_activity_key(status)]


def is_battery_report_valid(status: RobovacStatus) -> bool:
    """Return whether ``battery_capacity`` is a live reading (not sleep sentinel)."""

    try:
        pct = int(status.battery_capacity)
    except (TypeError, ValueError):
        return False
    if not 1 <= pct <= 100:
        return False
    if pct == 0 and int(status.mode) == MODE_SLEEP:
        return False
    return True


def effective_battery_percent(
    status: RobovacStatus,
    last_valid: int | None,
) -> int | None:
    """Return reported battery when valid, otherwise the last good in-session value."""

    if is_battery_report_valid(status):
        return int(status.battery_capacity)
    return last_valid
