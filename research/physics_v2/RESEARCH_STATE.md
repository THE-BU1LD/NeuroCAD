# NC-PHYSICS-V2-PROVENANCE research state

## Current verdict

`DEVELOPMENT_PASS / FROZEN_PREOUTCOME / CONFIRMATORY_NOT_EXECUTED`

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

Initial checks on 2026-10-11 were below the mandatory 512 MiB research-run
floor. Protected materialization later passed the unchanged gate. Freeze passed
with 868.71875 MiB free plus speculative memory and over 2 GiB free storage.
The confirmatory execution still requires a fresh passing gate.

## Development evidence

- `NC-PHYS-V2-DEV-001`: retained harness failure, `NO_RESULT`; a relative
  project path was resolved twice.
- `NC-PHYS-V2-DEV-002`: 12/12 bounded development cases behaved as declared,
  with no execution errors. This is development evidence only.
- The two-revision development budget is exhausted. Version 1 must now remain
  unchanged or be superseded by a new version before protected execution.
- The version-1 implementation and pre-results manuscript were committed at
  `faeede8`; a subsequent governance-only commit records that identity.

## Frozen identity

- source commit: `2627c106ede6c2ac4e3570700f2bd545a763943c`
- case count: 216
- case-file SHA-256: `9caa80fb7e5257f514143ec0b297711464767c5a68ffa49988070a2f97c94c49`
- semantic case SHA-256: `2e6bb79b5a649b191fb7b9a0635b9e0ae4053aae8d23b72af104fc5937ac0696`
- outcome state: not observed

The machine-readable authority is `RESEARCH_STATE.json`. Update it before every
session ends and preserve negative, mixed, invalid, and blocked outcomes.
