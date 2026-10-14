# Current six-gate implementation checklist

Updated 14 October 2026 for the request to implement every unblocked item.
This is the current checklist; the dated audit stages below retain earlier
observations. Checked means the stated, bounded action has evidence, not that
the whole scientific gate is complete. The implemented successor is merged in [PR110](https://github.com/THE-BU1LD/NeuroCAD/pull/110).

## 1. Freeze the validation contract — completed for the declared software envelope

- [x] Specify each supported model, exclusions, reference derivation, units,
  per-case tolerance and all-case pass criteria in versioned protocols.
- [x] Preserve v2 and previous failures. v3 successors v1–v5 retain their own
  source identities; the latest physics freeze binds 98 inputs and 40 protected
  historical files. It is not silently rebound to later source.
- [x] Freeze the separate native acceptance cases and tolerances before running
  five CAD goldens and repeated beam/plate/enclosure meshes.
- [x] Enforce byte-for-byte historical preservation before and after native
  acceptance; configure Windows checkout to preserve committed bytes.
- [x] Prepare separate external collection plans, mandatory provenance,
  pre-outcome freeze and no-overwrite audit commands in
  [external_validation_v1](../research/physics_v3/external_validation_v1/README.md).

## 2. Verify calculations — completed for the declared sampled software envelope

- [x] Run the 37 scalar reference cases, including ordinary/limiting inputs,
  rejected invalid states and numerical singularities; retain per-case errors.
- [x] Repair the opposing-load beam interior maximum, biaxial shaft maximum
  and centered-hole ligament calculation; retain their original failures.
- [x] Add 42 composite reference cases for shaft, I/L sections and perforated
  plates using independently derived analytical/polygon calculations.
- [x] Verify finite arithmetic, interval division, uncertainty, units and mesh
  normalization through the integrated maintained regression suite.
- [x] Verify five exact solids against analytic dimensions/volumes and compute
  tetrahedral mesh volume through the separate retained reference verifier.
- [x] Repair deterministic result extraction: actual edit/hierarchy timing
  fields now go into runtime metadata in format v2; preserve old v1 bytes.
- [x] Add a reusable read-only artifact auditor that reports missing, altered,
  unsafe and duplicate manifest entries; it cannot repair or synthesize evidence.
- [ ] **Blocked:** complete historical archival provenance for issue #6:
  recover authentic `logs/run.log` files for all four retained compiler runs and
  any missing original hardware/execution records. All present listed artifacts
  match; no absent log is reconstructed. See [provenance audit](RESEARCH_PROVENANCE_AUDIT_20261014.md).
- [ ] **Blocked:** strong external comparator/independently authored benchmark
  for issue #7. Closed generated-grammar outcomes do not establish superiority
  to current learned CAD systems.

## 3. Validate CAD-to-analysis workflows — completed for the declared installed-build envelope

- [x] Exercise fresh installed packages through 52 cases/workflows: four complex
  composite shapes, dimensions, materials, loads, units, geometry binding,
  uncertainty, overlays and stale-result invalidation. Four meshes compiled.
- [x] Integrate all 17 original repair PR histories; verify package installation,
  browser editing and portable operating-system behavior on exact source.
- [x] Implement source-hash-bound planar semantic mesh groups, strict selectors,
  deterministic Gmsh settings and independent serialized group verification.
- [x] Record exact OpenCascade kernel identity and reject forged/missing revision
  provenance; correct Windows canonical JSON newline hashing.
- [x] Execute five native goldens plus six meshing runs on each of Linux/macOS/
  Windows; candidate bf4cdca passed 182 native/rejection tests per platform.
- [x] Verify final candidate `518208b` after the Windows preservation fix: all
  ten product jobs, three native jobs and interoperability pass. Failed and
  cancelled attempts remain retained; 40 protected files match on every OS.
- [x] Add all three native platform jobs to the existing ten required checks;
  merge PR110 normally as `0bef391`. Its tree exactly matches tested `518208b`.
- [x] Confirm merged-main CI38577282155, retain the final receipt, reconcile
  issue dispositions and update project/portfolio state. Immutable v0.5.0a6
  remains a separate, older published source identity.
- [ ] **Blocked locally:** native builds/meshes require two stable memory
  admission samples; observed 112.72/92.16 MiB versus the 512 MiB floor with
  rising pageouts. Hosted verification covers this engineering work.

## 4. Establish physical accuracy — collection tooling complete; measurements blocked

- [x] Prepare capability-specific plan/evidence schemas, calibration and
  uncertainty fields, frozen case lists and negative-result retention.
- [ ] **Blocked:** identify experimenter, apparatus and calibration records;
  choose the claimed beam/thermal/vibration/pressure capabilities and conditions.
- [ ] **Blocked:** freeze real procedures, assumptions, tolerances, repetitions
  and measurement uncertainty before collecting outcomes.
- [ ] **Blocked:** execute experiments, retain predictions and raw measurements,
  compare within declared uncertainty, investigate discrepancies and publish
  the observed applicability envelope. No measured results have been supplied.

## 5. Obtain independent reproduction — handoff tooling complete; executor blocked

- [x] Prepare clean-install instructions, source/package hashes, frozen cases,
  discrepancy retention and an integrity auditor that refuses empty evidence.
- [ ] **Blocked:** obtain an executor outside the implementation effort, their
  clean environment and identity/independence declaration.
- [ ] **Blocked:** have that executor run the frozen cases, retain original
  outputs and submit their discrepancy report. Hosted project CI is internal
  engineering evidence and does not satisfy this gate.

## 6. Verify practical usability — product checks complete; intended users blocked

- [x] Implement worked examples, explicit supported boundaries, material/load
  checks, stale-result warnings and browser-level edit/import/export acceptance.
- [x] Prepare frozen task plans and per-participant evidence/rubrics for material,
  load and unit entry, error recovery, limitations and screening-result meaning.
- [ ] **Blocked:** recruit intended users with consent and freeze representative
  tasks/success criteria before observing their performance.
- [ ] **Blocked:** record task completion/errors/interpretation, fix observed
  usability defects and repeat the affected tasks with retained observations.

## Other tracked dependencies and scope

Issues #21/#22/#36 require independent benchmark authorship, human review and
provider/budget decisions; #27 requires authentic historical session records;
#41 requires actual design partners/users; #42 requires a defined fabrication
process and physical evidence; #76 requires external reference confirmation;
#78 requires genuine licensed geometry and Cubit access; #82 requires measured
evidence, authorship and publication decisions. Issues #64/#65 are closed after the verified PR110 merge. Eleven issues remain
open for the documented evidence/data/authority dependencies. Concurrent PR111
adds a separate executable readiness checklist pinned to earlier source `079902f`;
it currently has merge conflicts with new main. Its source reconciliation and
CI belong to that active work, which is preserved and not claimed complete.

The 109 separately inventoried expansion proposals remain proposed future
scope, not automatically added current-release requirements. No paid provider
run, external message, physical result, independent review or new public release
is implied by this checklist. The software work cannot fill those evidence gaps.

# Prior closure (superseded for current native work)

PR109 is merged and exact-main CI passed. All 17 originally open PR histories are included; no PR remains open. Seven issues are closed. See [the final receipt](verification/composite-final-20261014/REPORT.md) for the 1,677-test outcome, 42 new composite references, retained failures and 13 remaining issues. Earlier audit stages below are retained chronologically and superseded where this receipt states completion.

# NeuroCAD work register — 14 October 2026

This register accounts for every open GitHub issue and PR observed at audit,
plus every unchecked expansion proposal. It preserves completed/failed studies
and distinguishes implementation, verification, external evidence and future
scope. The expansion checklist itself says those proposals do not silently
expand current-alpha requirements.

## Integration work

The isolated candidate combines PRs 88–102 and 105–106, preserving their commits,
regressions, native reference artifacts and failure receipts. Output ownership,
daemon shutdown/recovery, numerical diagnostics, interval division, Monte Carlo
summary arithmetic, quantity conversion, mesh normalization and complete Gmsh
batch verification are included. Combined verification passed at e71b63c: 1,632 maintained tests, all required operating systems and browsers, fresh packages, exact CAD/Gmsh and 37/52 scalar/installed conformance checks. See [the receipt](verification/work-closure-20261014/REPORT.md).

Conflict resolutions preserve the alpha no-overwrite default and original
integer identity checks. Nonzero unrepresentable products/ratios now raise
instead of producing misleading zero reports. Two inherited tests now enforce
that stricter contract; their earlier expectations remain in parent history.

Repository-only frozen-harness tests are excluded from source distributions
because their study artifacts are not shipped. Their tests still run from the
checkout and the conformance workflows; product coverage is retained.

## Open issue routing

| Issue | Status | Evidence or next dependency |
|---|---|---|
| [#2](https://github.com/THE-BU1LD/NeuroCAD/issues/2) | CLOSED_VERIFIED_RELEASE | Live immutable alpha metadata and original release/anonymous CI rechecked. |
| [#5](https://github.com/THE-BU1LD/NeuroCAD/issues/5) | CLOSED_VERIFIED_RELEASE | Clean-install receipts remain bounded to published v0.5.0a6. |
| [#6](https://github.com/THE-BU1LD/NeuroCAD/issues/6) | HISTORICAL_CLAIM_AUDIT_REVIEW_REQUIRED | RESEARCH_TRUTH.md; EVIDENCE_LEDGER.md |
| [#7](https://github.com/THE-BU1LD/NeuroCAD/issues/7) | CLOSED_PREDECESSOR_EXTERNAL_SUCCESSOR_GATED | BASELINES.md; research/protocols/EXTERNAL_EVALUATION_V0.md |
| [#11](https://github.com/THE-BU1LD/NeuroCAD/issues/11) | CLOSED_VERIFIED_RELEASE | Live asset digests match retained provenance/checksums. |
| [#21](https://github.com/THE-BU1LD/NeuroCAD/issues/21) | EXTERNAL_AUTHORSHIP_AND_REVIEW_REQUIRED | Final independent benchmark and human labels absent |
| [#22](https://github.com/THE-BU1LD/NeuroCAD/issues/22) | BLOCKED_BY_BENCHMARK_PROVIDER_AND_BUDGET | No exact provider/revision/cost and human-reviewed benchmark freeze |
| [#27](https://github.com/THE-BU1LD/NeuroCAD/issues/27) | EXTERNAL_SESSION_RECORD_REQUIRED | No new retrospective evidence may be invented |
| [#36](https://github.com/THE-BU1LD/NeuroCAD/issues/36) | CANDIDATE_POOL_EXISTS_SELECTION_REVIEW_REQUIRED | 110 candidates are not a human-reviewed frozen final study |
| [#41](https://github.com/THE-BU1LD/NeuroCAD/issues/41) | EXTERNAL_USERS_AND_DESIGN_PARTNERS_REQUIRED | No completed external pilot supplied |
| [#42](https://github.com/THE-BU1LD/NeuroCAD/issues/42) | SEPARATE_FUTURE_SUCCESSOR | Requires defined fabrication process and physical evidence |
| [#44](https://github.com/THE-BU1LD/NeuroCAD/issues/44) | PROVENANCE_COMPLETED_PENDING_MERGE | 157 source entries, repository-wide text/path inventory, exact object identity checks; prior manifests unchanged. |
| [#58](https://github.com/THE-BU1LD/NeuroCAD/issues/58) | CLOSED_MAIN_PROTECTION_ENABLED | Ten strict required checks, mandatory PR, admin enforcement; zero approving reviews because only one write collaborator. |
| [#60](https://github.com/THE-BU1LD/NeuroCAD/issues/60) | CLOSED_VERIFIED_RELEASE | Original release and current integrated software receipts retained separately. |
| [#64](https://github.com/THE-BU1LD/NeuroCAD/issues/64) | BOUNDED_NATIVE_SUITE_PASS | 106 exact CAD tests passed on Linux. Full spike golden-shape/platform acceptance remains separately scoped. |
| [#65](https://github.com/THE-BU1LD/NeuroCAD/issues/65) | BOUNDED_NATIVE_SUITE_PASS | 174 interoperability tests and retained references passed; do not claim every requested shape or platform. |
| [#68](https://github.com/THE-BU1LD/NeuroCAD/issues/68) | CLOSED_VERIFIED_REQUIREMENT_BINDING | Main source unchanged; full native requirement/revision adversarial tests passed. |
| [#76](https://github.com/THE-BU1LD/NeuroCAD/issues/76) | EXTERNAL_REFERENCE_CONFIRMATION_REQUIRED | Cannot contact WayKen without explicit communication instruction |
| [#78](https://github.com/THE-BU1LD/NeuroCAD/issues/78) | EXTERNAL_DATA_LICENSE_AND_TOOL_ACCESS_REQUIRED | Actual source geometry, permissions and Cubit availability unresolved |
| [#82](https://github.com/THE-BU1LD/NeuroCAD/issues/82) | EXTERNAL_EVIDENCE_AND_AUTHORSHIP_REQUIRED | Physical-world manuscript cannot claim measurements not collected |

All 109 unchecked expansion items are individually retained in
[the machine-readable register](verification/work-closure-20261014/WORK_REGISTER.json).
They include future capabilities and research directions; no capability is
claimed implemented by this inventory.

## External gates

Physical experiments, an independent executor and intended users are absent.
The external_validation_v1 package is prepared but its null templates cannot
pass freeze or evidence admission. Existing terminal science remains closed.
No partner message, paid provider call, third-party attribution or submission
is authorized merely by this implementation request.

## Remaining implementation coverage

The software pass is bounded. Add independently derived references for all composite section properties and structural outputs; finish the exact-CAD spike's full golden-shape/platform acceptance; extend native mesh references to the complete requested plate/enclosure/beam matrix. These remain software work, separate from the external gates. Review/merge PR107 before treating its repairs as main or a release.

## Later circular-shaft coverage finding

The e71b63c software receipts remain valid for their declared cases, but a broader review then found a missing biaxial-shaft maximum. The original pure-function baseline passed 2/6 and failed 4/6 declared analytical cases, including a false yield pass. A separate correction, 14 public-builder references and source-bound validation_v4 are now pending hosted verification on codex/neurocad-shaft-reference-20261014. This supersedes review-readiness of PR107; the original candidate must not be released with that known defect.

## Final composite reference candidate

The shaft successor at 9231aab passed the full hosted matrix (38564024326), conformance (38564015307) and native backend checks (38564024276). Its source remains preserved. A final v5 source contract additionally corrects single-row/column hole ligaments, with eight exact distance checks, and adds 20 independent polygon/signed-area reference cases. Together with the 14 shaft cases these cover all four declared composite families over the selected inputs. Tests remain project-authored calculations, not physical or independent-executor evidence. The final candidate is codex/neurocad-composite-final-20261014; its hosted checks are the outcome authority. PR107 and PR108 are superseded and must not be released as final candidates.

The broader composite-reference action above is now implemented for the declared sampled envelope. Unsupported arbitrary geometry, new shape/platform acceptance, physical trials and external studies remain open.
