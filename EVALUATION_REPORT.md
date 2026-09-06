# NeuroCAD evaluation report

**Evaluation date:** 2026-09-03  
**Primary frozen run:** `NC-RUN-2026-09-03-FULL`  
**Expanded kernel run:** `NC-RUN-2026-09-03-FULL` complete

## Measured results

| Experiment | Measured result |
| --- | ---: |
| Controlled compiler semantic exactness | NeuroCAD 240/240; nearest-neighbor retrieval 144/240; raw-number baseline 110/240; fixed box 0/240 |
| Canonical IR generation/validation/round trip | 1,000/1,000 |
| Predeclared malformed-input rejection | 240/240 |
| Constraint corruption detection | 200/200 with constraints; 0/200 after constraint removal |
| Automated editable-program modifications | 200/200 |
| Complete real OpenSCAD/STL execution | 240/240; Wilson 95% interval 98.42–100% |
| Hierarchy bound | depth 128 accepted; depth 129 rejected |

The controlled compiler dataset SHA-256 is `9c6b70937a4ea08ef5f06796c37809854768d71ccda919f66de447e5951d720a`. The 1,000-program JSONL SHA-256 is `9ddcb2434dddb1a28005f353a08c50d9d43271f25b5b3a91b3f9af0303829db8`.

## Strongest checks

The expanded kernel evaluator does not equate “OpenSCAD returned zero” with valid geometry. Each STL must contain only finite vertices, have positive three-axis extent and volume, be watertight, have consistent winding, form exactly one connected body, and match the canonical program's expected axis extents within `max(0.2 mm, 1%)` on each axis. Any failed sample makes `--require-kernel` exit nonzero and prevents a final run manifest. The completed run retains 240 validation files, 240 STL files, 240 PNG renders, and 1,210 artifact hashes; 181 interrupted-run artifacts were revalidated against exact task/current IR/current SCAD bytes and 59 were freshly compiled in the completing pass.

## Strongest observed failures and negative evidence

- A prior historical typed-parser mechanism claim is falsified; current compiler results do not rehabilitate it.
- An unscoped historical test collection has 14 import/collection/runtime failures caused by missing research dependencies and mutually incompatible legacy APIs.
- A historical legacy “STEP” exporter wrote marker text, not STEP data; the direct legacy method is now hard-disabled and covered by integrity tests.
- Stage 1 VeriCodeGen cells were scripted fixtures with no model calls.
- The current S3 request has no discoverable candidate pool or authorization manifest, so learned outcomes have not been accessed.
- External reproducibility is unproven because this checkout has no Git metadata or external CI/public-release receipts.

## Interpretation boundary

The results support a deterministic compiler over a generated, declared grammar. They do not demonstrate open-world language understanding, a learned representation, BREP reconstruction, manufacturing fitness, safety, or superiority to general text-to-CAD systems. The perfect system score is expected for a compiler tested on its explicitly generated contract and must not be marketed as general intelligence.
