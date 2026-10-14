# Integrated numerical and geometry candidate

This candidate combines four existing repairs and preserves their commit
histories and earlier evidence. Main at the start of integration was
`23c7284048512ca8d956c9a2c4c62eb1f8b8ea89`.

| Component | Parent commit | Behavior |
| --- | --- | --- |
| PR #95 | `6b3c27f0b07732b7b61dc83035ec2282d7ac2ff5` | Polynomial differentiation at zero and Jet dimensions |
| PR #96 | `c906105907cdd710b717d04d5d75b95ec3cac54a` | Reject invalid quadratic variance and malformed tolerance inputs |
| PR #97 | `e87726d3c7efe575e697770cbba5a064ec371e35` | Scale-aware linear residuals and covariance admission |
| PR #98 | `982eafb1665a9c31868cfcfda7c75571885c2cd8` | Scale-invariant mesh normalization and finite translation handling |

The two changes to `core/scientific_kernel.py` affect different functions and
merged automatically. Independent AST inspection confirmed that their changed
functions were retained. Engineering-math and mesh changes are in separate
modules. Other active artifact-publication and native-backend candidates are
outside this integration.

## Additional failure discovered during review

Converting integer inputs to float before matrix multiplication repaired fixed
integer overflow, but it could also erase a real residual. The integrated
predecessor returned residual zero and backward error zero for:

```python
linear_system_diagnostics(
    matrix=((1,),),
    rhs=(2**53,),
    solution=(2**53 + 1,),
)
```

The supplied equation has residual one. Its two distinct integers round to the
same float64 value. The same problem occurs in matrix coefficients, in negative
and unsigned integers, and when a Python sequence mixes floats and integers.

The diagnostic now checks original Python/NumPy integer scalars for lossless
float64 conversion before using the numerical arrays. Object-array inspection
preserves mixed-sequence integer identity, and comparison uses Python `int` and
`float` so NumPy's type-promotion equality cannot hide the difference. A lossy
integer raises `ValueError` instead of publishing a misleading residual.
Exactly representable large integers remain supported. Inputs that were already
rounded before reaching the API cannot be reconstructed by this check.

The 16 new regressions produced **12 failures and four passing exact-value
controls** on the integrated predecessor. The repaired numerical-kernel tests,
including all 16 new cases, passed **96 tests with warnings treated as errors**.
These are analytical software fixtures, not observations from a protected study.

## Verification records

The full product-suite output and source hashes are in
`research/verification/numerical-integration-20261010/`. The integer baseline
receipt binds its source and tests separately. The final integration receipt
records the actual commands, exit statuses, environment, skipped optional
backends, and full-suite outcome. Hosted status belongs to the exact PR revision
and is linked in the PR description.

```bash
python -m pip install -e '.[dev]'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -q tests
python -m ruff check core/scientific_kernel.py core/engineering_math.py core/mesh_geometry.py tests/test_linear_integer_admission.py
python -m mypy core/scientific_kernel.py core/engineering_math.py core/mesh_geometry.py
```

The first full-suite attempt stopped during collection because the scratch
Python environment lacked `jsonschema`. Installing the declared project/dev
dependencies in an isolated environment resolved that prerequisite. No product
or test assertion was weakened to accommodate the missing dependency.

The complete local run then finished with **1,289 passes, nine skips, and two
failures** in 406.50 seconds. Both failures occur when Python creates an
`AF_UNIX` socket and receives `PermissionError` from this execution environment,
before daemon behavior can be checked. The tests are unchanged and remain
required in hosted CI. This local run is not reported as a green full suite.
All executable sources were stable throughout the run. A later lint correction
removed one extra blank line in the imported mesh test and a whitespace
correction removed the extra EOF blank line in the imported polynomial test.
Both ASTs were verified unchanged. Final scoped Ruff, Mypy and source/document
whitespace checks pass; raw stdout logs preserve original traceback whitespace.
The initial lint failure and formatting-only changes remain in the receipts.

## Scientific and release boundary

The external evaluation protocol, independent challenge requirements, historical
source-bound controlled run, and frozen evidence remain intact. The historical
typed-parser causal claim remains falsified and the research disposition remains
`EVIDENCE_PARTIAL`. This candidate establishes numerical software behavior only.
Independent challenge data/adjudication, a strong comparator, external
replication, physical validation, and final release evidence are separate gates.

The component PRs remain reviewable; this integration does not close or merge
them or publish a release. No scientific outcome campaign was run.
