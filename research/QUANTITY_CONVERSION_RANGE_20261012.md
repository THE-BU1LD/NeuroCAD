# Quantity conversion range repair — 12 October 2026

## Defect and scope

At exact PR101 head `48237e7afa575b4678e137707cce5a7303f7e784`, `quantity(1e308, "m").to("mm")` returns infinity. The output bypasses the finite-value contract used by other Quantity construction and arithmetic paths. Eight sign/unit-pair cases reproduce this.

The sole runtime change validates the converted result with the existing `_finite` helper. Finite ordinary/extreme conversions, signed zero, existing underflow-to-zero behavior and dimension mismatch rejection remain covered. This is not arbitrary precision, an underflow fix, a physical-validation result or a change to the Monte Carlo algorithm.

## Evidence

The parent kernel was reconstructed from the #100 source-distribution artifact and exact #101 delta, and its complete SHA-256 was verified against the published source. Baseline: 8 failed, 112 passed, 1 deselected. Corrected: 120 passed, 1 deselected. Environment: Python 3.13.5 and NumPy 2.3.5, one numerical thread.

There are 23 new conversion regressions and 47 separately authored sample-standard-deviation/rounding review checks. The latter use a centered exact-Fraction variance calculation and Decimal square root, plus exact rational midpoint ties. They already pass on the unchanged PR101 kernel. These assistant-authored fixtures are not human peer review.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest \
  tests/test_quantity_conversion_range.py tests/test_summary_independent_review.py \
  tests/test_scientific_kernel.py tests/test_scientific_kernel_polynomials.py \
  -k 'not monte_carlo' -q -W error
```

The inherited 40,000-draw seeded case is deliberately deselected. No random-model draws, trained model, protected outcome, scientific comparison or paid computation is part of this session. Prior budgets remain closed; the earlier recorded deviation is retained.

See `research/development/quantity_conversion_20261012/closure.json` for source identities, counts and timing. The pre-execution local contract and raw stdout/stderr remain in the conversation handoff. This append-only session record preserves the existing canonical state's historical disposition; its index should be reconciled during integration. The stack remains draft and unmerged. Supported-version CI, independent source review and release gates remain open.
