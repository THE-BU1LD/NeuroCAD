# NeuroCAD — final 9/10 acceptance checklist

**Subsequent GitHub handoff:** the repository is now public and PR #49 has merged
after twelve successful checks. See [the 2026-09-09 handoff](GITHUB_HANDOFF_20260909.md)
for the newer implementation snapshot, anonymous installation and PR dispositions.
The dated private/draft observations below are retained as audit history, not current status.

Prepared 2026-09-09. This is the single forward-looking checklist for improving
the eight areas scored in the [current audit](CODE_AUDIT_20260908.md).
Older audits remain historical evidence; the [expansion backlog](PRODUCT_EXPANSION_CHECKLIST.md)
is not an additional release commitment.

**The scores below are baselines and targets, not newly achieved results.**
Creating this checklist does not complete its implementation or validation.
Nine means a dependable, well-tested product within its explicit scope—not
perfect software, unlimited CAD, or a scientific/manufacturing certification.

The [final publication audit below](#final-publication-audit--2026-09-09)
records the subsequent implementation, new geometric defects found, measured
results and current score assessment. Earlier observations in this document
remain dated evidence rather than the state of the final working tree.

## Audit → implementation pass, 2026-09-09

This section records the follow-up request to classify the code and implement
improvements. It does not reset the older checklist or raise its scores by fiat.

| Inspected area | What is actually there | Action / disposition |
| --- | --- | --- |
| Typed enclosure/IR/OpenSCAD pipeline | Working bounded compiler, not pseudocode | Retained; expanded real-HTTP/kernel tests for plates, open-top cases, screw lids, and friction lids with cutouts/vents/standoffs |
| Semantic edit grammar | Real CLI implementation that was missing from the UI | Connected to a stateless, strict edit-preview API and explicit browser review/confirmation; canonical history and original source retained |
| Workbench state | Real UI, previously lacking clear unsaved-work protection and actual browser tests | Added unsaved/replacement/leave-page protection, visible project dimensions/revision, actionable errors and three-browser acceptance |
| Compiler failures | A real 30-second deadline could be misreported as missing OpenSCAD | Added distinct safe error categories and explicit 30/60/120-second per-part budgets; unchanged default, geometry and verification |
| Tolerance mathematics | Implemented analytical model with order-sensitive signed accumulation and huge-integer conversion gaps | Compensated summation, bounded conversion errors, cancellation/permutation/scaling and independent covariance-reference tests |
| Topology mathematics | Implemented classical finite-complex/manifold algorithms | Added vertex-relabeling, face-order and affine-embedding checks; no claim of novel topology, self-intersection certification or physical correctness |
| CI/release checks | Real workflows with permissive missing-test branches | Required test files and Node now fail closed; real Chromium/Firefox/WebKit jobs added; fresh remote execution remains a release gate |
| `legacy/python/cad_master_kernel_legacy_broken.py` | Abandoned implementation with `NotImplementedError` | Remains archived and excluded from distributions; not a supported feature to rebuild blindly |
| `model/` | Honest status documentation; no trained implementation or checkpoint | Preserved; do not invent a model or training result |
| Native CAD integrations | Real file-exchange adapters with unavailable native operations explicitly declared | Preserved; actual external-app acceptance and STEP/BREP remain separate work |
| VeriCodeGen Stage 1 | Executable scripted development fixtures, not model evidence | Preserve frozen/negative results; this product work makes no new research-outcome claim |
| Concurrent research changes | Separate uncommitted evaluator/report work already present | Inspected boundaries and preserved; excluded from the isolated product candidate and not claimed as this pass's results |
| HTML placeholders / exception subclasses | Legitimate input examples and typed exceptions | Not missing implementations; retained |

Execution checklist for the concrete defects/extensions in this pass:

- [x] Make absent required tests/Node fail the actual workflow prerequisite commands.
- [x] Implement and test strict, no-op-rejecting, history-preserving edit proposals.
- [x] Add explicit before/after review and confirmation in the live workbench.
- [x] Preserve valid projects on invalid/stale edits and rejected imports.
- [x] Add honest download/unsaved indicators and confirmed destructive replacement.
- [x] Exercise real file downloads/imports, keyboard confirmation and native
  leave-page warnings in Chromium, Firefox and WebKit.
- [x] Separate unavailable-kernel, timeout and compiler-contention errors;
  retain redaction, single-compiler locking and atomic output cleanup.
- [x] Expose bounded compile budgets without changing geometry/resolution or
  silently increasing the default deadline.
- [x] Repair signed tolerance accumulation and oversized-number validation;
  challenge covariance and topology with independent/metamorphic tests.
- [x] Update user/contributor instructions and package the release workflow needed
  by source-distribution tests. Browser tooling is an optional test dependency.
- [x] Finish the final source-bound verification record below; do not infer
  that older remote CI checks cover these new local edits.
- [ ] Complete the still-unchecked broader acceptance items, including external
  application imports, independent users/physical trials, review and publication.

Observed so far: an isolated pre-final-hardening candidate passed **467 tests**,
lint and typing, and built a safe **48-member wheel / 214-member sdist**. The
three-browser run passed **11 checks per browser**, including actual revised
body/lid compilation, byte-checked STL downloads, file import, edit confirmation,
responsive screenshots, and native leave-page warning dismissal. Five subsequent
oversized-integer regression cases and final UI diagnostics require the final
combined rerun; do not combine counts from separate runs into a claimed total.

GitHub was rechecked during this pass: repository **PRIVATE**, PR **#49 OPEN and
DRAFT**, still at `a870c12920483f66c98628fac92b892cdadab7f3`. These local changes
have not been pushed, merged, tagged or published. Human screen-reader/native
mobile testing, independent first-use trials and physical measurements are not
implied by desktop browser automation.

## Scope and evidence baseline

The target is the maintained local enclosure/basic-geometry product described
in [Capability boundary](CAPABILITY_BOUNDARY.md). Preserve its deterministic
grammar, canonical projects, revisions, OpenSCAD backend, verification, and
file-exchange contracts. Do not narrow existing promises to make tests pass.

Baseline HEAD inspected: `a870c12920483f66c98628fac92b892cdadab7f3`.
The working directory contains concurrent research/documentation changes;
these are not covered by the baseline's passing checks or this checklist edit.

Previously recorded evidence, **not rerun when writing this checklist**:

- [x] Typed CAD, enclosure revisions, real body/lid compilation and independent
  bundle verification exist and have passed recorded tests.
- [x] Project open/save, source downloads, stale-request protection, bounded
  input reads and compiler-contention handling are implemented.
- [x] Topology/manifold diagnostics and covariance-aware tolerance calculations
  have analytical and independent-reference tests, with explicit limitations.
- [x] Staged installation, rollback preservation, wheel/sdist validation and
  fresh-install gates have passed.
- [x] At the baseline SHA, all nine recorded PR checks passed. Linux Python
  3.10/3.11/3.12 each ran 431 tests; portable platforms had documented skips.
  [Exact CI run](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/34256015165).

Last-known publication state was a private repository and draft
[PR #49](https://github.com/THE-BU1LD/NeuroCAD/pull/49). Recheck this before any
release action; this document does not authorize a merge or visibility change.

## Scorecard

| Area | Last score | Target | Required acceptance items |
| --- | --- | --- | --- |
| Functionality | 8 | ≥9 | F1–F4: complete supported user journeys |
| Engineering | 8 | ≥9 | E1–E4: fail-closed gates and challenged correctness |
| Reliability | 8 | ≥9 | R1–R4: recovery, bounded operation and independent evidence |
| Design | 6 | ≥9 | U1–U4: usable, accessible, visually verified workbench |
| Organization | 7 | ≥9 | O1–O4: clear ownership and maintained boundaries |
| Documentation | 7 | ≥9 | D1–D4: one truthful, tested route through the product |
| Maintainability | 8 | ≥9 | M1–M4: understandable contracts and repeatable maintenance |
| Overall readiness | 6 | ≥9 | P1–P4, plus the preceding acceptance evidence |

Use `[x]` only with an evidence entry. Unchecked means acceptance is outstanding,
not necessarily that the underlying implementation is absent. Existing behavior
that passes its acceptance check needs no rewrite. These scores are qualitative
engineering judgments; a second reviewer must reassess them after execution.

Priority: **P0** = release/correctness/security gate; **P1** = supported workflow;
**P2** = quality, organization or additional confidence. Any newly found data-loss,
security, or wrong-artifact defect immediately takes priority over polish.

## Functionality

- [ ] **F1 · P1 — Prove the entire supported workflow, not individual buttons.**
  Files: `core/workbench.py`, `core/demo_server.py`, `core/project.py`,
  `tests/test_workbench_projects.py`, `tests/test_enclosure_product.py`.
  Change: add a shared acceptance fixture set covering a plate, open-top
  enclosure, friction lid, screw lid, cutouts, vents and mounting features.
  Cover valid combinations and deliberately incompatible requests.
  Done: prompt → validation → canonical project → real compilation → downloaded
  artifacts → independent verification → save/reopen preserves identity,
  dimensions and history. Invalid requests publish no successful artifact.

- [x] **F2 · P1 — Complete semantic editing in the browser.**
  Files: `core/workbench.py`, `core/demo_server.py`, `core/edit_language.py`,
  `core/project.py`, `tests/test_edit_language.py`, `tests/workbench_contract.cjs`.
  Change: expose the existing validated edit operations with a before/after
  summary; preserve the original prompt and append the canonical change record.
  Do not introduce a second editing model or silently reinterpret history.
  Done: resize, change walls, add/move/remove a supported feature, reject a bad
  edit without changing the project, then save/reopen and verify the new geometry.

- [ ] **F3 · P1 — Make failures actionable without changing design intent.**
  Files: `core/enclosure.py`, `core/validation.py`, `core/natural_language.py`,
  `core/demo_server.py`, `core/workbench.py`.
  Change: carry existing field/feature context into readable UI diagnostics;
  identify the conflicting dimensions and supported correction. Preserve input.
  Any suggested edit requires confirmation and normal validation.
  Done: fixture cases for missing dimensions, unsupported clauses, feature
  collisions and insufficient clearances identify the actual failing constraint;
  no automatic unit, tolerance or geometry change is disguised as success.

- [x] **F4 · P1 — Verify one complete external file-handoff journey.**
  Files: `core/integrations/exchange.py`, `core/integrations/handoff.py`,
  `core/integrations/registry.py`, `tests/test_integrations.py`,
  `docs/PRODUCT_WORKFLOW.md`.
  Change: close any reproducible export/import defect in a documented existing
  exchange workflow. Record the receiving application's version and settings.
  Done: a real external application opens the generated body/lid with correct
  scale, dimensions and part count. Retain source hashes and screenshots/receipts.
  Label this file exchange, not native API integration. Application access may
  be needed for acceptance; mocks alone cannot close it.
  Evidence: the final audit executed a Blender 5.0.1 import of the browser-saved
  revision's verified body and lid, checked dimensions/part count, and retained
  hashes, importer settings, a receipt and the actual `.blend` scene.

## Engineering

- [ ] **E1 · P0 — Make required test execution fail closed.**
  Files: `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  `tests/test_ci_gates.py`, `tests/test_workbench_ui.py`.
  Problem: workflow conditionals currently permit a missing `tests/` directory;
  the release workflow does not explicitly require Node for the JS harness.
  Change: require the expected test sources and Node, invoke tests unconditionally,
  and distinguish intentional portable skips from missing required tooling.
  Done: tests assert those workflow requirements, a disposable missing-tool/test
  probe fails, and normal CI plus release-equivalent commands pass.

- [ ] **E2 · P0 — Close security regressions across the complete local boundary.**
  Files: `core/demo_server.py`, `core/json_io.py`, `core/artifacts.py`,
  `core/mesh_preview.py`, `core/integrations/`, `tests/test_demo_resource_limits.py`,
  `tests/test_compiler_safety.py`, `SECURITY.md`.
  Change: exercise hostile request bodies, duplicate headers/keys, foreign origins,
  symlinks, traversal, malformed manifests, output collisions and compiler input.
  Fix uncovered paths while retaining loopback, validation and no-clobber controls.
  Done: rejection happens before unsafe work, sensitive paths/data do not leak,
  and the server handles a subsequent valid request. Scan the exact release tree
  and history; any actual exposed credential requires owner rotation.

- [ ] **E3 · P1 — Challenge geometry acceptance independently.**
  Files: `core/enclosure_verification.py`, `core/structural_verification.py`,
  `core/topology.py`, `tests/test_topology.py`, `tests/test_mesh_preview.py`,
  `tests/test_enclosure_product.py`.
  Change: extend negative fixtures for missing/blocked features, wrong extents,
  detached bodies, reversed orientation and singular vertex links; retain
  adversarial examples that share topology but differ geometrically.
  Done: each claimed property fails when specifically violated, supported valid
  references pass, and unsupported checks such as general self-intersection
  certification remain explicitly unknown—not inferred from matching Betti numbers.

- [ ] **E4 · P1 — Make mathematical guarantees precise and regression-resistant.**
  Files: `core/engineering_math.py`, `core/topology.py`, `core/calibration.py`,
  `tests/test_tolerance.py`, `tests/test_topology.py`, `tests/test_calibration.py`,
  `docs/MATHEMATICS.md`.
  Change: extend independent small-complex, boundary-value and transformation tests;
  test singular/near-PSD covariance, signed cancellation, overflow and declared
  numerical tolerances. Link each reported quantity to units and assumptions.
  Done: analytical reference cases and independent homology reduction agree;
  malformed/unsupported inputs fail deterministically. No sampled geometry,
  normal-model probability or calibration fit is relabelled a proof or measurement.

## Reliability

- [ ] **R1 · P1 — Verify recovery under interruption and stale state.**
  Files: `core/workbench.py`, `core/demo_server.py`, `core/mesh_preview.py`,
  `tests/test_demo_ui_race.py`, `tests/test_demo_resource_limits.py`,
  `tests/workbench_contract.cjs`.
  Change: exercise double submission, edits during compilation, tab-mode switches,
  HTTP 503/retry, browser timeout, server restart and expired mesh URLs.
  Done: old responses never replace newer work; no stale downloads look current;
  errors preserve editable input; users can recover. A cancelled browser request
  never falsely claims the server's compiler has been cancelled.

- [ ] **R2 · P1 — Establish measured resource and latency budgets.**
  Files: `core/mesh_preview.py`, `core/demo_server.py`, `core/topology.py`,
  `tests/test_demo_resource_limits.py`, `docs/QUICKSTART.md`.
  Change: measure cold/warm supported fixtures and bounded hostile cases on a
  recorded reference machine; set justified budgets before the acceptance rerun.
  Include worker/process limits, temporary-artifact retention and cleanup.
  Done: repeated runs stay within those budgets, rejected oversized inputs do not
  cause unbounded allocation, compiler children terminate on their server-side
  deadline, and the UI remains recoverable. Report measurements, not guessed speedups.

- [ ] **R3 · P2 — Run independent first-use trials.**
  Components: installed CLI, live workbench, `docs/QUICKSTART.md`, F1 fixtures.
  Change: predeclare a small product-acceptance pilot with three non-author users:
  each installs, creates/edits, saves/reopens and verifies a supported design.
  Record help requests, failures and time; repair reproducible blockers and repeat
  the affected journey. This is a proposed QA sample, not a statistical benchmark.
  Done: each participant completes every critical journey without undocumented
  intervention. Human participation is an external acceptance dependency.

- [ ] **R4 · P2 — Complete the existing physical evidence loop for one enclosure.**
  Files: `core/fit_sample.py`, `core/calibration.py`, `core/manufacturing.py`,
  `docs/PHYSICAL_VALIDATION_PROTOCOL.md`, `tests/test_fit_sample.py`,
  `tests/test_calibration.py`.
  Change: verify coupon → raw observations → fitted profile → preflight → verified
  enclosure using the existing contracts; repair software gaps. Then execute the
  unchanged physical protocol, retaining failed runs as well as successes.
  Done: the required independent print runs, measurements, hardware checks and
  hashed artifacts pass the predeclared criteria. Needs a printer, hardware,
  calibrated measurement equipment and a human operator. Public software alpha
  can ship without this, but it cannot earn physical-fit claims or this stronger
  evidence target by substituting simulation or invented data.

## Design and usability

- [ ] **U1 · P1 — Complete the workbench's visible states.**
  Files: `core/workbench.py`, `tests/workbench_contract.cjs`.
  Change: make input, active project/revision, edit, validate, compile and download
  actions unambiguous. Distinguish structural validation, kernel verification and
  physical validation. Finish loading, disabled, empty, error and expired states.
  Done: inspect the live rendering for every state; current revision and output
  status remain clear with long prompts/errors. Preserve the established branding.

- [ ] **U2 · P1 — Finish keyboard and assistive-technology access.**
  Files: `core/workbench.py`; browser tests added under `tests/`.
  Change: verify labels, focus order/visibility, keyboard-only import/edit/export,
  status announcements and error associations; repair actual barriers.
  Done: complete F1/F2 without a mouse, inspect the accessibility tree, and test
  dynamic status/error announcements with a screen reader. Automated checks alone
  do not count as a complete accessibility audit or formal compliance claim.

- [ ] **U3 · P1 — Verify responsive layout and browser behavior.**
  Files: `core/workbench.py`; browser tests and visual receipts under `tests/` or
  CI artifacts, not the runtime package.
  Change: test 320, 390, 768 and 1440 CSS-pixel widths, 200% zoom, long text and
  portrait/landscape. Check Chromium, Firefox and WebKit; include a real mobile
  browser for touch/file handling. Repair overflow and inaccessible controls.
  Done: critical controls stay usable, text is readable, and downloads/imports
  work on the declared browser support matrix. Recheck computer access; a prior
  session's locked Mac is not evidence of a current browser test.

- [x] **U4 · P1 — Make unsaved work and recovery explicit.**
  Files: `core/workbench.py`, `tests/workbench_contract.cjs`, `docs/QUICKSTART.md`.
  Change: display dirty/saved state and warn before destructive replacement where
  feasible; retain rejected-import state and provide an obvious project download.
  If recovery storage is added, make it opt-in, bounded, local and clearable.
  Done: browser checks cover replacement, reload/close warnings where supported,
  failed import and restoring a saved project. Document mobile/browser warning
  limitations; never promise autosave or durable storage that does not exist.

## Organization

- [ ] **O1 · P0 — Reconcile the exact candidate without overwriting concurrent work.**
  Components: Git diff, PR #49, modified research sources/reports, `MANIFEST.in`.
  Change: review each pending change with its owner and intended scope; group
  accepted work into coherent revisions. Leave unrelated work intact and use an
  isolated clean checkout for evidence runs.
  Done: every candidate change is accounted for, no unrelated edit is discarded,
  and every validation result names a single immutable source revision.

- [ ] **O2 · P2 — Make the maintained/imported/archived boundary enforceable.**
  Files: `pyproject.toml`, `MANIFEST.in`, `scripts/verify_distribution.py`,
  `tests/test_legacy_contracts.py`, `tests/test_release_build.py`, `legacy/`, `model/`.
  Change: check actual imports and package members before relocating dead weight;
  archive misleading abandoned code only with references preserved. Retain useful
  fixtures and real exception/input-placeholder code.
  Done: maintained commands never depend on excluded legacy scaffolding, wheel
  and sdist contain everything needed, and neither ships accidental caches,
  private artifacts or broken former implementations.

- [ ] **O3 · P2 — Give each maintained subsystem a clear owner and boundary.**
  Files: `CONTRIBUTING.md`, `docs/INDEX.md`, modules under `core/`.
  Change: document responsibility and dependency direction for parsing, project
  changes, geometry, verification, integrations, UI and research. Nominate actual
  reviewers with their agreement rather than inventing owners or teams.
  Done: a contributor can identify the right implementation, tests and reviewer
  for an enclosure edit or verifier change without following competing copies.

- [ ] **O4 · P2 — Keep the portal and research from distorting product status.**
  Files: `docs/INDEX.md`, `docs/CAPABILITY_BOUNDARY.md`, `RELEASE_STATUS.md`,
  revision-specific research reports and `research/`.
  Change: link separate ownership/release evidence; distinguish shipping product,
  experimental tooling and archived results. Review concurrent new reports before
  linking or packaging them. Do not rewrite frozen protocols or negative results.
  Done: no NeuroCAD score claims the separate membership portal is deployed, and
  no scripted experiment/checkpoint-free scaffold is described as a trained model.

## Documentation

- [ ] **D1 · P1 — Establish one authoritative capability matrix.**
  Files: `docs/CAPABILITY_BOUNDARY.md`, `docs/PRODUCT_WORKFLOW.md`,
  `docs/MATHEMATICS.md`, `README.md`, CLI help and integration registry.
  Change: classify capabilities as implemented/tested, analytically modelled,
  externally demonstrated, experimental or unsupported; link the evidence.
  Done: prompt grammar, lid types, units, file formats and limits agree everywhere.
  Claims of general CAD, native integration or manufacturing success require
  their own real implementations and evidence, not stronger marketing language.

- [ ] **D2 · P1 — Test the installation and first-use instructions verbatim.**
  Files: `docs/QUICKSTART.md`, `install.sh`, `neurocad_cli.py`,
  `tests/test_installer.py`, `tests/test_release_build.py`.
  Change: separate private-candidate and released-install instructions, document
  OpenSCAD discovery/missing-kernel behavior and supported Python/platforms.
  Done: clean Linux, macOS and Windows sessions follow the documented route;
  run outside the checkout, generate and verify real outputs. Record exact
  commands, versions and any legitimate platform-specific limitations.

- [ ] **D3 · P2 — Remove navigation drift, not historical evidence.**
  Files: `docs/INDEX.md`, `README.md`, `RELEASE_STATUS.md`, historical audit/checklist
  documents and `docs/examples/`.
  Change: point current guidance to this checklist and the capability/quickstart
  pages; label historical snapshots, repair broken links and test examples.
  Done: one obvious current entry point, no contradictory active completion
  claims, all local links resolve, and executable examples pass in a clean install.
  Do not bulk-delete Markdown or silently rewrite old test counts.

- [ ] **D4 · P2 — Give every conclusion a reproducible evidence trail.**
  Files: `docs/MATHEMATICS.md`, `docs/PHYSICAL_VALIDATION_PROTOCOL.md`,
  `NEUROCAD_RESEARCH_REPORT.md`, `research/`, and the evidence record below.
  Change: distinguish theorem/algorithm, deterministic fixture result, empirical
  measurement, hypothesis and negative result; require source/data hashes and
  methods for numerical claims. Preserve existing frozen decisions.
  Done: a reviewer can reproduce each shipped example and find every reported
  number's inputs. Missing external evidence is labelled pending, not extrapolated.

## Maintainability

- [ ] **M1 · P1 — Add actual browser regression tests alongside the Node harness.**
  Files: `tests/test_workbench_ui.py`, `tests/workbench_contract.cjs`,
  `.github/workflows/ci.yml`; new browser harness under `tests/`.
  Change: automate real HTTP/browser journeys for save/import, semantic edits,
  invalid input, compile/download and stale responses. Keep fast JS contract tests.
  Done: the browser lane runs in CI with real file chooser/download behavior,
  captures useful failure artifacts, and cannot silently skip its prerequisites.
  A small development-only dependency is acceptable if needed; no runtime framework
  migration is required.

- [ ] **M2 · P2 — Refactor only demonstrated maintenance bottlenecks.**
  Files: `core/workbench.py`, `core/demo_server.py`, `neurocad_cli.py`,
  `core/enclosure.py`, `core/research_suite.py`.
  Change: remove proven duplicate contract logic and isolate cohesive handlers
  where the changes above expose coupling. Preserve public entry points and
  versioned formats; extract browser assets only if packaging/tests justify it.
  Done: behavior/compatibility tests pass and each extraction has a concrete
  responsibility. Large line counts alone do not justify a rewrite.

- [ ] **M3 · P1 — Verify project and artifact compatibility deliberately.**
  Files: `core/project.py`, `core/ir.py`, `core/integrations/exchange.py`,
  `tests/test_workbench_projects.py`, `tests/test_ir.py`, `tests/test_integrations.py`.
  Change: retain older supported project fixtures, round trips and revised-project
  bundles; explicitly reject unknown future formats and stale/tampered receipts.
  Done: supported saved projects reopen without history loss; any format change
  has a tested migration or clear versioned rejection. No silent data rewriting.

- [ ] **M4 · P2 — Make a contributor's verification path match CI.**
  Files: `CONTRIBUTING.md`, `pyproject.toml`, `requirements-research.lock`,
  `.github/workflows/ci.yml`, `.github/workflows/release.yml`.
  Change: consolidate documented check commands, explain kernel/browser
  prerequisites, and reconcile duplicate setup without broad dependency upgrades.
  Done: a new environment runs the maintained tests, lint, typing, dependency
  checks, security scan and build; dependency/lock changes are reviewed and used
  consistently. Preserve hash-locked research reproducibility requirements.

## Overall readiness and publication

- [ ] **P1 · P0 — Run the complete ladder on the final candidate SHA.**
  Files: `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  `tests/`, `scripts/verify_distribution.py`.
  Change: repair any failures from targeted tests through the full supported
  platform matrix, lint/type/security checks, reproducible builds, fresh wheel
  and sdist installs, real kernel/browser smoke and bundle verification.
  Done: all required checks pass on the same immutable candidate. Record test
  counts and reasons for permitted skips; an earlier green commit is insufficient.

- [ ] **P2 · P0 — Obtain independent review and owner-controlled release approval.**
  Components: PR #49 or its verified successor, branch checks, `LICENSE`,
  `SECURITY.md`, package metadata, `RELEASE_STATUS.md`.
  Change: review the final diff, compatibility, secret/history findings, license
  and distribution contents. Present exact evidence and unresolved limitations.
  Done: reviewer signs off, owner approves merge/publication and the reviewed
  revision lands on the intended protected main branch. Do not bypass checks,
  assume consent to expose private work, or tag an unrelated branch.

- [ ] **P3 · P0 — Prove a real public release and credential-free installation.**
  Files: `.github/workflows/release.yml`, `install.sh`, `pyproject.toml`,
  `docs/QUICKSTART.md`, `README.md`, `RELEASE_STATUS.md`.
  Change: after P2, publish the approved version/tag and verified distributions
  with checksums; apply visibility changes only with explicit owner approval.
  Done: a logged-out, clean machine downloads the intended release, verifies
  checksums, installs, runs doctor, generates/edits/compiles and independently
  verifies an enclosure. GitHub/account permissions and publication approval
  are genuine external gates; private local installation is not this result.

- [ ] **P4 · P1 — Close the checklist with evidence and a fresh score review.**
  Files: this document, `RELEASE_STATUS.md`, `docs/CODE_AUDIT_20260908.md`.
  Change: attach receipts to completed items, retain precise pending blockers,
  and have a second reviewer assess all eight dimensions against the delivered
  scope. Document rollback/reinstall and an actionable bug-report route.
  Done: no unresolved critical/high-impact defect in the supported journey;
  every required acceptance above is evidenced; each score is independently
  justified at ≥9. If an item or score remains below target, say so—do not
  round up, remove the requirement, or substitute this document for execution.

## Execution order

1. **Protect the baseline:** O1 → E1/E2 → reproduce existing passing gates.
2. **Complete the user journey:** F1/F2/F3 with M1/M3 → U1/U2/U3/U4 → R1.
3. **Challenge correctness:** E3/E4 → R2 → F4; prepare R3/R4 protocols and
   arrange external participants/equipment without blocking independent code work.
4. **Make it maintainable and understandable:** O2/O3/O4, D1–D4 and M2/M4;
   coordinate concurrent documentation changes rather than overwriting them.
5. **Accept and release:** repeat P1 after the last code change → P2 → P3.
   Close R3/R4 when real evidence exists; P4 cannot claim all target scores first.

The public-alpha release gate is narrower than the all-eight-at-nine confidence
target. Pending physical trials or learned-model research must be disclosed but
do not automatically forbid releasing honest, bounded software. Conversely,
publication alone does not close those evidence tasks or raise its scores.

## Evidence record and non-goals

Append a concise row when an item is actually completed:

| Item | Exact commit | Platform/tool versions | Command or manual protocol | Result/artifact | Reviewer |
| --- | --- | --- | --- | --- | --- |
| Local publication audit | Uncommitted candidate above `d22172a`; not a release commit | macOS 26.5.2, Python 3.12.14, OpenSCAD 2021.01, Blender 5.0.1 | Commands and limitations below | `.provenance/publication-20260909/` | Automated checks and agent inspection; not independent acceptance |

Keep detailed logs/screenshots/bundles in appropriately scoped CI artifacts or
versioned evidence locations, not as accidental wheel payloads. Record failures
and subsequent fixes; distinguish automated tests from manual demonstrations.

Do not add general STEP/BREP modelling, arbitrary-language CAD, learned models,
simulation certification, autonomous manufacturing, or a new membership portal
to close these scores. Those are separate products/research programs with their
own specifications and acceptance evidence. Useful additions here are completed
semantic browser editing, actionable diagnostics, real browser regression tests
and the existing calibration/fit workflow—not unsupported claims of “PhD math.”

## Final publication audit — 2026-09-09

### Project and initial state

NeuroCAD serves makers and developers who need dimensioned plates, basic solids
and electronics-enclosure parts. Explicit requirements become editable projects,
canonical IR, OpenSCAD and optionally independently checked STL. Its objective is
a dependable local alpha with reviewable files and honest evidence boundaries.

The compiler, project revisions, calibration, topology, tolerance mathematics and
file-exchange contracts were functional. The starting working tree already held
an unfinished hardening pass covering semantic browser edits, request limits,
numeric robustness and browser testing. Those changes were preserved and tested
together. The retained research subsystem at local HEAD `d22172a` is included in
the current full suite. No learned-model result or physical trial was created.

### Highest-value findings and completed changes

| Priority | Finding / root cause | Implemented correction |
| --- | --- | --- |
| P0 | Rounded body cavities used rectangular lid plugs; identical extents and manifold topology missed the collision | Match plate/plug corner offsets to the body, add independent off-axis mesh probes and regression meshes that deliberately restore the wrong shape |
| P0 | Screw bores cleared the screw but left the insertion plug intersecting the larger boss ring | Cut boss relief below the screw-bearing plate; probe four ring locations per boss |
| P0 | Interior-height validation ignored insertion depth | Reserve plug depth when checking floor, standoffs and the declared PCB/component envelope; report conflicting dimensions |
| P1 | Rounded-box limits emitted empty geometry or rejected valid zero/tiny radii | Emit a cube at radius zero and a disk/capsule at maximum radius; permit derived corner radii below 0.1 mm while retaining overall solid-size limits |
| P1 | Fixed standoff floor overlap could extend below a thin specified floor | Bound attachment overlap by half the actual floor thickness |
| P1 | Kernel failure cleared validated source/project downloads | Retain output for unchanged input while preserving stale-response invalidation; test HTTP outage and real browser recovery |
| P1 | Alpha release command omitted prerelease classification; tag publication could bypass browser acceptance | Test actual shell arguments for alpha/RC/stable versions, use `--verify-tag`, prevent prereleases becoming latest stable, and require all three browsers before release |
| P1 | Sdist shipped tests without the helper modules they import | Include the five retained helpers in the sdist, keep the wheel scope unchanged, move two archival checks to a checkout-only test file, and execute extracted-sdist tests in CI/release |
| P1 | Full 1,000-program research stress run aborted when a structurally valid fixture exceeded exporter limits | Preserve the generated dataset; record export errors and failed determinism instead of aborting or silently replacing hard fixtures; add a release-sized regression |
| P2 | Archive safety checks missed ZIP symlinks, duplicate/case-colliding entries and Windows drive/stream paths | Reject those forms before release and cover each with hostile archives |
| P2 | Contributor command omitted some maintained lint/type inputs and allowed missing Node | Expand `scripts/test.sh` coverage and require its shipped Node harness inputs |
| P2 | External import acceptance was absent | Add and execute `scripts/check_blender_import.py` inside Blender; retain exact source hashes, settings, dimensions and scene |
| P3 | Security/release instructions described outdated overwrite behavior and release ordering | Correct `SECURITY.md`, release gates, quick start, architecture, contribution instructions and changelog; explain geometry compatibility/rebuild behavior |

There was no broad architecture rewrite. Runtime dependencies and the frozen
research evidence were preserved. Historical experiments remain excluded from
the distribution; legitimate exceptions, input placeholders and test doubles
were not mistaken for unfinished production features. This local tool has no
database, billing, acquisition funnel or outreach system to retrofit.

### Verification and measured results

Local platform: macOS 26.5.2 arm64, CPython 3.12.14, OpenSCAD 2021.01,
Playwright 1.62.0 and Blender 5.0.1. Detailed evidence is retained locally under
`.provenance/publication-20260909/`; it is excluded from the wheel and sdist.

- Complete checkout: `python -m pytest -q tests` — **498 passed**, no skips,
  233.65 seconds before the final research error-reporting regression; JUnit and console logs retained.
- Final corrected candidate, full extracted-source suite: **497 passed**, no
  skips, **296.50 seconds**. The two checkout-only archival checks passed
  separately. This run includes the new research regression and the workbench
  path where the earlier checkout process crashed. All 97 packaged source/test/
  configuration files compared against the working tree matched exactly.
- Extracted review sdist: **496 passed**, no skips; the two checkout-only archive
  tests are intentionally excluded. Fresh wheel and sdist installs, out-of-tree
  CLI checks and independently verified rounded-enclosure compilation passed.
- The review wheel and normalized sdist were byte-identical across two builds
  (**49 wheel members / 254 sdist members**). These predate the final research
  error-reporting fix and are not a tagged-release checksum claim.
- The corrected candidate was then rebuilt twice, again byte-identically;
  its archive SHA-256 values are recorded in the local evidence README.
  From that isolated source archive, **33 IR/research tests** and **30 UI-contract,
  release, packaging and installer tests** passed. These are separate runs, not
  numbers to add to the older complete-suite count.
- Real staged installer retry published both working launchers and passed doctor
  using separately resolved runtime dependencies. An earlier invocation stopped
  before publication; its log is retained, and the interruption was not reproduced.
- Syntax compilation and Ruff passed. Mypy passed across **63 maintained source
  files**, including the optional external-import script.
- `pip check` passed. Bandit reported no findings. `pip_audit` against the
  unchanged research lock reported no known vulnerabilities. The pattern scan
  inspected **1,619 current tracked/unignored files** and all local Git history,
  with no high-confidence secret matches; this is not an exhaustive secret proof.
- Final isolated browser run: **12 checks each** in Chromium, Firefox and WebKit,
  including actual saved/imported revisions, keyboard confirmation, an injected
  kernel outage, real mesh downloads, 320/390/768/1440px layouts, 200% CSS zoom,
  and a native leave-page warning. Desktop/mobile-width screenshots were inspected.
- Blender imported exactly **two meshes**. Body: **80 × 60 × 30 mm**; lid:
  **79.4 × 59.4 × 4.5 mm**, within the 0.001 mm import-check tolerance. STL has no
  embedded units, so the script explicitly uses a 0.001 import scale into metres.
- Full isolated controlled research campaign `NC-PUBLICATION-20260909-INTERNAL`:
  **240/240 kernel samples passed**, **240/240 compiler prompts semantically
  exact**, and **240/240 invalid cases rejected**. IR stress recorded **999/1,000
  successful exports**, preserving fixture 500's below-minimum torus radius as
  an explicit negative result. The run completed with a provenance manifest;
  it does not replace frozen evidence or imply physical/model validation.
- All local Markdown links in the 11 current entrypoint/product documents resolved.
- In 25 calls per fixture, warm median source-validation latency was **12.08 ms**
  for a plate and **8.74 ms** for an enclosure. Unsupported input was rejected
  in **0.17 ms** median and an oversized prompt in under **0.003 ms** maximum.
  These are local measurements under the audit workload, not universal budgets.

Retained failures matter: a sandboxed OpenSCAD case exceeded 120 seconds, then
passed with normal application access in a 35.52-second isolated test. Five new
lid/envelope regressions first failed on the original implementation and passed
after correction. During simultaneous kernel/browser testing, WebKit timed out
waiting for a stable click; the subsequent isolated three-browser run passed.
The unsuccessful browser trace is retained. Earlier mixed-source runs are not
used as final verification evidence.

A later concurrent checkout test/research rerun failed: Python terminated with
a native bus error while loading STL, and 34 of 240 OpenSCAD operations reported
`current_path: No such file or directory`. These are unsuccessful runs, not
passing evidence. The host was under heavy load with its internal disk 99% full;
this observation is not proof of the bus error's root cause. Final artifact
verification was moved to an isolated archive on internal storage. The final
isolated full suite and 240-sample kernel campaign passed; neither failure was
reproduced there, but the original host-level cause remains unproven. The final
research-only evaluator change is the sole core-source difference from the
successful three-browser receipt; it adds explicit export-error reporting.

### Remaining gates and quality assessment

GitHub was rechecked: repository **PRIVATE**, PR **#49 OPEN / DRAFT** at
`a870c12920483f66c98628fac92b892cdadab7f3`, nine prior checks successful, and no
published release listed. This audit does not make the local changes remotely
verified or publicly available. No merge, tag or visibility change was performed.

Remaining work, in impact order:

1. Commit/review the complete candidate and pass the remote platform/browser
   matrix on that revision; review geometry compatibility and the full diff.
2. Obtain owner approval for public visibility/merge, run the tag workflow and
   verify generated release provenance and anonymous installation.
3. Perform independent first-use and screen-reader/native-mobile acceptance.
4. Execute the existing physical-validation protocol with real equipment and
   participants before making physical-fit claims. Conference evidence remains
   **EVIDENCE_PARTIAL**; software tests cannot supply independent research results.

| Area | Current assessment /10 | Main remaining gap |
| --- | --- | --- |
| Functionality | 8.5 | Supported paths tested locally; independent users and more receiving applications remain |
| Engineering | 8.5 | Correctness substantially strengthened; complete assembly equivalence is outside the sampled oracle |
| Reliability | 8 | Remote final matrix and repeatability on other machines remain; transient WebKit failure disclosed |
| Design | 7.5 | Real desktop/responsive/keyboard coverage; human screen-reader and native-mobile review remain |
| Organization | 8 | Product/archive boundaries improved; extensive historical reports still require the documentation map |
| Documentation | 8.5 | Current setup, geometry, compatibility and release guidance updated; anonymous-install recipe still awaits publication |
| Maintainability | 8.5 | More meaningful regression/packaging gates; browser and release lanes need ongoing upkeep |
| Overall publication readiness | 7.5 | Local candidate ready for review; remote checks, approval and public-release receipts still open |

These are the audit author's engineering judgments, not independent scores or an
assertion that all eight targets reached nine. The broader unchecked acceptance
items above remain visible. No additional known high-impact code defect from this
audit is being deferred behind a cosmetic score.

### Exact operator commands

From a reviewed checkout (use a new virtual environment and new output paths):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev,security,browser]'
neurocad doctor
neurocad demo

PYTHON_BIN=.venv/bin/python sh scripts/test.sh
python -m bandit -q -r core research/vericodegen scripts neurocad_cli.py text_to_cad.py text_to_openscad.py
python -m pip_audit -r requirements-research.lock --no-deps --disable-pip
python -m playwright install chromium firefox webkit
python tests/browser/run_workbench.py --require-kernel --output /tmp/neurocad-browser-new

SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)
export SOURCE_DATE_EPOCH
python -m build --outdir /tmp/neurocad-dist-new
python scripts/normalize_sdist.py /tmp/neurocad-dist-new/neurocad_research-0.5.0a6.tar.gz "$SOURCE_DATE_EPOCH"
python scripts/verify_distribution.py /tmp/neurocad-dist-new/neurocad_research-0.5.0a6-py3-none-any.whl /tmp/neurocad-dist-new/neurocad_research-0.5.0a6.tar.gz

neurocad enclosure interpret "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm" --project-id controller --project-output controller.json
neurocad enclosure build controller.json --output-dir controller-built --stl
neurocad enclosure verify controller-built
neurocad integrations export controller.json --output-dir controller-exchange --stl
neurocad integrations verify controller-exchange
blender --background --factory-startup --python scripts/check_blender_import.py -- --bundle controller-exchange --output /tmp/neurocad-blender-new
```

Publication follows the ordered gates in `RELEASE_STATUS.md`; there is no cloud
deployment step for this local application. The hash-locked research reproduction
command remains `PYTHON_BIN=python3.12 scripts/reproduce_research.sh`. The local
campaign above was run from the isolated candidate archive with locked Python
dependencies using:

```bash
neurocad research --output /tmp/neurocad-research-new --run-id NC-PUBLICATION-NEW --compiler-tasks 240 --ir-programs 1000 --invalid-cases 240 --edit-cases 200 --constraint-ablation-cases 200 --kernel-samples 240 --fn 48 --require-kernel
```
