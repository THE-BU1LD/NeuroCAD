# Reviewer 1 — empirical/statistics

## Summary
The artifact evaluates a deterministic compiler on data generated from its declared grammar. Engineering execution is unusually transparent, but scientific external validity is weak.

## Strengths
Per-task records, paired controls, explicit failures, exact McNemar tests, and separation of static from kernel validity.

## Weaknesses and fatal concern
The 100% headline is essentially contract coverage. The historical run lacks producing-source identity and reused 181/240 kernel artifacts. This prevents accepting it as confirmatory evidence for current code.

## Major concerns
Weak baselines; eight malformed templates repeated 30 times; no independently authored prompts, human study, or external benchmark; no componentwise frontend ablation.

## Minor concerns
Wilson intervals can invite population interpretation despite deterministic generation. Local timing is not portable.

## Missing experiments
Blind independent prompt set, strong compatible baseline, systematic paraphrase/noise robustness, fresh non-resuming kernel run, external replication.

## Assessment
Novelty: low. Reproducibility: strong pipeline, incomplete historical provenance. Likely score: **3/10 reject**. Confidence: **5/5**.

## Post-audit disposition
Claims are narrowed and the malformed-fixture interval is withdrawn. Fatal external-evidence concern remains unfixable without a new frozen study.
