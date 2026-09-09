#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
"$PYTHON_BIN" -m pytest -q tests
"$PYTHON_BIN" -m ruff check core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py tests
"$PYTHON_BIN" -m mypy core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py
"$PYTHON_BIN" -m pip check
