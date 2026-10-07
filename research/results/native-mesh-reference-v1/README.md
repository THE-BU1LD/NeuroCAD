# Native STEP-to-tetrahedron reference audit

Status: **PASS**. Six native runs; two analytic reference parts.

| Part | Max size (mm) | Tetrahedra | Mesh volume (mm³) | Relative volume error | Minimum SICN |
|---|---:|---:|---:|---:|---:|
| box | 4 | 643 | 1000.000000 | 0.000000% | 0.342522 |
| box | 2 | 731 | 1000.000000 | 0.000000% | 0.255033 |
| box | 1 | 5033 | 1000.000000 | 0.000000% | 0.305936 |
| holed_plate | 4 | 736 | 914.525444 | 0.526629% | 0.310400 |
| holed_plate | 2 | 816 | 914.503659 | 0.524234% | 0.314870 |
| holed_plate | 1 | 4838 | 911.139902 | 0.154483% | 0.306093 |

The box volume is 20 × 10 × 5 = 1000 mm³. The plate is 20 × 12 × 4 mm with a radius-2 mm through hole: 960 − 16π mm³.
The fixed relative-volume tolerances are 1e-9 for the box and 2.5% for the plate; they are declared in the runner before meshing.
All STEP files, ASCII MSH files, receipts and the aggregate report are retained here. Reproduce using `python scripts/reproduce_mesh_quality.py NEW_DIRECTORY`.

## Limits

- Two synthetic reference CAD parts across three fixed mesh sizes; no empirical manufacturing or physics study.
- Positive native minSICN, serialization integrity and an independent tetrahedron-volume sum are checked.
- Volume agreement is not a solver-convergence, structural-safety, topology-completeness or general CAD benchmark claim.
- No learned parser, protected VCG stage, dataset split or closed research result was changed or rerun.
- STEP headers and native mesher details may differ on replay; retained hashes bind this run only.
