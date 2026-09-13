# Research Audit Checklist — Assumption-Integrity

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/Assumption-Integrity`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Evidence-partial with adverse natural result: guarded synthetic paths exist, but Adult natural benchmark favors the unconditioned model.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **1200**
- Top extensions: .gz:630, .json:219, .csv:143, .pt:99, .md:48, .npz:38, .zip:6, .png:5
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=5
- README excerpt: # Assumption Integrity Under Distribution Shift  Can a predictor use regime metadata without being confidently wrong when that metadata is false? This repository tests that question with binary classification, controlled descriptor interventions, and a natural-metadata counterexample. The contribution is a reproducible failure-mode study and an identifiability boundary—not a superior new architecture.  For evidence X and claimed descriptor A, models estimate p(Y|X,A). The guard interpolates logits: z = z_e + sigmoid(q(X,A))(z_c-z_e). If valid and invalid worlds have identical observable laws over (X,A), no detector using those observations can distinguish them above chance under equal priors.  ## Evidence boundary  Status: **EVIDENCE_PARTIAL**. Local implementation and execution are verified; broad natural-domain validity and independent reproduction are not established.  - Historical fr...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Evidence-partial with adverse natural result: guarded synthetic paths exist, but Adult natural benchmark favors the unconditioned model. |
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
- `research/RELATED_WORK.md:43` - **Kirchmeyer et al. (2022), Context-Informed Dynamics Model (CoDA).** CoDA conditions dynamics on context vectors to generalize across physical systems. Again, context conditioning
- `research/NOVELTY_AUDIT.md:5` - ## Claims that are not novel
- `paper/EVIDENCE_LEDGER_20260829.md:29` - - ACP is state of the art.
- `paper/CLAIM_CALIBRATION.md:24` - - state of the art;


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
_No items assigned at this severity by this pass._
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Assumption-Integrity` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Assumption-Integrity` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Assumption-Integrity` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

