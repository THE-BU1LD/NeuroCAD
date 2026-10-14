# Advanced engineering completion checklist

Evidence audit: **PASS**. Overall completion: **False**.
Verified source: `079902fa20d22c2cf102104b0f42b28bec8bc382`. Current source matches: **True**.

Completed means the stated bounded acceptance criterion has retained evidence. Blocked and concurrent work remain open; software results do not close external gates.

- [x] **V01 — Preserve v2 and failed successors** (DONE)
  Acceptance: All 40 protected v2/release/paper file hashes retained; predecessor failures remain recorded.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V02 — Correct opposing-load beam stress** (DONE)
  Acceptance: Interior maximum and yield counterexample pass in the separately frozen successor.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V03 — Correct circular-shaft biaxial extrema** (DONE)
  Acceptance: Replace four-point sampling with the full circular boundary extremum; retain failed baseline.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V04 — Correct hole-boundary ligaments** (DONE)
  Acceptance: Use actual hole geometry rather than the configured grid margin; preserve the failure.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V05 — Expand composite reference checks** (DONE)
  Acceptance: 42 authored references cover shaft, polygon section/structural, perforated-plate integral and hole-distance cases.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V06 — Run isolated installed conformance** (DONE)
  Acceptance: 52/52 scalar and workflow checks with an isolated wheel and frozen inputs.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V07 — Compile composite meshes** (DONE)
  Acceptance: All four declared composite examples compile through the kernel.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V08 — Run maintained regression and source-distribution tests** (DONE)
  Acceptance: Maintained suite 1677 passed/9 skipped; extracted sdist 1658 passed/9 skipped.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V09 — Verify portable product and browser matrix** (DONE)
  Acceptance: The ten required jobs succeeded on exact merged commit 079902fa20d22c2cf102104b0f42b28bec8bc382.
  Evidence: `docs/verification/composite-final-20261014/main-run.json` (SHA-256 `53919897f401c5493c8010896766e872e6022e5d19bf525346f1692ad587570c`).

- [x] **V10 — Pass native integration baseline** (DONE)
  Acceptance: 106 exact CAD tests, 174 native checks; bounded authored fixtures only.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V11 — Reconcile repair history and review/merge** (DONE)
  Acceptance: Integrated correction is merged as PR109; historical repair PR dispositions retained.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V12 — Preserve published alpha identity** (DONE)
  Acceptance: v0.5.0a6 remains immutable; do not call main-only repairs a new published version.
  Evidence: `docs/verification/composite-final-20261014/SUMMARY.json` (SHA-256 `5db41b0bdc67a92f5bfad4e43b776192df4a8481006a89fb7d0b1210da5c803a`).

- [x] **V15 — Make checklist claims executable** (DONE)
  Acceptance: 13 fault-injection/CLI tests pass; evidence hashes and JSON values are checked; incomplete work and source drift cannot pass the completion gate.
  Evidence: `docs/verification/readiness-20261014/implementation.json` (SHA-256 `7d88aecca4fb6c6abd5dfa5469e3574aed799f1dea0ba49e87ede5b6a0c6e540`).

- [ ] **V13 — Complete expanded native platform acceptance** (IN_PROGRESS)
  Acceptance: Exact-CAD goldens and tagged beam/plate/enclosure meshes pass on Linux, macOS and Windows; final source and preservation checks merge.
  Blocker/current state: Active PR110 has a failing Windows native acceptance job at c2776fa; its product matrix passed. The owning worktree has a workflow repair in progress.
  Next action: Finish the active native session and import its exact final receipts; do not edit its worktree concurrently.

- [ ] **V14 — Ship a corrected immutable release** (BLOCKED)
  Acceptance: New reviewed tag, wheel/sdist checksums, provenance and anonymous installation receipts include the fixes.
  Blocker/current state: Final native source is still being finalized; the old immutable alpha cannot be replaced.
  Next action: After final candidate checks and merge, version and publish a new alpha, then verify both public installation paths.

- [ ] **E01 — Measure physical accuracy** (BLOCKED)
  Acceptance: Predeclared predicted-versus-measured limits pass with calibration and uncertainty records.
  Blocker/current state: No physical apparatus, operator or measurement dataset is supplied.
  Next action: An experimenter completes and freezes the external physical plan before collecting real measurements.

- [ ] **E02 — Obtain independent reproduction** (BLOCKED)
  Acceptance: A distinct executor runs the frozen package, retains raw results and reviews discrepancies.
  Blocker/current state: Our CI and authored references are not independent execution.
  Next action: Supply an independent executor and their unedited reproduction artifacts.

- [ ] **E03 — Run intended-user and accessibility tasks** (BLOCKED)
  Acceptance: Real intended users complete representative tasks and interpret assumptions correctly; observed defects are resolved.
  Blocker/current state: No participants, consent records, screen-reader or native-device user evidence is supplied.
  Next action: Recruit intended users and execute the prepared usability protocol; retain failures and interventions.

- [ ] **E04 — Author and review the held-out benchmark** (BLOCKED)
  Acceptance: 120 independently authored/reviewed tasks, duplicate audits and freeze receipts satisfy issues 21/36.
  Blocker/current state: Independent task authorship and human review cannot be substituted with evaluated-agent generation.
  Next action: Provide reviewed tasks and sign-off; retain frozen predecessors and use a separate successor.

- [ ] **E05 — Execute matched baseline research** (BLOCKED)
  Acceptance: Provider/model identities, prompt/seed/budget manifest and benchmark freeze are reviewed before calls (issues 7/22).
  Blocker/current state: Held-out benchmark, exact provider and cost authorization are missing.
  Next action: Complete E04, select and approve the provider/model and bounded cost, then freeze the baseline matrix.

- [ ] **E06 — Run external CAD/dirty-CAD cases** (BLOCKED)
  Acceptance: Licensed exact inputs, original baseline, repair copy and separate meshing results exist (issues 76/78).
  Blocker/current state: External geometry, license/tool access or confirmed invariants are absent.
  Next action: Obtain the exact public/licensed assets and approved invariants before executing the retained capture protocols.

- [ ] **E07 — Close industrial pilot claims** (BLOCKED)
  Acceptance: Reconstructable external reviewer tasks and outcomes support issue 27/41 conclusions.
  Blocker/current state: No reviewer-authored outcomes or customer acceptance evidence is available.
  Next action: Collect consented external cases and retain critiques; do not infer endorsement from correspondence.

- [ ] **E08 — Close paper and provenance gaps** (BLOCKED)
  Acceptance: Every paper-facing claim maps to preserved evidence; missing historical artifacts remain marked missing (issues 6/82).
  Blocker/current state: External outcomes and one historical run log remain unavailable; native provenance follow-up is concurrent.
  Next action: Retain the missing-log limitation; finish source-bound provenance review, then draft new results only from supplied evidence.

Run `python3 scripts/audit_v3_readiness.py` to check the machine-readable inventory. Use `--require-complete` for a gate that refuses open work or source drift.

Scope: the advanced engineering readiness request. The 109 earlier expansion proposals remain a separate product backlog; implementing FEA/CFD or inventing external study results is not implied by this checklist.
