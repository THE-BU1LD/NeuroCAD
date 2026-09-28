# NeuroCAD revision-integrity acceptance contract

Status: frozen external-feedback acceptance specification, v0.1  
Date: 2026-09-28  
Primary implementation issue: #68  
External provenance: C3D Labs feedback from Daniil Kalmykov, 2026-09-28, on the bounded enclosure wall-thickness evaluation.

## Why this exists

A successful parameter edit is not established by:
- the requested scalar changing,
- a plausible render,
- a valid STEP file,
- or a valid B-Rep alone.

For a wall-thickness-only edit, NeuroCAD must independently prove that geometry which was not authorized to change remains equivalent to the accepted baseline, while the edited result remains a valid solid. An infeasible edit must fail without changing the last accepted model or silently relaxing unchanged requirements.

This contract deliberately stays narrower than general CAD equivalence. It freezes one acceptance invariant that can be implemented and falsified.

## Existing integration points

The smallest implementation should extend the current exact-CAD path rather than add a parallel architecture:

- `core/exact_build123d.py`
  - `Build123dBackend.compile`
  - `Build123dBackend.inspect`
  - `Build123dBackend.export_verified_step`
  - current STEP round-trip tolerances and fail-closed staging behavior
- `core/requirement_verification.py`
  - `RequirementBindingSet`
  - `verify_exact_requirements`
  - binding hashes and must-level failure semantics
- `tests/test_exact_build123d.py`
  - native exact-CAD edit, validity and atomic-publication acceptance tests
- `tests/test_requirement_verification.py`
  - unchanged must-level binding regression checks

Do not infer geometric invariance from Feature IR parameter equality. The invariant must be evaluated against resulting exact geometry.

## Frozen terminology

**Baseline**: the last accepted exact-CAD model and its receipts.

**Candidate**: the geometry produced by applying exactly one requested edit to the baseline Feature IR.

**Authorized change region**: geometry that is expected to change because of the edited parameter. In this pilot, that is the inner wall surface implied by wall thickness.

**Unaffected region**: exact geometry explicitly declared unchanged by the edit. In this pilot:
1. enclosure external boundary;
2. cutout boundary geometry;
3. cutout position.

**Accepted edit**: candidate passes every must-level requirement, exact-kernel validity checks, and all frozen unaffected-geometry comparisons.

**Rejected edit**: any candidate that fails one or more acceptance checks. Rejection must not publish or replace an accepted artifact.

## Tolerances

Use one declared tolerance family for this pilot. Do not silently widen tolerances after observing results.

- linear geometric tolerance: `1e-6 mm`
- centroid/location tolerance per axis: `1e-6 mm`
- relative scalar tolerance for area/length/volume comparisons: `1e-9`
- absolute scalar floor: `1e-12` in the corresponding squared/cubed unit

These intentionally align with the current exact-CAD STEP round-trip absolute tolerance in `core/exact_build123d.py`. If the native kernel demonstrates that these tolerances are below stable numerical precision on CI, revise this file in a separate reviewed commit before evaluating outcomes; do not change them inside a result-producing run.

## Required baseline evidence

Before any edit is attempted, freeze and retain:

- baseline Feature IR serialized bytes and SHA-256;
- baseline Requirement IR serialized bytes and SHA-256;
- baseline RequirementBindingSet serialized bytes and SHA-256;
- baseline exact build receipt;
- baseline STEP bytes and SHA-256;
- exact backend + version;
- selected external-boundary geometric signature;
- selected cutout geometric signature.

The signature format may evolve, but it must be derived from exact-kernel geometry, not from stored parameters or rendered pixels.

## Case A — feasible wall-thickness edit

Input: change only wall thickness to a feasible value while preserving every other declared requirement.

The edit passes only if all of the following are true.

### A1. Requested edit took effect

The wall-thickness requirement is satisfied using exact geometric evidence or a dedicated exact probe. Parameter-store equality alone is insufficient.

### A2. External boundary preserved

Compare the selected external-boundary geometry from candidate against baseline.

Required:
- same semantic selector identity / declared role;
- same number of selected external faces;
- bidirectional maximum point-to-surface deviation <= `1e-6 mm`;
- external-boundary bounding extents unchanged within `1e-6 mm`.

A global model bounding box is not sufficient by itself.

### A3. Cutout geometry preserved

For the cutout boundary selected by semantic role:

Required:
- same number of boundary wires/edges;
- centroid coordinate delta on each axis <= `1e-6 mm`;
- perimeter/curve-length agreement within `1e-9` relative tolerance;
- enclosed area agreement within `1e-9` relative tolerance;
- bidirectional maximum boundary deviation <= `1e-6 mm`.

Do not infer this from unchanged cutout parameters.

### A4. Solid validity preserved

Candidate must satisfy all of:

- `valid_brep == true`;
- `manifold == true`;
- `solid_count == 1`;
- no self-intersection reported by the kernel validation path;
- no zero-thickness or degenerate region accepted as valid output.

If build123d/OCP cannot independently expose one of the last two checks, record that capability as unsupported and keep the case failing closed until an exact predicate exists. Do not relabel `is_valid` as proof of every topology condition.

### A5. Unchanged requirements remain satisfied

Re-run `verify_exact_requirements` using the candidate's exact inspection/evidence and bindings rebound to the candidate Feature IR hash.

Every unchanged must-level requirement must remain satisfied. A candidate cannot pass by dropping, weakening, rebinding, or converting an unchanged must requirement to should/preference.

### A6. Published receipt records the comparison

A successful accepted-edit receipt must record at minimum:

- baseline Feature IR SHA-256;
- candidate Feature IR SHA-256;
- baseline requirements SHA-256;
- candidate requirements SHA-256;
- unchanged binding identities;
- comparison tolerance values;
- per-invariant pass/fail evidence;
- backend + version.

No receipt should claim complete CAD equivalence; it proves only the declared invariant set.

## Case B — infeasible 40 mm wall-thickness edit

Attempt the 40 mm wall-thickness edit under the same unchanged external envelope and cutout constraints.

Expected behavior:

1. candidate evaluation fails explicitly with a domain error;
2. no accepted artifact directory is created or replaced;
3. baseline STEP SHA-256 remains unchanged;
4. baseline build-receipt SHA-256 remains unchanged;
5. baseline Feature IR / Requirement IR / binding SHA-256 values remain unchanged;
6. no unchanged requirement is removed, weakened, or rebound to a different meaning;
7. no fallback geometry is auto-published;
8. the failure result identifies which invariant/requirement blocked acceptance.

A valid but constraint-relaxed solid is a failure.

## Transaction semantics

The pilot must treat the accepted model as immutable until the complete candidate acceptance suite passes.

Implementation rule:
- build and verify in private staging;
- compare candidate to baseline from immutable inputs;
- publish a new accepted artifact only after all checks pass;
- never mutate the baseline directory in place;
- on any exception or failed invariant, delete candidate staging and return failure.

The current `export_verified_step` staging behavior is a useful primitive, but the edit test must additionally verify preservation of the separate baseline artifact.

## Frozen acceptance tests

Add these native tests to `tests/test_exact_build123d.py`:

1. `test_wall_thickness_edit_preserves_external_boundary_exactly`
2. `test_wall_thickness_edit_preserves_cutout_geometry_and_position`
3. `test_wall_thickness_edit_keeps_single_valid_manifold_solid`
4. `test_wall_thickness_edit_rechecks_unchanged_must_requirements`
5. `test_infeasible_40mm_wall_edit_preserves_last_accepted_bundle`
6. `test_infeasible_edit_does_not_relax_unchanged_bindings`
7. `test_revision_receipt_binds_baseline_candidate_and_tolerances`

Add a dependency-light regression to `tests/test_requirement_verification.py` proving that unchanged must requirements cannot disappear or change verification method during a candidate edit.

## Implementation sequence

1. Build one deterministic enclosure fixture with semantic roles for:
   - outer boundary,
   - inner wall,
   - cutout boundary.
2. Add exact-kernel selector helpers that return those regions without persisted raw face/edge indices.
3. Add a small geometric-comparison helper using the frozen tolerance family.
4. Add the seven tests above first.
5. Implement candidate revision receipt + transactional wrapper until tests pass.
6. Run the native exact-CAD lane and full CI on the exact head.
7. Record executed evidence on #68.
8. Only after executed evidence exists, send the acceptance table back to C3D Labs.

## Claim boundary

Passing this pilot would establish evidence for one bounded revision-integrity invariant on one exact-CAD backend. It would not establish universal CAD equivalence, manufacturability, structural correctness, physical fit, safety, or interoperability across arbitrary kernels.
