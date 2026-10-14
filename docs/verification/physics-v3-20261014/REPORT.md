# Physics v3 frozen validation — 2026-10-14

**Overall gate: FAIL.** The requested frozen validation suite and installed
acceptance runner are implemented and executed. The analytical contract has a
retained maximum-bending-stress counterexample; it is not fully validated.

Protocol: `NC-PHYS-V3-CONFORMANCE-1`,
[`PROTOCOL.md`](../../../research/physics_v3/validation_v1/PROTOCOL.md).
Frozen CI commit: `7c53a0c287071135b962b19b6d5bfe651a84c67f`.
Freeze SHA-256: `6a49e4f94cbb7b6e143a071eb3b10373defd2117a5e5ecfb1e8d6fd8ca64dff0`.
[Hosted run 38547582177](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38547582177).

## Completed checks

| Check | Fresh result | Interpretation |
|---|---|---|
| Local frozen scalar matrix | 31/32 passed | One retained mathematical counterexample |
| Hosted frozen scalar matrix | 31/32 passed | Same content under Linux/Python 3.12 |
| Fresh wheel and isolated installation | Completed; dependency check passed | Candidate installation, not a new public release |
| Installed conformance plus workflow acceptance | 46/47 passed | Detailed failures retained; all-cases gate remains FAIL |
| Installed workflow acceptance alone | 15/15 passed | Includes stale geometry rejection and uncertainty references |
| Four complex-shape STL compilations | 4/4 completed | Kernel/mesh engineering evidence, not physical fit |
| Repository regression | 1,230 passed, 9 skipped; 5 subtests passed | Separate compatibility evidence; not additive to study cases |
| Verifier unit tests and Ruff | Passed | Three verifier unit tests |
| Verifier fault injection | 3/3 passed | Rejects frozen-input tampering, protected-file addition and existing lock |
| Protected v2/release/paper inventory | 40 files unchanged locally and in CI | Full path and SHA-256 inventory bound by the freeze |

The CI steps retaining numerical failures use `continue-on-error` so remaining
evidence is collected. GitHub displays those individual step conclusions as
success; their actual outcomes are failure, and the final required gate is
red. The overall run is deliberately not represented as green.

## Defect

For a 120 mm beam with opposing tip/distributed loads, both endpoint moments
are zero but the interior moment is nonzero. The implementation reports maximum
bending stress as 0 MPa instead of the reference 2.1 MPa.
See [derivation and affected contract](BEAM_FINDING.md) and the complete raw
report in `source-scalar-01/receipt.json`. Production source was not changed.
The installed wheel reproduced this same single defect; all 15 workflow
acceptance probes passed. The installed module paths and production-file hashes
are retained in `ci-38547582177/v3-installed/receipt.json`.
Fixing it requires a separately versioned source and freeze; preserve v1 and
its failure. Known-case replay after repair is regression evidence.

## Acceptance scope

The installed runner exercises the four idealized shape families, independent
volume references, artifact hashes/sizes, refusal to overwrite, invalid shape
and unsupported plate loads; bound geometry, materials, temperature
interpolation, load combinations, all three uncertainty methods, nonspatial
overlays, stale geometry rejection and non-geometric edit specificity. Raw
commands, stdout, stderr and reports are retained by the workflow.

The 32 scalar cases cover the six new analytical models. Inherited models retain
their existing contracts and regression coverage; this is not a new independent
assessment of every inherited formula. Composite structural outputs likewise
retain existing unit coverage: this first frozen suite does not separately
verify every section property or structural screen.

Reference equations were authored separately from the evaluator, with source
and prior tests visible. This is project-authored conformance, not blinded
confirmation or independent reproduction. Hash freezing establishes content
identity, not third-party preregistration or correctness of the references.

## Resource and execution boundaries

Local installed execution was refused at 99.48/151.00 MiB free-plus-speculative
memory with increasing pageouts, below the unchanged 512 MiB guard. The local
32-case run directly loaded the stdlib-only scalar module without importing
the package or tensor libraries. Hosted execution passed admission with about
14.6 GiB available memory. No local heavy installation, mesh run or full suite
was performed.

GitHub CLI authentication initially failed inside the network sandbox and
succeeded outside it. The first push was denied by automatic review because
destination ownership was unverified. A read-only API check established ADMIN
permission for the authenticated account on the existing project remote;
the subsequent reviewed push succeeded. No alternative destination was used.

The first supplemental fault-injection setup failed before exercising the
verifier because its subprocess mock affected Python platform detection.
The mock was corrected; that setup failure and the three successful checks are
retained in `verifier-fault-injection.json`. Frozen inputs remained unchanged.

The full 60 MB artifact download stalled. Required receipts, dependency/wheel
identity, JUnit and archive inventory were recovered with bounded HTTP range
reads; the redundant full download was stopped. The completed job log is also
retained. Full generated bundles and STL files remain in the hosted artifact;
they were not locally reconstructed or presented as physical measurements.

## Remaining gates

1. Correct the opposing-load maximum-stress defect in a separately versioned
   successor and verify the fix without overwriting v1 evidence.
2. Extend independent reference coverage for composite section/structural
   outputs and additional numerical edge cases before broadening claims.
3. Physical validation: **NOT_STARTED**. Requires measured experiments,
   calibration and uncertainty records against predeclared limits.
4. Independent reproduction: **NOT_STARTED**. Hosted CI is still our own
   execution, not an independent executor or independently authored benchmark.
5. Intended-user usability study: **NOT_STARTED**.

No FEA/CFD, physical accuracy, general engineering safety, manufacturing
readiness or independent scientific validity is established by this task.
