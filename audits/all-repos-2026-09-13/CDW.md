# Research Audit Checklist — CDW

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/CDW`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Implementation-rich with mixed/negative evidence; not a blanket-success monorepo.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **336**
- Top extensions: .py:141, .md:82, .tex:38, .json:37, .txt:7, .sha256:7, .sh:5, .pdf:4
- Marker counts: todo=0, placeholder=1, stub=12, hardcoded=0, claim-language=16
- README excerpt: # Counterfactual Defect Worlds  Counterfactual Defect Worlds (CDW) is an auditable research monorepo for paired factual, corrupted-observation, and physically intervened PDE worlds. It has one shared numerical/experimental package and seven projects with independent protocols, evidence, gates, and paper outputs.  The repository is executable, but its scientific findings are not a blanket success. The completed pilots are intentionally preserved even when the learned methods lose to simple baselines.  ## Evidence at a glance  | Project | Evidence state | What the retained evidence says | Next gate | |---|---|---|---| | [00 — Phase 1 pilot](projects/00_phase1_pilot/) | Complete negative pilot | One-step pipeline is real and reproducible; learned factual/counterfactual models lose to persistence and mask IoU is zero | Immutable historical record | | [01 — Counterfactual rollouts](projects/0...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Implementation-rich with mixed/negative evidence; not a blanket-success monorepo. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=1, stub=12 |
| hardcoded shortcut | hardcoded/toy markers=0 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | CDW | Unresolved placeholder/stub markers require manual triage. | `docs/audit_report.md:82` - - Projects 04--06 use empty honest summaries and explicit gates instead of fake; `MODEL_IMPLEMENTATION_CHECKLIST.md:57` - | 04 | Intentional preflight scaffold | Scientific training/evaluation runner | Implement only after Project 01 successor passes its gate |; `pyproject.toml:57` - # third-party implementations or treating dependency-stub defects as CDW errors.; `papers/restoration_vs_intervention/README.md:18` - embedded in the compact manuscript. The bibliography stub is not consumed; `projects/05_expert_architectures/experiments/README.md:6` - experiment is authorized. The aggregate stub also exits 2; `aggregated: false` | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
- `docs/audit_report.md:82` - - Projects 04--06 use empty honest summaries and explicit gates instead of fake
### stub
- `MODEL_IMPLEMENTATION_CHECKLIST.md:57` - | 04 | Intentional preflight scaffold | Scientific training/evaluation runner | Implement only after Project 01 successor passes its gate |
- `pyproject.toml:57` - # third-party implementations or treating dependency-stub defects as CDW errors.
- `papers/restoration_vs_intervention/README.md:18` - embedded in the compact manuscript. The bibliography stub is not consumed
- `projects/05_expert_architectures/experiments/README.md:6` - experiment is authorized. The aggregate stub also exits 2; `aggregated: false`
- `projects/02_restoration_vs_intervention/README.md:92` - - Evidence-backed manuscript scaffold: `../../papers/restoration_vs_intervention/`
- `projects/06_external_validation/experiments/README.md:7` - command into a successful scientific run. The aggregate stub also exits 2. No
### hardcoded
_No examples found in scanned text files._
### claim
- `PROJECT_FINISH_CHECKLIST.md:110` - - **New research/publication claim: NOT READY.** Existing pilots are negative,
- `projects/00_phase1_pilot/README.md:38` - The pilot covers one-step periodic Burgers and Fisher--KPP dynamics only. It does not support claims about multi-step rollouts, restoration, real systems, regime changes, or state-
- `projects/00_phase1_pilot/claims.json:44` - "state-of-the-art performance"
- `projects/00_phase1_pilot/snapshot/docs/research_protocol.md:26` - - state-of-the-art performance,
- `projects/00_phase1_pilot/protocol/v1.md:26` - - state-of-the-art performance,
- `projects/01_counterfactual_rollouts/README.md:25` - state-of-the-art performance.


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/CDW` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/CDW` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/CDW` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/CDW` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

