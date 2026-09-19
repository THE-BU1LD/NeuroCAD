# Research Audit Checklist — FI-JEPA

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/FI-JEPA`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Evidence-partial negative: FI-JEPA underperforms raw-context ridge/persistence on retained evidence.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **116**
- Top extensions: .md:27, .json:26, .py:26, .pdf:11, .png:5, .sh:5, <none>:3, .yaml:3
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=5
- README excerpt: # FI-JEPA  FI-JEPA is an audited PyTorch experiment asking whether future latent prediction learns useful multivariate time-series representations. An online encoder maps a context window to $z$; a frozen target encoder maps future windows to $\bar z_h$; one independent predictor per horizon minimizes $\sum_h\alpha_h\|q_h(z)-\operatorname{sg}(\bar z_h)\|^2$ plus collapse regularization.  The current scientific status is **EVIDENCE_PARTIAL with a negative development result**. On the five-seed U.S. macrodata experiment, full FI-JEPA had test MSE 0.9699, versus 0.4420 for raw-context ridge and 0.4161 for persistence. This does not establish a publishable general negative result: only one small dataset has been evaluated and its test set was used during development.  The historical “Financial-Informed” operator, memory, uncertainty, and finance-penalty claims were not supported by executabl...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Evidence-partial negative: FI-JEPA underperforms raw-context ridge/persistence on retained evidence. |
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
- `research/NOVELTY_AUDIT.md:5` - The broad idea—EMA/self-distilled latent prediction for time series and multi-horizon forward JEPA—is not novel. TS-JEPA (2025), LaT-PFN (2024), and CF-JEPA (2026) already cover ov
- `docs/RESEARCH.md:9` - The actual contribution is an audited implementation and a well-provenanced adverse result, not a novel financial operator or superior forecasting method. See `research/MATHEMATICA
- `audit/CONFERENCE_READINESS_CHECKLIST.md:110` - Conference gate: not passed.
- `audit/FINAL_AUDIT.md:30` - Engineering and development artifact gate: pass. Conference/paper evidence gate: fail by design. Verdict: **EVIDENCE_PARTIAL**.


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FI-JEPA` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FI-JEPA` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/FI-JEPA` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

