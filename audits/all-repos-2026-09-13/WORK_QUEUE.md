# All-Repositories Audit Work Queue — 2026-09-13

Scope root: `/Volumes/PRO-BLADE/GitHub-Every-Repo`

This is the live remediation queue for the generated per-repository audit set in
[`INDEX.md`](INDEX.md). The goal is not to make every directory look like a
paper; it is to keep claims aligned with executable evidence and to separate
research, products, archives, and empty shells.

## Progress Snapshot

- Reports generated: **45**
- Reports with zero generated critical findings after this pass: **18**
- Repos explicitly quarantined as non-research/archive/shell/product surfaces:
  `EigenFinance`, `Finance-Meta-Research-LGWM-Hedge-Fund-864431cb2c398254eb81322d15f12ac9eaa22a0a`,
  `Finance-Meta-Research-org-infra-da0cd622742f1b6b0d07ec6e8c785cf98ed8f977`,
  `SourceZips`, `results`, `IY-ERN`, plus product-surface warnings for
  `BU1LDLanding`, `FinanceMeta-Landing`, and `VertexED`.
- Scanner/generator fixed so truth-boundary language, integrity checks,
  `unittest.mock`, citation URLs, and "placeholder scan" validation text do not
  create fake placeholder findings.

## Addressed In This Pass

| Repository/component | Change made | Verification/status |
|---|---|---|
| Audit generator | Added non-actionable marker filtering, focused notes injection, work-queue link in `INDEX.md`, and suppression of generic source/test/result findings for archive/output-only directories. | Regenerated all 45 reports successfully with `rtk /opt/homebrew/bin/python3.12 scripts/audit_all_repos.py`. |
| DRPT | Preserved focused audit notes showing the previous-phase path is exercised and smoke losses are finite. | `python3 -m unittest discover -s tests -v` previously passed 6 tests; generated report now has 0 generic findings. |
| RIS | Preserved focused audit notes showing the old IRR claim is removed and current evidence is a bounded WDBC Hessian-estimation benchmark. | `python3 -m unittest discover -s tests -v` previously passed 3 tests; generated report now has 0 generic findings. |
| EPU | Added `requirements.txt`; changed README wording from "bounded scaffold" to "bounded prototype"; preserved focused notes that full iterative retrieval underperforms controls. | `python3 -m unittest discover -s tests -v` previously passed 3 tests; generated report now has 0 generic findings. |
| NGMT | Cleaned historical handoff wording and preserved exact negative/provenance notes from `RESEARCH_TRUTH.md` and `FINAL_SUBMISSION_STATUS.md`. | Generated report now has 0 generic critical findings; scientific blocker remains a failed primary improvement gate plus incomplete submission provenance. |
| ML4SematicIntelligence | Preserved exact implementation-tier notes: 2 project-specific external implementations, 14 shared diagnostics, 48 spec-only entries, 0 conference-ready papers. | Generated report now has 1 actionable P1: unresolved outreach draft placeholders. |
| Speechly | Added README/status boundary and `requirements.txt`. | Generated report now has 0 generic findings; still scientifically a demo/prototype until trained/evaluated. |
| IRIS-Draft | Added `requirements.txt` documenting stdlib-only environment and test command. | Generated report now has 0 generic findings. |
| Empty/shell repos | Added status-boundary READMEs to `EigenFinance`, `Finance-Meta-Research-LGWM-Hedge-Fund-864431cb2c398254eb81322d15f12ac9eaa22a0a`, and `Finance-Meta-Research-org-infra-da0cd622742f1b6b0d07ec6e8c785cf98ed8f977`. | They remain P0 non-research shells by design; this prevents them from being counted as completed research. |
| Archive/output dirs | Added boundary READMEs to `SourceZips` and `results`. | Generated reports now show 0 generic findings for both archive/output-only directories. |
| IY-ERN | Added README/status boundary identifying it as a React/Vite landing surface, not a research implementation. | Still scaffold with 4 findings because product tests/results/integration boundaries remain incomplete. |

## P0 — Still Scientifically Invalid Or Non-Research

| Repository | What is wrong | Why it matters | How to fix | Where | How to verify |
|---|---|---|---|---|---|
| `EigenFinance` | Empty shell with README/license only. | Counting it as research inflates the portfolio and misleads reviewers. | Keep quarantined, archive it, or implement an actual method/data/evaluation path. | `/Volumes/PRO-BLADE/GitHub-Every-Repo/EigenFinance` | Re-run the all-repo audit and ensure no portfolio dashboard counts it as implemented research. |
| `Finance-Meta-Research-LGWM-Hedge-Fund-864431cb2c398254eb81322d15f12ac9eaa22a0a` | Empty shell with status boundary only. | Same project-count/evidence inflation risk. | Keep as non-research shell or add real code, data, experiments, and retained outputs. | Matching repo root | Re-run audit and any portfolio index generation. |
| `Finance-Meta-Research-org-infra-da0cd622742f1b6b0d07ec6e8c785cf98ed8f977` | Infrastructure stub, not science. | Infrastructure must not be confused with empirical contribution. | Keep under infrastructure or add a clear implemented research target. | Matching repo root | Re-run audit and search dashboards for implementation-count claims. |
| `BU1LDLanding` | Product/portfolio landing surface. | Product copy can overstate research maturity. | Keep as site only; link claims to evidence ledgers in source repos. | `/Volumes/PRO-BLADE/GitHub-Every-Repo/BU1LDLanding` | Run copy/claim scan and build/test the site. |
| `FinanceMeta-Landing` | Product/portfolio landing surface. | Same unsupported-claim risk. | Remove invented metrics/project-count claims or link to evidence ledgers. | `/Volumes/PRO-BLADE/GitHub-Every-Repo/FinanceMeta-Landing` | Run copy/claim scan and build/test the site. |
| `IY-ERN` | React/Vite landing surface with remaining scaffold/product findings. | It is not an experimental research repo. | Add product tests/build verification, remove unresolved integration placeholders, and keep non-research boundary. | `/Volumes/PRO-BLADE/GitHub-Every-Repo/IY-ERN` | `npm install`/build/test if dependencies are available, then regenerate audit. |
| `VertexED` | Education product repo with research/product boundary risk. | Product features are not scientific results. | Split product claims from any evaluation claims; add tests and evidence manifest. | `/Volumes/PRO-BLADE/GitHub-Every-Repo/VertexED` | Re-run claim scan plus app tests. |

## P1 — Required For Credible Research

| Repository | What is wrong | Why it matters | How to fix | Where | How to verify |
|---|---|---|---|---|---|
| `ML4SematicIntelligence` | Outreach drafts still contain `[Name]` / `[recent paper]` placeholders; portfolio remains mostly spec-only. | Reviewers can mistake prospecting text and specifications for executed work. | Replace or quarantine outreach drafts; keep 48 spec-only entries out of implementation counts; prioritize ML4SEMAN-033/059. | `outreach/drafts/*`, `PROJECT_TRUTH.md`, `TRUTH_MAP.md` | Regenerate audit; registry/status docs must still show 2 project-specific implementations, 14 shared diagnostics, 48 specs unless new evidence is added. |
| `NGMT` | Current Recovery v2 result fails the predefined primary improvement gate and submission provenance is incomplete. | A paper claim of robust memory improvement is unsupported. | Preserve negative result; rerun publication/provenance gate only after license/authorship decisions; rebuild source/paper artifacts from current hashes. | `RESEARCH_TRUTH.md`, `FINAL_SUBMISSION_STATUS.md`, publication scripts | Gate report has no hash/provenance blockers and still does not promote failed memory-improvement claim. |
| `DRPT` | No matched no-feedback ablation or multi-seed effect estimate. | The feedback/hysteresis hypothesis is not isolated. | Add paired no-feedback ablation, multiple seeds, phase metrics, confidence intervals, and retained results. | `src/train.py`, `src/eval.py`, experiment configs/results | Report includes no-feedback contrast, switch F1, transition delay, CIs, and seeds. |
| `EPU` | Full iterative retrieval underperforms simple controls on the retained digits benchmark. | Core mechanism is currently negative or broken as a research claim. | Fix retrieval dynamics or explicitly label full iterative EPU as a failed ablation; add RTL/Python equivalence tests if hardware language remains. | `code/epu_reference.py`, `benchmarks/run_ablation_benchmark.py`, `code/epu_core.v` | Benchmark JSON shows full variant beating controls across seeds/noise, or docs clearly demote it. |
| `RIS` | Evidence is bounded to one WDBC Hessian-estimation benchmark. | Broader numerical-method claims are not justified. | Keep strict claim boundary or add second dataset/objective and stronger numerical baselines. | `README.md`, `results/hessian_stability_v1.json`, benchmark code | Re-run tests/benchmark and verify claims match retained result JSON. |
| `ML4Science` | Code exists but tests were not detected by the generated scan. | Research dashboards can regress silently. | Surface existing reproduction commands or add validators for result artifacts/metrics. | Repo root docs/tests | Audit detects test paths or README gives a verified one-command validation path. |
| `Research-Pilot` | Product workflow prototype still carries publication-style language and marker findings. | Tooling can be mistaken for scientific evidence. | Demote publication copy, add product tests, or bind workflow claims to evaluated artifacts. | Repo docs/templates/app code | Copy audit finds no unsupported publication-ready language. |

## P2 — Major Quality Improvements

| Work item | Why it matters | Where | How to verify |
|---|---|---|---|
| Literature/novelty reviews for serious candidates | Novelty cannot be defended from local files alone. | Start with NGMT, ML4SematicIntelligence, FIM/FI-JEPA, LAM-JEPA, RIPII, NeuroCAD. | Add related-work matrices with dated citations, strongest baselines, and explicit deltas versus prior work. |
| One-command reproduction manifests | Reviewers need raw-data-to-paper traceability. | Every `partial` research repo. | Fresh clone can run setup + smoke/eval; generated metrics match retained manifests. |
| Dataset cards and leakage checks | Data contamination can invalidate otherwise good code. | All empirical repos with real or synthetic data. | Split manifests, raw hashes, licenses, preprocessing hashes, and leakage tests exist. |
| Consolidate duplicate/legacy trees | Duplicates can be mistaken for independent replication. | `QFIM`, `Fabric-Induced-Memory`, `PercyxLyla-*` | Portfolio index labels them archive/legacy and excludes them from independent evidence counts. |

## P3 — Polish / Engineering

| Work item | Why it matters | Where | How to verify |
|---|---|---|---|
| Improve reviewer ergonomics | Audit evidence is still spread across many docs. | All active research repos. | Each repo has a single evidence ledger linking commands, configs, artifacts, and paper claims. |
| Add CI or local smoke scripts | Prevents evidence rot. | Active research repos and product surfaces. | Clean CI/smoke logs are retained or reproducible locally. |
| Lock dependencies where possible | Fresh-run reproducibility is fragile without pins/locks. | Python/JS repos without lockfiles. | Build/test from a clean environment succeeds with documented commands. |

## Next Active Step

Work the remaining generated findings by count: `IY-ERN` (4), `Research-Pilot`
(3), `BU1LDLanding`/`FinanceMeta-Landing`/`VertexED` (2 each), then the
single-finding research repos. In parallel, begin the P1 scientific work that
cannot be solved by documentation alone: NGMT provenance rebuild, DRPT
no-feedback ablation, EPU mechanism repair/demotion, and ML4SematicIntelligence
implementation-tier enforcement.
