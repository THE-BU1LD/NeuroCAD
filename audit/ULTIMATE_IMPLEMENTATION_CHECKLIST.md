# Ultimate implementation and research checklist

**Status date:** 2026-09-08
**Rule:** check an item only when its stated verification exists. `P0` affects
truth/correctness, `P1` conference validity, `P2` meaningful quality, `P3` optional.

## 1. Pseudocode, fake work, and scaffolding inventory

- [x] **P0 — supported fake implementation removed.** Historical marker-text STEP
  export is hard-disabled and kept only in `legacy/`. Verify: packaging excludes
  `legacy/`; integrity test rejects fake STEP markers in supported source.
- [x] **P0 — learned-model claim removed.** `model/` contains no checkpoint/training
  system and is documented as such. Verify: claim ledger prohibits learned results.
- [x] **P0 — VeriCodeGen scaffolding classified.** Stage 1 is real plumbing with
  scripted fixtures, not a model experiment; S3 is pre-outcome and unauthorized.
  Verify: execution gate rejects example/unauthorized manifests.
- [x] **P1 — ordinary optional returns inspected.** Canonical `return None` paths
  represent parse misses/probe absence, not silent success. Verify: callers convert
  absence into explicit invalid reports where required.
- [ ] **P1 — archive-level pseudocode inventory incomplete.** `legacy/` contains
  abandoned, incompatible, and import-active prototypes. Action: generate a
  hash-preserving archive index by capability/failure class. Done: every legacy
  entry is classified without importing or repairing it.
- [ ] **P2 — native integrations are handoff-only.** Fusion/Onshape/FreeCAD/Blender
  and slicer records do not create native documents. Action: retain precise labels;
  implement only one versioned integration after a real acceptance protocol. Done:
  target app imports exact artifact and receipt records observed outcome.

## 2. Bad or risky implementations

- [x] **P0 — fail-open geometry defaults addressed.** Unsupported and underspecified
  prompts fail explicitly. Done: negative tests cover features, signed dimensions,
  counts, unknown operators, nonfinite values, and bounds.
- [x] **P0 — static validity is not called kernel validity.** Done: distinct fields
  and real STL tests.
- [x] **P0 — artifact overwrite/staleness guarded.** Done: atomic writes, collision
  refusal, source/config hashes, and bundle re-verification tests.
- [x] **P0 — research resume risk repaired for future runs.** `force_recompile=True`
  and new-output enforcement. Done: manifest records zero reuse for fresh run.
- [ ] **P0 — historical FULL cannot be rehabilitated.** Action: never promote it to
  confirmatory. Done only when a clean published revision produces a new full run.
- [ ] **P1 — monolithic ownership.** `neurocad_cli.py`, `core/enclosure.py`, and
  `core/research_suite.py` mix orchestration and domain logic. Action: extract only
  stable cohesive boundaries, preserving APIs and frozen experiment semantics.
  Done: complexity decreases and all compatibility tests pass.
- [ ] **P1 — semantic evaluator is deliberately narrow.** Action: add reviewed
  full-program or geometry-equivalence checks for future benchmark families. Done:
  equivalence metric rejects same-extents/wrong-feature counterexamples.
- [ ] **P1 — render availability is coupled to full research success.** This is
  correct for artifact completeness but fragile on macOS/headless hosts. Action:
  preflight an actual PNG render before expensive cases and report a distinct
  environment failure. Done: preflight fails in seconds with retained diagnostics.
- [ ] **P2 — root compatibility modules.** Action: map live imports and deprecate or
  move noncanonical modules without breaking console entry points. Done: one
  implementation per supported responsibility.

## 3. Scientific validity

- [x] **P0 — central question narrowed.** Controlled compiler correctness, not AI
  reasoning. Evidence: `research/HYPOTHESES.md`.
- [x] **P0 — statistical unit corrected.** Task/program is the unit; malformed
  repetitions have no population interval. Done: future generator uses unique
  hashed fixtures.
- [ ] **P1 — independent benchmark.** Build a blinded, independently authored,
  licensed prompt/spec set outside compiler templates. Done: freeze content/hash,
  exclusions, and scoring before current-source outcome access.
- [ ] **P1 — strong compatible baseline.** Add a grammar-independent code/CAD
  generator or parser with equal information, kernel, timeout, and evaluation.
  Done: raw outputs/failures and compute/provider provenance retained.
- [ ] **P1 — real component ablations.** Isolate unit normalization, named versus
  positional dimensions, feature parsing, constraints, and fail-closed validation.
  Done: tests prove each switch changes only intended computation.
- [ ] **P1 — multiple-comparison policy.** Apply Holm correction to confirmatory
  secondary comparisons. Done: raw and adjusted p-values generated from records.
- [ ] **P1 — leakage audit.** Search prompt/spec near-duplicates across authoring,
  development, and confirmatory sets. Done: frozen receipt lists exact and reviewed
  near-duplicate decisions.
- [ ] **P1 — external replication.** Done: independent machine/researcher reproduces
  from public tag and reports matching deterministic outcomes or retained mismatch.

## 4. Robustness, OOD, and failure science

- [x] **P1 — immutable development challenge.** Stored and executed 24 unique
  accepted/rejected cases with dataset and evaluator hashes; 24/24 passed. Boundary:
  audit-authored after implementation inspection, not independent confirmation.

- [ ] **P1 — paraphrase robustness.** Predeclare in-scope lexical variations and
  meaning-preserving perturbations. Done: curves separate supported grammar from
  explicit rejection; no post-outcome grammar editing.
- [ ] **P1 — unsupported-input false acceptance.** Use adversarial out-of-scope CAD
  requests. Done: zero silent approvals with confidence interval at request level.
- [ ] **P2 — numeric boundary matrix.** Sweep minimum/maximum dimensions, aspect
  ratios, tolerances, feature proximity, and CSG degeneracy. Done: all failures are
  classified and no NaN/partial artifact appears.
- [ ] **P2 — kernel/version shift.** Compare pinned OpenSCAD platforms/versions.
  Done: deterministic scientific outcomes and mesh differences reported separately.
- [ ] **P2 — enclosure fault injection.** Extend existing missing/moved/filled/wrong
  part faults across every supported face/feature. Done: independent verifier catches
  all predeclared faults without generator metadata.
- [ ] **P2 — negative-result localization.** For every failed regime, identify the
  smallest responsible stage and whether rejection is preferable to repair. Done:
  failure taxonomy and examples are generated from raw records.

## 5. Mathematics and mechanisms

- [x] **P1 — formal compiler/IR semantics added.** Evidence:
  `research/MATHEMATICAL_SPEC.md`.
- [ ] **P1 — geometry semantics completeness.** Formalize primitive parameter
  domains, Boolean empty-set behavior, tolerances, and bounds approximation. Done:
  executable property tests correspond to each definition.
- [ ] **P1 — constraint intervention.** Remove, randomize, freeze, and substitute
  constraints under identical corruptions. Done: only semantically relevant
  constraints receive causal credit.
- [ ] **P2 — numerical conditioning.** Construct near-coincident CSG and resolution
  sweeps. Done: stability envelope states kernel/version/tolerance boundaries.
- [ ] **P2 — complexity measurement.** Measure parse/validate/export and kernel
  scaling separately over prompt length, nodes, depth, and facets. Done: raw repeated
  timings, hardware, warmups, and uncertainty retained.
- [ ] **P3 — do not add learned objectives gratuitously.** A model/loss/gradient
  study is allowed only under a new falsifiable hypothesis, dataset, multi-seed
  protocol, checkpoint policy, and compute authorization.

## 6. Product and physical evidence

- [x] **P1 — bounded enclosure workflow implemented.** Typed projects, edits,
  preflight, body/lid artifacts, verification, calibration helpers, and handoffs.
- [ ] **P1 — human usability.** Run the frozen human protocol with representative
  users. Done: task success, interventions, time, failures, and exclusions retained.
- [ ] **P1 — physical fit.** Print coupons and held-out enclosures under a versioned
  process. Done: measured outcomes, failed fits, printer/material/settings, and
  source hashes retained. `EXTERNAL_EXECUTION_REQUIRED`.
- [ ] **P1 — safety/manufacturing boundary.** Keep qualified review mandatory.
  Done: no UI/report implies certification from mesh or heuristic preflight.
- [ ] **P2 — protected interfaces.** Add connector/mount locks and conflict reports
  across edits. Done: accepted/rejected multi-edit chains preserve prior valid state.
- [ ] **P2 — slicer evidence.** Integrate one pinned slicer and compare estimates to
  actual jobs. Done: settings, logs, tool version, and failure state retained.

## 7. Abstraction and cleanup

- [ ] **P1 — experiment primitives.** Extract manifest hashing/verification and
  statistical record analysis from orchestration without changing experiment IDs.
  Done: unit tests cover reusable APIs and historical files remain immutable.
- [ ] **P1 — CLI command modules.** Separate enclosure, integration, research, and
  basic compiler handlers behind the existing entry point. Done: help/exit/output
  compatibility tests pass.
- [ ] **P2 — enclosure modules.** Separate schema/model, validation, geometry build,
  and verification. Done: no circular imports and independent fault tests remain.
- [ ] **P2 — representation boundary.** Document `DesignGraph` to canonical IR
  information loss and consider direct IR construction. Done: property tests prove
  round trips or explicitly enumerate loss.
- [ ] **P2 — generated/cache junk.** Keep caches/build directories ignored and out
  of distributions. Done: clean clone and archive verifier contain none.
- [ ] **P3 — legacy size.** Consider a Git tag/LFS archival release only if forensic
  hashes and discoverability are preserved. Never delete negative evidence merely
  to make the tree look clean.

## 8. Canonical automation

- [x] **P0 — preflight:** `scripts/preflight.sh`.
- [x] **P0 — tests/static checks:** `scripts/test.sh`.
- [x] **P0 — real kernel smoke:** `scripts/run_smoke.sh`.
- [x] **P1 — development/frozen runner:** `neurocad research` and
  `scripts/reproduce_research.sh`.
- [x] **P1 — analysis summary:** `scripts/analyze.sh`.
- [x] **P1 — artifact hash verification:** `scripts/verify_artifact.sh`.
- [ ] **P1 — manuscript generation.** Generate every numeric table/figure from one
  selected manifest and fail on unsupported claim IDs. Done: paper build has no
  hand-copied quantitative cells.
- [ ] **P1 — clean-clone release rehearsal.** Done: wheel/sdist built twice,
  byte-compared, installed outside checkout, tested, and provenance retained.

## 9. Release and external gates

- [ ] **P1 — clean exact revision.** Commit reviewed changes and ensure clean tree.
- [ ] **P1 — hosted CI.** Exact commit passes Linux/macOS/Windows gates; Linux runs
  OpenSCAD under Xvfb. `EXTERNAL_EXECUTION_REQUIRED`.
- [ ] **P1 — immutable release.** Publish tag/artifacts/provenance and anonymously
  install exact wheel. `EXTERNAL_EXECUTION_REQUIRED`.
- [ ] **P1 — confirmatory freeze.** Complete every blank in
  `research/protocols/FROZEN_CONFIRMATORY_V1.md`, sign/hash it, then expose outcomes.
- [ ] **P1 — evidence promotion.** Promote only a fresh, non-resumed, source-bound
  run; preserve null/negative results unchanged.

## 10. Completion gate

- [ ] Full suite, Ruff, mypy, dependency, and security checks pass on final source.
- [ ] Smoke and small development run pass with fresh kernel artifacts.
- [ ] Full frozen run passes or yields a retained scientifically interpretable
  negative result.
- [ ] Raw data generate all reported statistics/figures/tables.
- [ ] Public exact revision and independent reproduction exist.
- [ ] Claims, paper, truth ledger, and evidence ledger agree.

Until all P0/P1 scientific and external gates close, the maximum honest verdict
remains **EVIDENCE_PARTIAL**.
