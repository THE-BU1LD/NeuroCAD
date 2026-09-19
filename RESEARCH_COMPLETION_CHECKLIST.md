# Research completion checklist

Audit date: 2026-09-13. `DONE` means completed in the current repository scope; it does not convert development evidence into external confirmation.

## [DONE] [P0] Honest supported-system boundary

Current: Maintained compiler, historical experiments, VeriCodeGen, and legacy code coexist.

Problem: A sophisticated filename could be mistaken for working or supported research.

Required: Separate maintained, partial, broken, missing, and historical surfaces.

Implementation: `docs/PROJECT_STATE_AUDIT.md` classifies every major subsystem; legacy fake STEP and Stage 1 remain negative evidence.

Verification: Marker search, package manifest review, archive/integrity tests.

## [DONE] [P0] Frozen benchmark evaluation must not rewrite the dataset

Current: The former `benchmark` command always regenerated the dataset and then collided with tracked default paths.

Problem: The documented evaluation path was unusable and conceptually violated frozen-data evaluation.

Required: Load, validate, and evaluate existing bytes; make generation explicit.

Implementation: Added strict `load_benchmark`; `neurocad benchmark` now reads by default and requires `--generate` to create data.

Verification: `tests/test_dataset_pipeline.py::test_benchmark_cli_evaluates_existing_dataset_without_mutating_it`.

## [DONE] [P1] Dataset lifecycle and manifest

Current: Deterministic generators existed only as internal functions.

Problem: Researchers lacked a bounded prepare/validate/inspect interface and explicit checksum manifest.

Required: Collision-refusing generation, strict loading, checksum and summary.

Implementation: `core/data.py`, `neurocad data`, and `python -m core.data` support prepare/validate/inspect.

Verification: Dataset pipeline tests and validation of the tracked product benchmark.

## [DONE] [P1] Disclose product-benchmark duplicate records

Current: The 48-row frozen product benchmark contains 46 unique prompts; one training sphere prompt appears three times.

Problem: Row count overstates prompt diversity.

Required: Preserve frozen bytes, reject cross-split duplicates, report within-split redundancy.

Implementation: Dataset summary emits `unique_prompt_count`, `duplicate_prompt_records`, and a warning.

Verification: tracked dataset validation hash and duplicate tests.

## [DONE] [P1] Executable reviewed research configuration

Current: A JSON config existed, but the CLI could not load it.

Problem: Reproduction depended on copying values into command-line flags.

Required: Strict config loading with version and unknown-field rejection plus explicit overrides.

Implementation: `load_research_config` and `neurocad research --config`; added smoke config.

Verification: research config unit tests and research smoke command.

## [DONE] [P1] Ablation declaration

Current: Constraint and parser baselines existed but no compact machine-readable matrix identified causal limitations.

Problem: The raw-number baseline could be overread as an isolated unit ablation.

Required: Declare factors, variants, metrics, and confounding.

Implementation: `configs/ablation_manifest.json` and `docs/RESEARCH_PROGRAM.md`.

Verification: JSON parse/static checks and smoke research execution.

## [DONE] [P2] Top-level reproducibility commands

Current: Shell scripts existed but common setup/test/lint/type/data/smoke/benchmark/reproduce targets did not.

Problem: Entry points were scattered.

Required: Thin project-native commands that call the real paths.

Implementation: Added `Makefile` without duplicating research logic.

Verification: execute applicable targets or their exact underlying commands.

## [DONE] [P1] Requested canonical audits

Current: Many dated and overlapping reports existed, but the six requested filenames were absent.

Problem: A reviewer could not find one current state map, research plan, data audit, claim matrix, master checklist, and final report.

Required: Create those exact artifacts and cross-link evidence.

Implementation: Added the requested documents dated 2026-09-12.

Verification: documentation link and integrity checks.

## [DONE] [P1] Citation and related-work audit

Current: All 15 manuscript references resolve to primary CVF or arXiv records.

Problem: Abbreviated bibliography entries and unretained metadata checks left an avoidable reviewer gate open.

Required: Verify identity, venue/year where declared, input/output task, and support for each comparative characterization.

Implementation: `literature/CITATION_AUDIT_20260913.md` records the source-by-source audit; bibliography titles and venue labels were corrected.

Verification: each primary link resolves and the paper makes no numerical or compatibility claim from citation alone.

## [DONE] [P0] Fresh clean full controlled reproduction

Current: `NC-REPRO-508EC40` reproduces the controlled results from clean commit `508ec404dd520ae16f2b4d3cf211d5b1fa46b800`; `NC-REPRO-CB1D4A9` preserves the pre-fix 999/1,000 IR failure.

Problem: The previous historical run could not authenticate current source or serve as confirmatory evidence.

Required: Run `scripts/reproduce_research.sh` from one clean published CPython 3.12.14 revision with all 240 kernel artifacts fresh.

Implementation: The non-resuming source/lock/kernel-bound runner completed with 1,212 hashed artifacts, 1,000/1,000 IR programs, 240/240 fresh kernel records, and zero reuse.

Verification: the retained manifest reports clean Git, matching package version, `force_recompile=true`, 240 fresh kernel records, zero reuse, source/lock/OpenSCAD provenance, and valid artifact hashes. Public tag/CI and independent replication remain separate external gates.

## [MISSING] [P1] Independent in-scope prompt benchmark

Current: All evaluated prompts are generator- or audit-authored after seeing the implementation.

Problem: No external validity or blind generalization claim is possible.

Required: Outside-authored, licensed, deduplicated, frozen supported/unsupported prompt set with adjudicated signatures.

Implementation: Protocol specified as NC-EXP-008; do not generate outcomes from this audit.

Verification: pre-outcome hash, annotation agreement, leakage report, raw predictions, paired effect CI, and failure audit.

## [MISSING] [P1] Strong compatible baseline

Current: Fixed, raw, normalized-dimension, and retrieval controls are simple.

Problem: They do not exclude performance from a stronger grammar-independent parser or contemporary code-generation system.

Required: Freeze a compatible baseline with identical inputs, allowed output subset, preprocessing, kernel, and metrics.

Implementation: Baseline contract defined in `docs/RESEARCH_PROGRAM.md`; direct published-score comparison is prohibited.

Verification: raw outputs, version/model identity, budget, failures, and paired comparison on NC-EXP-008.

## [PARTIAL] [P1] Factorial frontend ablations

Current: Normalized-dimensions and raw-number comparators remove multiple parser capabilities.

Problem: Unit, lexical, and feature effects are not separately identified.

Required: Add unit-only, feature-only, and optional lexical-only switches while keeping all other logic fixed.

Implementation: Matrix specified; current results explicitly marked coupled.

Verification: frozen paired task records and per-family effects. Not implemented because this would change the maintained parser design and requires a predeclared follow-up experiment, not post-outcome patching.

## [MISSING] [P1] Human editability study

Current: Automated named edits pass; no users were studied.

Problem: Machine round trip does not establish usability.

Required: Ethics/recruitment-appropriate counterbalanced study with a credible editing baseline.

Implementation: `analysis/HUMAN_EVALUATION_PROTOCOL.md` and NC-EXP-009 define the work.

Verification: preregistration, anonymized raw data, analysis code, and uncertainty. Blocked by participants/ethics outside this execution.

## [MISSING] [P1] Physical fabrication and calibration evidence

Current: Preflight and calibration mathematics are tested synthetically.

Problem: Mesh validity does not prove fit, strength, tolerance, or printability.

Required: Execute coupon and enclosure prints with retained measurements and hardware/material provenance.

Implementation: `docs/PHYSICAL_VALIDATION_PROTOCOL.md` and NC-EXP-010.

Verification: signed measurement sheets, photos/artifact hashes, repeated prints, and disclosed failures. Blocked by hardware and physical execution.

## [BLOCKED] [P1] VeriCodeGen S3 outcomes

Current: Safe ledger, schema, verifier, prompt freeze, and preflight exist; no model outcomes exist.

Problem: Provider execution without authorization/model/budget freeze would be scientifically invalid.

Required: Candidate pool, deterministic pilot selection, exact model/provider identity, budget and authorization manifest.

Implementation: Pre-outcome gates remain fail-closed.

Verification: only the authorized protocol may produce and finalize raw outcome ledgers.

## [BLOCKED] [P1] External release and replication receipt

Current: CI/release workflows exist; local checks are not hosted receipts.

Problem: Public reproducibility cannot be inferred from a local checkout.

Required: Published exact SHA, passing CI URLs, immutable tag, artifact checksums, anonymous install, independent rerun.

Implementation: Workflows and provenance scripts are ready.

Verification: retain generated `RELEASE_PROVENANCE.json` and external URLs.

## [PARTIAL] [P2] Stronger mesh correctness

Current: Verifier checks finite values, volume, manifold/winding/connectivity and expected extents.

Problem: These predicates do not prove absence of all self-intersections or exact geometric equivalence.

Required: Add a justified intersection/equivalence method only if claims expand.

Implementation: Current docs explicitly bound the predicate.

Verification: adversarial fixtures against any future stronger checker.

## [MISSING] [P3] STEP/BREP, sketches, and learned generation

Current: None is supported; historical fake STEP is disabled.

Problem: Older project naming may imply broader CAD capability.

Required: Treat each as a separate research program with real kernel/data/baselines.

Implementation: Explicitly excluded from current definition of done.

Verification: no claim until end-to-end artifacts and tests exist.
