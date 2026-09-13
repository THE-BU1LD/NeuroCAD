# Research-grade report

**Audit date:** 2026-09-12  
**Verdict:** **strong engineering artifact; partial research evidence**

## 1. Research idea assessment

NeuroCAD asks whether a deterministic typed compiler can map a declared dimensioned-English subset to exact editable CSG programs and valid solids more reliably than simple controls. The question is falsifiable and the implementation is real. The strongest aspects are fail-closed parsing, typed/canonical IR, deterministic artifacts, real OpenSCAD execution, raw per-case evidence, and unusually honest preservation of negative history.

The weakest aspects are decisive for publication: evaluation data are authored from the same grammar, the fast product benchmark has only 46 unique prompts in 48 rows, baselines are simple, the historical full run cannot authenticate its source and reused 181 kernel artifacts, and no independent, human, physical, or external replication exists.

Novelty verdict by category:

| Category | Verdict | Reason |
|---|---|---|
| Conceptual | INCREMENTAL | Controlled language + typed intent + executable verification is useful but established in principle |
| Algorithmic | ALREADY STANDARD | Parsing, schemas, CSG, unit normalization, and constraint checking are standard |
| Architecture | PLAUSIBLE systems integration | Coherent fail-closed evidence path, but not a new CAD representation class |
| Training method | MISSING / not applicable | No learned model or training |
| Dataset | UNSUPPORTED as novelty | Project-authored synthetic regression data, not a community benchmark |
| Evaluation | PLAUSIBLE | Strong traceability and failure retention; external validity absent |
| Systems | STRONGEST | Reproducibility gates, typed artifacts, verification and honest boundaries |
| Application | INCREMENTAL | Useful narrow enclosure workflow without physical validation |

Recent work further narrows any novelty claim: CAD-Llama generates parametric CAD sequences with LLMs; Pointer-CAD joins BREP entity selection to command generation; September 2026 CIT-CAD explicitly uses inferred constraint-intent trees for generation, verification, and repair. NeuroCAD should therefore claim a bounded reproducible reference compiler/evidence harness, not novelty in intent-aware text-to-CAD.

Primary literature checked for this audit: [CAD-Llama (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/html/Li_CAD-Llama_Leveraging_Large_Language_Models_for_Computer-Aided_Design_Parametric_3D_CVPR_2025_paper.html), [Pointer-CAD (CVPR 2026)](https://openaccess.thecvf.com/content/CVPR2026/html/Qi_Pointer-CAD_Unifying_B-Rep_and_Command_Sequences_via_Pointer-based_Edges__CVPR_2026_paper.html), and [CIT-CAD (arXiv, 2026-09-07)](https://arxiv.org/abs/2609.07434).

## 2. Initial repository state

The checkout was clean and already heavily audited. Maintained code had no unresolved algorithmic placeholder markers, 55 source files passed initial mypy, Ruff passed, and dependency consistency passed. However, the six requested canonical documents were absent, benchmark evaluation regenerated instead of loading frozen data, experiment JSON could not be loaded by the CLI, and dataset lifecycle commands were missing.

The complete component classification is in `docs/PROJECT_STATE_AUDIT.md`; no subjective completion percentage is claimed.

## 3. Major fixes completed

- Added strict bounded frozen-benchmark loading and cross-split leakage rejection.
- Changed benchmark execution to preserve existing dataset bytes; generation now requires `--generate`.
- Added deterministic data prepare/validate/inspect commands and checksum manifests.
- Exposed row count versus unique-prompt count and the product benchmark's two redundant training records.
- Added strict versioned research-config loading with explicit CLI override semantics.
- Added a machine-readable ablation manifest and reviewed smoke configuration.
- Added top-level setup/test/lint/type/data/smoke/benchmark/reproduce targets.
- Added all six requested audit/research deliverables.

## 4. Repository organization

The maintained product remains under `core/`, research protocols/data/results under `research/`, configs under `configs/`, tests under `tests/`, and reviewer documentation under `docs/`/`audit/`. The 225 MB `legacy/` tree remains quarantined and excluded from packaging because it is negative forensic evidence. Large historical artifacts were not moved or rewritten.

## 5. Dataset state

Dataset provenance, schemas, counts, licenses, retrieval, and leakage risks are in `docs/DATASETS.md`. The 48-task product benchmark validates with SHA-256 `0822e45a56e4cc2d405da50561899f8310e9bffb4a4a833e98affe27672e4546`, 46 unique prompts, and no exact cross-split duplicate. This redundancy is disclosed, not repaired post hoc.

## 6. Benchmark and baseline state

The product benchmark can now evaluate frozen JSONL without mutation and saves per-example and aggregate machine-readable outputs. Fixed, raw-number, normalized-dimension, and train-only retrieval baselines are implemented on identical data/metrics. No contemporary strong compatible baseline exists, so comparative claims remain preliminary.

## 7. Experiment and ablation state

NC-EXP-001 through NC-EXP-007 are implemented. Constraint presence/removal is a clean paired ablation. Frontend controls are useful but partly coupled; unit-only and feature-only causal ablations are intentionally not retrofitted after outcomes. NC-EXP-008 through NC-EXP-010 specify independent prompts, human editing, and physical validation and remain unexecuted.

## 8. Reproducibility

New research runs record config, source snapshot, Git SHA/dirty state, dependency-lock digest, package versions, Python/platform, OpenSCAD executable/version/digest, raw and deterministic metrics, runtime observations, and artifact hashes. New output directories are collision-refusing and a source mutation during execution prevents final manifest publication.

The historical FULL run predates these controls. It remains development evidence only.

## 9. Tests, performance, and systems

The audit revision collects 517 tests spanning unit, integration, research, regression, smoke, CLI, browser contract, kernel, packaging, and scientific provenance behavior. Timing fields are treated as diagnostics and excluded from deterministic result hashes. No before/after performance optimization was justified by evidence, so no unsupported speed claim is made.

## 10. Scientific evidence and negative results

Historical outcomes are traceable in `docs/CLAIM_EVIDENCE_MATRIX.md` but are not reclassified as current confirmation. Negative evidence retained:

- historical typed-parser causal claim was falsified because Stage 1 made no model calls;
- historical STEP export was fake marker text and is disabled;
- historical FULL source provenance is absent and most kernel artifacts were reused;
- general CAD, BREP, learned reasoning, manufacturability, physical fit, usability, and external reproducibility remain unsupported.

## 11. Remaining blockers

No feasible local code patch can manufacture the missing independent evidence. The remaining P0/P1 gates require: a clean published exact revision for the full fresh run; an outside-authored frozen prompt set; a strong compatible baseline; physical hardware/measurements; human-study governance and participants; authorized model/provider/budget inputs; and hosted CI/tag/anonymous-install receipts.

## 12. Verification commands

Commands executed during this audit are recorded honestly in the final handoff and include test collection, focused/full tests, Ruff, mypy, compile-all, dependency consistency, dataset validation, benchmark smoke, research smoke, artifact verification, and Git status. Sandbox-only socket failures are environment failures and are separated from native reruns.

## 13. Recommended next experiments

1. Freeze NC-EXP-008 using outside authors and a compatible strong baseline before opening any outcomes.
2. Run the clean full 240-kernel suite from the published exact revision and retain its source-bound manifest.
3. Only then run isolated unit/feature frontend ablations on the same frozen task set.
4. Execute the existing physical coupon protocol before making fit or manufacturing claims.
5. Treat any learned/VeriCodeGen run as a separate authorized study with frozen model and budget identity.
