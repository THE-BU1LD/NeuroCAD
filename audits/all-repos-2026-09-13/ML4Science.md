# Research Audit Checklist — ML4Science

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **untested**. Audited negative/inconclusive portfolio; external proposals fail.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **1200**
- Top extensions: .md:867, .json:162, .csv:98, .mmd:48, .png:10, .bib:5, <none>:4, .lock:2
- Marker counts: todo=0, placeholder=0, stub=5, hardcoded=9, claim-language=311
- README excerpt: # ML4Science: audited research hypothesis portfolio  This repository is **not 64 finished research projects**. It tracks 64 scientific-ML hypotheses, consolidated into eight shared mechanism families. Sixty currently have only synthetic diagnostic coverage. Four have external case studies, and none supports a positive scientific or main-track conference claim.  The repository's value is the audited experimental system: fail-closed dataset and split checks, development-only model selection, strong baseline challenges, uncertainty estimates, negative results, exact-hash reruns, and explicit claims boundaries. Project names are hypotheses—not proof that a domain-specific method exists.  ## What is real  | Evidence tier | Count | Meaning | |---|---:|---| | Tracked hypothesis | 64 | Question, falsifier, protocol, and synthetic diagnostic identity exist | | Shared mechanism family | 8 | The 64...

## Component Classification

| Classification | Evidence |
| --- | --- |
| untested | Audited negative/inconclusive portfolio; external proposals fail. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=0, stub=5 |
| hardcoded shortcut | hardcoded/toy markers=9 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | ML4Science | Code exists without detected tests. | No path containing 'test' was found in the repository scan. | Claims can regress silently and reproducibility cannot be independently checked. | Add unit tests for metrics/data/model contracts and an end-to-end smoke test. |
| P1 | ML4Science | Unresolved placeholder/stub markers require manual triage. | `NEXT.md:6` - 1. Obtain a second, structure-bearing molecular dataset and preregister scaffold/chronological splits for ML4SCIEN-012.; `RESEARCH_COMPLETION_REPORT.md:53` - 2. ML4SCIEN-012: chemically meaningful scaffold splits, multiple datasets, calibrated boosting/SVM/GNN baselines.; `papers/external_studies/render_individual_papers.py:52` - "Predeclare several chemically meaningful scaffold or descriptor shifts, reserve an "; `papers/external_studies/ML4SCIEN-012/manuscript.md:34` - This is a retrospective single-dataset analysis. It does not establish novelty, causal mechanism, prospective utility, deployment value, or cross-dataset generalization. Predeclare; `projects/ML4SCIEN-012/paper/related_work.md:10` - MoleculeNet uses scaffold splits for molecular generalization and compares multiple neural and conventional models. The present descriptor-tail split is a narrower stress test and  | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
_No examples found in scanned text files._
### stub
- `NEXT.md:6` - 1. Obtain a second, structure-bearing molecular dataset and preregister scaffold/chronological splits for ML4SCIEN-012.
- `RESEARCH_COMPLETION_REPORT.md:53` - 2. ML4SCIEN-012: chemically meaningful scaffold splits, multiple datasets, calibrated boosting/SVM/GNN baselines.
- `papers/external_studies/render_individual_papers.py:52` - "Predeclare several chemically meaningful scaffold or descriptor shifts, reserve an "
- `papers/external_studies/ML4SCIEN-012/manuscript.md:34` - This is a retrospective single-dataset analysis. It does not establish novelty, causal mechanism, prospective utility, deployment value, or cross-dataset generalization. Predeclare
- `projects/ML4SCIEN-012/paper/related_work.md:10` - MoleculeNet uses scaffold splits for molecular generalization and compares multiple neural and conventional models. The present descriptor-tail split is a narrower stress test and 
### hardcoded
- `research/MASTER_RESEARCH_REGISTRY.md:13` - - **Datasets:** controlled synthetic only
### claim
- `PROJECT_STATUS.md:31` - - Enforced sealed-test selection, deterministic refitting, 5,000 paired bootstrap replicates, scientific hashes, per-project publication copies, and fail-closed verification.
- `PROJECT_ERROR_AUDIT.md:37` - - Replaced publication-ready labels with evidence-bounded package labels.
- `pyproject.toml:16` - publication = ["matplotlib>=3.10", "reportlab>=4.4", "pypdf>=6.0"]
- `README.md:6` - scientific or main-track conference claim.
- `RESEARCH_COMPLETION_REPORT.md:22` - - Main-track positive-result paper-ready: 0
- `REPRODUCIBILITY.md:19` - python -m pip install -e '.[dev,publication,research]'


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
- **WHAT:** Code exists without detected tests.
  **WHY:** Claims can regress silently and reproducibility cannot be independently checked.
  **HOW:** Add unit tests for metrics/data/model contracts and an end-to-end smoke test.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Science` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

