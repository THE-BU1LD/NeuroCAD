# VeriCodeGen AI4AutoSci 2026 evidence checklist

This is a backup submission track. Issues #21 and #22 remain authoritative for scientific execution.

## P0 — held-out benchmark freeze

- [ ] exactly 120 tasks, IDs `VCG-001..VCG-120`;
- [ ] exactly 40 in-distribution, 40 compositional, 40 OOD-constraint-stress;
- [ ] each task has >=1 supported hard constraint + >=1 semantic rubric criterion;
- [ ] selected evaluated provider/model/version recorded before execution;
- [ ] evaluated model did not author/rewrite/filter/rank/repair/select held-out tasks after selection;
- [ ] no Stage-1 fixture or tutorial/test example leaked into held-out set;
- [ ] units/dimensions/counts/relations/tolerances manually reviewed;
- [ ] impossible/contradictory tasks removed pre-freeze;
- [ ] exact duplicate audit passes;
- [ ] token-Jaccard near-duplicate audit passes at frozen 0.88 threshold;
- [ ] canonical benchmark JSONL + manifest retained;
- [ ] benchmark/manifest/schema/per-task SHA-256 evidence retained;
- [ ] independent reviewer sign-off records no outcome access before freeze.

## P1 — matched execution freeze

- [ ] deterministic 12-task pilot selected exactly 4/family;
- [ ] public pilot-selection salt frozen before provider calls;
- [ ] pilot selection hash retained and matches execution manifest;
- [ ] direct prompt template frozen + hashed;
- [ ] structured prompt template/output schema frozen + hashed;
- [ ] shared verifier frozen + hashed;
- [ ] analysis plan frozen + hashed;
- [ ] exact NeuroCAD commit retained;
- [ ] OpenSCAD version, `$fn`, compile timeout retained;
- [ ] exact provider/model/revision retained;
- [ ] temperature/top-p/max-output tokens retained;
- [ ] seed set frozen;
- [ ] symmetric max attempts + feedback policy retained;
- [ ] human correction disabled;
- [ ] exact call ceiling/cost cap reviewed;
- [ ] separate human review of complete Stage-2 manifest;
- [ ] `authorized=true` only after every pre-outcome gate closes.

## P2 — outcome retention

- [ ] every raw response retained;
- [ ] every failed attempt retained;
- [ ] every compile log retained;
- [ ] hash-chain ledger intact;
- [ ] direct HVR reported;
- [ ] structured HVR reported;
- [ ] paired delta reported;
- [ ] prespecified exact McNemar result reported;
- [ ] prespecified bootstrap interval reported;
- [ ] failure taxonomy reported without deleting bad cases;
- [ ] retries/latency/tokens/cost reported;
- [ ] infrastructure failures distinguished from scientific failures;
- [ ] no prompt/schema/baseline/seed/metric edit after outcome access.

## P3 — inference boundary

- [ ] Stage-2 pilot explicitly described as exploratory;
- [ ] full Stage-3 benchmark completed before any claim that requires it;
- [ ] historical typed-parser causal claim remains falsified and is not revived;
- [ ] hard-verifier passing is not called complete semantic correctness;
- [ ] compilation is not called manufacturability;
- [ ] no validated scientific-instrument-design claim without a matching instrument benchmark;
- [ ] null/negative/mixed findings remain unchanged.

## P4 — workshop manuscript

- [x] double-blind manuscript shell exists;
- [x] result blocker is visible pre-outcome;
- [x] old falsified claim is explicitly excluded;
- [x] experiment-design relevance is bounded rather than exaggerated;
- [ ] verified primary-source related work added;
- [ ] tables regenerated from retained evidence;
- [ ] all outcome/failure categories represented;
- [ ] abstract/conclusion rewritten from actual retained result;
- [ ] sentence-level claims audit complete;
- [ ] final IEEE BigData template + page-count rule checked;
- [ ] identifying metadata scrubbed;
- [ ] workshop portal/deadline details re-checked before submission.

## Kill criterion

If the full inference boundary cannot be completed rigorously without distracting from Space-JEPA, keep VeriCodeGen as a future paper. Do not submit a dressed-up Stage-1 engineering smoke or a favorable 12-task pilot as if it established the full scientific claim.