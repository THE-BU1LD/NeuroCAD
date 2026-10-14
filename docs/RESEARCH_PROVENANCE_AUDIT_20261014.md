# Retained compiler provenance audit — 14 October 2026

The source-bound controlled compiler result remains bounded engineering
evidence. This audit reads retained files; it does not rerun or reopen the
terminal study, change its outcomes, or constitute independent reproduction.

`research/development/result_timing_v2_20261014/retained_artifact_audit.json`
records a fresh check of the `NC-REPRO-508EC40` manifest: **1,211 present artifacts
match their hashes; one listed artifact, `logs/run.log`, is missing** from the
local retained copy. The original manifest, numerical results and files remain
unchanged. No replacement log has been invented. Full archival completeness is
therefore not established by this audit.

The manifest identifies clean source
`508ec404dd520ae16f2b4d3cf211d5b1fa46b800`, capture time
`2026-09-13T14:21:56.198647Z`, dataset hash
`4460b8e88b36127149c006ce1aad3d74a06b2d8f7b34c58b70e51d31a08c9314`,
seed `20260902`, CPython 3.12.14, macOS ARM64 and OpenSCAD 2021.01. Configuration
and source/lock/result digests are retained in the audit JSON. A detailed CPU/RAM
identity or independently witnessed execution command is not inferred.

| Maintained result | Retained experiment | Falsifier / boundary |
|---|---|---|
| 240/240 compiler exact matches; baseline counts 144/130/110/0 | NC-EXP-001 | Any contract mismatch defeats perfect conformance; generated grammar only |
| 1,000/1,000 static program checks | NC-EXP-002 | Any structural/roundtrip/export failure; no kernel claim for these 1,000 |
| 240/240 malformed fixtures rejected | NC-EXP-003 | Any malformed fixture accepted; eight designed categories, not population inference |
| 200/200 constraint detections versus 0/200 without constraints | NC-EXP-004 | Missing detections or no paired advantage; no inferred intent |
| 200/200 automated edits | NC-EXP-005 | Any declared edit fails; no human usability evidence |
| 240/240 freshly compiled kernel cases | NC-EXP-006 | Kernel/topology/extents failure or artifact reuse; no physical validation |
| Depth 128 accepted, 129 rejected | NC-EXP-007 | Contract-bound failure; constructed stress only |

The original `neurocad-deterministic-results-v1` artifact incorrectly retains
`mean_edit_validate_export_ms` and `validate_export_ms` (ten values). Its digest
still identifies those exact bytes, but is **not timing independent**. The
observed fields and original hashes are preserved in
`contract_and_baseline.json`. New format `neurocad-deterministic-results-v2`
moves both fields into runtime metadata. Regression checks change only timing
and verify invariant outcome serialization, then change correctness and verify
that the outcome serialization changes. Historical artifacts are not migrated.

Issue #6 remains open for full research-wide claim/provenance reconciliation
and the missing original log. Issue #7 remains open for a compatible strong
external comparator and the independently authored evaluation; the four simple
controlled baselines do not establish superiority to modern learned CAD
systems. VeriCodeGen/S3 protected authoring, authorization and provider gates
remain unchanged. Physics v2 retains its separate frozen evidence; native mesh
and Physics v3 software checks do not supply physical or independent evidence.
