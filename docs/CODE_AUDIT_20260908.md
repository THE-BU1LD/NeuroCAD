# Code audit and execution checklist — 2026-09-08 continuation

Latest execution: see [Local workbench completion](#local-workbench-completion)
below for the follow-up implementation, exact-revision checks, and remaining
interactive/release gates. Earlier evidence is retained with its original scope.

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

## Local workbench completion

Implementation commit: `98f05b6acdd4b33a07b760160ac48a9497667db6` on draft PR #49.
This pass began at `7d919ab`. It preserves the independent research edits visible
in the shared worktree; those edits are neither claimed nor included in this
commit. No main merge, visibility change, tag, or release was performed.

### Ranked findings and completed fixes

| Priority | Actual root cause / missing workflow | Implemented resolution and evidence |
| --- | --- | --- |
| P1 security | `parse_project` allocated `list(range(...))` from an arbitrary untrusted revision integer before checking history | Compare revision to bounded history length and stream expected indexes; enormous-integer regression in `tests/test_workbench_projects.py` |
| P1 reliability | Project, calibration, exchange and KiCad readers allocated whole files before checking their declared limits | Bounded reads include one overflow byte; tests simulate growth after `stat`; `core/json_io.py`, `core/project.py`, CLI and integration readers |
| P1 correctness | Mesh preview reconstructed a spec from historical source text, losing later project edits | Verify the current validated `spec`; real OpenSCAD test compiles a revision whose walls differ from its original prompt |
| P1 product | Browser output could not be saved as an editable project or reopened | Canonical project import/export preserves ID, revision and history; part-specific OpenSCAD and IR downloads use actual pipeline output |
| P2 state | Switching modes replaced drafts; obsolete request cleanup could unlock newer work | Independent tab-local drafts, cancellation/generation guards, token-aware cleanup and timeouts; shipped JavaScript executed in Node regression harness |
| P2 failure recovery | Invalid or late imports could overwrite current work in a naive implementation | Validate before replacing input; preserve current output on failed import; test edits during file reading and HTTP responses |
| P2 API | Duplicate Host accepted, origin boundary implicit, flags validated after computation, compiler contention reported as bad input | Reject ambiguous Host and foreign/duplicate Origin, validate request contract first, HTTP 503 plus Retry-After for contention; real socket tests |
| P2 integrity | Bundle-spec hash was read separately from the bytes being parsed | Hash the same bounded byte buffer; test prohibits a second hash read |
| P3 maintenance | Minified UI mixed directly into the HTTP handler | Extract readable `core/workbench.py`; no frontend framework, remote assets or runtime dependencies |

### Completed checklist

- [x] Preserve the existing strict grammar, IR, geometry kernel and security model.
- [x] Add project save/reopen and source downloads using real canonical data.
- [x] Preserve per-mode drafts, reject invalid imports without data loss, and
  prevent stale requests from publishing geometry or changing newer busy states.
- [x] Keep kernel-unverified, verified mesh and unverified physical fit distinct.
- [x] Add explicit focus styles, responsive min-width-safe layout, semantic
  sections, loading/error states and keyboard validation without replacing branding.
- [x] Add bounded-read, revision-overflow, current-spec mesh, HTTP and shipped-JS
  regression coverage; require Node in CI and include the CJS harness in sdist.
- [x] Build, install, compile, independently verify, lint, type-check and audit
  dependencies; exact results below.
- [x] Update quick-start usage, contributor prerequisites and release status.
- [ ] **Blocked — locked Mac:** complete rendered desktop/mobile visual review,
  keyboard traversal and native browser save/file-picker round trip. The live page
  and download links were inspected before lock; Node tests are not a substitute
  for these remaining interactive checks. Unlock the Mac to resume them.
- [ ] **Blocked — release authorization:** review/adopt PR #49, authorize public
  visibility and release, then verify anonymous installation and tag artifacts.
- [ ] **Unperformed external validation:** independent users, physical coupons,
  real external-app imports and measured manufacturing outcomes. No new scientific
  result or successful native Fusion/Onshape integration is claimed.

### Observed validation for the workbench implementation

- Isolated checkout of `98f05b6`: `python -m pytest -q tests` — **431 passed in
  150.64 seconds**, including actual OpenSCAD and loopback-server tests.
- An earlier mutable-worktree run had **429 passes and one provenance failure**:
  source changed during a research test. This was not hidden or bypassed; rerun
  from an isolated commit passed. Concurrent research changes remain separate.
- [CI run 34254474680](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/34254474680)
  — all six release jobs pass. Python 3.10/3.11/3.12 each **431 passed**.
  Portable Ubuntu/macOS each **415 passed, 16 kernel skips**; Windows **410 passed,
  21 skips** (16 kernel and 5 POSIX-installer tests). Workbench JavaScript tests ran.
- Methodology preflight, offline ledger and Stage 1 smoke workflows pass on that
  exact revision. These validate tooling, not learned-model or external accuracy.
- Full CI-scope Ruff passes; isolated mypy passes on **61 source files**. Bandit,
  `pip check`, locked `pip-audit` and CI high-confidence Git-history secret gate
  pass. A scan finding no known issue is not a guarantee of no vulnerabilities.
- Wheel and sdist build with the pinned build environment; distribution verifier
  accepts **48 wheel / 209 sdist members**. Legacy/generated/private material is
  excluded by existing distribution rules. CI double-build reproducibility and
  fresh wheel/sdist installation gates pass.
- Actual staged `install.sh` using the new wheel and isolated install/bin paths
  passes version, dependencies, doctor and generation checks. Installed command,
  outside the checkout, creates revision 1, edits walls to 2.4 mm, builds body/lid
  STL and independently verifies the 9-artifact revision-2 bundle.
  Body SHA256: `f6cf53bf34b9acb20a451c59f111d8585d3d269213932ae081e53247b8b85b27`.
  Lid SHA256: `f1100724555f2ec2ef12e276e3062480d287244451525fc534b6e74fb7a9152f`.
- Browser page loaded the updated workbench, rendered the real enclosure
  specification and exposed project/body/lid source links. Mac lock prevented
  completing visual/mobile/file-picker verification; those gates remain open.
- Final formatter pass covers the new UI/test modules and bounded JSON helper;
  targeted browser/project tests pass afterward. Later PR-head checks remain
  authoritative for later formatting/documentation commits.

### Architecture, content and quality assessment

The maintainable boundary remains Python CLI + typed specification + canonical
IR + deterministic OpenSCAD + independent mesh checks. The workbench is an adapter
to that same pipeline, not a second CAD engine or an authenticated SaaS portal.
Its HTML/CSS/JS lives in a shipped Python module so package and source-provenance
rules include it without an asset build or new server. No browser persistence,
analytics, paid service, new model provider, or speculative orchestration layer
was added. Code now uses ordinary input placeholders only as UI hints, not fake
production output. The unsupported STEP path and legacy research scaffolds remain
honestly classified in the earlier table.

Subjective engineering scores for the **documented local alpha**, not universal
CAD capability or certification:

| Dimension | Score / 10 | Remaining gap |
| --- | --- | --- |
| Functionality | 8 | Bounded enclosure/basic-geometry grammar, no general sketches or STEP/BREP |
| Engineering | 8 | Sound shared contracts; further geometry robustness and interactive coverage needed |
| Reliability | 8 | Strong exact-commit tests, but real user/device/manufacturing evidence is limited |
| Design | 6 | Cleaner working layout and states; final visual/mobile/keyboard inspection blocked |
| Organization | 7 | Product/legacy boundary exists; concurrent reports and historical docs still need ownership review |
| Documentation | 7 | Quick start is actionable; research/publication claims require careful revision-specific reading |
| Maintainability | 8 | Readable shared pipeline and regression tests; UI remains a small inline-script application |
| Overall readiness | 6 | Usable private local alpha, not a fully signed-off public release |

Highest-impact worthwhile next work is (1) the blocked interactive acceptance
pass, (2) reviewed public-alpha release and anonymous-install evidence, (3) measured
enclosure/fit pilots, then (4) user-tested grammar/semantic editing improvements
and (5) robust embedding/self-intersection or native-CAD work with an explicit
acceptance scope. Adding mathematical terminology, more mock adapters or an
unvalidated model would not close those gaps. Verdict: **KEEP / FIX**, not DELETE,
and not "perfect" or "unlimited".
