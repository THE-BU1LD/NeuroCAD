# Research Audit Checklist — DRPT

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/DRPT`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Partial runnable prototype: train/eval now exercise previous-phase conditioning, smoke losses are finite, and unit tests pass; no matched no-feedback ablation, external baseline, multi-seed study, or validated hysteresis effect exists.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **16**
- Top extensions: .py:9, .json:3, .tex:1, .txt:1, .md:1, .sh:1
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=0
- README excerpt: # DRPT  Early runnable prototype for Dynamical Representation Phase Transitions. It is not yet a validated research result or a submission-ready package.  ## What is included  - a four-expert representation bank, - a phase controller with hysteresis-style previous-phase conditioning, - shared anchor-space alignment, - phase-supervised and self-supervised training signals, - a LaTeX extension note.  Dataset items are complete trajectories. The training and evaluation loops process every trajectory in time order and feed the predicted phase from one step into the next controller call, so the implemented previous-phase path is exercised. This is only hysteresis-style conditioning. A matched no-feedback ablation is available through `--no-phase-feedback`: it preserves all controller parameters and computation but zeros the prior-phase input. No completed run yet establishes a hysteresis effe...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Partial runnable prototype: train/eval now exercise previous-phase conditioning, smoke losses are finite, and unit tests pass; no matched no-feedback ablation, external baseline, multi-seed study, or validated hysteresis effect exists. |
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
_No examples found in scanned text files._


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.

## Focused Audit Notes

- Unit verification passed with `python3 -m unittest discover -s tests -v` (6 tests).
- `src/train.py` and `src/eval.py` feed `prev_onehot`; tests verify that the previous phase changes the controller path.
- `runs/drpt_smoke/history.json` records finite losses and no NaNs in the smoke run.
- Next fix: add a paired no-feedback ablation across multiple seeds before claiming a hysteresis/phase-memory advantage.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
_No items assigned at this severity by this pass._
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/DRPT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/DRPT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/DRPT` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

