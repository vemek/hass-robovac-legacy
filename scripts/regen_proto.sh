#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAN_DIR="$ROOT/custom_components/robovac_legacy/lan"
PROTO_FILE="$LAN_DIR/proto/LocalServerInfo.proto"
PROTO_SRC_DIR="$LAN_DIR/proto"

PROTOC_BIN="${PROTOC:-$(command -v protoc || true)}"
if [[ -z "$PROTOC_BIN" ]]; then
  printf '%s\n' "protoc required (PROTOC=/path/to/protoc). Install protobuf compiler >= 26.x;" \
    'CI uses arduino/setup-protoc; linux devs commonly pull from https://protobuf.dev/downloads/.' >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

"$PROTOC_BIN" --proto_path="$PROTO_SRC_DIR" --python_out="$tmpdir" --pyi_out="$tmpdir" "$PROTO_FILE"

mv -f "$tmpdir/LocalServerInfo_pb2.py" "$LAN_DIR/LocalServerInfo_pb2.py"
mv -f "$tmpdir/LocalServerInfo_pb2.pyi" "$LAN_DIR/LocalServerInfo_pb2.pyi"
printf '%s\n' "Regenerated $LAN_DIR/LocalServerInfo_pb2.{py,pyi} with $($PROTOC_BIN --version)"
