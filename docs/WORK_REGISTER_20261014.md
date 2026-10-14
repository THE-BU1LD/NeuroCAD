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
