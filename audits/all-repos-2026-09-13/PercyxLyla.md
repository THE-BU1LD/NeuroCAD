# Research Audit Checklist — PercyxLyla

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/PercyxLyla`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Software/control-plane project, not a scientific contribution by project count.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **441**
- Top extensions: .md:177, .json:168, .py:47, .sha256:35, .txt:5, <none>:3, .cff:1, .toml:1
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=46
- README excerpt: # PercyXLyla  PercyXLyla is a local-first execution and portfolio-intelligence control plane. **Percy owns action. Lyla owns truth. Evidence closes the loop.** The core runs without a cloud account, paid API, external database, or background telemetry.  This repository implements 64 bounded, independently evaluated workstreams spanning durable state, scheduling, evidence, truth synthesis, adapters, interaction, safety, recovery, and evaluation. “Implemented” means code exists. “Smoke tested” means its deterministic local acceptance probe passed. Neither label implies production deployment or real-world outcomes.  ## Quick start  ```bash python3 -m venv .venv . .venv/bin/activate python -m pip install -e . pxl --state .percyxlyla/state.db init --workspace . pxl --state .percyxlyla/state.db doctor pxl --state .percyxlyla/state.db evaluate all --workspace . pxl --state .percyxlyla/state.db ...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Software/control-plane project, not a scientific contribution by project count. |
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
- `README.md:54` - - `projects/`: 64 publication-oriented workstream dossiers generated from the canonical registry.
- `evidence/portfolio-verification.ci.json:4` - "claim_boundary": "publication dossier completeness and bounded local evidence; not peer review, deployment, or outcomes",
- `evidence/qualification.ci.json:290` - "claim_boundary": "publication dossier completeness and bounded local evidence; not peer review, deployment, or outcomes",
- `evidence/publication_verification.json:2` - "claim_boundary": "local publication structure, links, citation, version, license, and governance consistency; not external hosting, indexing, peer review, or legal advice",
- `evidence/publication-verification.ci.json:2` - "claim_boundary": "local publication structure, links, citation, version, license, and governance consistency; not external hosting, indexing, peer review, or legal advice",
- `evidence/finalizer_rehearsal.md:17` - The expanded archive contract also passed against that terminal build: all 87 required pre-build publication/evidence artifacts were present, including preserved failed and aborted


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/PercyxLyla` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/PercyxLyla` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/PercyxLyla` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

