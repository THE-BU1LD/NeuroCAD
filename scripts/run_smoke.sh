#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
SMOKE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/neurocad-smoke.XXXXXX")
trap 'rm -rf -- "$SMOKE_DIR"' EXIT INT TERM
"$PYTHON_BIN" -m neurocad_cli ir 'a 120 x 80 x 4 mm plate with four 4 mm holes' -o "$SMOKE_DIR/plate.json"
"$PYTHON_BIN" -m neurocad_cli compile "$SMOKE_DIR/plate.json" --format scad -o "$SMOKE_DIR/plate.scad"
"$PYTHON_BIN" -m neurocad_cli compile "$SMOKE_DIR/plate.json" --format stl -o "$SMOKE_DIR/plate.stl"
"$PYTHON_BIN" -m neurocad_cli evaluate --ir "$SMOKE_DIR/plate.json"
test -s "$SMOKE_DIR/plate.scad"
test -s "$SMOKE_DIR/plate.stl"
printf '%s\n' 'smoke passed'
