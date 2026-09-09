# NeuroCAD capability boundary

## Verified product surface

NeuroCAD deterministically converts fully dimensioned prompts for plates,
rectangular boxes/enclosures, and box/cylinder/sphere primitives into validated
canonical JSON and editable OpenSCAD. With OpenSCAD installed, it compiles STL
and verifies finite vertices, watertightness, winding, positive volume, body
count, and expected extents. The typed enclosure workflow additionally verifies
body/lid cavities, walls, floors, requested cutouts, vents, standoffs, and lid
material with request-level probes.

Outputs refuse path collisions by default. Unsupported, ambiguous, incomplete,
and oversized requests fail nonzero without a successful artifact.

## Explicitly not provided

- arbitrary natural-language or general-purpose CAD;
- STEP/BREP or native Onshape, Fusion, FreeCAD, Blender, or slicer documents;
- arbitrary PCB-outline extraction or inferred connector placement;
- structural, thermal, fluid, electromagnetic, fatigue, or material simulation;
- slicing, G-code, printer control, quoting, ordering, or manufacturing;
- load ratings, regulatory compliance, safety certification, or physical-fit
  claims;
- a trained or learned CAD model.

SCAD/STL handoff readiness means files passed NeuroCAD's declared verification.
It does not mean another application imported them or a machine produced them.

## Evidence needed to extend the boundary

Each added geometry or integration needs a typed contract, strict validation,
deterministic compilation, negative tests, request-level geometric evidence,
documented failure behavior, and an honest external acceptance test. Physical
fit claims additionally require the completed evidence in
`docs/PHYSICAL_VALIDATION_PROTOCOL.md`.
