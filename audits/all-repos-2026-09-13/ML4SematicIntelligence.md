# Research Audit Checklist — ML4SematicIntelligence

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4SematicIntelligence`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Partial evidence-indexed portfolio: 2 project-specific external implementations, 14 shared diagnostics, and 48 specification-only entries; zero conference-ready papers or defensible positive scientific claims.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **242**
- Top extensions: .md:155, .py:46, .json:20, .csv:5, .svg:4, <none>:3, .sh:3, .bib:2
- Marker counts: todo=0, placeholder=5, stub=0, hardcoded=8, claim-language=32
- README excerpt: # ML4SemanticIntelligence  ML4SemanticIntelligence is a reproducibility-first research foundry for controlled experiments in compositionality, grounding, semantic memory, concept learning, relational reasoning, pragmatics, uncertainty, and evaluation.  The repository contains 64 **research hypotheses**, not 64 claims of novelty or success. Every claim is tied to a machine-readable status and an artifact. The first executable tranche contains 16 minimal mechanisms evaluated on deterministic synthetic diagnostics. Those diagnostics test implementation invariants and cheap falsifiers; they are not evidence of general language understanding.  ## Quick start  ```bash python3 -m ml4semantic validate python3 -m ml4semantic run-wave --wave all python3 -m ml4semantic cogs-relational --per-case 1000 python3 -m ml4semantic cogs-benchmark-audit uv run --extra neural python -m ml4semantic cogs-neural...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Partial evidence-indexed portfolio: 2 project-specific external implementations, 14 shared diagnostics, and 48 specification-only entries; zero conference-ready papers or defensible positive scientific claims. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=5, stub=0 |
| hardcoded shortcut | hardcoded/toy markers=8 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | ML4SematicIntelligence | Unresolved placeholder/stub markers require manual triage. | `outreach/drafts/companies.md:21` - Hi [Name] — I’m developing a semantic-reliability evaluation layer for enterprise retrieval. A focused pilot would test whether answers remain stable when sources conflict, become ; `outreach/drafts/universities.md:15` - Dear Professor/Dr. [Name] — Your work on [recent paper] aligns with ML4SEMAN-002, ML4SEMAN-006, and ML4SEMAN-033. The repository provides hypotheses, falsifiers, controlled reruns, | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
_No examples found in scanned text files._
### placeholder
- `outreach/drafts/companies.md:21` - Hi [Name] — I’m developing a semantic-reliability evaluation layer for enterprise retrieval. A focused pilot would test whether answers remain stable when sources conflict, become 
- `outreach/drafts/universities.md:15` - Dear Professor/Dr. [Name] — Your work on [recent paper] aligns with ML4SEMAN-002, ML4SEMAN-006, and ML4SEMAN-033. The repository provides hypotheses, falsifiers, controlled reruns,
### stub
_No examples found in scanned text files._
### hardcoded
- `EVALUATION_REPORT.md:46` - - Retrieval shortcut: explicit bounded nearest-neighbor baseline.
- `research/RESEARCH_DASHBOARD.md:6` - | ML4SEMAN-002 | Does Systematic Role-Filler Generalization capture semantic structure rather than surface correlations under controlled compositional or grounding shifts? | SHARED
- `tools/build_research_governance.py:54` - else "synthetic only"
### claim
- `PROJECT_STATUS.md:49` - - The attentive GRU is a valid trained health-check comparator, not a contemporary state-of-the-art baseline.
- `RESEARCH_MASTER_INDEX.md:12` - - Conference-ready papers: **0** (the flagship still lacks an untouched compositional evaluation and contemporary baseline)
- `PROJECT_BY_PROJECT_STATUS.md:12` - - 0 conference-ready papers and 0 defensible positive scientific claims
- `DEFINITION_OF_DONE.md:35` - | Conference submission | Every scientific gate above passes | FAIL | do not submit current draft |
- `MASTER_RESEARCH_REPORT.md:58` - - **ML4SEMAN-031 — Novel Concept Compositionality:** formulation only; parked until a higher-tier project creates reusable data or evidence that makes this experiment discriminatin
- `RESEARCH_COMPLETION_REPORT.md:43` - ## Strongest Publication Candidates


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.

## Focused Audit Notes

- `PROJECT_TRUTH.md` classifies 64 hypotheses as 2 project-specific external implementations, 14 shared diagnostics, and 48 specification-only entries; a claim of 64 implemented projects is false.
- ML4SEMAN-033 COGS artifacts are verified but mixed/development-informed. GRU exact-match generalization is 0.000 and structural diagnostics are nonzero, so it is negative/error-analysis evidence, not a success claim.
- `TRUTH_MAP.md` blocks any main-conference paper claim until there is a clean holdout, stronger baseline, independent replication, and human/venue review.
- Next fix: narrow active scope to ML4SEMAN-033/059 and freeze the 48 spec-only entries out of implementation counts.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4SematicIntelligence` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4SematicIntelligence` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4SematicIntelligence` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4SematicIntelligence` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

