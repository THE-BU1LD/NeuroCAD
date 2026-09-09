# Reproducibility entry point

```bash
PYTHON_BIN=python3.12 scripts/preflight.sh
PYTHON_BIN=python3.12 scripts/test.sh
PYTHON_BIN=python3.12 scripts/run_smoke.sh
python3.12 -m core.challenge \
  research/benchmarks/neurocad_prompt_challenge_v1.jsonl \
  /tmp/neurocad-challenge.json
```

Full fresh, non-resuming, kernel-backed suite:

```bash
PYTHON_BIN=python3.12 scripts/reproduce_research.sh
```

CPython must be exactly 3.12.14 for the archival protocol. OpenSCAD is required.
Detailed lock, provenance, headless-rendering, packaging, and release requirements
are in `../REPRODUCIBILITY.md`.
