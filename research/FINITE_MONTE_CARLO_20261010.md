# Finite Monte Carlo sample summaries

## Problem and exact scope

Finite model outputs can have representable means, standard deviations and
quantiles even when intermediate sums, squared deviations or endpoint
differences overflow binary64 arithmetic. The predecessor's direct NumPy
reductions could return nonfinite values for those cases.

This revision changes the outcome-summary arithmetic in
`core/scientific_kernel.py::monte_carlo_propagate`. The input distributions,
correlation handling, random generator, seed, draw order, model calls, quantile
levels and returned report schema retain their existing behavior. It implements
the existing sample-statistic definitions:

\[
\bar y=\frac1n\sum_i y_i,\qquad
s^2=\frac1{n-1}\sum_i(y_i-\bar y)^2,\qquad
\mathrm{SE}=s/\sqrt n.
\]

`statistics.mean` and `statistics.stdev` perform exact-ratio reductions of the
finite binary64 samples. The standard deviation retains Bessel's correction.
For each existing probability `p`, the implementation sorts the outcomes and
forms the linear-quantile index `(n-1) * Fraction.from_float(p)`. It interpolates
between adjacent sorted endpoints as an exact rational convex combination and
converts to float only at the end. This avoids overflowing an endpoint
subtraction. The probability is the actual binary64 value supplied by the
existing quantile level, not a newly selected decimal probability.

Any nonfinite sample or unrepresentable reported statistic is rejected. An
unrepresentable summary raises
`ValueError("sample statistics exceed the finite numerical range")`; it cannot
be returned as a successful report containing infinity or NaN. Standard error
uses the reported standard deviation and the existing square-root operation.

The sample count and sorting complexity remain unchanged. Exact-rational
reductions carry additional integer-arithmetic cost; this bounded pass does not
establish throughput at large sample counts. Correct linear quantiles may differ
in their last bits from the predecessor's floating-point operation order. This
is a prospective arithmetic revision. Historical reports are not regenerated or
silently relabeled.

## Discriminating evidence and reproduction

`development/finite_monte_carlo_20261010/contract.json` preceded implementation
and execution. Its exact incoming canonical state and all raw command outputs
are retained alongside the evidence.

| Retained attempt | Outcome | What it checks |
| --- | --- | --- |
| `baseline.json` and logs | 10 failed, 11 passed | Predecessor failures on finite extreme sample statistics. |
| `candidate.json` and logs | 63 passed, warnings treated as errors | 21 new cases plus the existing scientific-kernel and interval-division contracts. |
| `demo_command.json`, `demo/report.json` | Completed | Three retained generated cases, including an actual seeded eight-draw linear Gaussian model. |

The new cases use independent Fraction and high-precision Decimal oracles for
sample means, Bessel-corrected standard deviations and linear quantiles. They
cover signed extreme values, adjacent large floats, subnormal samples, zero
variance, ordinary values, unrepresentable standard deviations, permutation
invariance and exact preservation of the seeded draws supplied to the model.
The demo retains raw draws, outputs, complete reports and source hashes.
Independent source review checked the reductions, quantile definition, failure
admission and unchanged sampling path without additional execution.

After installing the existing project development environment, run from the
repository root with a fresh output directory:

```sh
python -m pytest -q -W error -o addopts= tests/test_monte_carlo_finite_summary.py tests/test_scientific_kernel.py tests/test_interval_division.py
python scripts/demo_finite_monte_carlo.py --output /tmp/new-finite-monte-carlo
```

Commands, environments, elapsed time, child peak RSS, exit status and log hashes
are retained. `closure.json` records actual budget use and final source hashes.
The original baseline tests are also preserved byte-for-byte; subsequent test
changes only sorted imports. The numerical implementation in the passing gate
and final revision is identical.

## Scientific boundary

The parent is PR #100 at `f560df8dfd31d0df9bf5886ec78a1fab839e3f5a`. Existing
canonical records, partial evidence and the falsified typed-parser claim remain
unchanged. This correction establishes sample-summary arithmetic on the declared
fixtures. It does not establish a physical uncertainty model, empirical coverage,
manufacturability or safety. The independent protected challenge remains unrun.

This finite local session closes after the retained gate, demo and source review.
Its draft uses `[skip ci]` so that the much broader inherited product, browser,
CAD and research workflows are not added to the session's execution budget.
Those wider gates remain necessary before a release; this draft is an
engineering correction, not a completed scientific release.
