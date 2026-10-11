# NC-PHYSICS-V2-PROVENANCE research state

## Current verdict

`DEVELOPMENT_PASS / READY_TO_FREEZE / CONFIRMATORY_RESOURCE_BLOCKED`

This is a versioned successor to the terminal NeuroCAD controlled-compiler
study. It does not reopen, overwrite, or upgrade the predecessor's evidence.

## Research question

For bounded analytical-physics requests over NeuroCAD agent primitives, do
geometry-, material-, and load-bound receipts detect predeclared stale or
contradictory analyses that an unbound request file cannot detect, while
retaining deterministic valid-case behavior?

## Contribution boundary

The intended contribution is an executable reference contract plus a controlled
conformance study. It is not a new physics method, FEA/CFD system, material
authority, full CSG property engine, safety proof, or general CAD/CAE result.

## Central mechanism

Each result retains the exact analytical inputs and hashes of the complete
request, selected CAD component geometry, versioned material card, and named
load case. Exact geometry/model mappings are checked before evaluation. Saved
reports can be rechecked against the current component; geometry drift yields a
machine-readable stale result and a nonzero exit status.

## Primary falsifiers

- Any in-scope contradiction is accepted by the full binding.
- Any in-scope geometry mutation leaves a bound result current.
- Any declared non-geometric mutation invalidates the geometry receipt.
- Valid bound requests lose deterministic scientific fields.

## Resource state

On 2026-10-11, free plus speculative memory was approximately 104 MiB, below
the mandatory 512 MiB research-run floor. Static work, implementation, and
small unit tests are admissible; protected and expensive runs are not.

## Development evidence

- `NC-PHYS-V2-DEV-001`: retained harness failure, `NO_RESULT`; a relative
  project path was resolved twice.
- `NC-PHYS-V2-DEV-002`: 12/12 bounded development cases behaved as declared,
  with no execution errors. This is development evidence only.
- The two-revision development budget is exhausted. Version 1 must now remain
  unchanged or be superseded by a new version before protected execution.

The machine-readable authority is `RESEARCH_STATE.json`. Update it before every
session ends and preserve negative, mixed, invalid, and blocked outcomes.
