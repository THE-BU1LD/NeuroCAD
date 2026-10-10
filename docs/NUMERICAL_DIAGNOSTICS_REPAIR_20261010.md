# Numerical diagnostics repair — 10 October 2026

Base: main `23c7284048512ca8d956c9a2c4c62eb1f8b8ea89`.
This is an engineering correction to `core/scientific_kernel.py`; the S3
pre-outcome boundary and retained research conclusions are unchanged.

## Linear-system diagnostics

The accepted integer input `A = [[2**32]], x = [2**32], b = [0]` produced a
wrapped integer product and a reported residual of zero. The actual residual
is `2**64`. Float residuals at scales such as `1e-200` and `1e200` also produced
zero or infinity when the Euclidean norm squared their entries. An overflowing
normalizer could hide a material error.

Inputs are now converted to floating point before arithmetic. Power-of-two
scaling and stable vector norms evaluate the existing normwise backward error

`||A x - b||_2 / (||A||_F ||x||_2 + ||b||_2)`

without overflowing the denominator. A representable direct residual is retained
for mixed-scale systems. Unrepresentable or nonfinite direct residuals raise a
clear error rather than becoming successful JSON diagnostics. Rank and condition
number use the normalized coefficient matrix. This remains a binary64 numerical
diagnostic, not an exact-arithmetic solution certificate. A physical residual
below binary64 range may round to zero while its scale-free backward error is
still nonzero.

## Monte Carlo covariance admission

The previous absolute `1e-12` symmetry and eigenvalue tolerances admitted a
negative variance of `-1e-14`, and admitted the indefinite matrix
`1e-14 * [[1, 2], [2, 1]]`. NumPy then produced samples instead of rejecting the
invalid distribution. A covariance's physical units should not decide whether
its mathematical structure is valid.

Symmetry and eigenvalue checks now operate relative to the largest covariance
magnitude. Negative diagonal variances are rejected independently. Valid,
already-symmetric inputs retain the existing NumPy sampling call and identical
seeded draws. Only admitted roundoff-level asymmetry is symmetrized, in normalized
units to avoid overflow.

## Verification and limits

- Original diagnostic regression set: **7 failed, 6 passed** before repair.
- Original covariance regression set: **4 failed, 10 passed** before repair.
- Final maintained scientific-kernel tests and 29 new regression cases:
  **47 passed**, using warnings as errors.
- Scoped Ruff, Mypy and patch-whitespace checks passed.
- Local runtime: CPython 3.12.14, NumPy 2.5.3, pytest 9.1.1.

```sh
python -m pytest tests/test_scientific_kernel.py tests/test_linear_system_numerics.py tests/test_monte_carlo_covariance.py -q -W error
python -m ruff check core/scientific_kernel.py tests/test_linear_system_numerics.py tests/test_monte_carlo_covariance.py
python -m mypy core/scientific_kernel.py tests/test_linear_system_numerics.py tests/test_monte_carlo_covariance.py
```

No native CAD kernel, mesher, held-out S3 outcome, provider API, physical part,
release or deployment was exercised by this repair. It establishes the specified
numerical behavior on analytic cases and preserves prior evidence; it does not
certify a geometry, physical design or learned-model claim. The release and
research requirements in `../RESEARCH_CLOSEOUT_2026-09-16.md` still apply.
