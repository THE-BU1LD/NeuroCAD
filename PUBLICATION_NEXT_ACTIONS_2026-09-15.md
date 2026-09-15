# NeuroCAD publication next actions — 2026-09-15

## Publication decision

Treat the maintained deterministic compiler as the flagship research object. Freeze the current supported scope and turn the existing engineering/evaluation evidence into one bounded compiler/evaluation paper. Do not wait for the separate learned S3 extension and do not redefine unsupported general CAD, BREP, simulation, or learned-model behavior as requirements for the current paper.

## Evidence already strong enough to write around

- Supported prompt families and structured-input limits are documented and fail closed.
- The typed canonical representation and semantic validator cover primitives, transforms, hierarchy, references, constraints, cycles, finite values, and deterministic round trips.
- At least one non-hard-coded supported input reaches real OpenSCAD, produces STL, and passes topology/dimensional checks.
- The selected full benchmark records 240/240 geometry-robustness passes.
- The evaluation package contains per-task records, baselines, exact paired tests, failures, and hashes.
- The demo uses the production parser/IR/validator/exporter rather than a disconnected mock path.
- Reproducibility, evaluation, evidence-ledger, baseline, experiment, and research-report artifacts already exist in the repository.

## Missing experiment

The strongest missing publication experiment is a blind independent frozen benchmark on prompts/tasks not authored or iterated against during development. Freeze the task set, acceptance criteria, exact source revision, baselines, and analysis before seeing aggregate outcomes. Preserve every failure.

This is more valuable than adding another feature or learned model because it tests whether the current deterministic compiler generalizes beyond its development benchmark.

## Baseline gap

Reuse the existing baseline framework and keep all comparisons capacity/scope matched. At minimum the paper should report the current documented baselines under exactly the same frozen task set and geometry checks. Do not add deliberately weak baselines. If a baseline cannot support the same input contract, state that boundary rather than silently changing the benchmark.

## Ablation gap

Only claim component contribution when a component can be disabled or replaced without changing the evaluation contract. High-value candidates are the existing semantics/normalization, validation, and constraint-handling stages if the current harness supports clean toggles. Otherwise present an error taxonomy instead of inventing causal ablations. A bounded paper does not require every subsystem to have an ablation.

## Reproducibility gap

The internal package is strong, but external exact-revision evidence is incomplete. Before submission:

1. Freeze one clean Git SHA.
2. Obtain exact-revision CI receipts on the declared platform matrix.
3. Build wheel/sdist from that same clean revision and record checksums.
4. Install anonymously or in a fresh environment outside the checkout, including real OpenSCAD integration, and retain the receipt.
5. Bind benchmark manifests, generated geometry, metrics, source revision, environment, and release artifacts into one publication evidence manifest.

## Manuscript gap

The repository contains substantial research/evaluation reports but no clearly designated canonical submission manuscript in the current root evidence set. Build the manuscript from the existing final research report, evaluation report, baseline documentation, reproducibility record, and evidence ledger rather than starting a new research direction.

The paper should center three contributions:

1. a typed deterministic representation and fail-closed compiler path for the explicitly supported prompt families;
2. real OpenSCAD end-to-end geometry verification with a frozen benchmark and exact acceptance checks;
3. a transparent failure/evidence/reproducibility framework that separates supported, legacy, refuted, and blocked surfaces.

## Submission gap

A live target venue, truthful final author order/affiliations, licensing/release metadata, final paper format, and submission receipt are not yet part of the current evidence package. Select the venue only after the blind-benchmark scope is frozen so formatting pressure cannot change the scientific protocol.

## Single next move

Freeze the blind independent benchmark protocol and exact candidate SHA. Execute it once with the existing baselines and acceptance checks, preserve adverse cases, then convert the existing research/evaluation reports into the canonical paper around that frozen result.

## Stop rules

- Do not start S3 learned-outcome evaluation before its existing pre-outcome authorization/freeze conditions are satisfied.
- Do not broaden the supported CAD claim to general CAD/BREP/simulation.
- Do not modify the blind benchmark after aggregate outcomes are visible.
- Do not hide failures or relax geometry acceptance criteria to improve the paper.
