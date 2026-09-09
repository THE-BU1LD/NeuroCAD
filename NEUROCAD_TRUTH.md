# NeuroCAD truth map

**Audit date:** 2026-09-06  
**Scope:** NeuroCAD only. ColorWorld and all organization/membership products were explicitly excluded.

## Executive truth

NeuroCAD is now a working, narrow CAD program compiler: a documented subset of dimensioned English prompts is parsed into a typed, versioned JSON intermediate representation (IR), semantically validated, deterministically serialized, rendered as OpenSCAD, and optionally compiled to STL through an external OpenSCAD installation. It is not a general text-to-CAD model, a BREP kernel, a constraint solver, or an engineering simulator.

The disconnected historical Python experiments and root-generated CAD outputs
have been moved into `legacy/`. Packaging deliberately includes the maintained
`core` package and three CLI modules, not that archive.

The historical claim that a NeuroCAD typed parser caused improved model behavior remains **falsified**. Better parser/compiler engineering does not revive it. The successor VeriCodeGen protocol has an offline Stage 1 plumbing receipt only; no authorized Stage 2 model run or Stage 3 scientific result exists in this checkout.

## Evidence recovered

- A new local Git repository was initialized during the 2026-09-06 audit to identify the transformed baseline. It cannot recover the missing prior branch, tags, ancestry, or complete commit history.
- Historical receipts name Stage 1 merged commit `6e04ecf6d2f8633da2f19dcff251239307520d00`; that is receipt evidence, not a locally verified Git fact.
- `research/vericodegen/STAGE1_RECEIPT.md` records three scripted fixtures and six final cells. It explicitly says there were no language-model calls and no scientific treatment evidence.
- `research/VERICODEGEN_2026_PROTOCOL.md` and related methodology files explicitly preserve the falsified historical claim and block Stage 2 without a frozen, authorized manifest.
- `docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md` keeps exact-tag, public installer, and external release evidence pending.
- Large `.scad`, `.stl`, and `.obj` outputs show prior generation activity but do not establish correctness, provenance, or research claims by themselves.

## Supported system contract

### Input

1. A supported, fully dimensioned engineering prompt, limited to 4096 characters; or
2. Canonical `neurocad-ir-v1` JSON, limited to 1 MiB when compiled by the CLI.

Supported prompt families are plates, rectangular boxes, open-top rectangular enclosures, cylinders, and spheres. Plates may have explicitly dimensioned circular holes or rectangular slots. Units are mm, cm, m, and inches and are normalized to millimetres.

### Representation

The canonical IR contains:

- typed primitives: box, rounded box, sphere, cylinder, cone, and torus;
- transforms: translation, XYZ rotation, and scale;
- hierarchy and references;
- union, difference, and intersection composition;
- dimension, coincident, offset, child-count, and bounds constraints;
- schema validation, semantic validation, deterministic JSON serialization, and exact round trips.

### Output

- canonical editable JSON;
- deterministic OpenSCAD;
- a validation/design manifest;
- STL when an operational OpenSCAD executable is available;
- evaluation metrics and a deterministic top-view demo preview.

### Failure contract

Incomplete, ambiguous, out-of-domain, structurally malformed, cyclic, non-finite, or constraint-violating inputs fail closed. The system does not approve default geometry for fabrication.

## What is verified now

| Capability | Status | Evidence |
|---|---|---|
| Prompt parsing and unit normalization | Verified, narrow grammar | Maintained tests; 48-task regression and NC-EXP-001 |
| Semantic rejection of incomplete/unsupported prompts | Verified | Maintained tests |
| Canonical typed IR and JSON Schema | Verified | Round-trip, malformed-input, reference, cycle, transform, and constraint tests |
| Prompt → legacy graph → canonical IR → OpenSCAD | Verified | Integration tests and CLI smoke tests |
| Deterministic serialization/export | Verified | Evaluation and round-trip tests |
| JSON/SCAD CLI workflows | Verified | CLI subprocess tests |
| STL compilation and mesh verification | Verified locally and with fixture | OpenSCAD 2021.01 compiled simple and four-hole programs; `trimesh` verified watertight meshes |
| Local demo payload uses real system | Verified | Demo integration tests |
| Maintained test suite | Verified locally for the a6 working tree | External CI for an exact Git revision is still required; historical totals are not current evidence |
| Lint and type checking | Locked Ruff and mypy gates passed locally | Only an external CI receipt closes the release gate |
| Dependency/static security audit | Locked pip-audit and Bandit gates passed locally | Only an external CI receipt closes the release gate |
| Typed enclosure workflow | Verified locally through language, project revisions, preflight, OpenSCAD, STL, and request-level probes | This is a bounded design aid, not proof of physical fit or manufacturability |
| Application exchange | v2 bundles reverify canonical IR, SCAD, hashes, inventory, and optional STL; KiCad application is source-hash-bound | Other CAD/slicer integrations are file handoffs, not native imports or API execution |
| Deterministic benchmark | NeuroCAD 48/48 | Frozen JSONL and result JSON |
| Controlled compiler stress | NeuroCAD 240/240 | NC-EXP-001; frozen per-task records and paired tests |
| Typed IR stress | 1,000/1,000 | NC-EXP-002 |
| Invalid-input rejection | 240/240 | NC-EXP-003; eight predeclared categories |
| Real kernel benchmark | 240/240 STL passed topology and expected-extents verification | `NC-RUN-2026-09-03-FULL`; IR, SCAD, STL, PNG render, validation, and hashes retained |

## Broken, fake, stubbed, or disconnected functionality

- `legacy/python/cad_intelligence_core_allinone.py` historically wrote marker text instead of STEP. v0.5.0a5 hard-disables that legacy method; it remains not STEP export.
- `legacy/python/cad_master_kernel_legacy_broken.py` is explicitly a broken legacy implementation and contains incomplete paths.
- The unused extensionless `core/constraints_py` assertion stub was removed from the supported source surface in v0.5.0a2; it never provided constraint solving.
- The old `design_ir.py` is a small metadata dataclass and is not a sufficient program IR.
- `schema.py`, `validator.py`, `evaluation.py`, `design_intent.py`, `nlp.py`, and `cad_nlp_engine.py` belong to older, disconnected paths and do not define the supported product contract.
- Many historical root-level “tests” execute expensive work at import time and are not safe unit tests.
- An unscoped historical `pytest` collection produced 14 collection/runtime errors: missing Torch/scikit-image, missing `physics.mass`, incompatible `SDFGraph`/kernel APIs, and absent kernel attributes. These failures are preserved, not reclassified as passing.
- Generated historical outputs are not reproducible evidence unless their exact source, dependencies, settings, and verifier receipts are supplied.
- No current UI/API existed before the new local workbench; the workbench is intentionally local and unauthenticated, not a hosted multi-user service.

## Unsupported claims

NeuroCAD has no current evidence for:

- general natural-language-to-CAD intelligence;
- learned geometric reasoning or representation learning;
- causal improvement caused by a typed parser;
- exact STEP/BREP reconstruction;
- arbitrary topology correctness;
- load, tolerance, material, safety, regulatory, or manufacturability guarantees;
- aircraft, vehicle, medical, or other safety-critical design readiness;
- production deployment, public installer success, or tagged release provenance from this checkout.

## Intended interfaces and relationships

The supported interface is now `prompt or IR → validate → canonical IR → deterministic OpenSCAD → optional STL verification`. The legacy `DesignGraph` remains a compatibility parser output but is immediately adapted into canonical IR; exporters and the demo consume canonical IR.

ColorWorld was excluded by direct instruction. No NeuroCAD–ColorWorld interface was implemented or claimed.

## Remaining product/research boundaries

High-value next work requires a deliberate scope expansion: a real grammar for sketches/constraints, a BREP-capable geometry backend, or a properly frozen and authorized learned-model study. Those are separate projects, not unfinished lines hidden behind the current demo.
