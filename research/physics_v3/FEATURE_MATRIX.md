# NeuroCAD Physics v3 feature matrix

Status date: 2026-10-11

This matrix separates implemented analytical engineering functions from work
that would require an actual external solver or physical evidence.

| Capability | Implementation | Verification scope | Status |
|---|---|---|---|
| Temperature-aware material cards | Piecewise-linear, in-range interpolation with source and hash receipts | Exact endpoint/interpolation and rejection tests | Implemented, engineering-tested |
| Reusable load cases and combinations | Named v1 cases, common-coordinate gate, algebraic coefficients, contradiction checking | Combination and mixed-coordinate tests | Implemented, engineering-tested |
| Cantilever beam mechanics | Euler-Bernoulli tip plus uniform load, reactions, response, optional yield utilization | Hand-calculated formula tests | Implemented, engineering-tested |
| 3D combined stress | Symmetric tensor principal values, maximum shear, hydrostatic and von Mises stress | Uniaxial and hydrostatic invariant tests | Implemented, engineering-tested |
| Thermal networks | Linear conductance matrix with fixed-temperature nodes and energy residuals | Two-node balance and singular-network tests | Implemented, engineering-tested |
| Forced vibration | Harmonic force and base excitation for one linear damped mode | Direct closed-form comparison and invalid excitation tests | Implemented, engineering-tested |
| Pipe networks | Series Darcy-Weisbach loss plus one balanced parallel bank | Laminar, transition-stop, equal-branch, mass and pressure residual tests | Implemented, engineering-tested |
| Coupled workflow | Self-consistent electrical resistance, Joule heat, lumped temperature, expansion and restrained stress | Closed-form feedback and instability tests | Implemented, engineering-tested |
| Interval propagation | Complete box-corner enumeration, capped at 12 inputs | Exact envelope tests | Implemented, engineering-tested; not a global interval proof |
| Monte Carlo propagation | Seeded independent uniform sampling, up to 10,000 samples | Repeatability test | Implemented, engineering-tested; not a reliability or tail certificate |
| Local sensitivity | Central finite differences at the declared base point | Analytic derivative comparison | Implemented, engineering-tested |
| CAD result overlay | Hash-bound component-level scalar annotation and pass/fail/not-evaluated legend | CLI integration and hash tests | Implemented, engineering-tested; explicitly not a spatial field |
| Composite-shape generation | Hollow shaft, I-beam, L-bracket, and perforated-plate canonical IR plus OpenSCAD bundles | IR validation, deterministic receipt, and CLI publication tests | Implemented, engineering-tested |
| Composite section/mass analysis | Exact idealized volume, surface, centroid, section and mass inertia; unsymmetric L-section coupling | Hand-calculated formula and invariant tests | Implemented, engineering-tested |
| Composite structural screening | Axial/biaxial bending, shaft torsion, cantilever deflection, Euler screening, and ideal modes when inputs are explicit | Formula tests plus fail-closed unsupported-load tests | Implemented, engineering-tested; not FEA |
| FEA adapter and solver | No solver invocation, mesh, convergence, or result-file contract exists | None | Not implemented |
| CFD adapter and solver | No solver invocation, mesh, turbulence model, convergence, or result-file contract exists | None | Not implemented |
| Physical validation | No new experiment or calibrated benchmark was executed for v3 | None | Not performed |
| Independent reproduction | No independent party has reproduced v3 | None | Open |

The full-field items remain unimplemented because relabeling closed-form scalar
results as FEA or CFD would be false evidence. A future adapter must identify
the external solver and version; hash the geometry, mesh, materials, boundary
conditions, solver settings, convergence history, and result files; and retain
validation evidence independently of NeuroCAD's report renderer.
