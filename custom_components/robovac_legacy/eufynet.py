"""Eufy Home cloud calls for onboarding (Apache-2.0 payload layout aligned with PyRobovac).

Runtime device control stays on LAN via PyRobovac — no Tuya.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

_LOGGER = logging.getLogger(__package__)

LOGIN_URL = "https://home-api.eufylife.com/v1/user/email/login"
DEVICES_GROUPS_URL = "https://home-api.eufylife.com/v1/device/list/devices-and-groups"


class EufyLegacyError(Exception):
    """Cloud interaction failed."""

    def __init__(self, translation_key: str, message: str | None = None) -> None:
        super().__init__(message or translation_key)
        self.translation_key = translation_key


@dataclass(frozen=True)
class LegacyVacuumCandidate:
    """A supported cleaner from Eufy ``devices-and-groups`` payload."""

    device_id: str
    alias: str
    model_name: str
    lan_ip: str
    local_code: str
    mac: str | None
    product_code: str


def _extract_product_code(device: dict[str, Any]) -> str | None:
    product = device.get("product")
    if isinstance(product, dict):
        raw = product.get("product_code")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    raw = device.get("product_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def legacy_candidates_from_items(
    items: list[Any],
    supported_product_codes: frozenset[str],
) -> list[LegacyVacuumCandidate]:
    """Build picker rows; skip malformed entries silently.

    Mirrors structure used by PyRobovac ``get_local_code``.
    """
    out: list[LegacyVacuumCandidate] = []
    for item in items:
        if not isinstance(item, dict) or "device" not in item:
            continue
        device = item.get("device")
        if not isinstance(device, dict):
            continue

        wifi = device.get("wifi") or {}
        if not isinstance(wifi, dict):
            continue

        lan_ip = (wifi.get("lan_ip_addr") or "").strip()
        local_raw = device.get("local_code")
        local_code = local_raw.strip() if isinstance(local_raw, str) else ""
        if not lan_ip or not local_code or len(local_code) != 16:
            continue

        product_code = _extract_product_code(device)
        if not product_code or product_code not in supported_product_codes:
            continue

        dev_id_raw = device.get("id") or device.get("device_sn")
        if not isinstance(dev_id_raw, str) or not dev_id_raw.strip():
            continue
        device_id = dev_id_raw.strip()

        alias = ""
        ali = device.get("alias_name")
        if isinstance(ali, str) and ali.strip():
            alias = ali.strip()
        name = ""
        nm = device.get("name")
        if isinstance(nm, str) and nm.strip():
            name = nm.strip()
        alias = alias or name or device_id

        mac_raw = wifi.get("mac")
        mac: str | None = None
        if isinstance(mac_raw, str):
            cand = mac_raw.strip().replace("-", ":").upper()
            if cand:
                mac = cand

        out.append(
            LegacyVacuumCandidate(
                device_id=device_id,
                alias=alias,
                model_name=name or product_code,
                lan_ip=lan_ip,
                local_code=local_code,
                mac=mac,
                product_code=product_code,
            )
        )

    out.sort(key=lambda c: (c.alias.casefold(), c.device_id))
    return out


def fetch_legacy_candidates(
    email: str,
    password: str,
    *,
    supported_product_codes: frozenset[str],
    timeout: float = 30.0,
) -> list[LegacyVacuumCandidate]:
    """Log in once, list ``devices-and-groups``, return supported legacy LAN vacuums."""
    payload = {
        "client_id": "eufyhome-app",
        "client_Secret": "GQCpr9dSp3uQpsOMgJ4xQ",
        "email": email,
        "password": password,
    }
    login = requests.post(LOGIN_URL, json=payload, timeout=timeout)
    if login.status_code != 200:
        _LOGGER.warning("Eufy login HTTP %s", login.status_code)
        raise EufyLegacyError("cannot_connect")

    try:
        body = login.json()
    except ValueError:
        raise EufyLegacyError("cannot_connect") from None

    if not isinstance(body, dict) or "access_token" not in body:
        _LOGGER.warning("Eufy login JSON missing token")
        raise EufyLegacyError("invalid_auth")

    headers = {"token": body["access_token"], "category": "Home"}
    devices_rsp = requests.get(DEVICES_GROUPS_URL, headers=headers, timeout=timeout)
    if devices_rsp.status_code != 200:
        _LOGGER.warning("Eufy devices list HTTP %s", devices_rsp.status_code)
        raise EufyLegacyError("cannot_connect")

    try:
        lst = devices_rsp.json()
    except ValueError:
        raise EufyLegacyError("cannot_connect") from None

    raw_items = lst.get("items") if isinstance(lst, dict) else None
    if not isinstance(raw_items, list):
        _LOGGER.warning("Eufy devices JSON had no usable items")
        raise EufyLegacyError("cannot_connect")

    return legacy_candidates_from_items(raw_items, supported_product_codes)


def refresh_lan_ip(
    email: str,
    password: str,
    device_id: str,
    *,
    timeout: float = 30.0,
) -> str | None:
    """Return ``lan_ip_addr`` from Eufy for the matching device id, if present."""
    payload = {
        "client_id": "eufyhome-app",
        "client_Secret": "GQCpr9dSp3uQpsOMgJ4xQ",
        "email": email,
        "password": password,
    }
    login = requests.post(LOGIN_URL, json=payload, timeout=timeout)
    if login.status_code != 200:
        return None

    try:
        body = login.json()
    except ValueError:
        return None

    token = body.get("access_token")
    if not isinstance(token, str):
        return None

    headers = {"token": token, "category": "Home"}
    devices_rsp = requests.get(DEVICES_GROUPS_URL, headers=headers, timeout=timeout)
    if devices_rsp.status_code != 200:
        return None

    try:
        lst = devices_rsp.json()
    except ValueError:
        return None

    raw_items = lst.get("items") if isinstance(lst, dict) else None
    if not isinstance(raw_items, list):
        return None

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        device = item.get("device")
        if not isinstance(device, dict):
            continue

        cid = device.get("id")
        csn = device.get("device_sn")
        cid_s = cid.strip() if isinstance(cid, str) else ""
        csn_s = csn.strip() if isinstance(csn, str) else ""
        cand_id = cid_s or csn_s
        if cand_id != device_id:
            continue

        wifi = device.get("wifi") or {}
        if not isinstance(wifi, dict):
            return None

        lan_ip = (wifi.get("lan_ip_addr") or "").strip()
        return lan_ip or None

    return None
