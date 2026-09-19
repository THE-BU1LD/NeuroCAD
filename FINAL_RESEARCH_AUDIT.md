# Final Research Audit

**Paper:** *NeuroCAD: An Executable, Fail-Closed Evaluation of a Controlled Text-to-CAD Compiler*  
**Repository:** NeuroCAD  
**Evidence-producing commit:** `508ec404dd520ae16f2b4d3cf211d5b1fa46b800` (clean at run start)  
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

The retained `NC-REPRO-508EC40` run contains raw per-task records, aggregate metrics, generated programs, mesh artifacts, figures, and SHA-256 entries for 1,212 artifacts. Its manifest records a clean Git state, the exact commit above, maintained-source SHA-256 `cbfef99766772b8bb6c345aaecfc6305ed1993ebcc05ba4d6a6541189ad7f929`, Python 3.12.14, OpenSCAD 2021.01, and zero resumed artifacts. It reports:

- 240/240 exact semantic matches for NeuroCAD on the synthetic compiler stress suite.
- 1,000/1,000 generated typed programs passing validation, exact round trip, and deterministic export.
- 240/240 unique generated malformed fixtures rejected across eight categories.
- 200/200 injected parameter drifts detected with declared constraints versus 0/200 after constraint removal.
- 200/200 automated named-parameter edits surviving validation and export.
- 240/240 OpenSCAD mesh executions passing the retained topology and extent checks.
- Constructed hierarchy depth 128 accepted and depth 129 explicitly rejected.

These artifacts resolve the previous source-provenance and artifact-reuse failure for the controlled contract. They remain internal synthetic evidence and do not provide independent external validity.

Primary evidence paths:

- [`paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md`](paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md)
- [`research/runs/NC-REPRO-508EC40/manifest.json`](research/runs/NC-REPRO-508EC40/manifest.json)
- [`research/runs/NC-REPRO-508EC40/metrics/results.json`](research/runs/NC-REPRO-508EC40/metrics/results.json)
- [`EVIDENCE_LEDGER.md`](EVIDENCE_LEDGER.md)
- [`audits/CLAIM_LEDGER.md`](audits/CLAIM_LEDGER.md)

## Strongest Baseline

The strongest executed baseline is train-only nearest-neighbor retrieval. It recorded 144/240 exact matches overall: 144/144 on training prompts and 0/48 on both validation and test prompts. The 96 discordant pairs all favored NeuroCAD; the retained exact two-sided McNemar value is `2.52e-29`.

This is a useful memorization control but not a strong contemporary or grammar-independent text-to-CAD comparator. A reviewed structured parser, constrained LLM-to-CadQuery/OpenSCAD system, or carefully task-mapped recent text-to-CAD implementation remains missing.

## Main Quantitative Result

On the frozen 240-task synthetic controlled suite, the source-bound run reports:

| System | Exact semantic matches | Rate | Absolute gap to NeuroCAD |
|---|---:|---:|---:|
| NeuroCAD | 240/240 | 100.0% | — |
| Nearest-neighbor retrieval | 144/240 | 60.0% | +40.0 percentage points |
| Unit-normalized dimensions only | 130/240 | 54.2% | +45.8 percentage points |
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

The most important remaining scientific failure is the omitted strong compatible baseline. The executed fixed, extraction, normalized-dimension, and retrieval controls do not establish competitiveness against a grammar-independent structured parser or contemporary text-to-CAD/code-generation system.

The repository also correctly preserves a negative result: the historical claim that the typed parser improved a learned model was falsified because the historical pipeline made no valid model calls. That claim must remain excluded.

## Primary Limitation

External validity is absent. The central dataset is project-authored, synthetic, generated from templates that match the supported grammar, and evaluated by exact signatures under the same declared contract. This is appropriate for compiler conformance but insufficient for claims about natural language, real CAD workloads, user value, or comparison with contemporary systems.

## Mathematical Risk

**Assessment: moderate-low for the narrow claim; high if generalized.**

The partial compiler, typed IR, constraints, semantic signatures, and mesh predicates are operationally clear and consistent with the implementation. No central invalid derivation was found, and no learned optimization claim requires training mathematics. However:

- the paper offers specification-level formalism rather than a new theorem;
- the evaluated prompt set is deterministic and generated, so binomial intervals do not establish population-level natural-language performance;
- the malformed fixtures are unique variants across only eight designed categories, so they remain regression evidence rather than a population sample;
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

**Assessment: moderate locally; high externally.**

The source-bound, non-resuming workflow completed against clean commit `508ec404dd520ae16f2b4d3cf211d5b1fa46b800`. It passed 559 tests and all static/security/package gates, regenerated 1,212 hashed artifacts, produced 240/240 fresh kernel results with zero reuse, built a wheel and sdist, installed the wheel into another clean environment, passed `neurocad doctor`, and generated a smoke design.

The remaining reproducibility risk is external: the exact commit and artifacts are local, with no public immutable tag, hosted CI URL, anonymous third-party clean-install receipt, or independent replication. The final documentation commit necessarily postdates the evidence-producing source commit but does not alter the measured implementation.

## Reviewer Attack Surface

1. **“This is a grammar conformance test, not natural-language CAD.”** Correct. The paper must stay explicitly within the bounded-language claim.
2. **“The benchmark was generated to match the parser.”** Correct. An independent frozen benchmark is required for external validity.
3. **“The baselines are too weak.”** Correct. Retrieval and extraction are diagnostic controls, not contemporary strong comparators.
4. **“The main run is not independently reproduced.”** Correct. Local exact-source reproduction now passes, but no outside lab or public CI has reproduced it.
5. **“The ablation does not isolate the parser mechanism.”** Correct. Componentwise frontend ablations are missing.
6. **“Perfect scores suggest circularity or insufficient difficulty.”** The perfect scores are plausible for a deterministic contract suite, but they cannot support broader empirical claims.
7. **“Wilson intervals imply sampling that did not occur.”** The paper now qualifies this, but all generated-suite intervals should remain explicitly descriptive.
8. **“Mesh validity is not CAD correctness or manufacturability.”** Correct. No BREP, exact topology equivalence, fabrication, fit, or safety claim is supported.
9. **“Where is the final manuscript artifact?”** There is a Markdown manuscript but no controlled final PDF, PDF visual audit, or venue-formatted submission artifact.
10. **“Were the citations independently verified?”** Yes for the manuscript's 15 references: `literature/CITATION_AUDIT_20260913.md` records primary-source metadata and claim-level dispositions. This does not substitute for executing a cited system as a compatible baseline.
11. **“Can another lab run it?”** Not yet shown; release and external replication receipts are absent.
12. **“Is the contribution novel?”** The repository's own novelty audit says no algorithmic novelty. Positioning must remain a systems/reference-implementation case study.

## Unresolved Issues

### Critical failures

1. **Key baseline omitted.** Execute at least one strong, compatible, grammar-independent baseline under identical frozen prompts, outputs, scoring, and kernel checks, or narrow the venue and contribution so that such comparison is genuinely unnecessary.

### Blocking scientific issues

1. Create, license, freeze, hash, and blindly evaluate an outside-authored in-scope/out-of-scope prompt benchmark; audit duplicate and development leakage before outcome access.
2. Execute unit-only, feature-only, and preferably lexical-alias-only frontend ablations using the declared matrix.
3. Add a preregistered systematic robustness matrix covering paraphrase, whitespace/punctuation, unit variants, missing fields, unsupported clauses, numeric boundaries, and increasing perturbation severity.
4. Publish or archive an immutable release candidate and capture independent execution receipts.
5. Produce the venue-formatted final PDF and complete visual, reference, pagination, and artifact-link audits.

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
| Primary experiments | Partial | Controlled experiments reproduced from clean source; required independent evaluation absent |
| Required baselines | Fail | No strong compatible comparator |
| Required ablations | Fail | Componentwise frontend ablations missing |
| Robustness/OOD | Fail | Internal regression coverage only; no independent/OOD evaluation |
| Statistical analysis | Partial pass | Exact paired tests are suitable for the frozen set; population inference is unsupported |
| Failure analysis | Pass for retained suite | Baseline failures and negative historical mechanism result are disclosed |
| Reproducibility audit | Local pass / external partial | Exact-source non-resumed run passed; public and independent receipts absent |
| Citation audit | Pass | All 15 references checked against primary CVF/arXiv records; claim-level dispositions retained |
| Visual audit | Not passed | No final PDF or completed visual audit |
| Final PDF audit | Not passed | No final PDF identified |
| External replication | Not passed | No independent execution receipt |

**Critical Failures:** 1  
**Blocking Scientific Issues:** 5  
**Primary Experiments:** Partial  
**Required Ablations:** Incomplete  
**Required Baselines:** Incomplete  
**Math Audit:** Passed only for the bounded conformance claim  
**Reproducibility Audit:** Passed locally; external replication pending  
**Citation Audit:** Passed  
**Visual Audit:** Not passed  
**Final PDF Audit:** Not passed

## Score

**78/100 — Major scientific revision**

| Category | Score | Maximum | Rationale |
|---|---:|---:|---|
| Scientific problem and claim discipline | 9 | 10 | Clear, falsifiable, and unusually honest boundaries |
| Formulation and mathematics | 8 | 10 | Coherent operational specification; limited theoretical content |
| Method and implementation alignment | 14 | 15 | Strong bounded compiler, validation, and evidence plumbing |
| Experimental design and execution | 10 | 15 | Broad internal controlled suite; synthetic and self-authored |
| Baselines | 5 | 10 | Useful simple controls; no strong compatible comparator |
| Ablations and robustness | 7 | 10 | Strong constraint ablation; coupled frontend and no OOD |
| Statistics and failure analysis | 8 | 10 | Appropriate paired tests and honest negative evidence; limited population basis |
| Reproducibility and provenance | 13 | 15 | Clean source-bound non-resumed run passed; public independent receipt absent |
| Manuscript, citations, and visuals | 4 | 5 | Conservative manuscript and verified citations; venue-formatted final PDF absent |
| **Total** | **78** | **100** |

Critical failures override the numerical score independently.

## Readiness Level

**Not P6. EVIDENCE_PARTIAL / major scientific revision.**

The project has passed question formulation, implementation alignment, narrow mathematical coherence, extensive internal controlled testing, local exact-source reproduction, and citation audit. It has not passed the standard's strong-baseline, independent-evaluation, external-replication, visual, or final-PDF gates. It cannot be called submission-ready.

## Recommendation

**Do not submit the current paper as a general text-to-CAD research result.** Preserve its conservative scope and use `NC-REPRO-508EC40` as the current controlled evidence.

For the shortest defensible path to a serious submission:

1. Before inspecting outcomes, freeze an independent outside-authored benchmark and the analysis plan.
2. Run one strong compatible baseline plus the missing componentwise frontend ablations under the identical evaluator.
3. Report robustness curves and all failures, not only aggregate success.
4. Obtain at least one anonymous independent replication receipt.
5. Build and visually audit a venue-specific final PDF only after the evidence gates pass.

If independent data and a strong comparator cannot be obtained, reposition the work as an auditable reference compiler, software artifact, or reproducibility/systems report rather than claiming a competitive text-to-CAD research advance.
