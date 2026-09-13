# Final Research Audit

**Paper:** *NeuroCAD: An Executable, Fail-Closed Evaluation of a Controlled Text-to-CAD Compiler*  
**Repository:** NeuroCAD  
**Commit:** `2e357d6400302cbce8c8dae72626a9422082cd8d` (audit checkout; worktree dirty)  
**Target Venue:** Not declared for the controlled-compiler paper  
**Date:** 2026-09-13  
**Auditor decision:** `EVIDENCE_PARTIAL`; not submission-ready

This audit applies the user-supplied research-paper standard literally. It evaluates retained evidence, not intended work, code volume, or manuscript polish. The repository's own conservative claim boundaries are accepted where they match the artifacts, but self-classification is not treated as independent verification.

## Scientific Question

Can a deterministic, typed, fail-closed compiler translate a deliberately bounded language of fully dimensioned CAD requests into semantically exact, editable CSG programs and kernel-checked OpenSCAD solids more reliably than simple fixed-output, raw-number, unit-normalized-dimension, and train-only retrieval controls?

The question is operational for the declared grammar. It is not a test of general natural-language understanding, learned text-to-CAD generation, CAD design-intent inference, BREP/STEP reconstruction, manufacturability, or state-of-the-art performance.

## Main Hypothesis

For prompts generated under the frozen controlled contract, the full NeuroCAD compiler will achieve exact declared semantics and valid outputs, outperform the implemented simple controls under the same evaluator, reject enumerated invalid inputs, preserve typed-program invariants, and expose constraint violations and edits without silent fallback.

The scientifically stronger hypothesis—that these advantages generalize to independently authored natural-language CAD requests or contemporary text-to-CAD systems—has not been tested.

## Main Contribution

The strongest defensible contribution is a well-tested systems case study: a bounded English-to-typed-CSG compiler with strict parsing, canonical IR, deterministic OpenSCAD export, fail-closed validation, kernel execution checks, artifact hashing, and an unusually explicit claim/evidence ledger.

There is no supported algorithmic-novelty claim. The contribution is engineering integration and controlled evaluation, not a new learned method or theorem.

## Strongest Evidence

The retained `NC-RUN-2026-09-03-FULL` development run contains raw per-task records, aggregate metrics, generated programs, mesh artifacts, figures, and SHA-256 entries for 1,210 artifacts. It reports:

- 240/240 exact semantic matches for NeuroCAD on the synthetic compiler stress suite.
- 1,000/1,000 generated typed programs passing validation, exact round trip, and deterministic export.
- 240/240 recorded malformed fixtures rejected, with the important qualification that these are eight templates repeated 30 times.
- 200/200 injected parameter drifts detected with declared constraints versus 0/200 after constraint removal.
- 200/200 automated named-parameter edits surviving validation and export.
- 240/240 OpenSCAD mesh executions passing the retained topology and extent checks.
- Constructed hierarchy depth 128 accepted and depth 129 explicitly rejected.

These artifacts are meaningful internal development evidence. They are not submission-grade primary evidence because the run manifest lacks the producing Git revision or source-tree digest, and 181/240 kernel samples were resumed from pre-existing artifacts.

Primary evidence paths:

- [`paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md`](paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md)
- [`research/runs/NC-RUN-2026-09-03-FULL/manifest.json`](research/runs/NC-RUN-2026-09-03-FULL/manifest.json)
- [`research/runs/NC-RUN-2026-09-03-FULL/metrics/results.json`](research/runs/NC-RUN-2026-09-03-FULL/metrics/results.json)
- [`EVIDENCE_LEDGER.md`](EVIDENCE_LEDGER.md)
- [`audits/CLAIM_LEDGER.md`](audits/CLAIM_LEDGER.md)

## Strongest Baseline

The strongest executed baseline is train-only nearest-neighbor retrieval. It recorded 144/240 exact matches overall: 144/144 on training prompts and 0/48 on both validation and test prompts. The 96 discordant pairs all favored NeuroCAD; the retained exact two-sided McNemar value is `2.52e-29`.

This is a useful memorization control but not a strong contemporary or grammar-independent text-to-CAD comparator. A reviewed structured parser, constrained LLM-to-CadQuery/OpenSCAD system, or carefully task-mapped recent text-to-CAD implementation remains missing.

## Main Quantitative Result

On the frozen 240-task synthetic controlled suite, the retained historical run reports:

| System | Exact semantic matches | Rate | Absolute gap to NeuroCAD |
|---|---:|---:|---:|
| NeuroCAD | 240/240 | 100.0% | — |
| Nearest-neighbor retrieval | 144/240 | 60.0% | +40.0 percentage points |
| Raw numbers, no unit normalization | 110/240 | 45.8% | +54.2 percentage points |
| Fixed box | 0/240 | 0.0% | +100.0 percentage points |

This result demonstrates exactness only on generated prompts aligned with the compiler's declared grammar. It cannot be interpreted as natural-language generalization or superiority over published text-to-CAD methods.

## Most Important Ablation

`NC-EXP-004` is the cleanest mechanism test: declared constraints detected 200/200 injected parameter drifts, while the same corruptions were detected 0/200 with constraints removed. It supports the narrow claim that executed declared constraints detect the chosen corruption class.

The frontend comparison from 240/240 to 110/240 is not a clean component ablation because it jointly removes unit normalization and structured feature parsing. Unit-only, feature-only, and lexical-alias-only variants remain unexecuted. No causal claim may attribute the entire frontend gap to unit normalization.

## Strongest Robustness Result

The strongest retained robustness result is fail-closed boundary behavior across enumerated invalid-input categories and constructed graph-depth limits. The repository also contains a 24-case audit-authored prompt challenge and extensive parser, schema, resource-bound, and fuzz-style engineering tests.

This is robustness against specified regression classes, not distributional robustness. There is no blinded outside-authored prompt set, systematic paraphrase/noise curve, cross-domain test, or OOD degradation measurement.

## Most Important Failure

The most important scientific failure is provenance: the only retained full headline run cannot be bound to the exact source that produced it. Its manifest has no Git commit or source-tree digest, and its kernel stage resumed 181 of 240 samples. Under the supplied standard, “main result cannot be reproduced” is an automatic failure, regardless of whether the current runner has since been hardened.

The repository also correctly preserves a negative result: the historical claim that the typed parser improved a learned model was falsified because the historical pipeline made no valid model calls. That claim must remain excluded.

## Primary Limitation

External validity is absent. The central dataset is project-authored, synthetic, generated from templates that match the supported grammar, and evaluated by exact signatures under the same declared contract. This is appropriate for compiler conformance but insufficient for claims about natural language, real CAD workloads, user value, or comparison with contemporary systems.

## Mathematical Risk

**Assessment: moderate-low for the narrow claim; high if generalized.**

The partial compiler, typed IR, constraints, semantic signatures, and mesh predicates are operationally clear and consistent with the implementation. No central invalid derivation was found, and no learned optimization claim requires training mathematics. However:

- the paper offers specification-level formalism rather than a new theorem;
- the evaluated prompt set is deterministic and generated, so binomial intervals do not establish population-level natural-language performance;
- the malformed fixture records are only eight effective template classes, and the paper correctly withdraws the earlier 240-sample interval;
- mesh predicates are necessary checks, not proofs of BREP equivalence, self-intersection freedom, fit, manufacturability, or safety;
- no formal complexity derivation connects parser/exporter bounds to measured end-to-end kernel behavior.

The math audit passes only for the bounded compiler-conformance interpretation.

## Experimental Risk

**Assessment: high.**

- The data generator and compiler grammar are closely coupled.
- The central suite is not independently authored.
- The strongest compatible baseline is missing.
- Frontend ablations are coupled and cannot isolate the claimed components.
- No OOD, independent-domain, or real-design corpus is evaluated.
- No human editability study has been executed.
- No physical fabrication, fit, calibration, or repeated-printer study has been executed.
- Timing is local diagnostic evidence rather than a controlled efficiency study.
- Kernel execution is sensitive to external OpenSCAD version, platform, and timeout/load conditions.
- The recent conversational-language engineering expansion has not been evaluated on a frozen independent benchmark and therefore does not strengthen the paper's scientific generalization claim.

## Reproducibility Risk

**Assessment: critical for the headline result.**

The current repository contains a substantially improved source-bound, non-resuming research runner, pinned dependency metadata, deterministic configs, hashes, and reproduction scripts. Those are reproducibility infrastructure, not a completed reproduction.

The audit checkout is dirty, so commit `2e357d6400302cbce8c8dae72626a9422082cd8d` does not identify the code under review. There is no retained clean full run for the current source, no public immutable tag, no hosted exact-revision CI receipt, no anonymous clean-install receipt, and no independent replication. The historical full run cannot fill this gap.

## Reviewer Attack Surface

1. **“This is a grammar conformance test, not natural-language CAD.”** Correct. The paper must stay explicitly within the bounded-language claim.
2. **“The benchmark was generated to match the parser.”** Correct. An independent frozen benchmark is required for external validity.
3. **“The baselines are too weak.”** Correct. Retrieval and extraction are diagnostic controls, not contemporary strong comparators.
4. **“The main run is not reproducible.”** Correct. The manifest is source-unbound and partly resumed.
5. **“The ablation does not isolate the parser mechanism.”** Correct. Componentwise frontend ablations are missing.
6. **“Perfect scores suggest circularity or insufficient difficulty.”** The perfect scores are plausible for a deterministic contract suite, but they cannot support broader empirical claims.
7. **“Wilson intervals imply sampling that did not occur.”** The paper now qualifies this, but all generated-suite intervals should remain explicitly descriptive.
8. **“Mesh validity is not CAD correctness or manufacturability.”** Correct. No BREP, exact topology equivalence, fabrication, fit, or safety claim is supported.
9. **“Where is the final manuscript artifact?”** There is a Markdown manuscript but no controlled final PDF, PDF visual audit, or venue-formatted submission artifact.
10. **“Were the citations independently verified?”** A related-work list exists, but no completed citation audit with authoritative metadata and claim-level support is retained.
11. **“Can another lab run it?”** Not yet shown; release and external replication receipts are absent.
12. **“Is the contribution novel?”** The repository's own novelty audit says no algorithmic novelty. Positioning must remain a systems/reference-implementation case study.

## Unresolved Issues

### Critical failures

1. **Main result not reproducibly bound to source.** Produce a clean, non-resumed, exact-revision full run and retain its source snapshot/digest, runtime receipt, raw outputs, and artifact manifest.
2. **Key baseline omitted.** Execute at least one strong, compatible, grammar-independent baseline under identical frozen prompts, outputs, scoring, and kernel checks, or narrow the venue and contribution so that such comparison is genuinely unnecessary.

### Blocking scientific issues

1. Create, license, freeze, hash, and blindly evaluate an outside-authored in-scope/out-of-scope prompt benchmark; audit duplicate and development leakage before outcome access.
2. Execute unit-only, feature-only, and preferably lexical-alias-only frontend ablations using the declared matrix.
3. Add a preregistered systematic robustness matrix covering paraphrase, whitespace/punctuation, unit variants, missing fields, unsupported clauses, numeric boundaries, and increasing perturbation severity.
4. Retain a clean exact-revision full research run generated from scratch with no resumed kernel artifacts.
5. Publish or archive an immutable release candidate and capture clean install plus independent execution receipts.
6. Complete a citation audit against authoritative sources and verify that every related-work characterization is supported.
7. Produce the venue-formatted final PDF and complete visual, reference, pagination, and artifact-link audits.

### Scope-dependent issues

- Execute the human editability study before making user-efficiency or usability claims.
- Execute the physical fabrication/calibration protocol before making fit or manufacturability claims.
- Add STEP/BREP, sketch, or assembly semantics only if the paper expands beyond OpenSCAD CSG.
- Run authorized VeriCodeGen Stage 3 only for a separately frozen learned-model research question; it is not required for the narrow deterministic compiler claim.

### Gate matrix

| Gate | Status | Basis |
|---|---|---|
| Scientific question and boundaries | Pass | Precise bounded compiler question; prohibited broad claims are explicit |
| Operational formulation | Pass | Typed IR, partial compiler, validators, metrics, and failure conditions exist |
| Method/implementation alignment | Pass | Maintained compiler path and tests correspond to the narrow paper |
| Math audit | Pass with scope qualification | Coherent specification; no broad statistical or geometry inference allowed |
| Primary experiments | Partial | Controlled experiments executed historically; required independent evaluation absent |
| Required baselines | Fail | No strong compatible comparator |
| Required ablations | Fail | Componentwise frontend ablations missing |
| Robustness/OOD | Fail | Internal regression coverage only; no independent/OOD evaluation |
| Statistical analysis | Partial pass | Exact paired tests are suitable for the frozen set; population inference is unsupported |
| Failure analysis | Pass for retained suite | Baseline failures and negative historical mechanism result are disclosed |
| Reproducibility audit | Fail | Headline run source-unbound; current clean exact-revision run absent |
| Citation audit | Not passed | References exist; authoritative claim-level verification not retained |
| Visual audit | Not passed | No final PDF or completed visual audit |
| Final PDF audit | Not passed | No final PDF identified |
| External replication | Not passed | No independent execution receipt |

**Critical Failures:** 2  
**Blocking Scientific Issues:** 7  
**Primary Experiments:** Partial  
**Required Ablations:** Incomplete  
**Required Baselines:** Incomplete  
**Math Audit:** Passed only for the bounded conformance claim  
**Reproducibility Audit:** Failed  
**Citation Audit:** Not passed  
**Visual Audit:** Not passed  
**Final PDF Audit:** Not passed

## Score

**69/100 — Incomplete research**

| Category | Score | Maximum | Rationale |
|---|---:|---:|---|
| Scientific problem and claim discipline | 9 | 10 | Clear, falsifiable, and unusually honest boundaries |
| Formulation and mathematics | 8 | 10 | Coherent operational specification; limited theoretical content |
| Method and implementation alignment | 14 | 15 | Strong bounded compiler, validation, and evidence plumbing |
| Experimental design and execution | 10 | 15 | Broad internal controlled suite; synthetic and self-authored |
| Baselines | 5 | 10 | Useful simple controls; no strong compatible comparator |
| Ablations and robustness | 7 | 10 | Strong constraint ablation; coupled frontend and no OOD |
| Statistics and failure analysis | 8 | 10 | Appropriate paired tests and honest negative evidence; limited population basis |
| Reproducibility and provenance | 5 | 15 | Good new infrastructure; central retained run fails exact-source reproduction |
| Manuscript, citations, and visuals | 3 | 5 | Conservative manuscript, but citation and final-PDF audits are absent |
| **Total** | **69** | **100** |

Critical failures override the numerical score independently.

## Readiness Level

**Not P6. EVIDENCE_PARTIAL / incomplete research.**

The project has passed question formulation, implementation alignment, narrow mathematical coherence, and extensive internal controlled testing. It has not passed the standard's baseline, independent-evaluation, reproducibility, citation, visual, or final-PDF gates. It cannot be called submission-ready.

## Recommendation

**Do not submit the current paper as a general text-to-CAD research result.** Preserve its present conservative scope and treat the retained full run as historical development evidence.

For the shortest defensible path to a serious submission:

1. Freeze a clean exact revision and run the complete suite from scratch with kernel resume disabled; retain all source, runtime, data, config, output, and artifact hashes.
2. Before inspecting outcomes, freeze an independent outside-authored benchmark and the analysis plan.
3. Run one strong compatible baseline plus the missing componentwise frontend ablations under the identical evaluator.
4. Report robustness curves and all failures, not only aggregate success.
5. Obtain at least one anonymous clean-install or independent replication receipt.
6. Verify every citation and related-work comparison against primary sources.
7. Build and visually audit a venue-specific final PDF only after the evidence gates pass.

If independent data and a strong comparator cannot be obtained, reposition the work as an auditable reference compiler, software artifact, or reproducibility/systems report rather than claiming a competitive text-to-CAD research advance.
