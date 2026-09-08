# VeriCodeGen AI4AutoSci 2026 claim-to-evidence audit

**Audit date:** 2026-09-08  
**Audited submission branch:** `research/vericodegen-ai4autosci-2026-submission-prep`  
**Scientific state:** **PRE-OUTCOME / NOT EVALUATED / NOT AUTHORIZED — UNCHANGED**

This is an independent manuscript-readiness audit. It does not execute Stage 2 or Stage 3, call a provider, inspect an outcome, select held-out tasks, alter the 120-task target design, revive the historical NeuroCAD typed-parser claim, or create a scientific result.

## 1. Boundaries that are already correct

The current manuscript correctly preserves the most important scientific boundaries:

- the historical NeuroCAD typed-parser causal interpretation remains falsified and is explicitly excluded from VeriCodeGen;
- the successor study is framed as a treatment-matched direct-vs-structured comparison rather than a rescue of the old result;
- Stage-2 is explicitly exploratory and cannot be promoted into the full successor claim;
- compilation/hard-verifier success is not equated with complete semantic correctness, manufacturability, structural safety, or validated scientific-instrument design;
- provider/model identity, decoding, prompt identities, verifier, analysis, retry/feedback policy, call/cost ceilings, and raw-output retention must be frozen before outcome-bearing calls;
- negative, null, mixed, failed, and infrastructure outcomes are retained;
- the Results section remains visibly blocked pre-outcome.

Those are appropriate and must remain unchanged.

## 2. Claim wording that is premature relative to the checklist

The branch's own `SUBMISSION_CHECKLIST.md` currently leaves **every P0 held-out-benchmark freeze item and every P1 matched-execution freeze item unchecked**. Therefore the manuscript must not read as though the final benchmark already exists as a frozen evaluated artifact.

### Current phrases that need a pre-outcome wording correction before release

1. Abstract: `The study uses a predeclared 120-task held-out benchmark ...`

   Until the canonical 120-task JSONL, manifest, per-task hashes, duplicate/near-duplicate audits, manual consistency review, and independent no-outcome sign-off exist, use wording such as **`The pre-outcome study design specifies a 120-task held-out benchmark...`** rather than implying the final frozen benchmark is already materialized.

2. Intended contribution: `a frozen 120-task language-to-CAD benchmark ...`

   This is not yet supported by the checklist. Before the P0 benchmark-freeze gate closes, use **`a prespecified 120-task benchmark design...`**. Restore `frozen benchmark` wording only after the retained benchmark/manifest/hash/sign-off package exists.

3. Intended contribution: `hard-verifier and semantic-rubric evidence ...`

   No Stage-2/3 outcome package exists yet. Keep this as a **planned endpoint/reporting surface**, not a completed contribution, until retained evidence exists.

These are manuscript-state corrections only. They must not be solved by fabricating tasks, hashes, provider identities, semantic ratings, or outcome values.

## 3. Evidence gates still open

The authoritative checklist still requires, before any scientific result can be inserted:

### Benchmark freeze
- exactly 120 final tasks, exactly 40/40/40 by frozen family;
- supported hard constraints plus semantic-rubric criteria per task;
- no evaluated-model authorship/filtering/ranking/repair/selection after model selection;
- leakage review against Stage-1/tutorial/test fixtures;
- manual units/dimensions/counts/relations/tolerances review;
- contradiction/impossibility review;
- exact duplicate audit;
- frozen token-Jaccard near-duplicate audit at 0.88;
- canonical benchmark JSONL + manifest + schema + per-task hashes;
- independent reviewer sign-off documenting no outcome access.

### Matched execution freeze
- deterministic 12-task Stage-2 selection exactly four/family and retained selection hash;
- frozen direct/structured prompt identities and shared verifier/analysis identities;
- exact source commit and OpenSCAD/runtime identity;
- exact provider/model/revision and decoding settings;
- frozen seeds, symmetric attempt/feedback budgets, call ceiling, and cost cap;
- human correction disabled;
- separate human review of the complete execution manifest;
- `authorized=true` only after all pre-outcome gates close.

### Outcome package
- raw responses, failed attempts, compile logs, hash-chain ledger;
- direct/structured HVR, paired delta, exact McNemar result, prespecified bootstrap interval;
- frozen failure taxonomy and resource-use reporting;
- no post-outcome prompt/schema/baseline/seed/metric edit.

Until those gates close, the paper is a **submission shell**, not a scientific submission candidate.

## 4. Current AI4AutoSci venue gate

Official AI4AutoSci @ IEEE BigData 2026 requirements checked on 2026-09-08:

- paper submission deadline: **2026-10-31**;
- format: **IEEE 2-column**;
- length: **up to 10 pages**;
- review: **double blind**;
- proceedings: **IEEE BigData**;
- presentation: **in person**;
- the workshop page says submission details/portal will be announced shortly, so portal state must be re-checked rather than guessed.

Primary source: https://ai4autosci.github.io/2026/

The current `IEEEtran`/anonymous shell is directionally aligned with the stated format, but final IEEE BigData template compliance, page count, identifying-metadata scrub, and portal state still require a final check after actual results are inserted.

## 5. Submission decision

VeriCodeGen remains a **backup** AI4AutoSci candidate behind the stronger Space-JEPA ESA track. The October 31 deadline does not justify weakening the benchmark or treating a favorable 12-task pilot as the full result.

**GO** only if the full inference boundary required by the frozen protocol is completed rigorously and retained evidence exists in time.

**NO-GO** if meeting the deadline would require:

- skipping human benchmark review;
- loosening the 40/40/40 or 120-task boundary post-outcome;
- changing model, prompt, verifier, retry, seed, metric, or statistical rules after seeing outcomes;
- promoting Stage-2 pilot performance into the Stage-3 claim;
- reviving the historical typed-parser causal interpretation;
- calling hard-verifier success manufacturability or complete semantic correctness.

## 6. Strongest next action

Close the **human benchmark-freeze gate** before any provider call: materialize and review the exact 120 final tasks, run the frozen exact/near-duplicate checks, retain benchmark/manifest/per-task hashes, and obtain an independent no-outcome sign-off. Only then should the matched Stage-2 execution manifest be eligible for authorization review.
