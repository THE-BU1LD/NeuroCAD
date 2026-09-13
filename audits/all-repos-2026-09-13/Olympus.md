# Research Audit Checklist — Olympus

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/Olympus`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Strong software platform, scientific scaffold: role families remain smoke-not-promoted.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **627**
- Top extensions: .py:164, .md:161, .json:113, .yaml:25, .lock:23, .csv:23, .awk:21, .gz:17
- Marker counts: todo=5, placeholder=18, stub=10, hardcoded=4, claim-language=53
- README excerpt: # OLYMPUS Cognitive Architecture  Olympus is a local-first research platform for building and evaluating cognitive behaviors:  - multimodal state representation, - interpretive branching with calibrated scoring, - dynamic representation selection, - retrodiction and forward prediction, - behavior compilation and graph execution, - structured verification, memory, data ingestion, and retrieval, - synthetic training/evaluation demos, - API, CLI, and a lightweight web console.  The repository now also includes a durable Model Foundry that performs a real, bounded dataset → experiment → checkpoint → held-out evaluation → export → serving lifecycle. Its built-in character-bigram run exists to verify the infrastructure cheaply; it is explicitly not Hermes and carries no assistant or reasoning capability claim.  Olympus is currently an alpha research system. Its tests establish executable engin...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Strong software platform, scientific scaffold: role families remain smoke-not-promoted. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=18, stub=10 |
| hardcoded shortcut | hardcoded/toy markers=4 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | Olympus | Unresolved placeholder/stub markers require manual triage. | `ALL_MODELS_RELEASE_EXECUTION_PROMPT.md:111` - binding and explicit selection at inference. No dummy domain routing responses.; `releases/hermes-local/AUDIT_CHECKLIST.md:17` - The word `placeholder` occurs in a grounding docstring explaining a restriction,; `releases/hermes-local/README.md:39` - Choose a model that fits your available memory; no universal hardware guarantee is made.; `releases/hermes-local/hermes_local/cli.py:15` - parser = argparse.ArgumentParser(description="Experimental Hermes powered by your chosen base."); `releases/hermes-local/hermes_local/grounding.py:309` - degrade into a non-differentiable placeholder. | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `PROJECT_MEGA_AUDIT_CHECKLIST_2026-09-08.md:112` - The search did not identify a blanket TODO/NotImplementedError implementation in the inspected active runtime. Calling the entire project pseudocode would be inaccurate. The import
- `PROJECT_FINISH_CHECKLIST.md:93` - - [ ] Re-scan maintained code for TODO/FIXME/HACK, swallowed exceptions,
- `releases/hermes-local/AUDIT_CHECKLIST.md:16` - No TODO/FIXME/NotImplemented handlers were found in the inspected package search.
### placeholder
- `ALL_MODELS_RELEASE_EXECUTION_PROMPT.md:111` - binding and explicit selection at inference. No dummy domain routing responses.
- `releases/hermes-local/AUDIT_CHECKLIST.md:17` - The word `placeholder` occurs in a grounding docstring explaining a restriction,
- `releases/hermes-local/README.md:39` - Choose a model that fits your available memory; no universal hardware guarantee is made.
- `releases/hermes-local/hermes_local/cli.py:15` - parser = argparse.ArgumentParser(description="Experimental Hermes powered by your chosen base.")
- `releases/hermes-local/hermes_local/grounding.py:309` - degrade into a non-differentiable placeholder.
- `portfolio_audit/portfolio_registry.json:119` - "state": "empty placeholder containing only a license",
### stub
- `README.md:141` - The former PostgreSQL/pgvector and Redis Compose scaffold is archived under
- `PROJECT_MEGA_AUDIT_CHECKLIST_2026-09-08.md:112` - The search did not identify a blanket TODO/NotImplementedError implementation in the inspected active runtime. Calling the entire project pseudocode would be inaccurate. The import
- `portfolio_audit/portfolio_registry.json:128` - "state": "incomplete experiment scaffold",
- `audits/ALL_REPOSITORIES_RESEARCH_AUDIT.md:80` - real-grade training/evaluation. Placeholder/stub: no production-trained weights by its README.
- `OlympusC/05_pantheon/research/RELATED_WORK.md:34` - 5. Nitya Nadgir et al. “Life After Benchmark Saturation: A Case Study of CORE-Bench.” arXiv:2606.26158 (2026). The paper releases CORE-Bench v1.1 and an OOD suite and argues for ev
### hardcoded
- `portfolio_audit/PORTFOLIO_PUBLICATION_READINESS_2026-09-07.md:136` - promotion has a hard-coded independent-evidence blocker because evaluation,
- `evidence/stage_02.md:6` - and model-card gates. A further hard-coded independent-evidence authority gate
- `audits/ALL_REPOSITORIES_RESEARCH_AUDIT.md:81` - Hardcoded shortcut risk: synthetic correction can validate renderer mechanics but not creative
### claim
- `HERMES_PUBLIC_REPOSITORY_README.md:25` - - Production, safety, general-intelligence or publication qualification.
- `PROJECT_STATUS.md:22` - boundaries, and numeric publication gates now fail closed in code rather than
- `PUBLICATION_AUDIT_2026-09-09.md:5` - **Software candidate: functionally verified in this checkout. Publication: not yet
- `PROJECT_EXECUTION_REPORT_2026-09-08.md:96` - or conference readiness.
- `PROJECT_EXECUTION_REPORT_2026-09-06.md:17` - correctly blocks publication because untracked Python files would enter the
- `README.md:97` - The publication-grade Foundry controls can prepare an immutable instruction


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Olympus` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Olympus` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Olympus` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Olympus` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

