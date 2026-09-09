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
openscad -o "$PREFLIGHT_DIR/preflight.png" --imgsize=64,64 --viewall --autocenter "$PREFLIGHT_DIR/preflight.scad" >/dev/null 2>&1
test -s "$PREFLIGHT_DIR/preflight.png"
printf '%s\n' 'preflight passed'
