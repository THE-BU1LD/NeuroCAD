# NeuroCAD project truth

**Audit date:** 2026-09-06  
**Scope:** this NeuroCAD checkout only  
**Declared source version:** 0.5.0a6; transformed release verification pending

## Evidence scale

- **L0 — assertion:** prose or a filename only.
- **L1 — inspection:** implementation exists and was read, but was not executed.
- **L2 — local test:** an automated test or deterministic local check passed.
- **L3 — end-to-end:** the real parser, IR, exporter, external CAD kernel, and verifier ran together.
- **L4 — independently reproducible:** exact Git revision, public artifact, external CI, and independent rerun are recorded.

## Product-by-product status

| Project surface | Actual current state | Evidence | Level | Blocking fact / next gate |
| --- | --- | --- | ---: | --- |
| Maintained NeuroCAD compiler | A bounded deterministic compiler for dimensioned plates, boxes, open-top enclosures, cylinders, spheres, holes, and slots. It accepts a declared English subset or canonical JSON IR and emits validated IR/OpenSCAD, with optional STL. | `core/`, `neurocad_cli.py`, maintained tests, `NC-RUN-2026-09-03-FULL` | L3 | It is not an open-world language or general CAD system. |
| Electronics-enclosure workflow | Typed body/lid specifications, validated face features, PCB envelopes, standoffs, semantic revisions, disclosed manufacturing heuristics, calibration profiles, independently reverified source/mesh bundles, and request-level STL probes run end to end. | `core/enclosure.py`, `core/project.py`, `core/workflow.py`, `core/manufacturing.py`, `core/calibration.py`, maintained tests | L3 local | Physical fit and manufacturing suitability still require measured hardware, coupons, and human review. |
| Application interoperability | Canonical v2 bundles can be independently reverified. OpenSCAD compiles native SCAD. KiCad has a source-reverified parser for a bounded rectangular board subset and hash-bound IPC/CLI receipts for the rest; other named applications receive verified file handoffs only. | `core/integrations/`, CLI integration tests, installed-wheel smoke | L3 local | No target GUI was launched and no native Fusion/Onshape/FreeCAD/Blender/slicer document was created. KiCad connector inventory and component height remain reviewed inputs. |
| Canonical IR | `neurocad-ir-v1` supports typed primitives, transforms, references, hierarchy, Boolean composition, constraints, validation, deterministic serialization, and exact round trips. | Schema, parser, semantic validator, exporter, IR tests, 1,000-program stress | L3 | No sketch solver, BREP topology, or assembly semantics. |
| Geometry/kernel path | OpenSCAD compiles the canonical program to STL; verification checks finite vertices, positive extents/volume, watertightness, winding, single-body connectivity, and agreement with expected program extents. | `core/artifacts.py`, kernel tests, `NC-RUN-2026-09-03-FULL` | L3, 240/240 | It is CSG/STL evidence, not exact BREP or manufacturing proof. |
| Controlled compiler research | Frozen deterministic experiments cover 240 prompts, four systems, 1,000 IR programs, 240 malformed-fixture records, 200 constraint corruptions, 200 edits, hierarchy bounds, and 240 kernel executions. The malformed records are eight templates repeated 30 times. | `research/runs/NC-RUN-2026-09-03-FULL/manifest.json` | L3 | Evidence applies only to this synthetic controlled grammar; the historical malformed-input result has no valid 240-sample interval. |
| Local workbench/demo | The browser workbench calls the real parser, validator, IR, evaluator, and OpenSCAD exporter. | Demo integration tests and `neurocad demo` | L2 | Local and unauthenticated by design; not a hosted multi-user product. |
| VeriCodeGen methodology | Safe capture/evaluation, frozen schemas/prompts/analysis, retry retention, and preflight machinery exist. Stage 1 was scripted plumbing only. | `research/vericodegen/`, tests, 2026-09-03 preflight receipt | L2 | No candidate pool, deterministic S3 pilot selection, authorized manifest, provider/model identity, budget authorization, or model outcomes exist. S3 is blocked before outcome access. |
| Legacy root research archive | Multiple mutually incompatible historical experiments and kernels are retained for negative evidence. They are excluded from the package. | `audits/HISTORICAL_TRUTH.md`, packaging metadata, integrity tests | L1 | Not a supported product. Repairing each abandoned experiment would create several new research projects, not finish the maintained compiler. |
| STEP/BREP claim | Refuted. A historical legacy method wrote marker text instead of STEP; it is now hard-disabled and no STEP/BREP kernel exists. | `legacy/python/cad_intelligence_core_allinone.py`, truth ledgers, integrity tests | L2 negative evidence | Requires a real BREP kernel and a separately defined/export-verified product scope. |
| Learned-model claim | No trained model exists in the supported system. The historical typed-parser causal claim remains falsified. | `MODEL_CARD.md`, `model/README.md`, historical ledger | L1 negative evidence | A learned result requires a new frozen, authorized multi-seed study. |
| Packaging/release | Source declares a6 and local wheel/sdist candidates build and install. A new local audit-baseline repository now identifies the transformed tree; it is not recovered history. The retained `dist/` snapshot still ends at a5; CI/tag workflows generate authoritative artifacts and provenance into fresh directories. | `pyproject.toml`, local build/install smoke, `.github/workflows/`, public ledger | L2 local | No external CI run, tag, generated release receipt, or anonymous public-install receipt is present. |

## Intended release contract

The supported end-to-end contract is:

`bounded prompt or neurocad-ir-v1 JSON → parse → semantic validation → canonical IR → deterministic OpenSCAD → optional OpenSCAD STL → mesh verification → metrics/manifest`

This is the contract that the transformed candidate must prove on a clean exact
revision. Historical run artifacts predate the current source and do not by
themselves establish that the current candidate satisfies it.

## Claims that remain unsupported

NeuroCAD does not currently establish general text-to-CAD reasoning, sketch/image input, real STEP/BREP reconstruction, arbitrary topology equivalence, numerical constraint solving, design-intent inference, manufacturability, safety, simulation, human usability, state-of-the-art model performance, external replication, or public release provenance.

## Provenance limitation

The 2026-09-06 audit initialized a new local Git repository solely to establish
an exact baseline for the transformed tree. It does not recover branch, tag,
ancestry, or historical commits that were absent from the delivered directory.
Any L4 release or scientific result remains blocked until that exact baseline
is pushed to a real remote and passes external CI.
