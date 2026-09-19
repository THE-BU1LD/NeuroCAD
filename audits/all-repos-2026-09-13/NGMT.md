# Research Audit Checklist — NGMT

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/NGMT`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Evidence-partial negative: current Recovery v2 result fails the primary improvement gate; submission package remains incomplete because historical cells and provenance do not match current source/paper artifacts.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **293**
- Top extensions: .png:96, .md:62, .py:48, .svg:18, .yaml:14, .sh:11, .txt:6, .json:6
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=58
- README excerpt: # NGMT: testing robust memory, without a superiority claim  NGMT asks whether a Student-t influence weight inside Transformer memory improves scalar one-step forecasting beyond a Student-t output distribution. The implementation is real; the strongest memory-performance claim is not supported.  ## Current status: EVIDENCE_PARTIAL  The prospective Recovery v2 study completed **60 cells**: six independent synthetic series, two optimization seeds, five models. Capping the memory influence at one did **not** meet the predefined improvement criterion versus original NGMT: raw-unit post-shock MAE difference **+0.003343**, 95% data-seed bootstrap interval **[-0.002039, 0.010004]**, exact two-sided sign-flip **p=0.4375**. This is not evidence of equivalence.  **Historical integrity correction:** six old mechanism cells were overwritten by quick runs (156 rather than 336 targets). The old mechani...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Evidence-partial negative: current Recovery v2 result fails the primary improvement gate; submission package remains incomplete because historical cells and provenance do not match current source/paper artifacts. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=0, stub=0 |
| hardcoded shortcut | hardcoded/toy markers=0 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
_No examples found in scanned text files._
### stub
_No examples found in scanned text files._
### hardcoded
_No examples found in scanned text files._
### claim
- `FINAL_HANDOFF.md:15` - - Publication tables/figures/claim generation, artifact validation, publication gate, and automatic submission ZIP creation.
- `PROJECT_STATUS.md:7` - Maintain a publication-grade falsification study that separates gains from heavy-tailed predictive output from gains attributable to a non-Gaussian latent-memory update.
- `RUN_EXPERIMENTS_AND_PUBLISH.md:55` - - regenerates conference figures and Markdown/LaTeX tables;
- `README.md:48` - This is small-model, univariate, one-step synthetic evidence, not SOTA, streaming filtering, multivariate forecasting or external validation. The memory resets within every input w
- `FINAL_RESEARCH_REPORT.md:26` - The main, mechanism, conference, tail and sensitivity runners isolate new results from history. Smoke uses unique roots and different quick/full IDs. Failure exceptions propagate. 
- `research/RELATED_WORK.md:3` - This project sits at the intersection of probabilistic neural forecasting and robust Student-t state estimation. The literature check weakens any claim that “Student-t latent state


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.

## Focused Audit Notes

- `RESEARCH_TRUTH.md` reports Recovery v2 over 60 cells with primary bounded NGMT-minus-original delta `+0.0033429166`, 95% CI `[-0.0020387918, 0.0100040585]`, sign-flip `p=0.4375`; this fails the improvement gate.
- `FINAL_SUBMISSION_STATUS.md` is explicitly `EXPERIMENT PACKAGE INCOMPLETE`; six quick/full protocol cells collide and source/paper/script hashes do not match the current artifacts.
- Six old mechanism seed-101 cells have 156 rather than 336 targets; keep them as compromised history, not publication evidence.
- Next fix: rerun the publication/provenance gate after license/authorship decisions and rebuild source/paper artifacts from the current tree without reusing collided IDs.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
_No items assigned at this severity by this pass._
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NGMT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NGMT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NGMT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

