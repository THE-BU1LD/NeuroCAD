PYTHON ?= python3.12

.PHONY: setup configure test lint typecheck validate-data smoke benchmark reproduce

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install -e '.[dev,security]'

configure:
	$(PYTHON) -m neurocad_cli setup

test:
	$(PYTHON) -m pytest -q tests

lint:
	$(PYTHON) -m ruff check core research/vericodegen scripts neurocad_cli.py text_to_cad.py text_to_openscad.py tests

typecheck:
	$(PYTHON) -m mypy core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py

validate-data:
	$(PYTHON) -m core.data validate research/benchmarks/neurocad_benchmark_v1.jsonl

smoke:
	PYTHON_BIN=$(PYTHON) scripts/run_smoke.sh

benchmark:
	$(PYTHON) -m neurocad_cli benchmark --dataset research/benchmarks/neurocad_benchmark_v1.jsonl --output research/results/neurocad_benchmark_v1.json --force

reproduce:
	PYTHON_BIN=$(PYTHON) scripts/reproduce_research.sh
