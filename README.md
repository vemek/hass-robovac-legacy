# Eufy RoboVac (legacy) — Home Assistant

Custom integration for **Eufy RoboVac 11C** cleaners (`T2103`) that expose a **LAN `local_code`** and are controlled locally via **[PyRobovac](https://pypi.org/project/robovac/)**.

## Requirements

- Home Assistant **2025.1** or newer recommended (see `hacs.json`)
- **`robovac==0.0.9`** (installed automatically from `manifest.json`)
- Supported cloud onboarding only lists models that advertise **legacy LAN secrets** compatible with PyRobovac

## Install with HACS

1. Remove any previous manual copy under `custom_components/robovac_legacy` if upgrading.
2. In HACS: **⋮ → Custom repositories** → URL `https://github.com/vemek/hass-robovac-legacy`, category **Integration**.
3. Open the repo in HACS, download & restart Home Assistant.
4. Settings → Devices & Services → Add integration → **Eufy RoboVac (legacy)**.

## Manual install

Copy `custom_components/robovac_legacy` into your `/config/custom_components/` tree and restart HA.

