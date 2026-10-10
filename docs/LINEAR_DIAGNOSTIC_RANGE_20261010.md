# Prevent integer wraparound and range loss in linear diagnostics

## Demonstrated failure

10 of the initial 15 analytical cases failed on the preceding source. For example, int64 [[2**32]] @ [2**32] wrapped to zero and falsely reported a perfect solve. Independent review added a product-underflow counterexample.

Inspected parent revision: `6b3c27f0b07732b7b61dc83035ec2282d7ac2ff5`.

## Implementation

Diagnostics require lossless finite float64 conversion, reject nonzero products that round to zero, use scaled residual norms, assemble the scalar backward-error denominator without overflow, and scale the matrix for rank and conditioning. Exact zero systems remain valid. Analytical and Decimal-based controls cover ordinary and extreme magnitudes.

## Verification

69 passed across the scientific kernel, polynomial and linear diagnostic suites; 18 cases are in the new range file.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -q tests/test_scientific_kernel.py tests/test_scientific_kernel_polynomials.py tests/test_linear_diagnostic_range.py
```

Hosted outcomes are recorded separately in the pull request and the dated execution register after exact-revision verification; local passes alone are not a hosted release gate.

## Preserved scientific boundary

The product-underflow check is deliberately conservative: if any nonzero scalar product rounds to zero, the diagnostic raises instead of asserting a perfect solution, even if a different right-hand-side term could dominate. Unrepresentable residuals and nonzero ratios also raise. No geometry, protected benchmark, CAD provider or retained research result is changed.

