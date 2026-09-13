# Research Audit Checklist — IY-ERN

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **scaffold**. React landing page with unreplaced integration placeholder, not scientific evidence.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **7**
- Top extensions: .jsx:2, .html:1, .js:1, .md:1, .json:1, .css:1
- Marker counts: todo=0, placeholder=0, stub=0, hardcoded=0, claim-language=4
- README excerpt: # IY-ERN Landing  ## Status  This repository is a React/Vite landing page for the International Youth Economics Research Network. It is not a scientific research repository and does not contain a paper archive, submission backend, review workflow backend, dataset, experiment, retained result, or validation evidence.  ## Claim boundary  Valid claims:  - static landing page implementation, - optional Google Form submission link via `VITE_GOOGLE_FORM_URL`, - public-facing copy and layout for a future research network.  Invalid claims:  - completed publication platform, - validated peer-review workflow, - retained research output, - evidence that submitted papers exist or were reviewed, - scientific or educational impact.  ## Run  ```bash npm install npm run dev ```  For production-like builds:  ```bash npm run build ```  Submissions remain closed unless `VITE_GOOGLE_FORM_URL` is configured....

## Component Classification

| Classification | Evidence |
| --- | --- |
| scaffold | React landing page with unreplaced integration placeholder, not scientific evidence. |
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
| P0 | IY-ERN | Repository is classified as scaffold, not a complete research artifact. | React landing page with unreplaced integration placeholder, not scientific evidence. | Any paper, benchmark, or project-count claim based on this component would overstate the evidence. | Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results. |
| P1 | IY-ERN | Code exists without detected tests. | No path containing 'test' was found in the repository scan. | Claims can regress silently and reproducibility cannot be independently checked. | Add unit tests for metrics/data/model contracts and an end-to-end smoke test. |
| P1 | IY-ERN | No retained result artifact detected. | No obvious result/run/metrics path was found. | The repository cannot support empirical claims without rerunning or trusting prose. | Commit frozen result manifests with seeds, hashes, configs, logs, and tables. |
| P1 | IY-ERN | Claim language appears without retained evidence. | `README.md:20` - - completed publication platform,; `src/App.jsx:35` - 'A simple publication flow that keeps submissions organized and presents approved work clearly.', | Novelty or SOTA framing may be unsupported. | Bind each claim to a checked result, citation, proof, or explicit limitation. |


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
- `README.md:20` - - completed publication platform,
- `src/App.jsx:35` - 'A simple publication flow that keeps submissions organized and presents approved work clearly.',


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.


## P0 Checklist
- **WHAT:** Repository is classified as scaffold, not a complete research artifact.
  **WHY:** Any paper, benchmark, or project-count claim based on this component would overstate the evidence.
  **HOW:** Either demote the public claim to the observed evidence tier, or implement the missing method/data/evaluation path and retain reproducible results.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P1 Checklist
- **WHAT:** Code exists without detected tests.
  **WHY:** Claims can regress silently and reproducibility cannot be independently checked.
  **HOW:** Add unit tests for metrics/data/model contracts and an end-to-end smoke test.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** No retained result artifact detected.
  **WHY:** The repository cannot support empirical claims without rerunning or trusting prose.
  **HOW:** Commit frozen result manifests with seeds, hashes, configs, logs, and tables.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Claim language appears without retained evidence.
  **WHY:** Novelty or SOTA framing may be unsupported.
  **HOW:** Bind each claim to a checked result, citation, proof, or explicit limitation.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

