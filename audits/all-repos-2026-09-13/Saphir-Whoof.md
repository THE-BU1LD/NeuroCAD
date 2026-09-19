# Research Audit Checklist — Saphir-Whoof

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/Saphir-Whoof`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Experiment-ready implementation with unverified real-model evidence.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **38**
- Top extensions: .py:21, .txt:5, <none>:4, .json:3, .md:2, .toml:1, .jsonl:1, .typed:1
- Marker counts: todo=0, placeholder=5, stub=0, hardcoded=3, claim-language=0
- README excerpt: # Epistemic Blind Spots  End-to-end toolkit for multilingual epistemic invariance experiments.  This repository includes:  - multilingual benchmark schema and JSONL tooling, - normalization and answer canonicalization, - output, calibration, representation, and causal metrics, - Hugging Face model wrappers for causal and seq2seq LMs, - layerwise activation capture and executable donor-to-recipient patching, - real-dataset adapters for public multilingual benchmarks, - synthetic benchmark generators, - ablation runners, - plotting and report generation, - and a CLI for full experiment workflows.  ## Install  ```bash pip install -e .[all] ```  For a lighter install:  ```bash pip install -e . pip install torch transformers datasets matplotlib ```  ## Quickstart  Run the included toy benchmark with a dummy oracle model:  ```bash python -m epistemic_blind_spots.cli demo --output out/demo ``` ...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Experiment-ready implementation with unverified real-model evidence. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=5, stub=0 |
| hardcoded shortcut | hardcoded/toy markers=3 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | Saphir-Whoof | Unresolved placeholder/stub markers require manual triage. | `README.md:33` - Run the included toy benchmark with a dummy oracle model:; `tests/test_hf_model.py:100` - wrapper = HuggingFaceCausalLM("fake/model", revision="abc"); `tests/test_extended.py:253` - "fake",; `src/epistemic_blind_spots/cli.py:55` - demo = sub.add_parser("demo", help="Run the toy benchmark with a dummy oracle model") | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
- `README.md:33` - Run the included toy benchmark with a dummy oracle model:
- `tests/test_hf_model.py:100` - wrapper = HuggingFaceCausalLM("fake/model", revision="abc")
- `tests/test_extended.py:253` - "fake",
- `src/epistemic_blind_spots/cli.py:55` - demo = sub.add_parser("demo", help="Run the toy benchmark with a dummy oracle model")
### stub
_No examples found in scanned text files._
### hardcoded
- `README.md:33` - Run the included toy benchmark with a dummy oracle model:
- `src/epistemic_blind_spots/model.py:57` - """A deterministic toy model for tests and demos."""
- `src/epistemic_blind_spots/cli.py:55` - demo = sub.add_parser("demo", help="Run the toy benchmark with a dummy oracle model")
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


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Saphir-Whoof` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Saphir-Whoof` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Saphir-Whoof` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Saphir-Whoof` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

