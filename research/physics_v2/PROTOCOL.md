# Frozen-candidate protocol: NC-PHYS-V2-CONFIRM

**Status:** `READY_TO_FREEZE / RESOURCE_BLOCKED / NOT_EXECUTED`  
**Date authored:** 2026-10-11  
**Seed:** 20261011

This protocol becomes frozen only when `freeze.json` records an exact clean Git
commit, source hashes, generator hash, case-manifest hash, Python identity,
dependency-lock hash, endpoints, and `outcomes_observed=false`.

## 1. Question and scope

For bounded analytical-physics requests over NeuroCAD agent primitives, does
the full binding detect predeclared stale or contradictory analyses that an
unbound request cannot detect, while retaining deterministic valid-case
behavior?

The experiment evaluates software-contract conformance. It does not evaluate
physical accuracy, safety, FEA/CFD, full CSG properties, enterprise PLM, or
external validity.

## 2. Independent unit

The independent unit is one generated case record. Repeated evaluation of the
same record is a determinism check, not an additional independent unit.

## 3. Confirmatory matrix

The generator must materialize exactly 216 unique cases before execution:

| Family | Count | Purpose |
|---|---:|---|
| valid bound requests | 48 | acceptance, exact receipt fields, repeat determinism |
| geometry/input contradictions | 24 | semantic geometry agreement |
| material/input contradictions | 24 | material provenance agreement |
| load/input contradictions | 24 | load provenance agreement |
| stale expected hashes | 24 | pre-execution content identity |
| post-result geometry mutations | 48 | freshness detection |
| non-geometric mutations | 24 | specificity against false invalidation |
| **Total** | **216** | |

Valid and geometry-related cases are balanced across circular-shaft torsion,
hydrostatic buoyancy, and lumped thermal transient where their exact mappings
apply. Parameter values are generated from the frozen seed within predeclared
positive bounded ranges. No case may be removed because a system fails.

## 4. Arms and expected capabilities

- `full`: all hashes, semantic consistency checks, and freshness verification.
- `hash_only`: component hash/freshness only; no geometry/material/load numeric
  consistency checks.
- `unbound`: analytical request only; no dependency receipt or freshness API.

The arm definition is a mechanism ablation, not a comparison to commercial
CAD/CAE or PLM products.

## 5. Primary endpoints

1. Full-binding contradiction detection: detected / 96 across the four
   contradiction families, plus family-stratified counts.
2. Post-result geometry freshness detection: detected / 48 for full, hash-only,
   and unbound arms.
3. Non-geometric specificity: remained current / 24 for full and hash-only.
4. Valid acceptance: accepted / 48 for full.

Because this is a deterministic fail-closed contract, the practical threshold
for each applicable endpoint is 100%. Any miss falsifies the corresponding
contract claim.

## 6. Secondary endpoints

- exact equality of scientific report fields across two executions;
- per-category false positives and false negatives;
- median, p95, and maximum evaluation/verification wall time;
- maximum resident set size when available;
- report byte size.

Timing and memory are host diagnostics only and do not support cross-system
performance claims.

## 7. Statistical analysis

Report exact numerators and denominators. Wilson 95% intervals are descriptive
for the fixed generated matrix and must not be presented as population
inference. For paired binary arm comparisons, report the discordance table and
exact two-sided McNemar p-value. The primary decision remains the deterministic
all-cases threshold, not statistical significance.

## 8. Development boundary

Development may use exactly 12 hand-declared smoke cases stored separately.
Confirmatory case records, parameters, and outcomes may not be copied into
development tests. At most two development revisions are allowed. Any code,
generator, endpoint, threshold, exclusion, or analysis change after outcome
access invalidates the run and requires protocol version 2.

The development budget is exhausted. `NC-PHYS-V2-DEV-001` produced no result
because a relative project path was resolved twice. Revision 1 fixed that path.
`NC-PHYS-V2-DEV-002` then evaluated all 12 development cases without an
execution error. Revision 2 completed the predeclared control-arm endpoints,
report-size diagnostic, confirmatory matrix validation, protected
materialization gate, and fail-before-execute single-attempt ledger. No further
version-1 source, generator, endpoint, threshold, or analysis change is allowed.
Any necessary change creates protocol version 2 and a new protected manifest.

## 9. Resource admission

Before materialization and before execution:

- free plus speculative memory must be at least 512 MiB;
- output disk must have at least 2 GiB available;
- only one study process may run;
- no prior output directory may be reused;
- Git must be clean at the frozen commit.

Failure of any gate yields `NOT_AUTHORIZED`; it is not a scientific result.

## 10. Failure and exclusion policy

Allowed pre-outcome exclusions are limited to invalid JSON, duplicate task ID,
or generator violation of this protocol. Every excluded record and reason must
be retained. Runtime exceptions, mismatches, stale results, and arm failures are
outcomes and cannot be excluded.

Infrastructure failure may yield `INCONCLUSIVE` or `INVALID` but cannot be
converted into success. All raw records, exceptions, timing, environment, and
analysis outputs must be retained.

## 11. Freeze and stop rule

The matrix is executed once after a valid freeze receipt. There is no adaptive
rerun. Results are classified `SUPPORTED`, `MIXED`, `NEGATIVE`, `INCONCLUSIVE`,
or `INVALID` against the four hypotheses. Post-hoc observations may motivate a
separate successor study only.
