# Development repair: mesh scale invariance

Date: 2026-10-10. Base: `23c7284048512ca8d956c9a2c4c62eb1f8b8ea89`. Evidence class: engineering regression verification.

## Failure and scientific scope

A one-millimeter normalization floor made tolerances effectively absolute for small meshes, causing scale-dependent intersection decisions. Computing (min+max)/2 could overflow for finite translated vertices.

No external challenge outcomes exist in the referenced truth record. This uses authored geometry regression fixtures, not independent scientific confirmation. Existing source-bound controlled run and frozen protocols are unchanged.

## Implementation contract

Normalize by actual maximum mesh extent, center with half-weighted extrema, and reject zero or unrepresentable extent before geometric predicates.

Four analytically chosen intersection/nonintersection fixtures preserve their verdict from 1e-180 to 1e160; a representable mesh near 1e308 can be centered without overflow.

## Verification and retained failures

The exact reproduction command, environment versions, source SHA-256 identities, test output, and exit status are in `research/verification/mesh_scale_invariance_20261010/receipt.json`. The canonical state retains the base-source regression failure counts and observed review failures. This record was written after exploratory defect discovery, and is not a preregistered confirmatory experiment.

An independent agent examined the modified source and regression assertions. This is project-controlled review, not external scientific replication.

## Limits and next action

Inputs whose total span is not representable in float64 are rejected explicitly. These checks do not establish physical validity, kernel-backed solid correctness, safety, or language generalization.

EVIDENCE_PARTIAL; historical typed-parser causal claim remains falsified.

- Review and integrate alongside separate jet differentiation and mesh integration work without discarding concurrent changes.
- Obtain independent challenge data and adjudication under the frozen external protocol.
- Complete strong comparator execution, external replication, release evidence and final artifact gates before stronger scientific or release claims.
