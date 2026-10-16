# Frozen repair specification and evidence boundary

This engineering successor starts from committed integration candidate `3e26da5542541cc38ea518363d247b81b5964f73`. The dated JSON contract and initial 31 tests precede production edits. The neighboring integration checkout has live parser/native-test edits; this isolated branch owns only the ledger, its tests and its documentation/evidence.

The mechanism is explicit admission plus manifest-first execution, per-artifact byte identities and read-only reconstruction of accounting. The falsifier is any declared malformed/altered receipt accepted as valid, a missing scheduled denominator after an ordinary adapter failure, or a regression in the original ledger cases. These are implementation properties, not a new research contribution.

| Flaw or limitation | Cause | Severity | Repair or next action | Required evidence |
|---|---|---|---|---|
| Custom/assertion adapter errors abort later cases | Narrow exception allowlist | High | Retain ordinary exceptions; propagate resource/cancellation failures | Both load/execute fault cases preserve all IDs |
| Altered manifest/outcome can report valid completion | Hash was read after callbacks; outcomes not rechecked | High | Pin intended bytes before callbacks/publication and verify all successful writes | Mutation/deletion injections produce integrity error |
| No standalone replay audit | Summary trusted without reconstruction | High | New read-only v2 audit and CLI | Valid replay plus false totals, duplicate IDs, missing rows and wrong anchors fail |
| SHA256 fields accept 40-character values | Shared revision/hash regex | Medium | Per-field identity contracts | Reject before any directory or callback |
| Iterator schedule may be consumed without limit | `list()` precedes length check | Medium | Consume only limit plus one | Instrumented generator proves bounded consumption |
| Arbitrarily large counts complicate persistence | Unbounded integer endpoint contract | Medium | Nonnegative signed-64-bit counts | Oversized values become retained execution errors |
| Summary aggregation builds redundant filtered lists | Multiple intermediate collections | Low | One accounting pass | Exact endpoint equality in old/new fixture cases; no measured speed claim |
| Corrupt JSON can obscure fields | Duplicate keys, non-finite values, nesting | High for offline audit | Reuse the repository's strict JSON reader and byte limits | Fault injection plus symlink rejection |
| Crash/interrupt can leave partial results | Process or resource failure | High | Retain manifest, refuse automatic resume and require explicit incomplete audit | Cancellation tests show no completion marker |
| Producer may forge self-consistent evidence | Hashes alone cannot authenticate | High, external boundary | Independently retain manifest and summary hashes; admit/authenticate adapter separately | External provenance review; not supplied by these tests |
| Executor may return incorrect but well-formed scores | No independent semantic scorer | High, research blocker | Independent scoring and task-compatible comparator study | Protected, source-bound comparative evidence |
| Full-scale cost and integration remain unknown | No admitted full/native/package run | Open | Profile and run exact-source checks on admitted resources | Timing/memory and full/native/install receipts |

The conditional argument is: fixed IDs define the denominator before execution; ordinary failures cannot change that set; exact outcome ordering and schemas prevent omission/duplication during audit; persisted bytes must match intended records; recomputed totals must equal the summary, including types. Under correct filesystem/hash behavior and trusted external anchors, the tested evidence substitutions are rejected. This is not a proof of semantic scoring, independent reproduction, perfection or SOTA performance.

The final algorithm/API is specified in `docs/EVALUATION_LEDGER.md`. Eight additional reader/CLI regression cases were added after the baseline; the baseline remains 31 cases and is not relabeled as 39. No protected data, language challenge, native kernel or model training is involved.
