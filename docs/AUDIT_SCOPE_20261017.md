# Requirement and evidence admission audit — 17 October 2026

Base: `64ebea82d402f6dc6073f82f01367ecba8cae6d0`. This change tightens existing input contracts; it adds no geometric operation, trained model or scientific result.

## Repaired behavior

The exact requirement verifier rejects boolean, nonnumeric, negative and nonfinite dimension measurements with structured binding errors. Output extents must be a three-element numeric vector. Expected dimensions, measured dimensions and tolerances cannot silently round nonrepresentable integers into equality. Exactly representable large integers remain admitted; this does not establish CAD kernel precision at those scales. Kernel validity requires an actual boolean. False is a normal failed check; malformed evidence is an error.

The standalone readiness audit rejects duplicate JSON keys, nonfinite numbers, malformed manifest containers, noninteger schema versions, invalid JSON Pointer escapes and noncanonical array indices. Nested assertion values compare types recursively. Evidence parsing reads at most 8 MiB and hashes the exact bytes parsed. Source hashing is streamed. Schema failure returns a non-complete structured result, including the Markdown CLI path.

## Acceptance contract

For an admitted, versioned geometry G and represented mandatory predicates R, acceptance requires every predicate in R to return true using the declared target, units, tolerance and measurement basis. Missing evidence, unsupported required checks, malformed values and stale bindings prevent acceptance. This is conditional correctness of represented requirements; it cannot establish that R captures every human intention.

Keep outcomes distinct: a valid proposal still requires review; missing recoverable intent requires clarification; unsupported operations remain unsupported; contradictory or geometrically infeasible requests are rejected; execution/numerical failure is recorded separately from model rejection. Do not infer completion from refusal, empty evidence, a preview, feature history or aggregate volume alone.

The existing final-bore contract remains isolated Cartesian cylindrical bores on one valid manifold solid. Feature history is construction evidence, aggregate checks concern only global properties, and the frozen C3D wall-thickness pilot remains narrow. No general sketch solver, freeform geometry, assembly mechanics, general FEA/CFD, physical fit or manufacturing certification is added.

## Validation and deployment boundary

Targeted local checks use actual source modules while bypassing the eager core package initializer to stay under a 96 MiB process-tree budget. They are not normal package import, installed-wheel, native, browser or full-suite acceptance. Exact-head hosted checks must be recorded separately before merging or publishing. Existing maintained CI collects the new regression tests. Original failing counterexamples, a rejected invalid-Feature-IR suspicion and initial lint failures remain retained in the audit archive.

The published immutable alpha remains v0.5.0a6. A new release needs a separate version/tag and exact artifact provenance plus anonymous installation acceptance. This document is not a release receipt.

## Research and external gates

The original compiler study remains terminal MIXED. The successor remains Checkpoint 1 BLOCKED and later checkpoints NOT_EVALUATED. Authored tests do not establish generalization. The prior 32-case language diagnostic remains observed development evidence.

Current primary-source checks confirm relevant overlap: [CIT-CAD](https://arxiv.org/abs/2609.07434v2) uses explicit intent constraints and verification/repair; [CADTests](https://arxiv.org/abs/2605.07807v1) evaluates geometry/topology requirements with executable tests; [CADEngBench](https://arxiv.org/abs/2608.09296) includes functional editing, assembly and simulation evaluation; [ReliCAD](https://arxiv.org/abs/2609.22325) addresses constraint-aware modeling and verification feedback. This limited review does not establish a new NeuroCAD contribution or reproduce their results.

Still required: independent task authors and adjudicators; a compatible matched comparator and prospective statistical plan; independent reproduction; calibrated physical measurements; intended-user/accessibility sessions; licensed external CAD assets and tools; external engineering pilots; and authentic recovery of four missing historical logs where available. Hashes prove consistency, not authorship or truthful measurement. Use the existing external-validation protocol; do not replace missing data with generated observations.
