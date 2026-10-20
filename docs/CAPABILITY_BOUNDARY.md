# NeuroCAD capability boundary

## Verified product surface

NeuroCAD deterministically converts fully dimensioned prompts for plates,
rectangular boxes/enclosures, and box/cylinder/sphere primitives into validated
canonical JSON and editable OpenSCAD. With OpenSCAD installed, it compiles STL
and verifies finite vertices, watertightness, winding, positive volume, body
count, and expected extents. The typed enclosure workflow additionally verifies
body/lid cavities, walls, floors, requested cutouts, vents, standoffs, and lid
material with request-level probes.

Separate, explicit-input analytical calculators cover Euler buckling, free and
fully restrained thermal expansion, one-dimensional steady conduction,
Darcy-Weisbach internal pipe flow, and thin-wall closed-end cylinders. These
calculators report their assumptions and applicability limits with every result.

Outputs refuse path collisions by default. Unsupported, ambiguous, incomplete,
and oversized requests fail nonzero without a successful artifact.

For supported enclosure body cutouts, NeuroCAD can generate and regenerate-
verify an atomic, source-bound ladder of aperture variants, emit a complete
printer/process passport and measurement worksheet, and conservatively evaluate
entered pass/fail observations. This is workflow and evidence support; no blank
template or generated coupon is counted as a physical measurement or fit claim.
A sealed, bracketed transition can drive a review-only, exact-source cutout
revision plan. Explicit application creates a new auditable project revision;
verification recomputes its ancestry and compiled aperture. This supports safe
evidence use, not evidence authentication, process transfer, or fit certification.

Selected connector cutouts, standoffs, PCB mounting coordinates, and modeled
lid/body interface fields can be captured in an exact-source interface contract.
Protected revision commands fail before writing when a selected interface is
missing, structurally changed, or exceeds its declared numeric tolerance.
Change-impact reports use stable feature IDs and coordinate-level paths to name
affected scopes and evidence that must be regenerated, and can be independently
recomputed from the exact source, candidate, and contract. These checks establish
project-field compatibility only; they do not inspect an unmodeled mating part or
certify physical compatibility.

The agent studio adds persistent conversational **concept drafting**. A built-in
offline planner supplies visible defaults for simple primitives, water bottles,
and a decorative cosplay shell. Configured OpenAI-compatible or Ollama models may
plan other benign objects. Provider plans are untrusted until strict schema,
component-order, parameter, and canonical-IR validation passes. Each component
produces a hashed checkpoint and loopback-only live preview. This expands the
interaction surface; it does not expand the verified manufacturing boundary.

The scientific kernel adds dimensional quantities, second-order forward
automatic differentiation, bounded nonlinear equality/inequality solving,
projected local optimization, elementary interval arithmetic, seeded correlated
Monte Carlo propagation, and linear-system diagnostics. These methods disclose
local convergence and numerical limits and do not replace domain solvers.

## Optional exact CAD and meshing

The optional build123d/OpenCascade backend builds the declared Feature IR
subset and exports STEP with re-imported geometry checks. Internal native
acceptance covers five authored reference solids on Linux, macOS and Windows.
The supervised Gmsh adapter creates bounded tetrahedral meshes and verifies
serialized memberships and source-bound planar boundary roles. These are
engineering checks for the tested cases and pinned tools, not arbitrary-CAD,
solver, manufacturing or physical-accuracy claims. See [native acceptance](NATIVE_ACCEPTANCE.md)
and [PR110](https://github.com/THE-BU1LD/NeuroCAD/pull/110).

Requirement binding coverage is accounting. `feature_presence` and
`feature_count` check construction history; they do not by themselves establish
holes or topology in the final solid. Exact extents, planar wall-thickness and
B-Rep probes have their own narrower geometric meaning. New final-geometry
predicates require explicit contracts and negative tests.

The immutable public alpha v0.5.0a6 retains its original source identity.
Post-release main-branch changes need their own installed-release validation.

## Explicitly not provided

- guaranteed interpretation of arbitrary natural language or production-ready general-purpose CAD;
- native Onshape, Fusion, FreeCAD, Blender, or slicer project documents;
- arbitrary PCB-outline extraction or inferred connector placement;
- finite-element, computational-fluid-dynamics, electromagnetic, fatigue, or
  general multiphysics simulation;
- automatic material selection, constitutive modeling, or applicability beyond
  the assumptions declared by the bounded analytical calculators;
- slicing, G-code, printer control, quoting, ordering, or manufacturing;
- load ratings, regulatory compliance, or safety certification; fit-study
  reports retain every replicated coupon outcome and sealed evidence bundles
  retain exact attachment bytes, but neither generalizes them into a certified
  physical-fit claim or authenticates the content of an attached file;
- a bundled trained CAD model;
- general-purpose production BREP/NURBS modeling, adaptive meshing, FEA, CFD, electromagnetics, acoustics,
  optics, topology optimization, or coupled multiphysics solver execution;
- verified general-purpose CalculiX, FEniCS, OpenFOAM, Blender, or FreeCAD
  solver/application orchestration; the bounded optional kernel/mesher path above
  does not establish these integrations.

SCAD/STL handoff readiness means files passed NeuroCAD's declared verification.
It does not mean another application imported them or a machine produced them.

## Evidence needed to extend the boundary

Each added geometry or integration needs a typed contract, strict validation,
deterministic compilation, negative tests, request-level geometric evidence,
documented failure behavior, and an honest external acceptance test. Physical
fit claims additionally require the completed evidence in
`docs/PHYSICAL_VALIDATION_PROTOCOL.md`.
