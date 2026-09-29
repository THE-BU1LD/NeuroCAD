# Current architecture and evidence reconciliation — 2026-09-29

Status: documentation reconciliation note for current `main` after PR #74.

## Why this note exists

Several authoritative-looking documents predate the merged exact-CAD work and now
contradict the repository:

- `RESEARCH_TRUTH.md` still says no real STEP/BREP path exists.
- `docs/CAPABILITY_BOUNDARY.md` still lists STEP/BREP and verified OpenCascade
  orchestration as absent.
- `docs/ARCHITECTURE.md` documents only the OpenSCAD execution path.
- `docs/C3D_REVISION_INTEGRITY_ACCEPTANCE_20260928.md` still says the bounded
  pilot is on a draft branch with CI pending.

Those statements are stale after PR #74 merged into `main`.

## Verified current repository state

PR #74, **Implement C3D revision-integrity acceptance pilot**, is merged.

- merge commit on `main`: `72da49cbf29460159d148914aa3de9051c66fe54`
- evidence-bearing hardening head: `74329a75282b50a6ddd818ce506043d3431b88c6`
- NeuroCAD CI run `36447126451`: success
- Exact CAD to Gmsh run `36447126791`: success

The exact-CAD implementation is in `core/exact_build123d.py` and the requirement
binding/verification layer is in `core/requirement_verification.py`.

## Current architecture model

NeuroCAD has two maintained geometry paths with different contracts.

### Deterministic prompt / OpenSCAD path

`prompt -> prompt_engine -> DesignGraph -> IR adapter -> neurocad-ir-v1 ->
validation -> deterministic OpenSCAD -> optional STL -> mesh/topology verification`

This remains the main bounded natural-language and typed-enclosure path.

### Bounded exact-CAD / STEP path

`Feature IR + Requirement IR + bindings -> build123d/OpenCascade -> exact geometry
-> STEP export -> STEP re-import -> kernel inspection -> exact requirement
verification -> provenance-bound receipt`

The exact path does not replace the OpenSCAD path. It provides a separate,
narrower exact-kernel contract for supported Feature IR operations.

## C3D-derived revision-integrity pilot

The merged pilot is deliberately narrow. It covers one frozen planar
single-sketch/single-extrusion wall-thickness revision class with analytic
LINE/CIRCLE boundaries.

For that class, the implementation checks:

- requested wall thickness from STEP-round-tripped exact geometry;
- unchanged external boundary and all three model extents;
- unchanged circular cutout geometry and position;
- one valid manifold solid;
- bounded self-interference and zero-thickness predicates;
- unchanged must-level Requirement IR semantics and bindings;
- baseline/candidate provenance and receipt hashes;
- transactional publication so rejected edits do not replace the accepted
  baseline.

The infeasible 40 mm wall-thickness fixture is expected to fail before
publication because the frozen 80 x 60 mm envelope would imply a non-positive
internal cavity.

## Claim boundary

The merged CI evidence establishes engineering evidence for this frozen bounded
pilot only.

It does **not** establish:

- arbitrary CAD equivalence;
- production-general BREP/NURBS modeling;
- arbitrary feature-history editing;
- manufacturability;
- structural correctness;
- physical fit;
- safety;
- interoperability across arbitrary kernels;
- endorsement or independent validation by C3D Labs.

The external provenance is engineering feedback from Daniil Kalmykov of C3D Labs,
not a validation relationship.

## Documentation changes that should follow

### `RESEARCH_TRUTH.md`

Replace the stale statement:

> No trained checkpoint, real STEP/BREP path, physical validation, safety proof,
> public release receipt, or independent replication exists.

with a split statement:

> NeuroCAD now has a bounded exact-CAD STEP/B-Rep path through
> build123d/OpenCascade, with supported Requirement IR checks and a merged
> CI-backed C3D-derived revision-integrity pilot. This is engineering evidence for
> the documented narrow exact-CAD scope, not arbitrary CAD or external validation.

> No trained checkpoint, completed physical validation, safety proof, public
> release receipt, or independent replication exists.

### `docs/CAPABILITY_BOUNDARY.md`

Move STEP/BREP from the blanket “not provided” list into the verified surface,
but describe it explicitly as a bounded Feature IR -> build123d/OpenCascade ->
STEP path.

Keep general-purpose STEP/BREP equivalence, production-general BREP/NURBS
modeling, arbitrary feature-history editing, and physical/manufacturing claims
outside the verified boundary.

### `docs/ARCHITECTURE.md`

Document both maintained geometry paths. Do not call the OpenSCAD path the only
canonical execution path now that the exact Feature IR / Requirement IR path is
merged and CI-backed.

### `docs/C3D_REVISION_INTEGRITY_ACCEPTANCE_20260928.md`

Update status from “draft branch, CI pending” to “merged to main with exact-head
CI evidence,” retaining the frozen tolerances and claim boundary unchanged.

## Source-of-truth order for collaborators

Until the stale files above are edited, use this order when statements conflict:

1. current code on `main`;
2. merged PR #74 and exact-head workflow results;
3. issue #68 evidence log;
4. `docs/C3D_REVISION_INTEGRITY_ACCEPTANCE_20260928.md` for the frozen numerical
   contract, but not its stale execution-status lines;
5. older architecture/capability summaries only where they do not conflict with
   the items above.

This note changes documentation interpretation only. It does not expand the
runtime or scientific claim boundary.
