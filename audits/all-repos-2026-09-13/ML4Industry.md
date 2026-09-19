# Research Audit Checklist — ML4Industry

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Industry`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Mixed portfolio: many shared scaffolds; only a small subset has external evidence.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **540**
- Top extensions: .md:292, .py:120, .json:105, <none>:6, .txt:6, .csv:4, .cff:1, .toml:1
- Marker counts: todo=10, placeholder=9, stub=125, hardcoded=10, claim-language=110
- README excerpt: # ML4Industry  ML4Industry is a reproducible applied-machine-learning foundry spanning 64 manufacturing, maintenance, supply-chain, operations, energy, reliability, process-intelligence, and deployment-economics research projects.  The repository is evidence-first: a project being specified or runnable is not presented as proof that its scientific hypothesis is true. Synthetic smoke experiments validate software and protocol behavior only. See [`TRUTH.md`](TRUTH.md) and [`evidence/`](evidence/) for claim boundaries.  ## Quick start  ```bash python3 -m venv .venv .venv/bin/pip install -e . ml4industry validate ml4industry list --top 16 ml4industry run ML4INDUS-001 --output artifacts/smoke/ML4INDUS-001 ml4industry run-all --lane top16 --output artifacts/smoke python3 -m unittest discover -s tests -v PYTHONPATH=src python3 scripts/audit_portfolio.py ml4industry research-audit ml4industry re...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Mixed portfolio: many shared scaffolds; only a small subset has external evidence. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=9, stub=125 |
| hardcoded shortcut | hardcoded/toy markers=10 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | ML4Industry | Unresolved placeholder/stub markers require manual triage. | `CODE_QUALITY_AUDIT.md:10` - | TODO/FIXME/XXX/HACK/pseudocode/placeholder comments | 0 |; `evidence/stage_01.md:9` - than repeated placeholder language. Claim: specifications and implementations; `outreach/OUTREACH_PACK.md:71` - > Would your group be open to a short discussion about benchmark validation,; `src/ml4industry/code_audit.py:13` - MARKERS = ("TODO", "FIXME", "XXX", "HACK", "PSEUDOCODE", "PLACEHOLDER"); `src/ml4industry/models.py:10` - from sklearn.dummy import DummyClassifier, DummyRegressor | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `CODE_QUALITY_AUDIT.md:10` - | TODO/FIXME/XXX/HACK/pseudocode/placeholder comments | 0 |
- `tests/test_code_audit.py:19` - (root / "src" / "bad.py").write_text("def pending():\n    # TODO implement\n    pass\n", encoding="utf-8")
- `src/ml4industry/code_audit.py:13` - MARKERS = ("TODO", "FIXME", "XXX", "HACK", "PSEUDOCODE", "PLACEHOLDER")
### placeholder
- `CODE_QUALITY_AUDIT.md:10` - | TODO/FIXME/XXX/HACK/pseudocode/placeholder comments | 0 |
- `evidence/stage_01.md:9` - than repeated placeholder language. Claim: specifications and implementations
- `outreach/OUTREACH_PACK.md:71` - > Would your group be open to a short discussion about benchmark validation,
- `src/ml4industry/code_audit.py:13` - MARKERS = ("TODO", "FIXME", "XXX", "HACK", "PSEUDOCODE", "PLACEHOLDER")
- `src/ml4industry/models.py:10` - from sklearn.dummy import DummyClassifier, DummyRegressor
- `src/ml4industry/external/cmapss.py:14` - from sklearn.dummy import DummyRegressor
### stub
- `EVALUATION_REPORT.md:33` - scaffold-only, and no prospective industrial outcome is available.
- `README.md:60` - | Project-specific canonical specifications + runnable scaffold | 64 | implemented |
- `EXECUTION_QUEUE.md:14` - | Q10 | Task-native expansion | selected Tier E only | governed datasets | implementation, strong baseline, frozen external run | High | HEAVY | no shared scaffold remains for prom
- `REPRODUCIBILITY.md:73` - specified/shared-scaffold projects, not completed empirical studies. No project
- `PROJECT_TRUTH.md:13` - | Every project has executable code | Narrowly supported | 64 smoke artifacts; 48 use shared scaffold | VERIFIED_LOCAL | 48 lack task-native implementations | Build only against go
- `research/MASTER_RESEARCH_REGISTRY.md:20` - | ML4INDUS-014 | Predictive Maintenance | Transfer a failure-risk scaffold from source fleets to a held-out target fleet without target-test leakage. | SHARED_SCAFFOLD_VERIFIED | P
### hardcoded
- `MASTER_RESEARCH_REPORT.md:21` - - **ML4INDUS-017 — Demand Shift Calibrator**: Recent-window calibration improves synthetic Brier score across seeds and frozen stress. Biggest reviewer concern: recent-window recal
- `research/MASTER_RESEARCH_REGISTRY.md:23` - | ML4INDUS-017 | Supply Chain | Recalibrate a demand-risk score after gradual temporal drift using only outcomes available before the evaluation window. | TASK_NATIVE_VERIFIED | Re
- `company_packages/ML4INDUS-017.md:29` - - Current blocker: recent-window recalibration is synthetic only; real product demand scores, label delay, and replenishment decisions remain
- `tests/test_scheduling.py:39` - fixture = """instance toy
- `scripts/summarize_runs.py:118` - "ML4INDUS-017": "recent-window recalibration is synthetic only; real product demand scores, label delay, and replenishment decisions remain",
- `registry/truth_ledger.json:272` - "blocker": "recent-window recalibration is synthetic only; real product demand scores, label delay, and replenishment decisions remain"
### claim
- `PROJECT_STATUS.md:11` - to conference-ready.
- `README.md:51` - current result has a sectioned manuscript draft and checksum-verified publication
- `DEFINITION_OF_DONE.md:23` - - Atomic/checksummed result publication; failed runs preserved separately.
- `RESEARCH_COMPLETION_REPORT.md:25` - | Paper-ready | 0 |
- `TRUTH_MAP.md:19` - | ML4INDUS-025 publication outputs | IMPLEMENTED + VERIFIED | PNG, SVG, two CSV tables, and manifest verify against the checksum-protected v3 source | Descriptive output only; does
- `PROJECT_TRUTH.md:22` - | Portfolio is conference ready | Unsupported | research/project audits report zero ready | NOT_RUN | Novelty, external validity, manuscripts | Complete gates per project |


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Industry` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Industry` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Industry` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/ML4Industry` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

