#!/usr/bin/env bash
# Verify custom_components/.../manifest.json "version" matches ref (semver X.Y.Z).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/custom_components/robovac_legacy/manifest.json"

ref="${1-}"
if [[ -z "${ref}" ]]; then
  ref="${GITHUB_REF_NAME:-}"
fi
if [[ -z "${ref}" ]]; then
  ref="${TAG:-}"
fi

if [[ -z "${ref}" ]]; then
  echo "Usage: $0 [<version_or_tag>]  (or set GITHUB_REF_NAME or TAG)" >&2
  exit 2
fi

if [[ "${ref}" == refs/tags/* ]]; then
  ref="${ref#refs/tags/}"
fi
if [[ "${ref}" == v* ]]; then
  ref="${ref#v}"
fi

if ! [[ "${ref}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "error: expected semver MAJOR.MINOR.PATCH (digits only): got ${ref}" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required on PATH" >&2
  exit 2
fi

if [[ ! -f "${MANIFEST}" ]]; then
  echo "error: manifest not found: ${MANIFEST}" >&2
  exit 2
fi

if ! jq -e '.version | type == "string"' "${MANIFEST}" >/dev/null; then
  echo "error: manifest 'version' must be a JSON string" >&2
  exit 2
fi

mver="$(jq -r '.version' "${MANIFEST}")"

if [[ "${mver}" != "${ref}" ]]; then
  echo "error: version mismatch:" >&2
  echo "  tag normalizes to: ${ref}" >&2
  echo "  manifest.json:     ${mver}" >&2
  exit 1
fi
