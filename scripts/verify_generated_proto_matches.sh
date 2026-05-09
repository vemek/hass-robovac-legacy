#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/regen_proto.sh"
exec git diff --exit-code \
  "$ROOT/custom_components/robovac_legacy/lan/LocalServerInfo_pb2.py" \
  "$ROOT/custom_components/robovac_legacy/lan/LocalServerInfo_pb2.pyi"
