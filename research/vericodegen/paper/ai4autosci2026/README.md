# VeriCodeGen — AI4AutoSci 2026 backup submission track

Status: **PRE-OUTCOME / BACKUP ONLY**

This is the secondary AI4AutoSci @ IEEE BigData 2026 candidate behind Space-JEPA.

## Why this track is scientifically legitimate

The historical NeuroCAD typed-parser causal interpretation remains falsified. This submission must **not** revive or repackage that claim.

The paper candidate is the separate VeriCodeGen successor study: a treatment-matched direct-vs-structured language-to-CAD comparison under a prespecified held-out-benchmark design that must be materialized and frozen before outcome access, with a shared verifier, symmetric retry/feedback budget, retained raw outputs, and paired inference.

## Working title

**VeriCodeGen: A Treatment-Matched Study of Verification-Constrained Language-to-CAD Generation**

Possible workshop-facing subtitle after the actual evidence is retained:

**Toward Auditable AI Assistance for Experimental Hardware Design**

Do not imply validated scientific-instrument design, manufacturability, or physical hardware performance unless a separate benchmark actually establishes those properties.

## Workshop fit

This candidate maps to AI4AutoSci's instrument/experiment-design theme as an auditable AI-assisted geometry-generation workflow. The scientific contribution is not "AI can design instruments". The narrow question is whether, after the benchmark and execution manifests are frozen pre-outcome, a structured/verifiable generation arm improves hard-verifier success relative to a treatment-matched direct generation arm on the resulting frozen CAD task set, and what failure modes remain.

## Frozen study hierarchy

Authoritative gates remain issues #21 and #22.

### Benchmark freeze

- exactly 120 held-out tasks;
- IDs `VCG-001..VCG-120`;
- 40 `in_distribution`;
- 40 `compositional`;
- 40 `ood_constraint_stress`;
- each task has at least one machine-checkable hard constraint and one semantic-rubric criterion;
- exact duplicate + 0.88 token-Jaccard near-duplicate audits;
- provider/model identity chosen before execution and forbidden from authoring/selecting the held-out set.

### Stage-2 pilot

- deterministic 12-task pilot: exactly four tasks per family;
- public selection salt frozen before any provider call;
- direct and structured prompt bundles frozen/hashes retained;
- shared verifier and analysis-plan identities frozen;
- provider/model/revision, decoding parameters, seeds, retry/feedback policy, call ceiling, and cost ceiling frozen;
- human correction disabled;
- every raw response, failed attempt, compile log, latency/token/cost record retained;
- paired outputs analyzed under the already declared McNemar/bootstrap plan.

Stage 2 is exploratory. It is not sufficient by itself to establish the full successor claim if the maintained protocol requires Stage 3 on the full frozen benchmark.

## Paper decision rule

This becomes an AI4AutoSci submission candidate only if:

1. the benchmark freeze is human-reviewed before outcome access;
2. the pilot is executed under the exact frozen manifest;
3. the full inference boundary required for the main claim is completed rather than inferred from Stage 1 engineering smokes;
4. semantic-verifier limitations are explicitly measured/reported;
5. all favorable, null, negative, and failed generations are retained;
6. the manuscript never equates compilation/hard-constraint passing with manufacturability or complete semantic correctness.

## Priority relative to Space-JEPA

**Space-JEPA stays Priority 1.** Do not sacrifice its ESA evidence package to force this backup paper over the line. VeriCodeGen should advance in parallel only where it does not create result-chasing or protocol shortcuts.
