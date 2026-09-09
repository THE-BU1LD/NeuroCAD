# Final research report

## Actual project

NeuroCAD compiles a bounded dimensioned-English language into typed millimetre CSG
programs and deterministic OpenSCAD, optionally executing and checking STL meshes.
Formally it is a partial function `C(x)=p` or explicit error, followed by static
validator `V(p)`, deterministic serializer/exporter, OpenSCAD kernel, and bounded
mesh predicate. Full equations are in `research/MATHEMATICAL_SPEC.md`.

## Evidence status

Current implementation is engineering-verified. Historical controlled outcomes are
development evidence. No confirmatory or external validation was produced in this
audit. Negative evidence—especially the falsified historical parser claim and the
FULL run's incomplete provenance—is retained.

## Scientific result

The historical bundle reports 240/240 exact generated-contract tasks versus
144/240 retrieval, 110/240 raw-number parsing, and 0/240 fixed output; 1,000/1,000
generated IR invariant checks; rejection of 240 records drawn from eight repeated
malformed templates; 200/200 constraint-corruption detections versus 0/200 without
constraints; 200/200 automated edits; and 240 kernel records. These numbers are not
newly rerun confirmatory evidence. The manifest lacks producing-source provenance
and records 181 resumed kernel samples.

## Fresh development execution

`NC-DEV-AUDIT-20260908-NATIVE` was executed after the audit changes as a small
development run: 30/30 compiler tasks, 24/24 generated IR programs, 16/16 unique
malformed fixtures, 12/12 constraint detections versus 0/12 without constraints,
12/12 automated edits, and 7/7 fresh OpenSCAD mesh/render cases passed. Artifact
reuse was disabled and all 47 manifest artifact hashes verified. This run was made
from a dirty audit worktree and is explicitly development evidence, not frozen
confirmatory evidence. A first sandboxed attempt retained valid meshes but failed
all PNG renders because OpenSCAD could not create `NSOpenGLContext`; native
execution then completed.

An immutable audit-authored prompt challenge subsequently passed 24/24 cases:
15 accepted semantic signatures and nine required rejections across documented
aliases, named/mixed/imperial units, singular features, unsupported features,
ambiguity, invalid numerics, missing information, and lossy characters. The
dataset hash is
`08325ac375bb1e337d0bb760fe2d86e3638e74e13a1df3857e781d046ac48b64`.
Because it was authored after implementation inspection, this is robustness-oriented
development evidence rather than independent external validation.

A new normalized-dimensions-only baseline was implemented to isolate unit-aware
dimension extraction from feature semantics. On the 48-case generated engineering
benchmark it scored 22/48 (45.83%), versus 18/48 (37.5%) for raw unnormalized
numbers and 48/48 for NeuroCAD. It failed all hole/slot/enclosure feature cases,
supporting only the narrow explanation that unit normalization helps but does not
explain feature-aware compilation.

## Conference readiness

**EVIDENCE_PARTIAL.** The software artifact is substantially stronger than the
scientific claim. The next highest-value experiment is a blind, independently
authored, frozen in-scope prompt/specification benchmark with a strong compatible
baseline and fresh kernel execution from a published exact revision.

## Final verification — 2026-09-09

- 435 tests passed in the final full regression run.
- Ruff passed; mypy passed across 55 source files; `pip check` passed.
- Compile-all and Bandit passed. PyPI advisory access timed out; the OSV retry
  completed and reported no known vulnerabilities in the pinned lock.
- Native OpenSCAD PNG preflight passed.
- `NC-ASTRA-VERIFIED-FINAL-20260909` passed 30/30 compiler cases, 24/24
  generated IR checks, 16/16 unique malformed rejections, 12/12 constraint
  interventions versus 0/12 without constraints, 12/12 edits, and 7/7 fresh
  kernel/render cases. Artifact reuse was disabled; 47/47 hashes verified.
- The immutable prompt challenge passed 24/24 cases.
- Fresh wheel and sdist passed archive safety inspection: 49 wheel members and
  243 sdist members before the final documentation-only cleanup.

## Reproduction

Use `scripts/preflight.sh`, `scripts/test.sh`, `scripts/run_smoke.sh`, and then
`scripts/reproduce_research.sh` for the expensive fresh archival suite. See
`REPRODUCIBILITY.md` and `research/protocols/`.
