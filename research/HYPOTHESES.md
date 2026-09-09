# Falsifiable hypotheses

## Status classes

- Historical FULL outcomes: **development evidence**; source provenance incomplete.
- Current implementation: **engineering-verified** by fresh tests/static checks.
- New confirmatory outcomes: **not yet run**.

## H1 — controlled semantic compilation

- H0: on a frozen independently authored in-scope set, NeuroCAD has no practically
  meaningful paired exactness advantage over the strongest compatible simple control.
- H1: NeuroCAD improves semantic exactness by at least 10 percentage points.
- Independent variable: compiler versus train-only retrieval and a reviewed
  grammar-independent parsing baseline.
- Experimental unit: one unique prompt/design specification.
- Primary metric: complete semantic-signature exactness; secondary: explicit
  rejection rate, kernel validity, error category.
- Selection/stopping: no training; one frozen version; evaluate all cases once.
- Statistics: paired effect with bootstrap CI and exact McNemar test; Holm correct
  secondary pairwise comparisons. No timestep/field is treated as a replicate.
- Decision: support only if the lower 95% paired-effect bound exceeds 0.10 and no
  P0 semantic or kernel defect appears.

## H2 — representation invariants

- H0: some valid generated program violates exact round trip, deterministic export,
  or declared constraints.
- H1: all predeclared generated cases pass those invariants.
- Unit: unique generated program. Failure criterion: any mismatch. This is an
  engineering acceptance test, not population inference.

## H3 — fail-closed behavior

- H0: at least one independently authored malformed/unsupported case is silently
  accepted or crashes without a classified error.
- H1: every frozen case is rejected explicitly and no output artifact is published.

## H4 — constraint mechanism

- H0: declared constraints do not improve paired detection of injected parameter
  drift over the identical program with constraints removed.
- H1: constraints increase detection by at least 90 percentage points.
- Required controls: same corruption, program, and validator; only constraint
  presence changes. Randomized/frozen constraints must not be credited as correct
  detection unless their declared relation is actually violated.

## H5 — external validity (confirmatory, not yet run)

- H0: performance on independent natural requests or reviewed public benchmark
  mappings falls below 90% exactness or includes silent false acceptance.
- H1: at least 90% exactness, zero silent unsupported acceptance, and at least 95%
  kernel validity on supported cases.
- Data and sample size remain to be frozen after a leakage audit. Until then:
  `EXTERNAL_EXECUTION_REQUIRED`.
