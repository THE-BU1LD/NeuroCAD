#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3.12}
test -s tests/test_workbench_ui.py
test -s tests/workbench_contract.cjs
node --version
"$PYTHON_BIN" -m pytest -q tests
"$PYTHON_BIN" -m ruff check core research/vericodegen scripts neurocad_cli.py text_to_cad.py text_to_openscad.py surfaces.py vector_fields_engine.py pipeline_stage.py exceptions.py thinking_engine.py tests
"$PYTHON_BIN" -m mypy core research/vericodegen scripts neurocad_cli.py text_to_cad.py text_to_openscad.py surfaces.py vector_fields_engine.py pipeline_stage.py exceptions.py thinking_engine.py
"$PYTHON_BIN" -m pip check
