# NeuroCAD failure and improvement checklist

15 October 2026. This is the proposed execution checklist. Open boxes identify work still required; they are not implementation or performance claims. Earlier results and closed study budgets remain unchanged.

The immediate product problem is incomplete language coverage and incomplete evidence of intended geometry. The retained original diagnostic completes 11 of 20 valid requests exactly. A fair competitive loss has not been measured: no matched strong-comparator results exist. Product reliability, comparative performance, research novelty and physical usefulness therefore need separate completion evidence.

15 October follow-up: separate quantity candidate `b12812ac4b652aac01d179ab66f1bc963167ace4` reports 14/20 on the same observed development cases, with integration still open. The subsequent [directional quantity repair](../research/development/directional_quantities_20261015/REPORT.md) prevents ambiguous or contradictory increase/decrease proposals and passes 111 focused tests. These are local engineering results. C02/C04 remain open for their broader evidence requirements; no research checkpoint or independent-performance claim is advanced.

**Baseline and completed foundations**

- [x] Recount the 32 retained language rows: 11/20 exact valid intents, 12/12 safe rejection cases, 21/32 exact overall, zero unsafe acceptances and zero provider errors. Two rejection cases use a different status label from the expected one. These developer-authored cases cover only two project contexts and remain development data.
- [x] Preserve the merged input-validation, immutable scoring-context and matched-report comparison repairs. The retained PR112 receipt reports 1,789 maintained tests passing with 10 skips, plus native acceptance on three platforms. These results do not measure broad language generalization.
- [x] Preserve the original terminal MIXED study, the supported controlled Physics v2 result, and the original Physics v3 failure alongside its corrected successor receipts.
- [x] Reuse the existing output-geometry candidate rather than rebuild it. Candidate `941eed7` already implements aggregate solid-count/volume checks and adjacent input repairs, with 86 focused tests passing. Native/full/package verification remains open.

**Observed language failures**

| Retained request | Observed response | Required behavior for this supported case |
|---|---|---|
| make the walls three millimeters thick | Clarification | Set wall thickness to 3 mm |
| add one millimeter to the wall thickness | Clarification | Add 1 mm to the current wall value |
| the wall should be 3 mm, floor 2 mm, leave all the other bits alone | Clarification | Apply both edits and preserve unrelated requirements |
| i need it sturdier, walls at 3 millimetres, same external size please | Unsupported | Apply the specified thickness and preserve external dimensions; do not claim measured strength |
| dont change the floor, only wall thickness to 3mm | Clarification | Preserve the floor and edit only the wall |
| not 4mm walls, make them 3mm | Clarification | Use 3 mm; do not apply the rejected 4 mm value |
| wall 3 millimeters lid clearance 0.4 millimeters | Clarification | Extract and apply both quantities to their correct targets |
| make that three millimeters instead | Unsupported | Resolve the referent from the supplied valid conversation context |
| make the power hole radius 3mm | Unsupported | Identify the named hole and convert to diameter 6 mm if that is the stored representation |

**Priority checklist**

- [ ] **C01 — Define the supported task and scoring contract. Priority P0.**
  Why it matters: current authored cases are too small and dependent to establish reliable generalization; a broad CAD claim has no fair comparison yet. I will propose enclosure revisions as the first bounded domain, enumerate supported shapes, operations, units and references, and specify the expected behavior for ambiguity and unsupported requests. I will separate complete task success from valid geometry, safe refusal and status-label accuracy. Completion evidence: a versioned task contract, independently reviewed labels, an agreed practical improvement threshold and an acceptable false-acceptance limit before protected evaluation. Domain reviewers and independent authors are external dependencies. A statistical sample size cannot be justified until the domain, effect target and development variability are known.

- [ ] **C02 — Normalize numbers, units and relative quantities. Priority P0; observed failures.**
  The bounded grammar misses number words, relative additions and radius wording. I will add typed quantity parsing with source spans and explicit operations such as SET, ADD and SUBTRACT. A relative edit will use the immutable baseline revision; applying the same transaction twice must not compound it accidentally. Radius-to-diameter conversion will be explicit. This should reduce unnecessary refusals without inventing values. Completion evidence: paired phrase variants, unit conversions, sign/zero/range cases, radius/diameter conflicts and replay checks, followed by new independently authored prompts. Passing the nine known misses alone is regression repair.

- [ ] **C03 — Extract complete multi-clause requests. Priority P0; observed failures and omission risk.**
  Fragmented instructions can contain multiple edits and preservation clauses. I will segment the request into typed requirements, retain each clause's source span, and classify unresolved or contradictory clauses explicitly. The transaction will not publish a partial design as a completed request. Informal goals such as “sturdier” will not become an unsupported physical-strength claim. The intended improvement is complete execution of supported requests and visible unresolved intent. Completion evidence: reordered clauses, missing punctuation, simultaneous edits, optional commentary and deliberately omitted requirements checked against separately authored intent labels. Span accounting helps trace omissions but cannot itself prove complete understanding.

- [ ] **C04 — Make negation, corrections and preservation explicit. Priority P0; observed failures.**
  “Not 4, use 3” and “do not change the floor” carry different meanings from ordinary positive assignments. I will represent additions, replacements, revocations and preserved requirements separately. An authorized new thickness must replace the earlier thickness constraint; unrelated requirements remain active. Completion evidence: counterfactual instruction pairs, valid replacement sequences, contradictory commands and atomic rollback. The expected improvement is fewer incorrect interpretations and fewer unnecessary rejections of legitimate changes.

- [ ] **C05 — Resolve conversation references against a specific revision. Priority P1; observed failure and source limitation.**
  The local evaluation route invokes the parser without history. I will add a bounded conversation interface that tracks referenced properties and entities against the baseline revision. A unique referent can resolve “that”; multiple or missing referents require clarification. Future messages must never enter earlier decisions. Completion evidence: reordered histories, absent referents, multiple holes, deleted entities, stale revisions, and matched tests with and without the needed context. This is a bounded reference resolver, not a claim of unrestricted conversational understanding.

- [ ] **C06 — Ask precise clarification questions. Priority P1; observed behavior gap.**
  Generic questions do not identify the missing information, and two safe rejections have the wrong expected status. I will distinguish a supported request missing a value from an unsupported operation, then ask for only the missing target, quantity or layout choice. Preserve answers as requirement provenance and count clarification turns. Completion evidence: reviewed clarification/refusal labels and complete user trajectories showing useful completion without guessed dimensions. An impossible request may require explaining which constraint must change; it must not silently relax that constraint.

- [ ] **C07 — Finish verification of the existing geometry candidate. Priority P0; incomplete engineering work.**
  The aggregate-check candidate has focused local evidence but no complete native/package result. I will reuse its exact commit, prepared native cases and remaining execution budget. Run the native matrix, full regression and wheel/sdist acceptance before integration. Completion evidence: retained results tied to the exact candidate or a recorded successor, with failures and protected-file preservation. Hosted upload remains subject to the earlier explicit destination/payload approval requirement; this checklist does not clear that requirement. Local heavy work still requires the unchanged resource guard.

- [ ] **C08 — Verify actual holes, clearances and topology. Priority P0; known verification boundary.**
  A construction-history cutter can exist without making a hole, and matching total volume cannot distinguish a shifted hole. I will extend the final-geometry verifier with separately named checks for axis, radius, position, depth, through/blind state, connectivity and required clearance within the chosen domain. Query the exported and reimported final solid, using declared tolerances and unambiguous target selection. Completion evidence: unused cutters, filled holes, blind/through swaps, shifted equal-volume holes, intersecting bores and disconnected solids. Unknown or ambiguous measurements cannot pass. This extends the aggregate candidate; it does not relabel aggregate checks as complete geometry proof.

- [ ] **C09 — Preserve requirements and invalidate changed evidence. Priority P0; broader coverage needs verification.**
  Existing transactions and hashes are useful foundations, but wider edit combinations require coverage. I will bind active requirements, baseline revision, candidate geometry, material, load, units, tolerances and checker identity to each verdict. Recompute affected checks after changes, using complete recomputation as the reference. Missing or multiply resolved entity references must stop publication. Completion evidence: mutation matrices and multi-edit sequences showing intended edits, preservation, authorized revocation, stale-result rejection and rollback. Incremental caching comes only after equivalence to the full-check reference; a cache defect has not been established by the current language diagnostic.

- [ ] **C10 — Build an independent challenge and a fair comparison. Priority P0 for performance claims; missing evidence.**
  Project-authored tests and more retries can make apparent gains misleading. I will provide the collection schema, adapters, deduplication checks, frozen runner and analysis. Independent people must supply and adjudicate new project families. Separate development and protected projects before tuning; group related revisions and paraphrases together. Pin compatible comparator versions and match input information, candidates, calls, timeouts and resource budgets. Record unsupported cases, errors and all attempts. Completion evidence: preserved raw outputs and a paired project-level analysis of useful completion, false acceptance, coverage and cost. For fixed-bank policy experiments, every policy sees the same candidates; interactive end-to-end effects need their own protocol.

- [ ] **C11 — Add bounded repair only after scoring is trustworthy. Priority P2; proposed improvement.**
  Some construction failures may be repairable, but benefit is unmeasured. I will add a limited candidate queue driven by specific failed requirements. Every retry must recheck all active requirements, preserve failed attempts and stop at a fixed budget. The planner cannot weaken the scoring rules. Completion evidence: an equal-budget repair-versus-no-repair comparison with full cost and failure accounting. Retain the feature only if it improves useful completion within the agreed error and cost limits. This is not permission to keep retrying until a desired result appears.

- [ ] **C12 — Measure performance before optimizing or adding a trained model. Priority P2; benefits unmeasured.**
  There is no measured bottleneck profile or supported trained CAD checkpoint. I will first record complete-path latency, peak memory, kernel work and retry cost. Optimize demonstrated bottlenecks with decision-equivalence tests, cancellation and bounded concurrency. Evaluate an optional provider behind the same typed proposal and deterministic verification interface if remaining language errors justify it. Training is conditional on licensed data, protected family splits, suitable compute and a separate budgeted study. Completion evidence: measured quality/cost tradeoffs against the unchanged baseline; no model-size or speed claim without results.

- [ ] **C13 — Validate physical accuracy and fit. Priority P0 for physical claims; external evidence absent.**
  Formula and mesh checks do not measure fabricated parts. I will prepare versioned prediction tables and analysis for the existing physical protocol, including tolerances, calibration, uncertainty and fixed pass criteria. An identified experimenter must fabricate or obtain representative parts and collect real measurements. Completion evidence: raw measurements, apparatus/calibration records, repeats and prediction-versus-measurement errors within the predeclared envelope. Any physical-model repair becomes a separately versioned validation effort; prior measurements remain intact.

- [ ] **C14 — Demonstrate independent reproduction and user usefulness. Priority P0 for external claims; evidence absent.**
  Project CI is not an independent executor, and browser tests do not show that people finish useful tasks. I will provide a pinned install/reproduction package, discrepancy form and intended-user task protocol. A distinct executor and actual intended users must supply their own records. Measure correct completion, time, interventions, critical input errors and understanding of limits, with a suitable comparison workflow. Completion evidence: independently produced artifacts and real task outcomes, including failures. Fix observed usability problems and repeat affected tasks without rewriting the original results.

- [ ] **C15 — Establish a distinct research question. Priority P0 for a research successor; unresolved.**
  The dated prior-art audit does not support broad novelty for verification-guided CAD or requirement preservation. I will refine the proposed requirement-omission study and compare its exact question and evidence with the closest work before implementing a research successor. Its possible contribution is separating incomplete interpretation from checker error while holding candidates and budgets fixed. Completion evidence: a defensible distinction, explicit falsifier, independent scoring and a frozen analysis. An effect explained by extra information, extra abstention or existing prior work fails the intended claim. A useful product can progress through engineering without claiming a novel research method.

- [ ] **C16 — Reconcile provenance and ship a separately versioned release. Priority P1; delivery and evidence gaps.**
  The dirty original checkout, later verified main and immutable alpha identify different source states. I will keep their identities explicit, integrate only reviewed verified changes, and prepare a corrected prerelease with checksums, provenance and anonymous installation acceptance. Recover the four missing original logs only from authentic sources; if unavailable, retain that limitation and avoid claims that need them. Completion evidence: exact release-source identity, clean install/native acceptance, preserved historical artifacts and an explicit release receipt. Publication is a separate action from writing this checklist.

**How the improved path would work**

Request and permitted conversation history → typed edits and active requirements → explicit clarification where needed → candidate built from the exact baseline → final-geometry and preserved-requirement checks → atomic acceptance or a specific refusal → source-bound evidence.

For “make the power hole radius 3 mm, keep the outside size, and add 1 mm to the walls,” the pipeline must identify the named hole, represent the radius correctly, derive wall thickness from the baseline, and retain the outside-size requirement. It then builds a candidate and measures the final hole and dimensions. A correctly sized hole in the wrong position or a changed outside size fails. Any authorized replacement of an old requirement is recorded explicitly. This example is an acceptance specification, not a reported new result.

**Execution order and checkpoints**

1. Establish C01 and prepare C10/C15 while preserving all current evidence. Define new engineering budgets before source changes; do not reset earlier exhausted budgets.
2. Finish C07 when its existing upload/resource conditions are met. This existing engineering candidate can proceed independently of the research novelty decision.
3. Implement C02–C06 in small isolated changes, keeping the old baseline and separate development results for each change.
4. Add C08–C09 under the declared geometry envelope. Demonstrate final-output correctness and edit preservation before adding repair or cache shortcuts.
5. Execute C10 only after the scientific question, data, comparators, endpoint, stopping rules and protected manifest are frozen. An engineering challenge and a scientific claim have different completion gates.
6. Admit C11–C12 only when measured failure or cost evidence justifies them. Run C13–C14 when the external operators, assets and participants exist. Complete C16 for the selected verified product scope.

**Definition of improvement**

Correct-and-accepted valid requests are the primary practical outcome. Safe abstention remains visible but does not count as completion. Report incorrect acceptance, conditional error among accepted outputs, coverage, clarification burden, latency and total cost separately. Conditional error is undefined if nothing is accepted.

Before protected comparison, choose the minimum useful improvement, maximum tolerable false-acceptance risk, confidence procedure and sample size with domain justification. A comparative success requires the predeclared improvement and risk criteria to pass together, with uncertainty calculated over independent project families. Zero observed unsafe outputs in 12 authored rejection cases does not prove zero risk. Preserve negative, mixed and inconclusive outcomes.

**Evidence and traceability**

- [Retained language rows](verification/verified-intent-20261014/candidate-artifacts/conversation-python-3.12.14/language-intent-evaluation/results.jsonl) and [merged engineering summary](verification/verified-intent-20261014/SUMMARY.json).
- [Implemented verified-intent repairs and earlier proposals](VERIFIED_INTENT_UPGRADE_PLAN_20261014.md).
- [Output-geometry candidate results](../research/development/output_geometry_20261014/RESULTS.md) and [geometric counterexamples](../research/development/output_geometry_20261014/AUDIT_AND_SPEC.md).
- [Existing external completion checklist](V3_READINESS_CHECKLIST.md) and [external evidence protocol](../research/physics_v3/external_validation_v1/PROTOCOL.md).
- [Canonical research pointer](../research/RESEARCH_STATE.json), which resolves the separately preserved successor study design and 36-item flaw register.

Coverage of the existing flaw register: C01/C10 cover F04, F08–F09, F15–F22 and F28; C02–C06 cover F05–F07 and F11–F12; C07–C09 cover F10 and F13–F14 plus F24–F25; C12 covers F26–F27; C13–C14 cover F23 and F29–F30; C15 covers F03 and F33; C16 covers F01 and F31–F35. Fixed budgets, finite scope and the definition of improvement apply across F02 and F36. This mapping records known issues, not an assertion that every possible defect has been found.

**Implementation update — 15 October 2026, quantity maintenance**

Local candidate `b12812a` implements the bounded C02 quantity grammar and precompiles parser patterns for C12. Number words, explicit baseline-relative scalar edits and named circular-hole radius now pass their authored cases. The focused suite passes 170 tests; all 48 new quantity cases pass. The unchanged development diagnostic improves from 11/20 to 14/20 valid exact requests, with 12/12 fail-closed rejections and no observed regressions. The prior baseline above remains historical.

C02 remains open for independent prompt coverage and integration. C12 remains open: median local timing is 6.26% lower but only one of five paired rounds is faster, so no reliable speedup is established. C03–C06, the pending geometry candidate, physical/reproduction/usability evidence and research Checkpoint 1 remain open. Initial fixture failure, a 30-second-terminated accidental native test selection, and lint/test-harness repairs are retained.

[Source, complete outcomes and failure records](/Volumes/PRO-BLADE/.codex-worktrees/neurocad-conversation-quantities-20261015/research/development/conversation_quantities_20261015/REPORT.md). The implementation is local in `/Volumes/PRO-BLADE/.codex-worktrees/neurocad-conversation-quantities-20261015`; no push, merge or release occurred.
