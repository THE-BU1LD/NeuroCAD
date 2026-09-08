# Mathematical tools and their contracts

These are implemented classical methods, not claims of new topology, trained
intelligence, manufacturing certification, or an unlimited CAD system.

## Mesh topology

`neurocad topology part.stl -o topology.json` returns a source-SHA-bound report.
`--require-closed-manifold` exits 1 for an open or singular complex; an ordinary
diagnostic run can successfully report defects. Neither option repairs geometry.

The Python API `core.topology.analyze_triangle_complex(vertices, faces)` accepts
indexed triangles. Connectivity is defined by indices. The STL CLI first applies
Trimesh vertex welding (`process=True`), and states that preprocessing in its
receipt. Welding may identify nearly coincident coordinates: this is not a
robust exact-arithmetic embedding proof.

For the triangle complex, with boundary ranks r1 and r2 over F2:

```
b0 = V - r1
b1 = E - r1 - r2
b2 = F - r2
chi = V - E + F = b0 - b1 + b2
```

Vertex connectivity gives r1. To compute ker(d2), each two-face edge equates
its incident face coefficients; each boundary edge forces a coefficient to zero.
Union-find collapses those equations. Singular edges contribute residual parity
equations, solved by exact bitset Gaussian elimination. This computes F2 homology
for the finite triangle complex, including non-manifold complexes, not persistence
across a filtration or integer torsion. The common manifold path needs no dense
matrix. See the [GUDHI homology API](https://gudhi.inria.fr/python/latest/simplex_tree_ref.html)
for coefficient-field terminology; GUDHI is not a runtime dependency here.

An edge must have one or two incident faces for a surface with boundary. Each
vertex link must also be a single path or cycle. The second condition detects
pinched vertices missed by edge-count/watertightness checks. See the
[CMU mesh-manifold discussion](https://15462.courses.cs.cmu.edu/fall2018/lecture/meshes/slide_013).
`verify_stl` now enforces this condition before certifying kernel mesh validity.

For each manifold component, face-orientation parity propagation determines
orientability; connected boundary cycles give b. An orientable connected compact
surface has genus g = (2 - b - chi)/2. A non-orientable surface instead reports
crosscap number k = 2 - b - chi, never an orientable genus. Classification fields
are null for singular complexes. Disconnected components are classified separately.

Tests cover sphere, torus, disk, Möbius strip, isolated vertices, pinched surfaces,
and random singular complexes compared against a separate dense boundary-matrix
reduction. They check d1*d2 = 0 over F2 and exact Betti/rank identities.

Limits: 100,000 faces, 300,000 vertices, 32 MiB per CLI STL, and 4,096 free
generators in singular-complex reduction. Degenerate/non-finite and duplicate
triangles fail explicitly. Kernel STL verification shares the face/vertex limits.
No self-intersection, knot type, shape equivalence, engineering load, or physical
fit claim follows from these invariants. Matching Betti numbers do not imply
matching CAD geometry. Historical mesh receipts may need re-verification under
the stricter current verifier; old evidence is not silently rewritten.

## Correlated tolerance propagation

```bash
neurocad tolerance docs/examples/tolerance.json -o tolerance-report.json
```

The example is hypothetical input, not measured printer data. Contributions
represent **signed clearance effects**, in millimetres. For nominal n, mean
shifts m, standard deviations s, and correlation matrix R:

```
mean = n + sum(m_i)
variance = s^T R s
worst_case_low = mean - sum(worst_case_i)
recommended_nominal = max(0, confidence_multiplier * sqrt(variance) - sum(m_i))
```

The normal-model probability is P(clearance >= 0). If variance is zero it is a
deterministic comparison. The documented default assumes independence (R = I).
Correlations apply after signs/sensitivities have been propagated into the
clearance contributions: shared dimensional error can cancel rather than add.
This follows the covariance terms in the
[NIST law of uncertainty propagation](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty).
The model here is linear; nonlinear uncertainty propagation is not implemented.

R must have unit diagonal, entries in [-1,1], symmetry, and positive-semidefinite
spectrum. Symmetry/PSD roundoff tolerance is 1e-12; singular matrices are allowed.
Stacks are limited to 128 uniquely named contributions. Invalid matrices, booleans
as measurements, duplicate names, and non-finite arithmetic fail explicitly.

Worst-case intervals and a normal distribution are distinct assumptions: a
normal distribution is unbounded. A three-sigma margin is not a proof or an
empirically measured success rate. No correlation is inferred from coupon data.
Tests include independent variation, perfectly correlated errors, common-mode
cancellation, and pairwise-plausible but globally impossible matrices.

Other existing tools remain bounded aids: Euler–Bernoulli small-deflection
cantilever estimates assume a prismatic, linear-elastic beam; shelf packing is a
feasibility heuristic, not a global optimizer; process costs are approximations.
