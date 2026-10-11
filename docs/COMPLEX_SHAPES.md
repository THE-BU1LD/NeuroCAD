# Complex composite shapes

NeuroCAD can generate four deterministic composite shape families as editable
canonical IR and OpenSCAD while producing a hash-bound analytical receipt.

```bash
neurocad complex-shape --list
neurocad complex-shape docs/examples/complex-i-beam.json \
  --output-dir output/complex-shapes/i-beam
```

The output directory is published atomically and contains:

- `request.json`: normalized source request;
- `shape.ncad.json`: canonical editable NeuroCAD IR;
- `shape.scad`: OpenSCAD source;
- `analysis.json`: exact idealized geometry and bounded structural analysis;
- `manifest.json`: byte hashes and source/program/analysis identities.

Existing output directories are refused. Compile the generated canonical IR to
STL with the established verified compiler when OpenSCAD is available:

```bash
neurocad compile output/complex-shapes/i-beam/shape.ncad.json \
  --format stl -o output/complex-shapes/i-beam.stl
```

## Supported families

### Hollow shaft

A cylinder minus a coaxial bore. The receipt contains exact annular area,
volume, surface area, second and polar moments, optional mass moments, combined
axial and biaxial bending stress, exact elastic torsional shear/twist, ideal
Euler screening, cantilever deflection, and uniform-beam bending frequencies.

### I-beam

Three face-connected rectangular solids form a symmetric I-section. The report
contains exact area, perimeter-derived surface area, major/minor section
moments and moduli, web/flange slenderness indicators, combined axial/biaxial
bending stress, coupled cantilever response, Euler screening, and ideal modes.

### L-bracket

Two non-overlapping rectangular legs form an extruded angle section. NeuroCAD
calculates the displaced centroid, nonzero product of inertia, principal moments
and principal-axis angle. Biaxial stress and displacement use the complete
centroidal inertia matrix rather than independent symmetric-axis formulas.

### Perforated plate

A rectangular plate minus a bounded grid of non-overlapping circular through
holes. The report contains exact net volume and surface area, open-area ratio,
minimum edge/inter-hole ligaments, face-section moments, and optional mass
inertia. It refuses structural loads because plate response requires a declared
support and plate theory or a verified solver.

## Analysis contract

An optional `analysis` object requires a non-empty `source` describing where
the declared values came from. Supported inputs include density, elastic and
shear modulus, yield strength, safety factor, axial force, orthogonal tip
forces, biaxial root moments, torque, and Euler effective-length factor.
Nothing is silently looked up or invented.

The structural result is a screening calculation over an ideal uniform member:

- normal stress combines axial load and unsymmetric biaxial bending;
- hollow-shaft torque uses the exact circular polar moment;
- von Mises screening combines maximum normal and shaft torsional shear;
- deflection uses small-displacement Euler-Bernoulli theory;
- buckling uses an ideal Euler column about the minimum principal axis;
- frequencies use the ideal uniform cantilever characteristic root.

No result covers local stress concentration, joints, welds, holes in a loaded
plate, lateral-torsional or local buckling, shear deformation, fatigue, creep,
plasticity, damping, contact, manufacturing defects, or physical validation.
These reports are not FEA, certification, or safety approval.
