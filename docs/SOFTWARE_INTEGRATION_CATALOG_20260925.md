# NeuroCAD software integration catalog — 2026-09-25

Status: expansion research inventory. This does not claim the listed integrations
are implemented. Existing NeuroCAD integrations and verified behavior remain unchanged.

## Integration rule

NeuroCAD should be a hub with explicit adapter boundaries, not a monolith.

Each adapter declares one of:

- CORE_LIBRARY — safe optional Python/library dependency used in-process.
- OPTIONAL_LIBRARY — optional in-process backend behind capability probes.
- EXTERNAL_PROCESS — executable/file/API integration with versioned receipts.
- RESEARCH_ADAPTER — experimental integration not enabled in normal product paths.
- VIEWER_ONLY — visualization/post-processing; never authoritative geometry.

Every adapter must record version, invocation, inputs, outputs, hashes, timeout,
failure mode, and claim boundary. GPL and heavyweight applications should usually
remain external-process adapters unless licensing review explicitly approves otherwise.

---

# A. Exact CAD / B-Rep

## build123d + OCP / OpenCascade — P0

**Role:** first exact-CAD backend candidate.

Why:
- Python parametric B-Rep modeling.
- OpenCascade kernel.
- STEP import/export and precise solid geometry.
- Strong match for NeuroCAD feature-history IR.
- build123d 0.13.0 moved to OCP/OCCT 8.0.1.

Integration:
- OPTIONAL_LIBRARY.
- Feature IR -> build123d/OCP builder.
- STEP + BREP validity + geometry inspection receipts.
- No raw kernel face indices persisted; resolve NeuroCAD semantic selectors at build time.

Acceptance:
1. sketch -> extrusion;
2. patterned holes;
3. revolve;
4. fillet;
5. chamfer/cutout;
6. STEP export/re-import;
7. deterministic dimensional checks;
8. edit/rebuild regression.

## CadQuery + OCP — P0/P1 compatibility backend

**Role:** second exact-CAD compiler / baseline.

Why:
- Python parametric CAD on OCCT.
- STEP and assembly export.
- Large ecosystem and useful comparison target for text-to-CAD research.

Integration:
- OPTIONAL_LIBRARY.
- Compile the same Feature IR subset to both build123d and CadQuery.
- Use differential testing: compare extents/body count/volume/topology/STEP roundtrip.

Do not make both APIs leak into the canonical IR.

## OpenCascade/OCP direct — P1

**Role:** low-level exact-kernel escape hatch.

Use only for capabilities missing in higher-level libraries:
- BRepCheck validation;
- STEP/XDE metadata;
- exact geometric interrogation;
- healing/sewing;
- stable geometric signatures.

Keep all OCP-specific objects behind an adapter boundary.

## FreeCAD 1.1.2 — P1

Current NeuroCAD only has file-exchange support. Expand to:
- headless FreeCADCmd verification;
- STEP/FCStd import tests;
- optional generation of a real editable FCStd document from the Feature IR;
- document object/property validation;
- round-trip dimensional checks.

Use EXTERNAL_PROCESS first. Native Python embedding can come later.

## SolveSpace — P2

**Role:** independent 2-D/3-D geometric-constraint solver baseline.

Potential uses:
- sketch constraint solving;
- over/under-constrained diagnostic comparisons;
- independent solver oracle for bounded sketch cases.

Keep as EXTERNAL_PROCESS unless the library interface is proven portable.

## SALOME 9.16 — P2

**Role:** high-end CAD/meshing/pre/post-processing reference environment.

Useful for:
- independent STEP/BRep opening;
- geometry repair and partitioning;
- meshing through SMESH/Gmsh/Netgen plugins;
- solver handoffs.

Heavyweight; EXTERNAL_PROCESS only.

---

# B. Mesh robustness / geometric verification

## Manifold 3.x — P0/P1

**Role:** robust manifold mesh Boolean and mesh-CAD fallback.

Why:
- Python package available;
- strong manifold-output guarantees for valid manifold inputs;
- fast Boolean operations;
- cross-platform deterministic work has landed in current releases.

Use for:
- robust preview/fabrication mesh CSG;
- differential checks against OpenSCAD;
- 3MF/glTF-oriented mesh exchange;
- mesh provenance IDs.

It does not replace exact B-Rep CAD.

## CGAL 6.2.1 — P1

**Role:** independent computational-geometry verifier/repair toolbox.

Useful capabilities:
- self-intersection and collision checks;
- Boolean operations;
- remeshing;
- polygon soup repair;
- convex decomposition;
- alpha wrapping;
- distance/intersection analysis.

Because many CGAL packages use GPL/commercial licensing, prefer a separately
installed EXTERNAL_PROCESS helper unless a license review approves a narrower library path.

## OpenVDB — P2

**Role:** sparse volumetric / signed-distance field backend.

Use for:
- implicit fields;
- voxelized fabrication checks;
- lattice/TPMS processing;
- distance fields;
- volumetric optimization experiments.

## libfive — P2/P3

**Role:** implicit/function-representation geometry research backend.

Good fit for:
- smooth blends and warps;
- generative geometry;
- graded fields;
- metamaterial/TPMS experiments.

Keep separate from the exact B-Rep feature tree.

---

# C. Meshing

## Gmsh 4.15.2 stable / 5.x development — P0/P1

**Role:** primary general meshing adapter.

Capabilities:
- OpenCascade geometry;
- STEP import/manipulation;
- 1D/2D/3D mesh generation;
- mesh-size fields;
- anisotropic/background meshes;
- physical groups;
- Python API.

Integration:
- EXTERNAL_PROCESS first, optional Python adapter second.
- Feature/STEP geometry -> tagged Gmsh model -> mesh + boundary-group receipt.

This is the bridge to FEA/CFD/EM solvers.

## Netgen / NGSolve — P1/P2

**Role:** meshing + multiphysics finite-element stack.

Useful for:
- tetrahedral meshing;
- solid mechanics;
- fluids;
- electromagnetics;
- high-order FEM;
- fast Python-driven research loops.

## meshio — P1

**Role:** neutral mesh format translation.

Use only as a translator, never as geometry verification.
Record exact source/target format and field/group preservation.

---

# D. Structural / thermal / multiphysics simulation

## CalculiX 2.23 — P0/P1

**Role:** first external structural FEA adapter.

Why:
- open source;
- linear/nonlinear mechanics;
- static/dynamic/thermal;
- Abaqus-like input format;
- simple executable boundary.

First bounded NeuroCAD study:
STEP/BRep -> Gmsh mesh -> CalculiX deck -> displacement/stress result ->
VTK/CSV receipt.

No automatic 'safe' verdicts. Results must expose loads, materials, boundary
conditions, mesh convergence status, and solver version.

## FEniCSx 0.11 — P1/P2

**Role:** programmable PDE research backend.

Use when NeuroCAD needs:
- custom elasticity;
- heat conduction;
- coupled PDEs;
- differentiable/research formulations.

Not the default end-user FEA path.

## MOOSE — P2/P3

**Role:** large multiphysics research adapter.

Useful for advanced heat transfer, mechanics, transport and coupled problems.
Heavyweight; external/containerized research backend only.

## Netgen/NGSolve — P1/P2

Can also serve as an integrated meshing + FEM path and independent comparison
against CalculiX/FEniCSx on small reference cases.

---

# E. CFD / fluids / heat transfer

## OpenFOAM 14 — P1

**Role:** external CFD/thermal-fluid backend.

Use for:
- internal/external flow;
- pressure drop;
- heat transfer;
- conjugate problems;
- flow around generated geometry.

Pipeline:
STEP -> Gmsh/snappyHexMesh-compatible surface -> case generator ->
OpenFOAM external run -> residual/convergence + field summary receipt.

On macOS, keep it behind the supported container/Multipass style boundary rather
than bloating NeuroCAD's Python environment.

## SU2 — P2

**Role:** aerodynamic/adjoint/design-optimization backend.

Useful later for:
- external aerodynamics;
- shape optimization;
- gradients/adjoints.

Prioritize after basic OpenFOAM handoff exists.

---

# F. Electromagnetics / RF / photonics

## openEMS — P1/P2

**Role:** RF/microwave/metamaterial FDTD adapter.

Strong fit for:
- antennas;
- RF enclosures;
- waveguides;
- microwave structures;
- metamaterials.

Python interface makes geometry + simulation receipts feasible.

## Meep — P2

**Role:** general FDTD photonics backend.

Use for:
- photonic structures;
- resonators;
- waveguides;
- frequency-domain response from time-domain simulations;
- inverse-design research.

## MPB — P2/P3

**Role:** photonic-crystal / periodic eigenmode backend.

Natural partner for NeuroCAD's lattice/periodic-geometry track:
parameterized unit cell -> MPB band structure -> objective -> optimizer.

---

# G. Atomistic / nanoscale

These are not CAD kernels. They are optional scale-specific simulation adapters.

## LAMMPS — P2/P3

**Role:** materials / molecular dynamics / mesoscale adapter.

Use for:
- atomistic materials;
- nanoparticle systems;
- indentation/contact studies;
- coarse-grained structures;
- selected mesoscale bonded-particle models.

Critical boundary:
A CAD solid cannot be silently converted into a physically meaningful atomistic
model. Material structure, lattice, potential/force field, boundary conditions,
temperature and scale must be explicit.

## GROMACS 2026.x — P3

**Role:** molecular dynamics for biomolecular/soft-matter use cases.

Only relevant if NeuroCAD expands into molecular/biomedical design.

## ASE — P3

**Role:** atomistic structure/data bridge for calculators and simulation codes.

Good interoperability layer for structures, calculators and optimization.

## OVITO 3.16 — P2/P3

**Role:** VIEWER_ONLY / post-processing for particle simulations.

Use for LAMMPS/atomistic visualization, defect analysis and derived fields.
Never authoritative CAD geometry.

---

# H. Optimization / calculus / inverse design

## OpenMDAO 3.x — P0/P1

**Role:** multidisciplinary design optimization orchestrator.

Use for:
- design variables;
- linked CAD + simulation components;
- constraints;
- driver/optimizer orchestration;
- derivative checks;
- multidisciplinary workflows.

NeuroCAD should own the problem/receipt schema; OpenMDAO is an execution backend.

## CasADi — P0/P1

**Role:** nonlinear optimization + algorithmic differentiation.

Good fit for:
- continuous parametric CAD optimization;
- equality/inequality constraints;
- sensitivity analysis;
- inverse geometry;
- compact optimization problems.

## SciPy optimize — P0

Keep as the lightweight baseline already compatible with the Python stack.

## NLopt — P1

Useful as a multi-algorithm derivative/free-derivative optimizer baseline.

## IPOPT — P1/P2

Use through CasADi or another maintained interface for constrained nonlinear
optimization where appropriate.

---

# I. Visualization / inspection / scientific results

## VTK 9.7 — P1

**Role:** low-level scientific visualization/data model.

Use for:
- mesh/volume display;
- simulation fields;
- slicing;
- streamlines;
- scalar/vector data;
- exportable scientific scenes.

## PyVista 0.49 — P1

**Role:** Pythonic VTK layer.

Likely the best NeuroCAD simulation-viewer API because it is NumPy-native and
works in scripts, notebooks and applications.

## ParaView 6.x — P2

**Role:** external high-end post-processing and independent result inspection.

Do not embed. Generate .vtu/.vtk/.xdmf plus a handoff receipt.

---

# J. Electronics / mechatronics

## KiCad 10.0.6 — P0

NeuroCAD already has a bounded KiCad path. Expand it for KiCad 10:

- use STEP-only official 3-D model ecosystem where possible;
- board outline and thickness;
- mounting holes;
- connector envelopes;
- maximum component envelope;
- keepouts;
- explicit coordinate transforms;
- enclosure cutout proposals;
- board/enclosure interference checks.

Continue to fail closed on unsupported board geometry.

## ngspice — P2

**Role:** circuit-simulation handoff if NeuroCAD gains electro-mechanical design constraints.

Keep circuit claims separate from mechanical geometry.

---

# K. Manufacturing / CAM / additive

## OpenSCAD + Manifold engine — P0

Keep OpenSCAD as the verified legacy/CSG backend.
Probe the current Manifold geometry engine where supported, but freeze version
and differential-test geometry before changing the authoritative path.

## PrusaSlicer — P1

Existing file-exchange adapter can be upgraded to an optional CLI verification path:
- import generated mesh;
- generate bounded slicing analysis;
- record profile/printer/material;
- parse time/material/support estimates;
- never send a print automatically.

PrusaSlicer 3.0 is currently a preview; do not make preview behavior a release dependency.

## CuraEngine / OrcaSlicer / Bambu Studio — P1/P2

Same adapter pattern:
verified mesh -> explicit profile -> external slice -> G-code/statistics receipt.

G-code generation is not physical print verification.

## FreeCAD CAM — P2

Potential CNC workflow:
Feature IR/STEP -> stock/tool/setup definition -> CAM path generation ->
simulation/verification receipt.

Do not generate machine-ready G-code without explicit machine/postprocessor/tooling configuration.

---

# L. AEC / BIM expansion

## IfcOpenShell / Bonsai — P3

Only if NeuroCAD expands into building-scale/AEC workflows.

Use for:
- IFC import/export;
- parametric building elements;
- spatial relationships;
- geometry conversion;
- openBIM checks.

This should be its own domain package, not part of the mechanical CAD MVP.

---

# Recommended implementation order

## Phase 1 — immediate

1. build123d 0.13 + OCP 8.0.1 exact backend spike.
2. CadQuery differential backend.
3. Gmsh meshing adapter.
4. Manifold mesh backend.
5. PyVista result/geometry viewer.
6. OpenMDAO + CasADi optimization adapter.
7. KiCad 10.0.6 integration audit.

## Phase 2 — engineering loop

8. CalculiX structural adapter.
9. OpenFOAM CFD adapter.
10. openEMS electromagnetic adapter.
11. FreeCAD headless exact-file verification.
12. CGAL independent mesh verification helper.
13. ParaView handoff.

## Phase 3 — multiscale/research

14. FEniCSx.
15. Netgen/NGSolve.
16. Meep + MPB.
17. LAMMPS + OVITO.
18. libfive/OpenVDB implicit geometry.
19. SALOME.
20. MOOSE/SU2.

---

# Architecture rule for software adapters

All adapters implement a common capability model:

```text
discover()
version()
capabilities()
validate_input()
execute()
collect_outputs()
verify_outputs()
write_receipt()
```

No adapter may return a generic "success". It must return claims with evidence:

```json
{
  "adapter": "gmsh",
  "version": "...",
  "operation": "volume_mesh",
  "input_sha256": "...",
  "status": "verified",
  "claims": [
    {"name": "volume_mesh_generated", "passed": true},
    {"name": "boundary_groups_preserved", "passed": true}
  ],
  "artifacts": [],
  "limitations": []
}
```

This lets NeuroCAD grow into a serious engineering orchestrator without making
unverified cross-domain claims.
