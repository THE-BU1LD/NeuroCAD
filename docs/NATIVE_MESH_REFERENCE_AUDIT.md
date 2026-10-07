# Native mesh reference audit

The maintained Gmsh adapter now evaluates `minSICN` for every generated volume element, querying at most 200,000 elements at once. The 2,000,000-element mesh ceiling is unchanged. Previously, a mesh exceeding 200,000 elements skipped the quality query entirely and returned null minimum/mean quality. Such a mesh could be published without this inverted-element check. The adapter now rejects incomplete, nonfinite or nonpositive results in any batch before publication. The mean is weighted by element count, including an uneven final batch.

## Executed reference parts

The [retained native bundle](../research/results/native-mesh-reference-v1/README.md) contains two STEP files, six ASCII MSH files, per-mesh receipts, an aggregate report and SHA-256 digests. These are actual Gmsh 4.15.2 results. They are separate from the fault-injection tests, which use API doubles to exercise late-batch failure and cleanup.

| Reference | Geometry | Independent expected volume | Fixed relative error tolerance |
|---|---|---:|---:|
| Box | 20 × 10 × 5 mm | 1000 mm³ | 1e-9 |
| Through-hole plate | 20 × 12 × 4 mm, central radius-2 mm hole | 960 − 16π mm³ | 2.5% |

The runner uses the fixed maximum mesh-size grid 4, 2 and 1 mm. It checks the CAD kernel's solid mass against the analytic volume, calls the maintained meshing/serialization backend, then independently sums oriented tetrahedral volumes from the serialized node coordinates and connectivity. It checks finite coordinates, positive individual tetrahedral volume, matching element counts, expected extents and the declared volume tolerance. This independent sum does not call Gmsh's mass or quality functions.

All six retained cases pass. The box mesh volume is 1000 mm³ for each setting. Plate relative volume error ranges from 0.154483% to 0.526629%; straight-sided tetrahedra approximate the circular boundary. The observed minimum SICN ranges from 0.255033 to 0.342522. These values describe these six retained meshes.

## Reproduce

Install the repository's `mesh-gmsh` optional dependency and its native runtime libraries. On Ubuntu the Gmsh wheel needs `libglu1-mesa` and `libxft2` in addition to the usual X11/font dependencies. Then run from the repository root:

```bash
python -m pip install -e '.[mesh-gmsh]'
python scripts/reproduce_mesh_quality.py /tmp/neurocad-native-reference-new
python -m pytest -q tests/test_gmsh_backend.py tests/test_gmsh_contract.py tests/test_gmsh_integrity.py tests/test_gmsh_process.py tests/test_mesh_cli.py tests/test_reference_tetrahedron.py
```

The output directory must not exist. The runner hashes relevant source before and after execution and refuses a completed result if it changes. Each receipt binds the STEP snapshot consumed and the actual MSH bytes. `summary.json` records the environment and source hashes; the git commit is the source base, while file hashes identify working-tree changes used in the run. Hashes of native output are evidence for that run; reproduction does not promise byte-identical STEP headers or native mesh ordering across environments.

## Interpretation and remaining research work

This is a completed engineering reference artifact for a bounded STEP-to-tetrahedron tool demonstration. It establishes executable geometry examples, all-element quality-query behavior, fail-closed publication tests and a transparent analytic volume comparison. The native examples contain 643–5,033 tetrahedra each; the large-query boundary itself is exercised with deliberately small batch limits in fault-injection tests. No runtime or memory advantage on a mesh exceeding 200,000 elements is claimed.

Two constructed parts do not establish broad coverage of industrial geometry, solver convergence, structural safety, manufacturability or learned CAD generation. The existing closed learned-parser/VCG studies remain unchanged. A competitive IMR/SMI research paper would still need a distinct research question, a representative corpus, matched methods and predeclared evaluation beyond these reference controls. A tool/poster contribution can accurately describe the working artifact and its current limits.
