# Research Audit Checklist — Causal-Memory-Use

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/Causal-Memory-Use`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Strong diagnostic package, but exchangeability failures weaken naive causal interpretation.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **139**
- Top extensions: .py:46, .md:39, .sh:10, .png:9, .yaml:9, .tex:6, .txt:5, <none>:4
- Marker counts: todo=0, placeholder=3, stub=2, hardcoded=5, claim-language=34
- README excerpt: # Causal Memory Use  **Status:** complete, reproducible diagnostic study with construction controls, a 20,250-call local-LLM factorial, and a 720-call resource-bounded LongMemEval-S study. The strongest naturalistic result is a falsification of naive causal interpretation, not a state-of-the-art memory claim.  ## Research question  Does a retrieved memory causally affect an agent's answer, or is it merely present in context? This project replays the same episode under paired relevant deletion, matched irrelevant deletion, semantic substitution, and semantics-preserving null edits.  The primary statistic is the specificity-adjusted causal memory-use score:  `CMUS = (clean - relevant deletion) - (clean - irrelevant deletion)`.  Directional following rate (DFR) separately tests whether an answer follows a controlled counterfactual value. Retrieval recall, exact-output instability, and null ...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Strong diagnostic package, but exchangeability failures weaken naive causal interpretation. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=3, stub=2 |
| hardcoded shortcut | hardcoded/toy markers=5 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | Causal-Memory-Use | Unresolved placeholder/stub markers require manual triage. | `PRE_RUN_HANDOFF.md:5` - ## Your remaining action; `docs/REAL_EXPERIMENTS.md:24` - # export the values in .env, or source them with your preferred shell tooling; `audit/FINAL_REPO_AUDIT.md:13` - - real-model adapter fake-provider end-to-end check: **PASS**;; `paper/generated/controlled_results.tex:15` - \texttt{3a34735a68ba7...b68776927} binds the code and configuration used to; `src/cmu/agents.py:27` - raise NotImplementedError | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
- `PRE_RUN_HANDOFF.md:5` - ## Your remaining action
- `docs/REAL_EXPERIMENTS.md:24` - # export the values in .env, or source them with your preferred shell tooling
- `audit/FINAL_REPO_AUDIT.md:13` - - real-model adapter fake-provider end-to-end check: **PASS**;
### stub
- `paper/generated/controlled_results.tex:15` - \texttt{3a34735a68ba7...b68776927} binds the code and configuration used to
- `src/cmu/agents.py:27` - raise NotImplementedError
### hardcoded
- `research/ERROR_ANALYSIS.md:35` - 10. shortcut solution that bypasses memory.
- `research/ROBUSTNESS.md:15` - The format result is more informative than the generic distractor sweep because it attacks a plausible retrieval-stage shortcut without changing the target semantic value.
- `research/FALSIFICATION_REPORT.md:11` - **No.** `retrieved_but_ignored` has target retrieval recall = 1.0 while CMUS = 0.0 and retrieved-but-unused rate = 1.0. This directly falsifies the observational shortcut "retrieve
- `scripts/generate_research_docs.py:221` - 10. shortcut solution that bypasses memory.
### claim
- `PROJECT_STATUS.md:22` - - Real result tables/figures and a rewritten publication manuscript.
- `PUBLISH_READY.md:1` - # Publication Evidence Gate
- `README.md:55` - - `paper/final_main.pdf`: seven-page publication manuscript.
- `FINAL_RESEARCH_REPORT.md:11` - LongMemEval estimate, or a state-of-the-art memory system.
- `EVIDENCE_LEDGER.md:23` - | The method is novel as causal memory intervention | `literature` | `research/RELATED_WORK.md` | **FAILED** |
- `TRUTH_MAP.md:17` - | State-of-the-art or production-agent claim | BLOCKED | neither tested nor claimed |


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Causal-Memory-Use` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Causal-Memory-Use` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Causal-Memory-Use` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/Causal-Memory-Use` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

