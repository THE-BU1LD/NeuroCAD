# NeuroCAD repair and evidence audit — 15 October 2026

**The numerical input repair passes 134 focused tests and lint. The complete product and successor research remain unfinished.** The original study remains terminal MIXED. No protected experiment, native kernel, full suite, installed package, training, external measurement, upload, merge or release was run in this session.

## Current evidence and source identity

The main checkout remains the pre-existing dirty `48cccef2` branch. GitHub main was read live and is `e1c09a80a58b0d883be9091a1bd5cb8b9b47aea1`. The original alpha and frozen science remain unchanged.

The newer integrated local candidate `3e26da5` retains 371 passing focused tests and a 32/32 observed language diagnostic (20/20 valid requests and 12/12 safe rejections). These are retained receipts, not rerun here. Those prompts already motivated development, so they are not independent confirmation. The subsequent ledger source `5a5f850` retains 49 passing ledger tests and an offline consistency audit. This repair starts from that exact ledger source, preserving both earlier histories. Neighboring uncommitted parser typing and native-test corrections were inspected and left intact; they are not part of this numerical candidate.

No trained CAD checkpoint or measured advantage over a matched independent baseline is established by these records. The new research direction remains Checkpoint 1 NOT_READY.

## New defect, repair and evidence

| Flaw | Cause | Severity | Repair | Evidence |
|---|---|---|---|---|
| Finite translated coordinates can erase an entire requested bore depth | At 1e20, adding 8 rounds back to 1e20 | High input-contract defect; native consequence unmeasured | Check translated axial and radial boundaries before accessing the shape/kernel | Positive/negative translations on all three coordinate axes rejected before native access |
| Tolerance can disappear around a radius | At radius 3, adding/subtracting 1e-20 leaves 3 unchanged | High input-contract defect | Require strictly ordered inner/nominal/outer radial coordinates and axial boundaries | Tiny-tolerance rejection and direct arithmetic witness |
| Nonzero displacement can still be too coarsely represented | A coordinate near 2**43 has floating spacing greater than 0.001 | High precision mismatch | Require float spacing no greater than the declared linear tolerance at checked positions | Counterexample distinguishes nonzero displacement from adequate resolution |
| Finite derived radius can overflow squared-volume arithmetic | Finite inputs do not imply finite intermediate expressions | Medium error-interface defect | Normalize arithmetic overflow to explicit ValueError; retain positive/finite volume checks | Resolved-offset large-scale overflow case rejected before kernel access |
| Conservative rejection narrows admissible translations | Global coordinates may not resolve a requested tolerance even when local geometry is meaningful | Limitation | Reject with a specific error; any future local-frame transform needs its own export/equivalence specification | No claim of translation-invariant native accuracy; ordinary scaled/translated controls pass |

The frozen initial baseline collected 43 tests: **20 failures and 23 passes**. These are repeated checks over ten failing configurations, not twenty independent defects or twenty incorrect CAD outputs. Several invalid inputs were already rejected correctly. The final test file has 45 cases after adding two checks for a separately reviewed squared-volume overflow path; the original baseline is not relabeled.

Candidate 1 passed 132 checks. Candidate 2 passed 134 after the overflow-path coverage was added. First lint failed on the repository's pairwise-loop rule; that failure is retained. Replacing adjacent zip iteration with itertools.pairwise passed lint, and the final allowed candidate batch passed **134/134**, in **0.935 seconds** with **64.94 MiB** peak child RSS. This is execution cost, not a speedup comparison. All runs used the unchanged 20-second/96-MiB cap and one thread.

### Conditional correctness and algorithm

The validator converts admitted numeric inputs to finite binary floats. It forms four ordered radial boundaries and six axial boundaries, checks strict ordering, and checks that the spacing between representable floats at every boundary is at most the requested tolerance. It translates these boundaries along the declared Cartesian axis and around each perpendicular coordinate, applying the same checks. Derived probe volumes must remain positive and finite. A violation raises before shape attributes or native constructors are accessed.

The routine has constant work and storage: fixed-size coordinate lists, no data-dependent loop, no learned parameters, no optimization or training. Under Python's floating arithmetic, these explicit checks guarantee only their stated ordering/finite/spacing preconditions. They do **not** prove native CAD accuracy, tolerance propagation through rotations/Boolean operations, topology, manufacturing fit, arbitrary-language understanding or complete geometric correctness.

## Updated project-wide flaw checklist

This supplements the preserved 16-item recovery checklist and prior 36-item flaw register. It is not a claim to have found every possible defect.

| Item | Current cause / state | Required repair or next action | Completion evidence |
|---|---|---|---|
| C01 bounded task and success criteria | General CAD perfection has no finite test; independent success/risk criteria absent | Freeze explicit enclosure/edit domain and practical thresholds | Prospective task contract, endpoint/risk rationale and sample-size plan |
| C02–C06 quantities, clauses, preservation, history, clarification | Locally implemented; observed 32/32 diagnostic is tuned development evidence | Reconcile exact integration source; retain unparsed-span and stale-history rejections; collect unseen independently authored tasks | Full candidate checks and protected family-level completion/false-acceptance results |
| C07 aggregate final geometry | Integrated locally; native checks pending | Execute source-bound export/reimport and wrong-output cases | Native/full/install receipts; aggregate counts/volume still cannot prove hole location |
| C08 final feature geometry | Isolated Cartesian bore code and adversarial native tests exist; this session fixes numerical admission | Run actual native axis, blind/through, shifted/filled/crossing-hole controls | Exact-source kernel results, exported STEP evidence and explicit supported envelope |
| C09 preservation and dependency consistency | Broad final-feature preservation and selective recomputation unproven | Audit all active requirements against final geometry; defer caching until equivalence is demonstrated | Counterfactual edits and stale/deleted dependency rejection |
| C10 independent evaluation | Independent intent labels, compatible baselines and protected splits absent | Obtain external scoring authority and authentic comparator outputs; freeze family splits and denominator policy | Matched-controls study with uncertainty; ledger consistency alone is insufficient |
| C11 bounded automatic repair | Benefit unmeasured and additional retries can confound efficacy | Admit only under a defined failure mechanism and equal candidate/compute budgets | Matched repair-off and compute controls, all failures retained |
| C12 efficiency / trained model | No reliable speedup, full-path profile or justified trained-model study | Measure complete-path latency/memory before optimizing; separately admit licensed training if needed | Quality/cost evidence and held-out matched baselines |
| C13 physical validity | No fabricated-part measurements or calibration | Actual operator follows existing physical protocol | Raw measurements, apparatus calibration, repeats and predeclared uncertainty |
| C14 independent reproduction / usability | No distinct executor or actual intended-user evidence | Execute existing reproduction and user-task protocols | Independent artifacts and genuine user completion/cost results |
| C15 scientific contribution | Existing verification/preservation/intent mechanisms overlap prior art | Establish a materially distinct falsifiable contribution before research implementation | Primary-source novelty comparison, valid task/oracle and frozen study |
| C16 provenance / release | Different local source states; four original logs missing; upload gate unresolved | Reconcile candidates, run exact-source hosted/native/package gates, retain missing logs as missing | New release identity and install/provenance receipts; old alpha unchanged |
| Evaluation accounting | Ledger v2 locally tested, source `5a5f850`; semantic validity is separate | Integrate with authenticated isolated adapters and retain independent manifest/summary anchors | Full integration and independently scored outcomes |
| Numerical admission | Fixed within declared arithmetic scope | Native verification on admitted resources | This package supplies 134 local tests; native result remains NOT_RUN |

## Research admission recheck

Three primary sources were reopened on 15 October. [CADTests](https://arxiv.org/html/2605.07807v1) already uses executable final-geometry tests and test-guided generation. [HistCAD](https://arxiv.org/html/2602.19171v3) defines edits with fixed preservation sets and separates reachability from successful preservation. [CIT-CAD](https://arxiv.org/html/2609.07434v2) explicitly identifies the risk that a verifier checks incorrectly extracted intent. My inference is that these sources continue to defeat a broad novelty claim for combining those ingredients. This is a focused recheck of the retained wider review, not an exhaustive proof that no novel contribution exists. No additional concept-review budget or scientific run was opened.

Successor checkpoints remain: 1 BLOCKED; 2–10 NOT_EVALUATED. A paper can describe prospective work or bounded prior results, but cannot truthfully report the requested new positive scientific result without the missing study.

## Resources, preservation and next gate

Two samples were approximately 102.63 and 97.73 MiB free-plus-speculative, with pageouts increasing 699571 to 699782; a later read showed 13446 MiB swap used. Heavy execution remains below the unchanged 512-MiB gate. No unrelated process was stopped. Only bounded standard Python tests and lint were run.

Static audit confirms 4,980 inherited paths unchanged, including 3,815 paths under protected research/physics/paper prefixes. The only inherited production change is core/final_geometry.py. The passing final receipt hashes match the final source and tests. Baseline failures and lint failure remain in this package.

The current repair budget is closed after baseline 1/1, candidate 3/3 and lint 2/2. Unused static-review capacity is for source/evidence closure, not additional outcome search. Native/full/type/install and scientific runs remain zero. Prior budgets and results remain intact.

Next: review the explicit upload manifest, reconcile the neighboring parser/native corrections, and perform exact-source hosted type/full/native/install verification under the separately declared integration budget. Automatic approval review in earlier sessions rejected upload to THE-BU1LD/NeuroCAD until the user explicitly approves that destination and the source/tests/workflows/development-evidence payload. No upload was attempted in this session. Native execution can alternatively proceed locally once resource admission passes. Physical, independent and human evidence still requires real external execution.
