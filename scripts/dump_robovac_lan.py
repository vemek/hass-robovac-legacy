#!/usr/bin/env python3
"""Poll a legacy RoboVac over LAN and print status (no Home Assistant).

Reads ``ROBOVAC_LOCAL_CODE`` and ``ROBOVAC_LAN_IP`` from the environment unless
overridden by ``--local-code`` / ``--lan-ip``. If the local code is missing,
optionally log in to Eufy Home, list devices with LAN credentials, and print a
``.env`` snippet for copy-paste (this script never reads or writes ``.env``).

Run from the repo root (needs ``requests`` and ``pycryptodome`` in the environment)::

    PYTHONPATH="$(pwd)" python scripts/dump_robovac_lan.py
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _bootstrap_robovac_legacy_package() -> None:
    """Load ``lan`` / ``eufynet`` without executing ``robovac_legacy/__init__.py`` (no HA).

    When Home Assistant is importable, skip stubbing so a shared venv behaves normally.
    """

    try:
        import homeassistant  # noqa: F401, PLC0415
    except ImportError:
        import types

        cc = types.ModuleType("custom_components")
        cc.__path__ = [str(_REPO_ROOT / "custom_components")]
        sys.modules.setdefault("custom_components", cc)

        rl = types.ModuleType("custom_components.robovac_legacy")
        rl.__path__ = [str(_REPO_ROOT / "custom_components" / "robovac_legacy")]
        sys.modules["custom_components.robovac_legacy"] = rl


_bootstrap_robovac_legacy_package()

from custom_components.robovac_legacy.eufynet import (  # noqa: E402
    EufyLegacyError,
    LegacyVacuumCandidate,
    fetch_all_local_candidates,
)

ENV_LOCAL_CODE = "ROBOVAC_LOCAL_CODE"
ENV_LAN_IP = "ROBOVAC_LAN_IP"


def _activity_hint(status) -> str:
    """Mirror ``status_inference.infer_activity_key`` without Home Assistant."""

    from custom_components.robovac_legacy.status_inference import (  # noqa: PLC0415
        ACTIVITY_CLEANING,
        ACTIVITY_DOCKED,
        ACTIVITY_ERROR,
        ACTIVITY_IDLE,
        ACTIVITY_RETURNING,
        MODE_CLEANING,
        MODE_GO_HOME,
        infer_activity_key,
    )

    key = infer_activity_key(status)
    if key == ACTIVITY_ERROR:
        return "ERROR (non-zero robovac_error_code)"
    if key == ACTIVITY_DOCKED:
        return "DOCKED (charger_status == 1)"
    if key == ACTIVITY_CLEANING:
        return f"CLEANING (mode == {MODE_CLEANING}, stop == 0)"
    if key == ACTIVITY_RETURNING:
        return f"RETURNING (mode == {MODE_GO_HOME}, charger_status == 0)"
    if key == ACTIVITY_IDLE:
        return "IDLE"
    return key.upper()


def _hex_spaced(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def _print_lan_dump(ip: str, local_code: str, *, port: int) -> None:
    from custom_components.robovac_legacy.lan import Robovac  # noqa: PLC0415

    rv = Robovac(ip, local_code, port=port)
    rv.connect()
    try:
        status, usr_data = rv.get_status_with_raw()
    finally:
        rv.disconnect()

    from custom_components.robovac_legacy.status_inference import (  # noqa: PLC0415
        effective_battery_percent,
        is_battery_report_valid,
    )

    effective_battery = effective_battery_percent(status, None)
    battery_label = status.battery_capacity
    if effective_battery is not None and int(status.battery_capacity) != effective_battery:
        battery_label = f"{status.battery_capacity} (effective: {effective_battery})"

    print("\n--- LAN status (parsed) ---")
    print(f"  battery_percent:     {battery_label}")
    print(f"  battery_reported:    {is_battery_report_valid(status)}")
    print(f"  mode (raw byte):     {status.mode}")
    print(f"  speed (raw byte):    {status.speed}  (HA fan: 1=max, else standard)")
    print(f"  charger_status:      {status.charger_status}")
    print(f"  error_code:          {status.error_code}")
    print(f"  stop (raw byte):     {status.stop}")
    print(f"  water_tank_status:   {status.water_tank_status}")
    print(f"  find_me flag:        {status.find_me}")
    print(f"  HA activity hint:    {_activity_hint(status)}")

    print("\n--- LAN status (raw usr_data) ---")
    print(f"  length: {len(usr_data)} bytes")
    print(f"  hex:    {_hex_spaced(usr_data)}")
    print("  indices (decimal value at each offset):")
    for i, b in enumerate(usr_data):
        print(f"    [{i:2d}] = {b:3d}  (0x{b:02x})")


def _prompt_yes(question: str, default_no: bool = True) -> bool:
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    raw = input(question + suffix).strip().lower()
    if not raw:
        return not default_no
    return raw in ("y", "yes")


def _interactive_eufy_pick() -> LegacyVacuumCandidate | None:
    if not _prompt_yes("Fetch local_code from Eufy Home (email login)?", default_no=True):
        return None
    email = input("Eufy account email: ").strip()
    if not email:
        print("No email entered.", file=sys.stderr)
        return None
    password = getpass.getpass("Eufy account password: ")
    if not password:
        print("No password entered.", file=sys.stderr)
        return None
    try:
        rows = fetch_all_local_candidates(email, password)
    except EufyLegacyError as exc:
        print(f"Eufy request failed: {exc}", file=sys.stderr)
        return None
    if not rows:
        print("No devices with LAN IP + 16-char local_code in the account response.", file=sys.stderr)
        return None

    print("\nDevices (any product with LAN credentials):")
    for i, r in enumerate(rows):
        mac = r.mac or "-"
        print(
            f"  [{i}] {r.alias!r}  id={r.device_id}  product={r.product_code or '(none)'}  "
            f"ip={r.lan_ip}  mac={mac}"
        )

    while True:
        choice = input(f"Select index 0–{len(rows) - 1} (or q to quit): ").strip().lower()
        if choice == "q":
            return None
        try:
            idx = int(choice)
        except ValueError:
            print("Enter a number or q.", file=sys.stderr)
            continue
        if 0 <= idx < len(rows):
            return rows[idx]
        print("Index out of range.", file=sys.stderr)


def _print_env_snippet(c: LegacyVacuumCandidate) -> None:
    print("\n--- Paste into your environment file (do not commit secrets) ---")
    print(f"# Robovac LAN debug ({c.alias})")
    print(f"{ENV_LOCAL_CODE}={c.local_code}")
    print(f"{ENV_LAN_IP}={c.lan_ip}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dump legacy RoboVac LAN status (battery, raw bytes, HA hints).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Environment variables:
  {ENV_LOCAL_CODE}   16-character device local secret
  {ENV_LAN_IP}       Vacuum IPv4 on your LAN

Example:
  export {ENV_LOCAL_CODE}=abcdefghijklmnop
  export {ENV_LAN_IP}=192.168.1.50
  PYTHONPATH="$(pwd)" python scripts/dump_robovac_lan.py

Requires ``requests`` for optional Eufy login; ``pycryptodome`` for LAN polling (integration manifest).
""",
    )
    parser.add_argument("--local-code", dest="local_code", default=None, help="override env local code")
    parser.add_argument("--lan-ip", dest="lan_ip", default=None, help="override env LAN IP")
    parser.add_argument("--port", type=int, default=55556, help="TCP port (default 55556)")
    args = parser.parse_args()

    local_code = (args.local_code or os.environ.get(ENV_LOCAL_CODE) or "").strip()
    lan_ip = (args.lan_ip or os.environ.get(ENV_LAN_IP) or "").strip()

    picked: LegacyVacuumCandidate | None = None
    if not local_code:
        picked = _interactive_eufy_pick()
        if picked is None:
            print(
                f"\nSet {ENV_LOCAL_CODE} (and {ENV_LAN_IP}) or pass --local-code / --lan-ip.",
                file=sys.stderr,
            )
            return 1
        _print_env_snippet(picked)
        local_code = picked.local_code
        lan_ip = lan_ip or picked.lan_ip

    if not lan_ip:
        print(f"Missing LAN IP: set {ENV_LAN_IP} or use --lan-ip.", file=sys.stderr)
        return 1

    if len(local_code) != 16:
        print(f"{ENV_LOCAL_CODE} must be exactly 16 characters (got {len(local_code)}).", file=sys.stderr)
        return 1

    if picked is not None:
        if not _prompt_yes("\nProbe LAN now with the selected device?", default_no=False):
            return 0

    try:
        _print_lan_dump(lan_ip, local_code, port=args.port)
    except OSError as exc:
        print(f"LAN error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
