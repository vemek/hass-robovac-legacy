"""Additional ``eufynet`` branches (pure Python, pytest)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.robovac_legacy.const import SUPPORTED_LEGACY_PRODUCT_CODES
from custom_components.robovac_legacy.eufynet import (
    legacy_candidates_from_items,
    refresh_lan_ip,
)


def test_extract_product_prefers_nested_dict() -> None:
    rows = legacy_candidates_from_items(
        [
            {
                "device": {
                    "id": "p1",
                    "alias_name": "A",
                    "name": "",
                    "local_code": "ABCDEFGHIJKLMNOP",
                    "product": {"product_code": "T2103"},
                    "wifi": {"lan_ip_addr": "10.0.0.1"},
                }
            },
            {
                "device": {
                    "id": "p2",
                    "alias_name": "Flat",
                    "name": "",
                    "product_code": "T2103",
                    "local_code": "BBBBBBBBBBBBBBBB",
                    "wifi": {"lan_ip_addr": "10.0.0.2"},
                }
            },
        ],
        SUPPORTED_LEGACY_PRODUCT_CODES,
    )
    assert {r.device_id for r in rows} == {"p1", "p2"}


def test_skips_wifi_not_dict_or_missing_device_shapes() -> None:
    payloads = (
        [{"device": {"id": "x", "wifi": [], "product": {"product_code": "T2103"}}}],
        [{}],
        [{"device": {}}],
    )
    for items in payloads:
        assert legacy_candidates_from_items(items, SUPPORTED_LEGACY_PRODUCT_CODES) == []


def test_refresh_login_json_failure_returns_none() -> None:
    login = MagicMock(status_code=200)
    login.json.side_effect = ValueError("boom")

    with patch("custom_components.robovac_legacy.eufynet.requests.post", return_value=login):
        assert refresh_lan_ip("a", "b", "id") is None


def test_refresh_devices_bad_json_returns_none() -> None:
    login = MagicMock(status_code=200)
    login.json.return_value = {"access_token": "tok"}
    rsp = MagicMock(status_code=200)
    rsp.json.side_effect = ValueError("boom")

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=rsp,
    ):
        assert refresh_lan_ip("a", "b", "id") is None


def test_refresh_wifi_not_dict_returns_none() -> None:
    login = MagicMock(status_code=200)
    login.json.return_value = {"access_token": "tok"}

    rsp = MagicMock(status_code=200)
    rsp.json.return_value = {
        "items": [{"device": {"id": "d1", "wifi": [], "local_code": "ABCDEFGHIJKLMNOP"}}]
    }

    with patch(
        "custom_components.robovac_legacy.eufynet.requests.post",
        return_value=login,
    ), patch(
        "custom_components.robovac_legacy.eufynet.requests.get",
        return_value=rsp,
    ):
        assert refresh_lan_ip("a", "b", "d1") is None
