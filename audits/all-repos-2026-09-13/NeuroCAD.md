# Research Audit Checklist — NeuroCAD

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Engineering-verified compiler with partial research evidence; benchmark is bounded to its own grammar.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **359**
- Top extensions: .py:234, .md:77, .json:15, .sh:7, .txt:7, <none>:5, .lock:2, .in:2
- Marker counts: todo=10, placeholder=40, stub=8, hardcoded=7, claim-language=51
- README excerpt: # NeuroCAD  NeuroCAD is a strict prompt-to-parametric-program tool for fully dimensioned plates, rectangular boxes/enclosures, and basic box, cylinder, and sphere primitives. Prompts compile through a versioned, schema-validated internal representation to deterministic OpenSCAD. Every exported length is expressed in millimetres.  Research status: the maintained compiler is engineering-verified, while the conference evidence is **partial**. The retained full benchmark is synthetic and historically source-unbound; it must not be read as external validation. Start with `RESEARCH_TRUTH.md`, `audit/REPOSITORY_MAP.md`, and `audit/CONFERENCE_READINESS_CHECKLIST.md` for the current evidence boundary.  NeuroCAD is an alpha design aid. Generated parts must still be reviewed by a qualified person before fabrication. It does not calculate load capacity, material behaviour, regulatory compliance, or ...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Engineering-verified compiler with partial research evidence; benchmark is bounded to its own grammar. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=40, stub=8 |
| hardcoded shortcut | hardcoded/toy markers=7 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | NeuroCAD | Unresolved placeholder/stub markers require manual triage. | `CHANGELOG.md:69` - - Replaced the legacy fake STEP writer with an explicit unsupported-format error so direct legacy use cannot create a misleading `.step` file.; `install.sh:95` - say "Add this to your shell profile if neurocad is not on PATH:"; `NEUROCAD_TRUTH.md:80` - ## Broken, fake, stubbed, or disconnected functionality; `RESEARCH_GRADE_REPORT.md:77` - - historical STEP export was fake marker text and is disabled;; `EXECUTION_MEGAPROMPT.md:18` - Your mission is to make the supported NeuroCAD workflow genuinely installable | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `docs/MEGA_AUDIT_AND_ACTIONS_20260908.md:50` - | Maintained `core/` and CLI | Executable implementation | No TODO/FIXME/NotImplemented markers found in the targeted scan; this does not prove absence of defects |
- `docs/EXECUTION_20260908.md:1` - # Master TODO execution — 2026-09-08
- `scripts/audit_all_repos.py:81` - "todo": re.compile(r"\b(TODO|FIXME|TBD|XXX)\b", re.I),
### placeholder
- `CHANGELOG.md:69` - - Replaced the legacy fake STEP writer with an explicit unsupported-format error so direct legacy use cannot create a misleading `.step` file.
- `install.sh:95` - say "Add this to your shell profile if neurocad is not on PATH:"
- `NEUROCAD_TRUTH.md:80` - ## Broken, fake, stubbed, or disconnected functionality
- `RESEARCH_GRADE_REPORT.md:77` - - historical STEP export was fake marker text and is disabled;
- `EXECUTION_MEGAPROMPT.md:18` - Your mission is to make the supported NeuroCAD workflow genuinely installable
- `RESEARCH_COMPLETION_CHECKLIST.md:13` - Implementation: `docs/PROJECT_STATE_AUDIT.md` classifies every major subsystem; legacy fake STEP and Stage 1 remain negative evidence.
### stub
- `docs/CODE_AUDIT_20260908.md:28` - | VeriCodeGen Stage 1 | Executable experiment scaffold | Scripted fixtures and kernel plumbing are not learned-model results |
- `docs/MEGA_AUDIT_AND_ACTIONS_20260908.md:51` - | `legacy/python/cad_master_kernel_legacy_broken.py` | Abandoned incomplete implementation | Contains `NotImplementedError`; excluded from supported distribution |
- `docs/FINAL_9_OF_10_CHECKLIST.md:37` - | `legacy/python/cad_master_kernel_legacy_broken.py` | Abandoned implementation with `NotImplementedError` | Remains archived and excluded from distributions; not a supported featu
- `scripts/audit_all_repos.py:91` - r".{0,120}\b(marker|placeholder|stub|mock|fake|publication|conference|paper-ready|implemented|claim|evidence)\b",
### hardcoded
- `DEFINITION_OF_DONE.md:10` - | Real end-to-end path | At least one non-hard-coded input reaches real OpenSCAD, produces STL, and passes topology and dimensional checks. | kernel integration tests and `NC-EXP-0
- `scripts/audit_all_repos.py:84` - "hardcoded": re.compile(r"\b(hardcoded|hard-coded|shortcut|toy|synthetic only)\b", re.I),
### claim
- `RESEARCH_TRUTH.md:13` - - Current conference-readiness verdict: **EVIDENCE_PARTIAL**.
- `CHANGELOG.md:24` - - Required three-browser kernel acceptance before tag publication; alpha/RC
- `install.sh:79` - # Keep the staged environment if publication partially succeeds; a launcher
- `README.md:10` - conference evidence is **partial**. The retained full benchmark is synthetic and
- `RESEARCH_GRADE_REPORT.md:10` - The weakest aspects are decisive for publication: evaluation data are authored from the same grammar, the fast product benchmark has only 46 unique prompts in 48 rows, baselines ar
- `EXECUTION_MEGAPROMPT.md:53` - - If credentials or a consequential publication decision are missing, complete


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
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/NeuroCAD` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

