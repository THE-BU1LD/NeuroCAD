# Project state audit

**Audit date:** 2026-09-13  
**Scope:** current `main` checkout, maintained package, research tooling, retained evidence, and archived legacy surface  
**Evidence rule:** a file is not implementation evidence; `COMPLETE` requires a connected path and a passing check.

## Research reconstruction

NeuroCAD hypothesizes that a deterministic, typed, fail-closed compiler can translate a declared dimensioned-English CAD subset into semantically exact, editable programs and valid OpenSCAD solids more reliably than simple fixed, numeric-extraction, and train-only retrieval baselines under controlled template, unit, and composition shifts.

This is a compiler/systems thesis, not a learned-model thesis. Its strongest defensible contribution is an auditable narrow-language compiler plus unusually explicit evidence boundaries. It does not establish general text-to-CAD intelligence, BREP/STEP generation, design-intent inference, manufacturability, human usability, or state of the art.

## Component map

| Component | Purpose | Current state | Evidence | Quality / trust boundary | Missing | Priority |
|---|---|---|---|---|---|---|
| Prompt parser | Parse bounded dimensioned English | COMPLETE | `core/prompt_engine.py`, parser/safety tests | Strong for declared grammar only | Independent natural-language set | P1 |
| Compatibility graph | Preserve older parser interface | FUNCTIONAL BUT WEAK | `core/design_graph.py`, adapter tests | Connected but not canonical | Eventual deprecation plan | P3 |
| Canonical IR | Typed editable CSG program | COMPLETE | `core/ir.py`, schema, round-trip tests | Strong bounded representation | Sketch/BREP/assembly semantics | P2 scope expansion |
| IR parser/serializer | Strict deterministic JSON | COMPLETE | `core/ir_parser.py`, `core/json_io.py`, tests | Duplicate keys, depth and size bounded | None in current scope | P3 |
| Semantic validation | References, domains, graph and constraints | COMPLETE | `core/ir.py`, validation tests | Checks declared relations; not a solver | More adversarial geometry cases | P2 |
| OpenSCAD exporter | Deterministic executable CSG | COMPLETE | `core/ir_export.py`, CLI/integration tests | OpenSCAD, not BREP | Alternative kernel only for scope expansion | P3 |
| External kernel execution | Compile SCAD to STL/PNG | COMPLETE | `core/artifacts.py`, installed OpenSCAD tests | External version/platform affects bytes | Cross-platform receipts | P1 |
| Mesh verification | Finite, volume, winding, components, extents | COMPLETE | `core/artifacts.py`, `core/topology.py`, tests | Does not prove self-intersection-free BREP equivalence | Stronger intersection checks | P2 |
| Structural evaluator | Program metrics and deterministic round trip | COMPLETE | `core/program_evaluation.py`, tests | Appropriate engineering metrics | None in current scope | P3 |
| Product benchmark runner | Compare compiler and simple baselines | COMPLETE | `core/benchmark.py`, dataset tests | Now loads frozen data without mutation | External compatible baseline | P1 |
| Benchmark dataset loader | Strict bounded frozen JSONL loading | COMPLETE | `load_benchmark`, `tests/test_dataset_pipeline.py` | Rejects unknown fields and cross-split duplicates | Optional near-duplicate detector | P2 |
| Dataset prepare/inspect CLI | Generate, checksum, validate owned data | COMPLETE | `core/data.py`, CLI tests | No network download because data are project-authored | External-data adapters | P2 |
| 48-task product dataset | Fast regression suite | FUNCTIONAL BUT WEAK | tracked JSONL; validator hash | 48 rows, 46 unique prompts; two within-train duplicate records | New version with unique independently authored prompts | P1 |
| 240-task compiler stress set | Controlled contract experiment | COMPLETE | generator, historical JSONL, tests | Synthetic and grammar-authored | Independent frozen evaluation | P1 |
| Invalid-input taxonomy | Fail-closed regression | COMPLETE | NC-EXP-003, unique future fixtures | Historical run repeated eight templates | Independently authored malformed cases | P1 |
| IR stress | Validate/export generated programs | COMPLETE | NC-EXP-002, research tests | Generated invariants, not real-design coverage | Real program corpus | P2 |
| Constraint ablation | Detect injected dimensional drift | COMPLETE | NC-EXP-004 | Clean paired mechanism test; narrow | Broader constraint types | P2 |
| Frontend ablation | Remove parsing capabilities | FUNCTIONAL BUT WEAK | benchmark baselines | Raw baseline removes several factors jointly | Factorial unit/feature/lexical ablations | P1 |
| Editability experiment | Automated parameter edits | COMPLETE | NC-EXP-005 | Machine editability only | Human task study | P1 |
| Hierarchy stress | Enforce depth boundary | COMPLETE | NC-EXP-007 | Constructed engineering stress | Breadth/memory scaling study | P2 |
| Research orchestration | Run suite and retain raw artifacts | COMPLETE | `core/research_suite.py`, `NC-REPRO-508EC40` | Clean source-bound non-resumed full run retained | External replication | P1 |
| Research config loading | Freeze and override reviewed settings | COMPLETE | `load_research_config`, config tests | Rejects unknown fields/version mismatch | Config schema if formats multiply | P2 |
| Ablation manifest | Declare factors and metrics | COMPLETE | `configs/ablation_manifest.json` | Honest about coupled frontend ablation | Execute expanded factorial design | P1 |
| Reproducibility metadata | Source, Git, lock, platform, kernel, artifacts | COMPLETE | `NC-REPRO-508EC40` manifest/runtime receipt | Clean commit, source/lock/kernel hashes, 1,212 artifact hashes, zero reuse | Public immutable receipt | P1 external gate |
| Current source-bound evidence | Retained controlled outcomes | COMPLETE | `NC-REPRO-508EC40` | Reproducible controlled evidence; synthetic and project-authored | Independent benchmark and replication | P1 |
| Historical FULL evidence | Retained controlled outcomes | PARTIAL | `NC-RUN-2026-09-03-FULL` | No producing-source provenance; 181 kernel artifacts reused | Never upgrade without rerun | P0 claim boundary |
| Prompt challenge | Audit-authored robustness set | FUNCTIONAL BUT WEAK | 24-case JSONL/results/tests | Authored after implementation inspection | Blind outside-authored challenge | P1 |
| Statistical analysis | Wilson intervals and paired exact tests | COMPLETE | runner/tests/statistical plan | Complete for controlled suite; generated cases are not population samples | Bootstrap effect CI on independent data | P1 |
| Error analysis | Raw failures and taxonomy | COMPLETE | result records, `analysis/` | No system failures in synthetic set; baseline errors retained | Independent failure corpus | P1 |
| Enclosure domain model | Typed body/lid/product specification | COMPLETE | enclosure modules and tests | Bounded design aid | Physical validation | P1 |
| Manufacturing preflight | Exact and disclosed heuristic checks | COMPLETE | `core/manufacturing.py`, tests | Heuristics are not certification | Coupon/print evidence | P1 |
| Calibration | Robust coupon-derived recommendations | COMPLETE | `core/calibration.py`, tests | No retained physical measurements | Execute physical protocol | P1 |
| Application integrations | Verified files and bounded KiCad extraction | COMPLETE | `core/integrations/`, tests | Complete for declared contracts; mostly handoff, not native API import | Real target-app receipts | P2 |
| Local browser workbench | Interactive real pipeline | COMPLETE | server/UI/browser contract tests | Local unauthenticated tool | Usability study and hosted security design | P2 |
| CLI | Product/research/data commands | COMPLETE | subprocess tests and smoke scripts | Stable alpha interface | Formal compatibility policy | P3 |
| Checkpointing/training/loss/optimizer | Learned-model pipeline | MISSING | no model claimed | Not applicable to compiler thesis | Separate frozen learned study | P3 scope expansion |
| VeriCodeGen Stage 1 | Historical model-comparison idea | BROKEN | protocol/ledger audits | Broken as evidence: scripted plumbing made no model calls | Do not cite as model outcome | P0 integrity |
| VeriCodeGen S3 | Authorized learned experiment | PARTIAL | safe capture/ledger/preflight tooling | Correctly pre-outcome and blocked | Candidate pool, provider/model, budget, authorization | P1 external gate |
| Legacy neural/CAD surfaces | Historical forensic archive | DEAD | `legacy/`, archive tests | Excluded from package; contains known broken paths | Keep quarantined | P2 |
| STEP/BREP export | Exact CAD exchange | MISSING | fake historical route hard-disabled | Unsupported | Real BREP kernel and tests | P3 scope expansion |
| Tests | Scientific and product invariants | COMPLETE | Maintained local and hosted suites | Some kernel tests require OpenSCAD; exact counts change with the suite | Exact-revision receipts | P1 |
| CI | Multi-version/OS/browser/kernel/package gates | COMPLETE | `.github/workflows/` and CI-gate tests | Configuration complete; no exact-revision hosted receipt in checkout | Run on published revision | P1 external gate |
| Packaging | Wheel/sdist/install verification | COMPLETE | build scripts/tests | Complete locally; checked-in `dist/` is historical | Fresh exact-revision release artifacts | P1 |
| Security audit | Static/dependency gates | COMPLETE | Bandit/pip-audit workflow | Configuration complete; advisory freshness needs network | Exact-revision online receipt | P2 |
| Documentation | Truth, architecture, protocols, limitations | COMPLETE | `docs/`, `audit/`, this audit | Several older reports remain for history | Keep index authoritative | P3 |

## Marker and dead-code audit

The maintained source search found no algorithmic TODO, FIXME, placeholder, mock, hardcoded-result, or pseudocode path. `pass` in maintained code is limited to exception class bodies. Test fixtures mentioning “fake” exercise failure handling. Known broken and fake implementations are confined to `legacy/` and explicitly excluded from packaging and supported claims.

## State totals

Across the 45 major components above: 35 `COMPLETE`, 4 `FUNCTIONAL BUT WEAK`, 2 `PARTIAL`, 2 `MISSING`, 1 `BROKEN`, and 1 `DEAD`. These are audit classifications, not performance percentages.
