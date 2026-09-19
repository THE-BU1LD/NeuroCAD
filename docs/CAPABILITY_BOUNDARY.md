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

## Explicitly not provided

- guaranteed interpretation of arbitrary natural language or production-ready general-purpose CAD;
- STEP/BREP or native Onshape, Fusion, FreeCAD, Blender, or slicer documents;
- arbitrary PCB-outline extraction or inferred connector placement;
- finite-element, computational-fluid-dynamics, electromagnetic, fatigue, or
  general multiphysics simulation;
- automatic material selection, constitutive modeling, or applicability beyond
  the assumptions declared by the bounded analytical calculators;
- slicing, G-code, printer control, quoting, ordering, or manufacturing;
- load ratings, regulatory compliance, safety certification, or physical-fit
  claims;
- a bundled trained CAD model;
- production BREP/NURBS, adaptive meshing, FEA, CFD, electromagnetics, acoustics,
  optics, topology optimization, or coupled multiphysics solver execution;
- verified OpenCASCADE/CadQuery, Gmsh, CalculiX, FEniCS, OpenFOAM, Blender, or
  FreeCAD orchestration.

SCAD/STL handoff readiness means files passed NeuroCAD's declared verification.
It does not mean another application imported them or a machine produced them.

## Evidence needed to extend the boundary

Each added geometry or integration needs a typed contract, strict validation,
deterministic compilation, negative tests, request-level geometric evidence,
documented failure behavior, and an honest external acceptance test. Physical
fit claims additionally require the completed evidence in
`docs/PHYSICAL_VALIDATION_PROTOCOL.md`.
