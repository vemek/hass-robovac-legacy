"""Tests for cloud HTTP helpers (requests mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.robovac_legacy.const import SUPPORTED_LEGACY_PRODUCT_CODES
from custom_components.robovac_legacy.eufynet import (
    EufyLegacyError,
    fetch_all_local_candidates,
    fetch_legacy_candidates,
    refresh_lan_ip,
)


def _login_ok_token() -> MagicMock:
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"access_token": "tok"}
    return m


def _devices_ok(items: list) -> MagicMock:
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"items": items}
    return m


def _candidate_item(device_id: str = "dev1") -> dict:
    return {
        "device": {
            "id": device_id,
            "alias_name": "Kitchen",
            "name": "RoboVac 11c",
            "product": {"product_code": "T2103"},
            "local_code": "ABCDEFGHIJKLMNOP",
            "wifi": {"mac": "aa-bb-cc-dd-ee-ff", "lan_ip_addr": "192.168.1.50"},
        }
    }


def _t2276_item(device_id: str = "dev2276") -> dict:
    return {
        "device": {
            "id": device_id,
            "alias_name": "Living",
            "name": "Other vac",
            "product": {"product_code": "T2276"},
            "local_code": "BBBBBBBBBBBBBBBB",
            "wifi": {"mac": "11-22-33-44-55-66", "lan_ip_addr": "192.168.1.60"},
        }
    }


def test_fetch_all_local_candidates_includes_non_t2103() -> None:
    login = _login_ok_token()
    devices = _devices_ok([_candidate_item(), _t2276_item()])

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        rows = fetch_all_local_candidates("a@b.c", "secret")

    ids = {r.device_id for r in rows}
    assert ids == {"dev1", "dev2276"}
    t2276 = next(r for r in rows if r.device_id == "dev2276")
    assert t2276.product_code == "T2276"
    assert t2276.local_code == "BBBBBBBBBBBBBBBB"


def test_fetch_candidates_success() -> None:
    login = _login_ok_token()
    devices = _devices_ok([_candidate_item()])

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ) as post_mock, patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ) as get_mock:
        rows = fetch_legacy_candidates(
            "a@b.c",
            "secret",
            supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES,
        )

    assert len(rows) == 1
    assert rows[0].device_id == "dev1"
    assert rows[0].lan_ip == "192.168.1.50"
    login.json.assert_called_once()
    post_mock.assert_called_once()
    get_mock.assert_called_once()


def test_fetch_candidates_login_http_error_raises() -> None:
    login = MagicMock()
    login.status_code = 500

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "cannot_connect"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_fetch_candidates_login_bad_json_raises() -> None:
    login = MagicMock()
    login.status_code = 200
    login.json.side_effect = ValueError("bad")

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "cannot_connect"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_fetch_candidates_missing_token_raises_invalid_auth() -> None:
    login = MagicMock()
    login.status_code = 200
    login.json.return_value = {}

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "invalid_auth"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_fetch_candidates_devices_http_error_raises() -> None:
    login = _login_ok_token()
    devices = MagicMock()
    devices.status_code = 503

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "cannot_connect"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_fetch_candidates_devices_bad_json_raises() -> None:
    login = _login_ok_token()
    devices = MagicMock()
    devices.status_code = 200
    devices.json.side_effect = ValueError("oops")

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "cannot_connect"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_fetch_candidates_items_not_list_raises() -> None:
    login = _login_ok_token()
    devices = MagicMock()
    devices.status_code = 200
    devices.json.return_value = {"items": None}

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        try:
            fetch_legacy_candidates("a@b.c", "x", supported_product_codes=SUPPORTED_LEGACY_PRODUCT_CODES)
        except EufyLegacyError as e:
            assert e.translation_key == "cannot_connect"
        else:
            raise AssertionError("expected EufyLegacyError")


def test_refresh_lan_ip_happy_by_id_match() -> None:
    login = _login_ok_token()
    devices = _devices_ok([_candidate_item("dev1")])

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        ip = refresh_lan_ip("a@b.c", "pw", "dev1")

    assert ip == "192.168.1.50"


def test_refresh_lan_ip_login_fail_returns_none() -> None:
    login = MagicMock()
    login.status_code = 401

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login):
        assert refresh_lan_ip("a@b.c", "x", "anything") is None


def test_refresh_lan_ip_device_not_found_returns_none() -> None:
    login = _login_ok_token()
    devices = _devices_ok([])

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=devices,
    ):
        assert refresh_lan_ip("a@b.c", "x", "missing") is None


def test_refresh_lan_ip_match_by_device_sn() -> None:
    login = _login_ok_token()
    payload = _candidate_item("will-use-sn-field")
    del payload["device"]["id"]
    payload["device"]["device_sn"] = "serial-9"

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=_devices_ok([payload]),
    ):
        assert refresh_lan_ip("a@b.c", "x", "serial-9") == "192.168.1.50"
