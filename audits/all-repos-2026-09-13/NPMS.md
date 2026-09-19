# Research Audit Checklist — NPMS

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/NPMS`

Audit date: 2026-09-13

Repository type: **repo-like directory/no local .git**

Executive verdict: **partial**. Strong controlled diagnostic, but external/public benchmark validation incomplete.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **190**
- Top extensions: .py:84, .md:53, .png:11, .sh:10, <none>:6, .txt:5, .tex:4, .yaml:4
- Marker counts: todo=3, placeholder=18, stub=7, hardcoded=3, claim-language=46
- README excerpt: # Neural Predictive Memory Spectroscopy (NPMS)  NPMS is an intervention-oriented diagnostic framework for measuring **how memory systems fail**, not a new memory architecture. It combines controlled stress-response surfaces, matched causal interventions, influence analysis, confidence/error analysis, and a real-system publication track on established long-term-memory benchmarks.  ## What is already verified  - **360,000** controlled main-matrix episode evaluations across five seeds. - **72,000** controlled causal-intervention evaluations. - Attention state tracking: **0.500 -> 1.000** after recent-tie resolution. - Associative state tracking: **0.761 -> 1.000** after latest-key deduplication. - Both repair contrasts improve all five seeds, but exact two-sided p-values are **0.0625** and Holm-adjusted p-values are **0.750**; neither rejects at 0.05. - Attention relevant-deletion effect: *...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Strong controlled diagnostic, but external/public benchmark validation incomplete. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=18, stub=7 |
| hardcoded shortcut | hardcoded/toy markers=3 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | NPMS | Unresolved placeholder/stub markers require manual triage. | `README.md:22` - Before running, make `OPENAI_API_KEY` available either in your shell or in a local `.env` file. Then copy-paste this block from the repository root:; `paper/SUBMISSION_CHECKLIST.md:8` - - [x] executable-code placeholder/stub scan; `audit/ULTIMATE_CHECKLIST.md:12` - ## 2. Pseudocode, stubs, placeholders, and fake work; `vendor/MemEval/README.md:129` - Requirements: Python `>=3.11` and `OPENAI_API_KEY` set in your environment (or `.env`).; `vendor/MemEval/CONTRIBUTING.md:3` - ## Add Your Benchmark | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `scripts/check_no_placeholders.py:12` - r"\b(TODO|FIXME|NotImplementedError|pseudocode|scaffold)\b", re.IGNORECASE
- `vendor/MemEval/src/agents_memory/systems/hindsight.py:5` - export OPENAI_API_KEY=sk-xxx
### placeholder
- `README.md:22` - Before running, make `OPENAI_API_KEY` available either in your shell or in a local `.env` file. Then copy-paste this block from the repository root:
- `paper/SUBMISSION_CHECKLIST.md:8` - - [x] executable-code placeholder/stub scan
- `audit/ULTIMATE_CHECKLIST.md:12` - ## 2. Pseudocode, stubs, placeholders, and fake work
- `vendor/MemEval/README.md:129` - Requirements: Python `>=3.11` and `OPENAI_API_KEY` set in your environment (or `.env`).
- `vendor/MemEval/CONTRIBUTING.md:3` - ## Add Your Benchmark
- `vendor/MemEval/src/agents_memory/training/memory_r1/prompts.py:65` - Output them before your answer.
### stub
- `FINAL_HARDENING_REPORT.md:21` - - executable-code stub/marker scan, Python compile gate, shell syntax gate;
- `paper/SUBMISSION_CHECKLIST.md:8` - - [x] executable-code placeholder/stub scan
- `scripts/check_no_placeholders.py:12` - r"\b(TODO|FIXME|NotImplementedError|pseudocode|scaffold)\b", re.IGNORECASE
- `vendor/MemEval/src/agents_memory/systems/_template.py:36` - raise NotImplementedError("Fill in answer logic")
### hardcoded
- `paper/generated/diagnostic_results.tex:1` - The four-probe profile classified the five fixed synthetic implementations at 0.980 accuracy versus 0.870 for the scalar control (paired gain 0.110; seed-bootstrap 95\% interval [0
- `scripts/build_diagnostic_assets.py:174` - r"These are development results on known toy mechanisms, not external or unseen-architecture validation. The confidence interval does not establish that the gain exceeds the 0.10 m
- `scripts/external/run_model_canary.py:60` - # only a toy two-line JSON response. Every added turn carries one atomic fact.
### claim
- `FINAL_HARDENING_REPORT.md:25` - The publication gate can pass with a null or negative scientific result if the declared evidence is complete. Large CMUS, masked-failure pairs, and ranking reversals are desirable 
- `PROJECT_STATUS.md:17` - - controlled-result table/figures in the publication manuscript and Tectonic-compatible release builds.
- `RESEARCH_TRUTH.md:15` - ## External publication track
- `README.md:3` - NPMS is an intervention-oriented diagnostic framework for measuring **how memory systems fail**, not a new memory architecture. It combines controlled stress-response surfaces, mat
- `PACKAGE_MANIFEST.md:9` - | `.github/workflows/external-publication-run.yml` | 2413 | `94bf301c1c592bc4f5526f7e868ad670024bf45b1e2fe3198d4f9529a88b91b6` |
- `FINAL_RESEARCH_REPORT.md:10` - - reproducibility, provenance, raw artifact hashes, failed-run preservation, publication figures and manuscript;


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NPMS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NPMS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NPMS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NPMS` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

