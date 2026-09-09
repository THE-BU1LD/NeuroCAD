# Repository map

**Audit date:** 2026-09-08
**Supported object:** `neurocad-research` 0.5.0a6

## Purpose and actual contribution

NeuroCAD is a deterministic compiler, not a trained ML model. It recognizes a
small declared English language for fully dimensioned plates, boxes, open-top
enclosures, cylinders, spheres, holes, and slots; lowers that intent to a typed
millimetre IR; validates it; and emits deterministic OpenSCAD. Optional OpenSCAD
execution produces STL that is checked independently with `trimesh`.

The defensible contribution is an engineering case study in bounded,
fail-closed, evidence-traceable text-to-parametric-program compilation. It is not
a novel CAD representation, general language understanding, BREP reconstruction,
learned generation, manufacturability proof, or safety certification.

## End-to-end map

`prompt -> core/prompt_engine.py -> core/design_graph.py -> core/ir_adapter.py ->
core/ir.py + schema -> core/ir_export.py -> OpenSCAD -> core/artifacts.py -> STL`

- Product entry points: `neurocad_cli.py`, `text_to_cad.py`, `core/demo_server.py`.
- Typed enclosure path: `core/natural_language.py`, `core/enclosure.py`,
  `core/project.py`, `core/workflow.py`, `core/enclosure_verification.py`.
- Data: deterministic generators in `core/benchmark.py` and
  `core/research_suite.py`; frozen JSONL under `research/runs/`.
- Baselines: fixed box, literal-number extraction, and train-only nearest-neighbor
  retrieval in `core/benchmark.py`.
- Evaluation/statistics: `core/research_suite.py`; raw per-task records and exact
  paired McNemar summaries in retained run metrics.
- Evidence production: `scripts/reproduce_research.sh` creates a fresh environment
  and output directory and runs tests, static checks, kernel execution, figures,
  packaging, and provenance checks.
- Paper production: `paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md` is hand-authored
  against `audits/CLAIM_LEDGER.md`; no automated PDF build exists.
- Tests: `tests/` covers parsing, IR, failures, kernel artifacts, enclosure
  features, CLI, integrations, statistics, provenance, packaging, and the demo.

## Evidence and experiment paths

- `research/runs/NC-RUN-2026-09-03-FULL/`: immutable historical development
  evidence. It reports 240 compiler tasks and 240 kernel records, but lacks source
  provenance and reused 181 pre-existing verified kernel artifacts.
- Future `NC-REPRO-*` directories: source-bound fresh runs made by the hardened
  reproduction script. None is promoted as frozen confirmatory evidence here.
- `research/vericodegen/`: frozen infrastructure only; no authorized model outcome
  run exists. `research/s3/PRE_OUTCOME_STATUS.json` is explicitly pre-outcome.
- `legacy/`: 225 MB forensic archive of mutually incompatible historical code and
  negative evidence. It is excluded from the supported package.

## Incomplete and obsolete surfaces

- No trained model/checkpoint, optimizer, training loop, or learned ablation exists.
- No external/public benchmark or representative human-prompt corpus was run.
- No physical fit, fabrication, safety, or native external-CAD import was verified.
- VeriCodeGen outcome execution requires authorization, provider identity, budget,
  and frozen manifest: `EXTERNAL_EXECUTION_REQUIRED`.
- Public tag, external CI receipt, anonymous install, and independent replication
  are absent: `EXTERNAL_EXECUTION_REQUIRED`.
- Root compatibility modules and `legacy/` are not canonical research paths.

## Critical dependencies

- CPython 3.12.14 and hashes in `requirements-research.lock` for archival runs.
- `jsonschema`, `numpy`, and `trimesh`; pinned quality/security tools for release.
- OpenSCAD 2021.01-compatible CLI for kernel-backed evidence and rendering.

## Claim chain

`QUESTION.md -> research/protocols/ -> core/research_suite.py -> run config + raw
records -> metrics/results.json -> audits/CLAIM_LEDGER.md -> manuscript`

Any claim that cannot traverse that chain is unsupported. Current source tests do
not retroactively authenticate the historical FULL run.
