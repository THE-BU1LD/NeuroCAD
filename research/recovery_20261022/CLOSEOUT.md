# NeuroCAD recovery and evidence closeout — 22 October 2026

## Disposition

The maintained implementation now passes 2,240 local tests with 12 optional-backend skips and 53 passing subtests, two reproduced input/provenance defects are repaired, and a fresh hosted execution reproduces the frozen Physics v2 decisions on all 216 original synthetic cases. The manuscript is a complete account of the bounded compiler, analytical receipts, historical failures, and remaining evidence limits. This is a concrete research artifact, not a claim of a perfect general CAD model.

The original compiler study remains **MIXED**. Its earlier typed-parser causal claim remains falsified. Physics v2 remains **SUPPORTED within its synthetic software contract**; the new execution is an internal cross-environment reproduction of already observed outcomes. Engineering extensions and test passes do not establish independent language generalization, physical accuracy, or user benefit.

## What was implemented

### 1. Feature IR admission before unsafe operations

Malformed JSON-shaped values in identity, role, parameter, node, or geometry fields could reach iteration, hashing, or operation dispatch before their structural type was established. Some inputs raised `TypeError` instead of returning structured validation errors; some malformed role or null geometry fields were accepted.

`core/feature_ir.py` now establishes string, array, and object structure before those operations. Required geometry cannot be null, operation membership is type guarded, and invalid dictionary keys receive structured parse failures. Valid references and optional null fields retain their prior semantics. The new 74-case regression set produced **46 failures and 28 passes on the original source** and passes on the repaired implementation. The connected feature/inspection/revision/backend/export cohort produced **158 passes and 5 optional-backend skips**.

This is an admission repair for supported JSON-shaped data and ordinary direct model construction. It is not a claim that arbitrary malicious Python subclasses or cyclic object graphs are supported.

### 2. Demo provenance belongs to the executing CLI

The old demo could execute `NEUROCAD_CLI` from one installation while identifying source through an unrelated `PYTHON_BIN`. It also did not reject persistent implementation changes across artifact generation.

The CLI now exposes `neurocad provenance --json`. The executing CLI supplies its own source path, and the shared identity function hashes the declared source and packaged-resource inventory. The demo takes snapshots before and after generation, checks their identities and version consistency, and refuses to issue a successful receipt if they differ. Its separate Python writer only serializes evidence. Git revision metadata is explicitly unverified as an implementation identity.

The receipt covers on-disk source and resources, not loaded bytecode, third-party dependencies, cryptographic authorship, or transient edits restored between snapshots. The original-script regression witnesses are retained alongside passing candidate tests.

## Actual execution evidence

| Execution | Observed result | Evidence |
| --- | --- | --- |
| Maintained full suite, ordinary sandbox | 2,208 passed, 13 skipped, 4 failed, 27 setup errors, 53 subtests passed; every unsuccessful case raised socket `PermissionError` | `engineering/full-tests.txt`, `engineering/full-tests.xml` |
| Same maintained full suite, local test sockets permitted | **2,240 passed, 12 skipped, 53 subtests passed in 98.32 s** | `engineering/full-tests-with-sockets.txt`, `engineering/full-tests-with-sockets.xml` |
| Real OpenSCAD demo | Plate, cylinder, enclosure body/lid generated; unsupported prompt rejected; **32 artifact hashes and 85 implementation file hashes verified** | `native-demo/DEMO_RECEIPT.json`, `engineering/native-demo-audit.json` |
| Frozen Physics v2 on GitHub CPU | Successful single execution; all 216 retained case verdicts and 13 endpoints reproduced; prerequisite suite 1,203 passed and 9 optional-backend skips | `hosted-reproduction/`, `hosted-job-log.txt`, `hosted_reproduction_audit.json` |
| Historical evidence reanalysis | Raw results regenerate checked descriptive results; known archival failure remains visible | `evidence_audit.json`, `evidence_reanalysis.json`, `reanalyze.py` |
| Historical file preservation | **4,277 prior research/paper/release files unchanged**; canonical state is the only changed prior file, and its original bytes are preserved | `history_integrity.json`, `original_artifact_hashes.json`, `entry_state.json` |

The first local suite failure remains part of the record. No assertion or test was removed to obtain the passing rerun. Optional native backends absent from the local environment account for remaining skips; the repository's native CI matrix is the corresponding integration gate.

### Hosted execution identity

- Workflow: `.github/workflows/physics-v2-internal-reproduction-20261022.yml`.
- Request recorded before execution: `REPRODUCTION_REQUEST.json`.
- Run: <https://github.com/THE-BU1LD/NeuroCAD/actions/runs/39726824693>.
- Workflow revision: `95aa315e87e0546191bbcdbce60f9c083b43b4b6`.
- Exact frozen source checkout: `786ba9ba5c2249a710529c3b07bf82d4e29c7f36`.
- Artifact ID: `12402399676`.
- Downloaded ZIP SHA-256: `4c8c9e7af18fcaed4a88d3ecd0bfa00d9b5161ae898ee20c7840d17e2220d217`.

The local resource preflight refused execution before any study case ran; its observations are retained in `evidence_audit.json` under `reproduction_preflight`. The hosted workflow required the original frozen source hashes, dataset, freeze, resource floors, preflight and full engineering checks. It did not weaken the runner or adapt any scientific endpoint. The declaration labels the execution `INTERNAL_CROSS_ENVIRONMENT_REPRODUCTION`. The legacy runner's `confirmatory` phase field is preserved verbatim; it does not turn this repeat into an independent protected experiment. There are still 216 unique synthetic cases, not 432 independent observations.

## Positive result and its scope

The original compiler run has 240/240 selected semantic signatures, 1,000/1,000 static IR checks, and 240/240 fresh kernel executions. These are controlled grammar-conformance outcomes. The benchmark's test split contains 48 tasks, and its reference baselines are deliberately simple. General English understanding or superiority to modern learned CAD systems does not follow.

The frozen Physics v2 study accepts 48/48 valid requests and detects 96/96 predeclared contradiction/stale-expected-hash cases. It detects 48/48 later geometry changes. The hash-only control detects changes but misses all 72 semantic contradictions; the unbound control misses all 48 later changes. This isolates the intended difference between content freshness and selected cross-field agreement checks. Neither a matching hash nor an internally consistent formula establishes physical adequacy.

The new hosted repeat reproduces the declared decisions without changing the evaluated code or cases. It strengthens execution reproducibility across environments. It does not create independent authorship, remove shared implementation/oracle assumptions, or establish physical truth.

## Flaw checklist, repair and required evidence

| Flaw or limitation | Cause and severity | Action and observed status | Evidence needed for a stronger conclusion |
| --- | --- | --- | --- |
| Malformed Feature IR crashes or acceptance | Structural admission occurs too late; high correctness impact | **Repaired.** Baseline failures reproduced; new and connected regression suites pass | Maintain adversarial admission tests with future schema changes |
| Demo may identify the wrong installation | Source identity computed by a separate interpreter; high provenance impact | **Repaired.** Identity is returned by executing CLI; snapshots and native artifacts verified | Installed-package identity remains part of CI and any release audit |
| Persistent source drift during demo | No before/after consistency gate; high provenance impact | **Repaired.** Drift prevents success receipt | External signatures or dependency capture would be a separate provenance scope |
| Broad language claims exceed benchmark | Synthetic template grammar and shared assumptions; high scientific impact | **Claims narrowed.** Raw split denominators and baseline limitations disclosed | Frozen external challenge with at least 160 independently human-authored/adjudicated prompts, including at least 120 valid and 40 rejection cases, plus the declared comparator |
| Earlier causal claim failed | Historical mechanism-off evidence contradicts it; high scientific impact | **Preserved as falsified.** Later repair does not rewrite that finding | A materially new hypothesis and separately frozen study |
| Simple comparators cannot establish state of the art | Missing strong matched comparators; high scientific impact | **No state-of-the-art claim.** Current relevant literature discussed | Executable strong comparator under matched data/information and predefined scoring |
| Receipt freshness mistaken for physical validity | Hashing tracks declared bytes, not reality; high scientific impact | **Claim boundary explicit.** Semantic and hash-only controls separated | Calibrated measurements, reference-model validation and stated uncertainty |
| No external human/user evidence | No independent dataset or observed user study is available; high external-validity impact | **Open.** No agent-generated substitute is represented as independent human data | Actual independent authors, adjudicators and intended-user observations |
| One original compiler log absent | Archive contains 1,211 matching artifacts of 1,212 listed; medium audit impact | **Retained as missing.** No historical log fabricated | Recover the authentic original log if it exists; otherwise keep qualification |
| Timing-sensitive historical digest | Ten timing fields affect the old result digest; medium reproducibility impact | **Disclosed.** Original bytes and digest preserved | A separately versioned semantic digest if designed for future studies |
| Historical median uses upper middle | Even-sample scorer chooses one central item; medium reporting impact | **Disclosed and reanalyzed.** Conventional medians are reported separately | Preserve frozen scoring; use explicit aggregation definitions in future protocols |
| Unequal timing samples and different machines | Successful-case conditioning and different hardware; medium efficiency impact | **No speedup claim.** Descriptive measurements and denominators disclosed | Matched workloads, environment and planned efficiency comparison |
| Local test socket denial | Execution sandbox prevented test-server setup; environmental | **Resolved for verification.** Original failure retained; unchanged full suite passes with socket access | Exact candidate CI checks before merge/release |
| Kaggle account inaccessible | Current task browser is signed out; execution access | **Open.** No Kaggle run or result retrieval is claimed | Authenticate the Kaggle session, then identify/download actual notebook outputs or run an explicitly recorded job |
| Universal perfection is not an empirical endpoint | Finite tests cannot prove arbitrary-input correctness; scope error | **Rejected as a claim.** Terminal outcomes are stated per study | Explicit contracts, reproducible tests, and calibrated claims rather than an unfalsifiable guarantee |

## Reproduction and artifact map

From the repository root, create and activate the documented supported environment,
then install this candidate with `python -m pip install -e '.[dev]'`. The older
published alpha does not contain the new `provenance` command. Figure regeneration
also requires Matplotlib; the native demo requires OpenSCAD on `PATH`. Use:

```bash
python research/recovery_20261022/reanalyze.py --check research/recovery_20261022/evidence_reanalysis.json
python paper/recovery_20261022/generate_evidence.py
python -m pytest -q tests
neurocad provenance --json
NEUROCAD_CLI=neurocad PYTHON_BIN=python bash demo/build_demo_kit.sh /tmp/neurocad-demo-reproduction
```

The demo destination must not already exist; choose a new directory for each repeat.
The historical reanalysis deliberately records the known missing-log audit failure. Read the paper directory README for LaTeX build and evidence regeneration details. The hosted workflow is the exact retained specification for the single internal scientific rerun; do not silently relabel additional executions as independent confirmation.

`paper/recovery_20261022/main.tex` and `main.pdf` contain the complete manuscript. `references.bib`, the original user-supplied `arxiv.sty`, generated tables, the result figure and `evidence_sources.json` are included. `engineering/REVIEW.md` describes implementation review. The canonical entry point remains `research/RESEARCH_STATE.json`; this recovery session appends evidence and preserves predecessor histories.

## Release boundary

This candidate is ready for exact-revision repository CI and review. A successful local suite and hosted frozen reproduction do not authorize an assertion that every optional backend/platform or scientific external gate has passed. The GitHub pull request and immutable candidate commit identify the integrated artifact. Publication, arXiv submission, human/physical validation and Kaggle retrieval are not represented as completed unless their actual receipts exist.
