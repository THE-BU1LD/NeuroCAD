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
batch verification are included. Combined verification is pending.

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
| [#2](https://github.com/THE-BU1LD/NeuroCAD/issues/2) | RELEASE_EVIDENCE_EXISTS_PENDING_LIVE_RECONCILIATION | docs/verification/alpha-20261014/REPORT.md |
| [#5](https://github.com/THE-BU1LD/NeuroCAD/issues/5) | RELEASE_EVIDENCE_EXISTS_PENDING_LIVE_RECONCILIATION | docs/verification/alpha-20261014/REPORT.md |
| [#6](https://github.com/THE-BU1LD/NeuroCAD/issues/6) | HISTORICAL_CLAIM_AUDIT_REVIEW_REQUIRED | RESEARCH_TRUTH.md; EVIDENCE_LEDGER.md |
| [#7](https://github.com/THE-BU1LD/NeuroCAD/issues/7) | CLOSED_PREDECESSOR_EXTERNAL_SUCCESSOR_GATED | BASELINES.md; research/protocols/EXTERNAL_EVALUATION_V0.md |
| [#11](https://github.com/THE-BU1LD/NeuroCAD/issues/11) | RELEASE_EVIDENCE_EXISTS_PENDING_LIVE_RECONCILIATION | docs/verification/alpha-20261014/published/RELEASE_PROVENANCE.json |
| [#21](https://github.com/THE-BU1LD/NeuroCAD/issues/21) | EXTERNAL_AUTHORSHIP_AND_REVIEW_REQUIRED | Final independent benchmark and human labels absent |
| [#22](https://github.com/THE-BU1LD/NeuroCAD/issues/22) | BLOCKED_BY_BENCHMARK_PROVIDER_AND_BUDGET | No exact provider/revision/cost and human-reviewed benchmark freeze |
| [#27](https://github.com/THE-BU1LD/NeuroCAD/issues/27) | EXTERNAL_SESSION_RECORD_REQUIRED | No new retrospective evidence may be invented |
| [#36](https://github.com/THE-BU1LD/NeuroCAD/issues/36) | CANDIDATE_POOL_EXISTS_SELECTION_REVIEW_REQUIRED | 110 candidates are not a human-reviewed frozen final study |
| [#41](https://github.com/THE-BU1LD/NeuroCAD/issues/41) | EXTERNAL_USERS_AND_DESIGN_PARTNERS_REQUIRED | No completed external pilot supplied |
| [#42](https://github.com/THE-BU1LD/NeuroCAD/issues/42) | SEPARATE_FUTURE_SUCCESSOR | Requires defined fabrication process and physical evidence |
| [#44](https://github.com/THE-BU1LD/NeuroCAD/issues/44) | PROVENANCE_MAP_EXISTS_REVIEW_SCOPE | docs/HISTORICAL_VERTEXED_PROVENANCE.md |
| [#58](https://github.com/THE-BU1LD/NeuroCAD/issues/58) | REPOSITORY_ADMIN_POLICY_OPEN | main currently reports protected=false; independent reviewer not assigned |
| [#60](https://github.com/THE-BU1LD/NeuroCAD/issues/60) | RELEASE_EVIDENCE_EXISTS_PENDING_LIVE_RECONCILIATION | docs/verification/alpha-20261014/REPORT.md |
| [#64](https://github.com/THE-BU1LD/NeuroCAD/issues/64) | IMPLEMENTED_AWAITING_INTEGRATED_NATIVE_CHECKS | core/exact_cad.py; tests/test_exact_build123d.py |
| [#65](https://github.com/THE-BU1LD/NeuroCAD/issues/65) | IMPLEMENTED_BOUNDED_NATIVE_COVERAGE | core/gmsh_backend.py; tests/test_cad_mesh_native.py; reference suite |
| [#68](https://github.com/THE-BU1LD/NeuroCAD/issues/68) | IMPLEMENTED_AWAITING_INTEGRATED_CHECKS | core/requirement_verification.py; requirement verification tests |
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
