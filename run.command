#!/bin/sh
set -eu

BASE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MANIFEST="${1:-$BASE_DIR/manifest.demo.json}"
PACKAGE="${2:-$BASE_DIR/demo-pass.zip}"
OUTPUT="${3:-$BASE_DIR/evidence-run}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：找不到 python3。"
  exit 2
fi

exec python3 "$BASE_DIR/handoff_seal.py" \
  --manifest "$MANIFEST" \
  --package "$PACKAGE" \
  --output "$OUTPUT"
