# Datasets and benchmark provenance

## Inventory

| Name | Source / license | Purpose | Retrieval / version | Schema and preprocessing | Split / count | Known issues and leakage |
|---|---|---|---|---|---|---|
| Product benchmark v1 | Project-authored; repository MIT license | Fast compiler/baseline regression | `research/benchmarks/neurocad_benchmark_v1.jsonl`; deterministic seed 20260902 | JSONL `BenchmarkTask`; dimensions already encoded in prompts; compiler normalizes units at evaluation | train 20, validation 12, test 16; 48 rows | 46 unique prompts: one training sphere prompt occurs three times. No exact cross-split duplicate. Templates match compiler grammar. |
| Prompt challenge v1 | Audit-authored after code inspection; MIT | Robust accept/reject challenge | tracked JSONL plus Markdown card/provenance | strict challenge schema; no training | 24 unique cases | Not independent; cannot confirm generalization |
| Compiler stress v1 | `generate_compiler_stress_tasks`; MIT | NC-EXP-001 and kernel selection | generated per run; seed/config/manifests retained | JSONL prompt + exact signature; deterministic unit/template variants | canonical historical run 240, nominal 60/20/20 | Synthetic grammar overlap; historical run source-unbound |
| IR programs | `generate_ir_stress_program`; MIT | NC-EXP-002 invariants | generated per run and hashed | canonical IR JSONL; no learned preprocessing | historical 1,000 | Generated coverage, not natural CAD distribution |
| Invalid fixtures | `_run_invalid_taxonomy`; MIT | NC-EXP-003 fail-closed checks | generated per run and hashed | eight error categories with source digest | historical 240 | Historical FULL repeats eight templates 30 times; effective category boundary is eight. Hardened runner makes records byte-unique but still regression data. |
| Kernel artifacts | OpenSCAD outputs from selected stress tasks; MIT source, generated binary artifacts | NC-EXP-006 | IR/SCAD/STL/PNG/validation per sample | compile then `trimesh`/topology/extents checks | historical FULL 240 | 181 artifacts were reused; producer source not authenticated |
| Calibration observations | User-supplied physical coupon JSON | Printer-specific recommendations | no retained real dataset | strict typed observations and robust estimates | none | Physical validation absent |
| VeriCodeGen S3 candidates/outcomes | Not yet acquired | Learned-method study | protocol only | frozen schema/ledger tooling | zero outcomes | BLOCKED by authorization, provider/model identity, budget, and candidate freeze |

## Deterministic commands

```bash
python -m core.data prepare /tmp/neurocad-benchmark.jsonl --seed 20260902
python -m core.data validate research/benchmarks/neurocad_benchmark_v1.jsonl
python -m core.data inspect research/benchmarks/neurocad_benchmark_v1.jsonl
python -m core.challenge research/benchmarks/neurocad_prompt_challenge_v1.jsonl /tmp/challenge-results.json
```

`prepare` writes the JSONL and a sibling checksum manifest and refuses existing paths unless `--force` is explicit. `validate`/`inspect` are read-only, bounded to 16 MiB/100,000 tasks, reject duplicate JSON keys, unknown fields, invalid splits, duplicate IDs, malformed intervention pairs, and exact cross-split prompt duplicates. They disclose within-split duplicates rather than rewriting frozen data.

## Integrity policy

- Freeze bytes and SHA-256 before outcome access.
- Report row count and unique-prompt count separately.
- Expected semantics must be created from source parameters, not parser output.
- Preprocessing is evaluated as part of the compiler and must not inspect test labels.
- Retrieval baselines may index only train-labelled records.
- Do not infer statistical population coverage from generated variants.
- Do not commit external corpora without license and redistribution review.
- DeepCAD, SketchGraphs, Fusion 360 Gallery, Text2CAD-derived data, and contemporary CAD-code benchmarks require explicit mapping/kernel audits before use; none is currently evaluated.
