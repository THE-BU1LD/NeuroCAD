# NeuroCAD historical truth ledger

**Frozen:** 2026-09-02  
**Scope:** this checkout only. A new Git baseline was initialized during the
2026-09-06 audit, but prior branch, tag, and commit-history claims remain
locally unverifiable.

| ID | Historical or current claim | Status | Evidence and boundary |
|---|---|---|---|
| HT-01 | A historical typed parser caused better model/CAD behavior. | **REFUTED** | The repository's VeriCodeGen protocol and Stage 1 receipt preserve this as falsified. The repaired 2026 compiler is a different implementation and cannot retroactively change that result. |
| HT-02 | VeriCodeGen Stage 1 established a model effect. | **REFUTED** | `research/vericodegen/STAGE1_RECEIPT.md` says the six cells were scripted fixtures and made no model calls. |
| HT-03 | VeriCodeGen Stage 2/3 produced scientific results. | **UNSUPPORTED** | The checked-in example manifest is `authorized=false`; no frozen model run, checkpoint, or Stage 3 result is present. |
| HT-04 | Historical root kernels form one working CAD product. | **REFUTED** | Unscoped collection produced 14 import/collection failures; interfaces conflict and many scripts execute at import time. |
| HT-05 | The repository exports real STEP/BREP. | **REFUTED** | The historical `legacy/python/cad_intelligence_core_allinone.py` path wrote marker text rather than STEP. v0.5.0a5 hard-disables that method with an explicit error; no STEP/BREP kernel exists. |
| HT-06 | Historical generated meshes prove correct CAD generation. | **UNSUPPORTED** | Outputs lack a complete source/config/kernel/verifier chain. Presence on disk is not correctness evidence. |
| HT-07 | The maintained system parses a bounded dimensioned-English grammar into editable CAD programs. | **SUPPORTED** | `core/prompt_engine.py`, `core/ir_adapter.py`, canonical IR, maintained tests, and NC-EXP-001. Limited to the declared grammar. |
| HT-08 | Canonical IR has schema, semantic validation, explicit references, constraints, deterministic serialization, and executable OpenSCAD. | **SUPPORTED** | `core/schemas/neurocad_ir_v1.schema.json`, `core/ir.py`, `core/ir_parser.py`, `core/ir_export.py`, and NC-EXP-002/003. |
| HT-09 | All syntactically valid programs are geometrically valid solids. | **UNSUPPORTED** | Static validation cannot establish kernel execution or manifoldness. NC-EXP-006 separately compiles a predeclared sample with OpenSCAD and verifies STL topology. |
| HT-10 | NeuroCAD is a general natural-language-to-CAD system. | **REFUTED** | The implementation intentionally fails closed outside plates, boxes, open-top enclosures, cylinders, spheres, holes, and slots. |
| HT-11 | NeuroCAD contains a trained or novel learned model. | **REFUTED** | The supported 2026 system is deterministic. No model checkpoint is produced; `MODEL_CARD.md` records this explicitly. |
| HT-12 | NeuroCAD infers design intent or solves arbitrary constraints. | **UNSUPPORTED** | It validates declared constraints; it does not infer intent or numerically solve sketches. |
| HT-13 | The maintained pipeline can compile real solids. | **PARTIALLY SUPPORTED** | OpenSCAD-backed execution is tested on a stratified sample, not every possible IR program or commercial kernel. |
| HT-14 | The maintained pipeline is fabrication- or safety-ready. | **REFUTED** | It provides no tolerancing, materials, loads, process constraints, certification, or human review workflow. |

## Negative evidence retention rule

### Current implementation note — 2026-09-08

This ledger preserves the frozen historical findings. Current supported code now
includes limited tolerance calculations, declared manufacturing profiles, and
measurement-based calibration helpers in `core/engineering_math.py`,
`core/manufacturing.py`, and `core/calibration.py`. HT-14's statement about the
absence of those aids describes the historical state; its rejection of general
fabrication/safety readiness still holds. These additions do not supply physical
fit evidence, simulation, arbitrary constraint solving, or a learned model.

New experiments use `NC-EXP-*` IDs and the expanded run ID `NC-RUN-2026-09-03-FULL`. They are evidence about the maintained controlled compiler only. Historical failures, stale modules, and the falsified typed-parser mechanism claim are not overwritten, renamed as successes, or included in current test totals.
