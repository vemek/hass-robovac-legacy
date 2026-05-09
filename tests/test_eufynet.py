"""Unit tests for Eufy onboarding parsing (stdlib only — no homeassistant)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PKG = _REPO_ROOT / "custom_components" / "robovac_legacy"


def _load(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "robovac_legacy"
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONST = _load("robovac_legacy.const.testing", _PKG / "const.py")
EUFY = _load("robovac_legacy.eufynet.testing", _PKG / "eufynet.py")

LEGACY_CODES = CONST.SUPPORTED_LEGACY_PRODUCT_CODES


def _device(
    *,
    dev_id: str,
    alias: str,
    product_code: str,
    lan_ip: str,
    code: str,
    mac: str | None = "AA:BB:CC:DD:EE:FF",
) -> dict:
    return {
        "device": {
            "id": dev_id,
            "alias_name": alias,
            "name": "RoboVac 11c",
            "product": {"product_code": product_code},
            "local_code": code,
            "wifi": {"mac": mac or "", "lan_ip_addr": lan_ip},
        }
    }


class LegacyCandidatesTests(unittest.TestCase):
    """``legacy_candidates_from_items`` normalization checks."""

    def test_keeps_supported_t2103(self) -> None:
        items = [
            _device(
                dev_id="a1",
                alias="Kitchen",
                product_code="T2103",
                lan_ip="192.168.1.50",
                code="ABCDEFGHIJKLMNOP",
            )
        ]
        cands = EUFY.legacy_candidates_from_items(items, LEGACY_CODES)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].device_id, "a1")
        self.assertEqual(cands[0].lan_ip, "192.168.1.50")
        self.assertEqual(cands[0].local_code, "ABCDEFGHIJKLMNOP")
        self.assertEqual(cands[0].product_code, "T2103")
        self.assertEqual(cands[0].mac, "AA:BB:CC:DD:EE:FF")

    def test_skips_unsupported_models(self) -> None:
        bad = [
            _device(dev_id="x", alias="Other", product_code="T2276", lan_ip="10.0.0.5", code="ABCDEFGHIJKLMNOP"),
        ]
        self.assertEqual(EUFY.legacy_candidates_from_items(bad, LEGACY_CODES), [])

    def test_requires_valid_local_secret_and_ip(self) -> None:
        missing_code = [_device(dev_id="a", alias="A", product_code="T2103", lan_ip="1.2.3.4", code="")]
        missing_ip = [_device(dev_id="a", alias="A", product_code="T2103", lan_ip="", code="ABCDEFGHIJKLMNOP")]
        short_code = [_device(dev_id="a", alias="A", product_code="T2103", lan_ip="1.2.3.4", code="TOOLONG")]
        self.assertEqual(EUFY.legacy_candidates_from_items(missing_code, LEGACY_CODES), [])
        self.assertEqual(EUFY.legacy_candidates_from_items(missing_ip, LEGACY_CODES), [])
        self.assertEqual(EUFY.legacy_candidates_from_items(short_code, LEGACY_CODES), [])

    def test_skips_broken_shapes(self) -> None:
        datasets = ([{}], [{"foo": True}], [{"device": {"id": "", "wifi": {}, "product": {"product_code": "T2103"}}}])
        for items in datasets:
            with self.subTest(items=items):
                self.assertEqual(EUFY.legacy_candidates_from_items(items, LEGACY_CODES), [])


if __name__ == "__main__":
    unittest.main()
