# Research Audit Checklist — RIS

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/RIS`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Partial bounded numerical benchmark: the unsupported IRR claim has been removed; current code/tests/results cover coordinate-adaptive finite-difference Hessian estimation on Wisconsin Diagnostic Breast Cancer only.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **7**
- Top extensions: .md:3, .py:3, .txt:1
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=0
- README excerpt: # RIS: bounded numerical-stability study  The previous repository described an “institutional-grade adaptive IRR stabilization framework,” but did not define RIS/IRR, a target outcome, or an evaluation protocol. That claim is unsupported and has been removed.  What is implemented is a falsifiable numerical study: coordinate-adaptive central finite differences for estimating a logistic-loss Hessian. The benchmark compares the estimate with the analytic Hessian on the real Wisconsin Diagnostic Breast Cancer dataset and ablates the adaptive step against three fixed step sizes.  ```bash python -m unittest discover -s tests -v python scripts/run_ablation_benchmark.py --seeds 7 17 29 ```  Results are written to `results/hessian_stability_v1.json`, including per-seed errors and mean/sample standard deviation. This validates numerical behavior only; it is not evidence of institutional readiness,...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Partial bounded numerical benchmark: the unsupported IRR claim has been removed; current code/tests/results cover coordinate-adaptive finite-difference Hessian estimation on Wisconsin Diagnostic Breast Cancer only. |
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

- Unit verification passed with `python3 -m unittest discover -s tests -v` (3 tests).
- README now removes the old IRR claim; retained results cover Wisconsin Diagnostic Breast Cancer with 3 seeds.
- Current evidence: adaptive `1e-4` and fixed `1e-4` are essentially tied, while fixed `1e-6` is much worse.
- Next fix: keep the bounded Hessian-estimation claim unless a second dataset/objective and stronger numerical baselines are added.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
_No items assigned at this severity by this pass._
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/RIS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/RIS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/RIS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

