# Research Audit Checklist — EPU

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/EPU`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Partial real-data prototype: Python reference tests pass and a digits retrieval benchmark exists, but full iterative retrieval underperforms nearest-prototype/single-step controls and RTL/hardware equivalence remains unverified.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **15**
- Top extensions: .md:7, .py:3, .txt:2, .v:1, .json:1, .sh:1
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=0
- README excerpt: # EPU-Ω∞ prototype  A bounded prototype for a Hopfield-inspired Engram Processing Unit. It is not a validated hardware or neuroscience result.  ## Included - `paper/EPU_Omega_Infinity_Paper.md` - `code/epu_reference.py` - `code/epu_core.v` - `logisim/Blueprint.md` - `benchmarks/Benchmark_Protocol.md` - `appendix/100_extensions.md` - `examples/test_vectors.json` - `figures/architecture_ascii.txt` - `scripts/run_demo.sh`  The RTL core asserts `converged` when a clocked update leaves every fixed-point state component unchanged. It remains an unverified illustrative core: its fixed memory initialization and arithmetic have not been shown equivalent to the floating-point Python reference.  ## Quick start ```bash bash scripts/run_demo.sh ```  ## Scientific benchmark  ```bash python -m unittest discover -s tests -v python benchmarks/run_ablation_benchmark.py --seeds 7 17 29 ```  The benchmark u...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Partial real-data prototype: Python reference tests pass and a digits retrieval benchmark exists, but full iterative retrieval underperforms nearest-prototype/single-step controls and RTL/hardware equivalence remains unverified. |
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
- `results/full_digits.json` is a real digits benchmark, but full iterative retrieval is about 0.0956 accuracy while direct nearest-prototype/single-step controls are much stronger; this is evidence against the full iterative mechanism.
- RTL is illustrative and is not verified equivalent to the Python reference.
- Fixed in this pass: added `requirements.txt`. Next fix: repair the dynamics or label the full iterative EPU as a failed ablation.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
_No items assigned at this severity by this pass._
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/EPU` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/EPU` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/EPU` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

