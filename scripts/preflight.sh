#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
"$PYTHON_BIN" -c 'import platform; assert platform.python_version() == "3.12.14", platform.python_version()'
command -v openscad >/dev/null
"$PYTHON_BIN" -m compileall -q neurocad_cli.py text_to_cad.py text_to_openscad.py core research/vericodegen
"$PYTHON_BIN" -c 'import jsonschema, numpy, trimesh; import core; import neurocad_cli'
PREFLIGHT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/neurocad-preflight.XXXXXX")
cleanup() {
    rm -rf -- "$PREFLIGHT_DIR"
}
trap cleanup EXIT INT TERM
"$PYTHON_BIN" -m neurocad_cli create 'a 10 x 10 x 1 mm plate' -o "$PREFLIGHT_DIR/preflight.scad"
"$PYTHON_BIN" -c 'import sys; from pathlib import Path; from core.artifacts import render_scad_png; render_scad_png(Path(sys.argv[1]), Path(sys.argv[2]), width=64, height=64)' "$PREFLIGHT_DIR/preflight.scad" "$PREFLIGHT_DIR/preflight.png"
test -s "$PREFLIGHT_DIR/preflight.png"
printf '%s\n' 'preflight passed'
