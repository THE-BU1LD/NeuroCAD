# NeuroCAD experiments

## E1 — canonical IR round trip

**Question:** Does a valid program survive deterministic JSON serialization and parsing without semantic drift?  
**Method:** Serialize typed programs, parse through Draft 2020-12 JSON Schema and semantic validation, compare complete dictionaries, serialize again.  
**Result:** Passing in the maintained suite, including composed geometry and natural-language-derived programs.  
**Boundary:** JSON identity is not BREP or mesh equivalence.

## E2 — malformed and adversarial structure

**Question:** Does the IR fail closed?  
**Cases:** malformed JSON, non-object roots, missing schema fields, unknown fields, missing references, duplicate parents, cycles, invalid transforms, invalid primitive parameters, and unsatisfied constraints.  
**Result:** Rejected with path-addressed errors. Recursive bounds evaluation is blocked for invalid hierarchies.

## E3 — deterministic engineering benchmark

**Artifact:** `research/benchmarks/neurocad_benchmark_v1.jsonl`  
**SHA-256:** `0822e45a56e4cc2d405da50561899f8310e9bffb4a4a833e98affe27672e4546`  
**Seed:** `20260902`  
**Tasks:** 48

| System | Train | Validation | Test | Overall |
|---|---:|---:|---:|---:|
| NeuroCAD | 20/20 | 12/12 | 16/16 | 48/48 |
| Raw-number ablation | 12/20 | 4/12 | 2/16 | 18/48 |
| Fixed box | 0/20 | 0/12 | 0/16 | 0/48 |

The raw-number ablation removes unit normalization and structured feature parsing. Its failure on centimetre/inch perturbations is the intended sanity check. Result details, per-task failures, and local latency are in `research/results/neurocad_benchmark_v1.json`.

## E4 — counterfactual intervention

Four pairs change one requested attribute: hole count, hole diameter, plate width, or slot count. NeuroCAD changed exactly the expected signature field in all 4 pairs. The raw-number ablation did so in 1/4; the fixed box did so in 0/4.

This checks local consistency inside the documented grammar. It is not causal evidence about a learned representation.

## E5 — maintained product suite

The maintained gate is the version-controlled test, lint, type, dependency, and
security command set in `REPRODUCIBILITY.md` and CI. No fixed test total is a
current project claim: the inventory changes whenever focused regressions are
added. A release receipt is valid only for the exact revision on which all gates
completed successfully.

## E6 — historical root-script audit

Unscoped collection of historical root-level test scripts produced 14 errors before tests could run. Observed classes were missing optional dependencies, missing symbols, incompatible kernel interfaces, import-time execution, and stale attributes. This is a retained negative result. `pyproject.toml` now declares `tests/` as the maintained product test boundary; it does not assert that historical experiments work.

## E7 — compiled mesh path

The maintained suite verifies watertight STL analysis using a known `trimesh` box fixture. A fresh local OpenSCAD 2021.01 run also compiled a 20×10×3 mm plate and the representative 120×80×4 mm plate with four 4 mm holes. The feature mesh was watertight with exact 120×80×4 mm extents, 776 vertices, 1,564 faces, and approximately 38,199.08 mm³ volume. This verifies the declared Boolean export path; it is not evidence for arbitrary topology.

## Interpretation

The experiments show deterministic engineering correctness for the declared subset. They do not establish scientific novelty, arbitrary CAD generalization, learned reasoning, or fabrication safety.

## E8 — NC-EXP-001 controlled compiler matrix

On 240 frozen tasks, NeuroCAD scored 240/240, nearest-neighbor retrieval 144/240, raw-number parsing 110/240, and fixed output 0/240. All paired discordances favored NeuroCAD. The set is generated from the declared grammar and is not a natural-language sample.

## E9 — NC-EXP-002 typed IR stress

All 1,000 generated programs passed schema and semantic validation, declared constraints, exact JSON round trip, and deterministic OpenSCAD export. Wilson 95% interval: 99.62–100%.

## E10 — NC-EXP-003 malformed-input taxonomy

All 240 cases were rejected, 30/30 in each of eight categories. Wilson 95% interval: 98.42–100%. Raw error messages remain frozen.

## E11 — NC-EXP-004 constraint ablation

Declared dimension constraints detected 200/200 injected one-millimetre drifts; identical unconstrained programs detected 0/200. This is parameter-drift detection, not design-intent inference.

## E12 — NC-EXP-005 automated editability

All 200 named-parameter edits survived validation, serialization, reparsing, and export. No human usability claim is made.

## E13 — NC-EXP-006 kernel execution and renders

The expanded complete benchmark run compiled 240/240 programs through OpenSCAD. Every STL passed finite-vertex, positive-volume, watertightness, winding, single-body, and expected-extents checks (Wilson 95% interval: 98.42–100%). Canonical IR, SCAD, STL, validation, hashes, and actual OpenSCAD PNG renders are retained under `NC-RUN-2026-09-03-FULL`.

## E14 — NC-EXP-007 hierarchy stress

Constructed programs exported through depth 128; depth 129 failed closed with `hierarchy_too_deep`. No recursive crash or silent truncation occurred.
