# Eufy RoboVac (legacy) — Home Assistant

Custom integration for **Eufy RoboVac 11C** cleaners (`T2103`) that expose a **LAN `local_code`**.
Local control previously relied on archived **[PyRobovac](https://pypi.org/project/robovac/)**; those bits are now vendor-copied under `custom_components/robovac_legacy/lan/` with protobuf stubs regenerated for modern Home Assistant stacks.

## Requirements

- Home Assistant **2025.1** or newer recommended (see `hacs.json`)
- **`pycryptodome>=3.6.6`** from `manifest.json` (AES-CBC LAN framing).
- **`google.protobuf`** is supplied by Home Assistant Core (`LocalServerMessage` stubs ship with this repo).
- Cloud onboarding lists models advertising **sixteen-character LAN secrets** for the protobuf protocol.

### Maintainer notes: protobuf stubs

Protocol sources live under `custom_components/robovac_legacy/lan/proto/LocalServerInfo.proto`.
Committed `LocalServerMessage` Python bindings were generated via `bash scripts/regen_proto.sh`
(`protoc` **27.x**, matching `.github/workflows/ci.yml`). After editing the `.proto` file regenerate
both `LocalServerInfo_pb2.{py,pyi}` before pushing so CI drift checks succeed.

See `NOTICE` for Apache-2.0 / archived PyRobovac lineage.

## Install with HACS

1. Remove any previous manual copy under `custom_components/robovac_legacy` if upgrading.
2. In HACS: **⋮ → Custom repositories** → URL `https://github.com/vemek/hass-robovac-legacy`, category **Integration**.
3. Open the repo in HACS, download & restart Home Assistant.
4. Settings → Devices & Services → Add integration → **Eufy RoboVac (legacy)**.

## Manual install

Copy `custom_components/robovac_legacy` into your `/config/custom_components/` tree and restart HA.

