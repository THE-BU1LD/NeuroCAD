# Code audit and execution checklist — 2026-09-08 continuation

Scope: maintained NeuroCAD package, CLI, mathematical helpers, mesh verification,
installer, packaging, CI and product documentation. The separate FinanceMeta portal
and concurrently edited research reports are preserved, not silently republished.
Baseline: `665e706`, draft PR #49. This is a supported-alpha improvement pass,
not a claim to have proved every historical line correct or exhausted CAD research.

## What is real, incomplete, or misleading

| Area | Classification | Evidence / disposition |
| --- | --- | --- |
| Typed IR, parser and SCAD exporter | Working implementation | `core/ir.py`, `ir_parser.py`, `ir_export.py`; validation/round-trip tests and real OpenSCAD CI |
| Enclosures, revisions, fit samples | Working bounded product | `enclosure.py`, `project.py`, `fit_sample.py`; explicit constraints and request-level mesh probes |
| Mesh acceptance | Real but had a correctness gap | Watertight/winding/volume checks did not test vertex links; pinched torus fixture passes those older checks. Fixed with independent topology checks |
| Analytical tolerance helper | Real but incomplete validation/model | Independent-normal only, duplicate names and Boolean means accepted. Now strict, finite, covariance-aware with PSD validation |
| Installer | Working happy path, unsafe upgrade sequence | In-place pip mutation and launchers published before version/doctor verification. Now staged, validated, ownership-checked and rollback-preserving |
| Fusion/Onshape and slicer adapters | File-exchange contracts, not native integration | `core/integrations/registry.py` explicitly describes missing API/import operations. Retained without pretending native success |
| `model/` | Documentation, not a trained model | No checkpoint or trained implementation claimed |
| VeriCodeGen Stage 1 | Executable experiment scaffold | Scripted fixtures and kernel plumbing are not learned-model results |
| Legacy kernel | Abandoned incomplete code | `legacy/python/cad_master_kernel_legacy_broken.py` contains `NotImplementedError`; excluded from wheel/sdist |
| Legacy STEP exporter | Disabled former fake capability | Raises "STEP export is unsupported"; not replaced with another fake exporter |
| UI input placeholders and exception-class `pass` | Legitimate code, not missing implementation | Do not delete ordinary input hints or empty exception subclasses based on keyword searches |
| Root reports / old checklists | Revision-specific history with drift | Added current map and supersession links; corrected release status, retained negative/frozen evidence |
| Public quick install | Not currently available | GitHub API confirms PRIVATE repo, open draft PR and no tags. Local checkout installation is documented and tested separately |

## Execution checklist

- [x] Inspect Git, current PR/visibility, package, source, tests, release workflow,
  existing audit and legacy implementation markers; preserve concurrent edits.
- [x] Implement finite triangular-complex F2 homology, Euler characteristic,
  boundary loops, orientability and compact-surface classification.
- [x] Detect non-manifold vertex links in kernel STL acceptance. Preserve existing
  disconnected-body, winding, extent and request-feature checks.
- [x] Expose source-hash-bound `neurocad topology` diagnostics, bounded inputs,
  explicit failure status, and no-clobber JSON output.
- [x] Add correlated tolerance propagation, strict PSD/symmetry/unit-diagonal
  validation, unique measurement names, Boolean/overflow rejection, and CLI.
- [x] Add sphere/torus/disk/Möbius/singular-complex tests and independent binary
  boundary-matrix cross-checks; add analytical covariance and failure cases.
- [x] Stage installer environments, validate dependencies/version/doctor before
  launcher publication, retain old environments, refuse unrelated executables.
- [x] Add installation failure injection and CI real-wheel quick-install smoke.
- [x] Add quick start, Windows usage, mathematical contract/reference guide,
  hypothetical input example, docs index and updated release status.
- [x] Full-suite/static/build/installed-package checks pass; observed results below.
- [x] Exact implementation-revision GitHub CI (`e0da3bc`): all six release jobs
  and all three research workflows pass. Require current PR checks before merge.
- [ ] Review baseline adoption and authorize merge/publication; private visibility,
  release tag/artifacts, and anonymous install remain distinct acceptance gates.
- [ ] Physical measurements, real external-app imports and independent research
  evaluation remain unperformed. No mathematical software test closes these gates.

## Observed validation

- CI: https://github.com/THE-BU1LD/NeuroCAD/actions/runs/34247703147.
  Linux Python 3.10/3.11/3.12: **417 passed** each, including real OpenSCAD.
  Portable Linux/macOS: **402 passed, 15 kernel skips**. Windows: **397 passed,
  20 skips** (15 kernel + 5 POSIX-installer tests; Windows uses documented venv).
- Local full suite: **415 passed in 316.78 seconds**. Two subsequently added
  validation/overflow cases also passed in the final 36-test targeted run;
  remote CI includes all 417 together.
- Ruff passes. Local mypy passes on 38 files; CI-scope mypy on 60 files. Bandit
  on core passes; CI dependency/security and clean-install gates pass.
- Clean `git archive e0da3bc` wheel/sdist build passes with pinned build tools.
  Distribution verification accepts **47 wheel / 205 sdist members** and excludes
  legacy/generated material. This avoids packaging concurrent uncommitted notes.
- Real staged install of that wheel in isolated local directories: pip dependency
  check, version, doctor, generation validation and launcher publication pass.
  CI independently exercises the installer from its own built wheel.
- Installed command, run outside the checkout: compiled a 40x30x3 mm four-hole
  plate to STL; topology assertion passed with Betti numbers **[1,8,1]**, genus
  **4**, zero boundary edges and valid vertex links. Artifact SHA256:
  `e34a6a440664d9d383e0a6bda3a995a9cb8ceb3a01b049cc2d36a110082ff8cc`.
- Installed tolerance example: mean clearance **0.35 mm**, sigma **0.2 mm** and
  recommended nominal clearance **0.75 mm**; these are hypothetical analytical
  inputs, not measured manufacturing evidence.
- Git repair: a confirmed ownerless 76-minute-old index lock was moved aside
  recoverably. User research changes and their README paragraph remain unstaged;
  no main merge, visibility change, tag publication or physical test was performed.

## Mathematical challenge and limits

Matching topology is necessary for some design requirements but insufficient for
geometric correctness: spheres and arbitrarily distorted spheres have the same
Betti numbers. Tests explicitly challenge manifoldness and orientation rather than
equating watertightness with a valid surface. F2 homology does not classify knots,
detect all self-intersections, prove dimensional fit, or supply integer torsion.

Covariance entries individually in [-1,1] are insufficient: the full correlation
matrix must be positive semidefinite. Perfectly correlated errors can either add
or cancel after dimensional sensitivities. Worst-case intervals and normal-tail
probabilities are separate assumptions, not interchangeable certifications.

These are useful classical algorithms, not a novel PhD contribution. No new
dependency, invented empirical result, protocol change or scientific claim was
needed. The product remains bounded by its explicit input/resource and geometry
contracts; "perfect with no limits" is not a testable completion standard.

## Further work requiring an explicit acceptance scope

- Robust triangle self-intersection/embedding analysis, with exact predicates or
  a reviewed geometry kernel; topology alone cannot replace it.
- STEP/BREP/native CAD and sketch constraints: separate representation/kernel
  work, not a filename/exporter substitution.
- Broader language support: independent user requests and measured acceptance
  before grammar changes or model-provider experiments.
- Physical validation: measured coupon/enclosure datasets tied to material,
  process, instrument resolution and held-out geometry.

Keep historical artifacts out of distributions but retain them for forensics.
Do not remove user reports, local environments, or legacy negative evidence as
cosmetic cleanup. Verdict: **FIX / keep the working alpha**, not an unlimited or
manufacturing-certified CAD replacement.
