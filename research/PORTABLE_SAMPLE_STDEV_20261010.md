# Portable sample standard deviation: bounded correction

## Why this follow-up exists

The earlier finite Monte Carlo summary change was verified by 63 selected tests
on Python 3.12. Its source and generated demonstration remain preserved under
`research/development/finite_monte_carlo_20261010/`. Final dependency review found
that this evidence did not cover the project's Python 3.10 reduction behavior.

In the [CPython v3.10.21 implementation](https://github.com/python/cpython/blob/v3.10.21/Lib/statistics.py),
`stdev` calls `variance` and then takes its square root. For floating inputs the
variance has already been converted to a float. Thus a finite sample standard
deviation can be lost when its square overflows or underflows. This is an
upstream-version difference, not a claim that the original Python 3.12 test
receipt was invalid or executed on Python 3.10.

The new contract was recorded before implementation or execution. It preserves
the closed earlier budget and starts a separate bounded corrective session.
The question is whether a portable reduction can correctly round the sample
standard deviation without constructing a floating-point variance.

## Exact arithmetic specification

The public Monte Carlo path has already admitted finite binary64 outcomes
`x_i` and an integer sample count `n >= 2`. Each outcome has an exact integer
ratio `a_i / d_i`; each `d_i` is a power of two. Let `D = max(d_i)` and let
`z_i = a_i * (D / d_i)`. The Bessel-corrected sample variance is exactly

\[
V = \frac{n\sum_i z_i^2 - (\sum_i z_i)^2}{n(n-1)D^2}.
\]

All numerator and denominator operations use Python integers. In particular,
the cancellation in the numerator does not use floating-point subtraction.
Two passes find `D` and accumulate the integer sums with constant auxiliary
storage. The work is linear in the number of outcomes, with integer operation
cost determined by the binary64 exponent range and the sample-count bit length.

For the nonnegative rational `V = N / B`, integer bit lengths and one comparison
find `e = floor(log2(V))`. Its square root has binary exponent `e // 2`.
The binary64 rounding grid has quantum `2**q`, where
`q = max(e // 2 - 52, -1074)`. The minimum quantum handles subnormal values.
Scale the rational by `2**(-2*q)` to obtain integer ratio `A / C`, and compute
`k = isqrt(A // C)`. This is the exact lower grid index because integer square
root is monotone and `floor(sqrt(A / C)) = isqrt(A // C)`.

Compare `4*A` with `C*(2*k+1)**2`. A larger left side selects `k+1`; a smaller
left side selects `k`; equality selects the even index. The resulting integer
is exactly representable before `math.ldexp` installs its power-of-two scale.
This handles ordinary values, the normal/subnormal boundary, exact halfway
cases, a carry to the next exponent, and rounding to zero. An overflowing final
result raises and is translated by the public API into its existing finite
range error. Zero variance returns positive zero.

The helpers are private. Their input domain is the finite binary64 outcomes
already validated by `monte_carlo_propagate`; they are not a new general-purpose
numeric input API. No Python 3.12-specific statistics implementation is used
for the standard deviation. The mean, quantile interpolation, sample generator,
draw order, covariance checks, Bessel correction and report schema are preserved.

## Retained evidence

The baseline replays the documented variance-then-square-root operation sequence
under the installed Python 3.12 interpreter: four cases fail and one constant
control passes. It exposes variance overflow, subnormal loss, total underflow,
and inaccurate subnormal variance rounding. This is explicitly **not execution
by an actual Python 3.10 interpreter**.

The final selected gate passes **93 tests with warnings treated as errors**:
the original 63-case cohort and 30 new cases. New evidence includes independently
centered Fraction/Decimal sample-variance oracles, exact rational halfway cases
with ties to even, ordinary and extreme exponents, subnormal values, zero,
invalid rational domains, insufficient sample counts, and the overflow midpoint.
The unchanged public draw-identity and report-schema controls remain in the gate.
Ruff passes for the changed source and new tests.

The original generated demonstration is retained at its original source hash;
it was not rerun or relabeled as evidence from the new implementation. No new
demonstration, training, scientific campaign, protected evaluation or paid
workload was executed in this corrective session. Complete command receipts,
source hashes, logs, independent review and budget use are recorded in
`research/development/portable_sample_stdev_20261010/closure.json`.

The session closes **with a recorded budget deviation**. Its contract set an
unqualified maximum of 32 samples per case while also explicitly selecting the
inherited `test_monte_carlo_is_seeded_and_matches_linear_reference` regression.
That unchanged test makes two 20,000-sample calls: 40,000 generated samples in
one case. The 30 new cases use at most four samples. This was identified during
closure, after the selected gate, and the prospective contract is not rewritten.
Two test commands used 3.554 seconds of the 90-second limit; one lint command
used 0.168 seconds. Numerical evidence remains valid within its engineering
scope, but the unqualified sample ceiling was not satisfied. No additional
execution was used to replace or conceal this deviation.

## Scope and next gate

This establishes the specified arithmetic on generated engineering cases and
provides a source-level rounding argument. The available interpreter is Python
3.12; an actual supported-version/platform CI matrix remains a release gate.
The finite Monte Carlo report is a sampling estimate under its declared input
distribution. Correct arithmetic does not establish coverage calibration,
physical validity, kernel-backed solid correctness, manufacturing safety,
language generalization or completion of the scientific research project.
Existing negative and partial conclusions remain unchanged in the canonical
research state, and the protected challenge remains unrun.

To reproduce the selected engineering gate in an appropriately provisioned
checkout:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q -W error -o addopts= tests/test_portable_sample_stdev.py tests/test_monte_carlo_finite_summary.py tests/test_scientific_kernel.py tests/test_interval_division.py
```

Reproduction is a new execution session and must receive its own prospective
budget; the recorded corrective budget closes with its retained evidence.
