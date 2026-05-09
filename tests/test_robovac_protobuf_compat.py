"""Robovac 0.0.9 ships proto stubs compiled for protobuf 3.x; HA often ships protobuf 6+."""

from __future__ import annotations

import json
import re
from pathlib import Path

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "custom_components/robovac_legacy" / "manifest.json"


def _manifest_reqs() -> list[str]:
    data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    reqs = data.get("requirements", [])
    return [str(r).strip() for r in reqs]


def test_manifest_pins_protobuf_for_robovac_stubs():
    """The PyRobovac wheels pin old ``_pb2`` code; protobuf 4+ rejects them.

    Symptoms on Home Assistant match:
    ``TypeError: Descriptors cannot be created directly``

    Regression coverage for:
    invalid handler / config_flow import cascading from ``robovac`` imports.
    """
    reqs = _manifest_reqs()
    reqs_lower = ",".join(r.lower() for r in reqs)
    assert "protobuf" in reqs_lower, "manifest must constrain protobuf alongside robovac"

    protobuf_lines = [
        r
        for r in reqs
        if re.match(r"^\s*protobuf\s*", r, flags=re.I)
    ]
    assert protobuf_lines, (
        "Add an explicit protobuf requirement "
        '(e.g. ``"protobuf>=3.19,<4"``) before ``robovac`` in manifest.json'
    )

    condensed = "".join(protobuf_lines).replace(" ", "")
    assert re.search(r"<\s*4(?:\D|$)|<=\s*3\.", condensed, re.I), (
        f"Protobuf must be capped below 4 for robovac 0.0.9, got lines: {protobuf_lines!r}"
    )


def test_pyrobovac_import_does_not_hit_descriptor_crash():
    """Fails with the HA loader error text when protobuf is newer than robovac’s bundled protos."""
    try:
        from robovac import Robovac  # noqa: PLC0415

        assert callable(Robovac)
    except TypeError as err:
        if "Descriptors cannot be created directly" in str(err):
            raise AssertionError(
                "Robovac import hit protobuf descriptor guard (PyRobovac vs protobuf>=4).\n"
                "Home Assistant merges ``manifest.json`` pip constraints — ensure "
                "``protobuf>=3.19,<4`` (or equivalent) sits next to robovac in requirements."
            ) from err
        raise
