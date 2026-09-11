# NeuroCAD external evaluation protocol v0

**Protocol status:** PREOUTCOME / DATA_NOT_MATERIALIZED / NOT_EXECUTED  
**Protocol ID:** NC-EXT-EVAL-V0  
**Date frozen:** 2026-09-10  
**Method under evaluation:** deterministic NeuroCAD compiler only; no trained model is part of the method.

## Purpose

This protocol addresses the largest remaining conference-readiness gap in the deterministic NeuroCAD study: the current generated benchmark is authored from the same declared grammar as the compiler and therefore measures controlled conformance, not independent natural-language validity. The historical typed-parser causal claim remains falsified and is outside this protocol.

The external evaluation is designed to test whether a frozen NeuroCAD revision can correctly accept, compile, and semantically reproduce independently authored prompts that remain inside the documented product scope, while rejecting independently authored prompts that are incomplete, unsupported, ambiguous, or outside that scope.

## Hard integrity boundaries

1. The exact NeuroCAD source revision, package lock, OpenSCAD identity, scoring code, prompt families, acceptance rules, and comparator identities must be frozen before reference labels are visible to the NeuroCAD developers.
2. External challenge prompts must be authored or curated by people who did not implement the evaluated parser rules for the frozen revision.
3. Prompt authors may read the public supported-scope documentation, but they must not read the parser source, regexes, benchmark generator, private failure cases, or hidden reference labels while authoring the challenge.
4. A separate adjudicator must independently verify each reference signature or rejection label before outcome access.
5. No prompt, label, comparator setting, retry budget, verifier threshold, exclusion rule, or statistical test may be changed after outcome access to rescue a result.
6. Every attempted prompt and every failure must be retained. There is no silent task deletion.
7. Human correction of generated CAD is forbidden for the primary automated endpoint.
8. Kernel unavailability is an infrastructure result and must not be converted into a semantic success.
9. Results from this protocol cannot be used to rehabilitate the falsified historical typed-parser causal claim.
10. Passing this protocol would support only the declared deterministic compiler scope. It would not establish general text-to-CAD intelligence, BREP/STEP correctness, manufacturability, physical fit, safety, or learned geometric reasoning.

## Evaluation population

The target challenge contains **at least 160 independently authored prompts** before exclusions are known to the system under test:

- at least 120 valid, fully dimensioned prompts that are intended to be within the documented supported language;
- at least 40 invalid or unsupported prompts that should fail closed.

The 120 valid prompts must contain at least 20 examples from each of these semantic families where applicable:

- plain rectangular plates/boxes;
- plates with circular holes;
- plates with rectangular slots;
- rounded plates with explicit corner radius;
- open-top rectangular enclosures with explicit wall thickness;
- dimensioned primitives: box, cylinder, and sphere.

The valid set must include unit and wording variation rather than copying repository templates verbatim. At minimum, the materialized set must contain millimetres, centimetres, inches, `x`/`by` dimension separators, and both sequence-style and labelled-dimension phrasing supported by the public contract.

The invalid set must include predeclared categories for missing dimensions, missing feature counts, missing feature sizes, unsupported requested features, unsupported domains, ambiguous/multiple dimension sequences, non-finite or out-of-range values, extra unconsumed prose, and normalization-destructive characters.

## Data record schema

Before evaluation, each challenge record must be serialized as a UTF-8 JSON object with these fields:

- `task_id`: stable opaque identifier;
- `prompt`: exact user-facing prompt;
- `validity`: `valid` or `reject`;
- `family`: predeclared semantic or invalid category;
- `expected_signature`: canonical semantic signature for valid tasks, otherwise `null`;
- `expected_error_class`: predeclared rejection class for reject tasks, otherwise `null`;
- `author_id`: pseudonymous external author identifier;
- `adjudicator_id`: pseudonymous adjudicator identifier distinct from `author_id`;
- `license_or_permission`: provenance statement permitting research use;
- `source_note`: whether the prompt was independently authored or derived from a public, licensed source.

The materialized JSONL file must be canonicalized and SHA-256 hashed before evaluation. The hash, record count, family counts, and author/adjudicator counts must be written to an immutable receipt.

## Freeze receipt required before labels are opened

The execution receipt must bind all of the following:

- exact Git commit SHA;
- source-snapshot SHA-256 from the maintained research provenance machinery;
- `requirements-research.lock` SHA-256;
- Python version and platform;
- OpenSCAD executable version and executable SHA-256 when kernel evaluation is enabled;
- challenge JSONL SHA-256 and record count;
- scoring implementation SHA-256;
- comparator implementation/configuration identities;
- retry budget (one deterministic NeuroCAD attempt per prompt for the primary endpoint);
- mesh-verifier policy and thresholds;
- statistical plan below;
- explicit `outcomes_observed=false` at freeze time.

If any required identity is missing, the run remains `NOT_AUTHORIZED`.

## Systems compared

The primary system is the frozen NeuroCAD compiler.

At least these repository baselines must be run on the identical challenge where applicable:

1. `fixed_box`;
2. `raw_numbers_no_unit_normalization`;
3. `normalized_dimensions_only`;
4. `nearest_neighbor_retrieval`, fitted only on the existing labelled training subset and never on external challenge labels.

For a conference claim of comparative language understanding, a **strong grammar-independent comparator is additionally required**. Its provider/model/tool identity, prompt, decoding settings, retry budget, CAD output format, and verifier must be frozen before external labels are opened. If that comparator cannot be executed reproducibly, the manuscript must weaken comparative claims rather than substitute a weaker baseline post hoc.

## Primary endpoints

Two primary endpoints are reported separately; they must not be averaged into one headline score:

1. **Valid semantic exact rate:** fraction of valid prompts whose generated canonical program passes validation and whose semantic signature exactly matches the adjudicated reference under the repository's predeclared numeric tolerance.
2. **Fail-closed rejection rate:** fraction of invalid/unsupported prompts for which NeuroCAD returns no program and an explicit validation failure.

A valid prompt that is rejected is a failure for endpoint 1. An invalid prompt that produces any program is a failure for endpoint 2.

## Secondary endpoints

- valid output rate;
- family-stratified semantic exact rate;
- unit/wording-stratified semantic exact rate;
- error-category rejection rate;
- deterministic repeat agreement on the same exact revision;
- exact IR round-trip rate;
- deterministic OpenSCAD byte equality;
- OpenSCAD compile success when the executable is available;
- for successfully compiled meshes: finite vertices, non-empty mesh, positive volume where expected, watertightness, winding consistency, connected-component count, and expected extents under the existing shared verifier.

Kernel and mesh endpoints are engineering checks, not evidence of manufacturability or physical correctness.

## Statistical plan

The unit of analysis is the prompt, not repeated program executions.

For each primary endpoint report:

- numerator and denominator;
- exact 95% binomial confidence interval;
- family/category-stratified counts and intervals.

For paired system comparisons on the same prompts, use an exact two-sided McNemar test on pass/fail discordances and report the 2x2 discordance table. Report effect size as the paired absolute success-rate difference with a prompt-clustered bootstrap 95% interval using a predeclared seed and at least 10,000 resamples.

H1-style comparative claims are allowed only when the comparison and endpoint were frozen before outcome access. Secondary analyses are descriptive unless separately preregistered.

## Exclusion policy

Allowed pre-outcome exclusions are limited to:

- duplicate `task_id`;
- invalid JSON/schema;
- missing provenance/permission;
- author and adjudicator are the same person;
- prompt is an exact duplicate of another challenge prompt;
- prompt is provably copied verbatim from NeuroCAD's existing generated benchmark or regression fixtures.

All exclusions must occur before scoring and be retained in an exclusion ledger with reason codes. No exclusion is allowed because NeuroCAD or a comparator failed.

## Perturbation / robustness extension

A robustness extension may be materialized from a frozen subset before outcomes are observed. Each source prompt may receive only predeclared transformations that preserve or deliberately break semantics, such as:

- supported synonym/word-order variation;
- `x` versus `by` separators;
- equivalent supported units;
- harmless whitespace/case changes;
- one deliberately missing required field;
- one deliberately unsupported trailing request.

Semantic-preserving perturbations must keep the same expected signature. Semantic-breaking perturbations must carry a predeclared rejection label. The transformation generator and seed must be frozen before scoring.

## Stop rules and result interpretation

- No adaptive prompt rewriting after failures.
- No parser edits after label access inside the confirmatory run.
- Any source change starts a new protocol version and requires a new challenge freeze before confirmatory scoring.
- Any missing strong comparator must be reported as a limitation.
- Any external-author conflict or label disagreement is resolved before outcome access or the task is excluded under the predeclared policy.

### Conference-readiness decision

`NC-EXT-EVAL-V0` closes the external-validity gate only when all required receipts, independent authorship/adjudication, full raw outputs, exclusion ledger, baseline outputs, primary statistics, and source-bound artifacts are retained. Merely adding this protocol does **not** close that gate.

Current state: **PROTOCOL_FROZEN / DATA_NOT_MATERIALIZED / OUTCOMES_NOT_OBSERVED / EVIDENCE_PARTIAL**.
