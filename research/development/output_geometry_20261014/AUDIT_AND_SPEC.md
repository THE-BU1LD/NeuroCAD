# NeuroCAD research audit and bounded output-geometry successor

Date: 14 October 2026. Starting scientific disposition: original compiler study
terminal **MIXED**; Physics v2 supported only within its frozen controlled
contract. This pass preserves those conclusions and all failed successor runs.

This document is an engineering specification and research go/no-go audit.
It is not a completed research paper, independent reproduction, trained-model
result, physical experiment or public release. Execution results belong in the
separate `RESULTS.md`; this specification does not predict their outcome.

## Current system and what is going well

The supported system is a deterministic typed CAD compiler with optional
language providers and native backends. No supported trained CAD checkpoint is
available. The original dirty checkout is at `48cccef2`; the engineering base
for this successor is main `e1c09a80a58b0d883be9091a1bd5cb8b9b47aea1`, freshly
confirmed against the remote. The changed verification module has identical
bytes at both starting revisions. An isolated Git index can place the bounded
patch on main without resetting the dirty checkout or copying its unrelated
changes.

Retained PR112 receipts report 1,789 maintained tests and 1,770 sdist tests,
three native platforms, source-bound requirements and language-evaluation
integrity repairs. These are historical bounded engineering results. The
unchanged 32-case authored language diagnostic has 11/20 exact valid intents,
12/12 safe non-proposal responses, 21/32 exact total outcomes and zero unsafe
acceptances. Two safe responses use a different refusal status. These numbers
are not independent generalization estimates or results from this successor.

Good foundations include explicit units, typed feature histories, deterministic
validation, source/data hashes, transactional revision checks, native STEP
roundtrips, rejected-output retention and immutable alpha provenance. The
earlier beam, shaft and hole-ligament defects and their corrected successor
receipts remain visible. Physics v2 has used its two development revisions and
one confirmation; those budgets are closed.

## Prior art and novelty decision

Primary sources were read on 14 October 2026. Descriptions below are claims
about what the papers specify, not reproduced results or a fair score
comparison with NeuroCAD.

| Source | Consequence for NeuroCAD |
| --- | --- |
| [CADTests](https://arxiv.org/html/2605.07807v1) | Final B-Rep requirements, mutation-strengthened checks and test/log-guided repair already exist. |
| [HistCAD v3](https://arxiv.org/html/2602.19171v3) | Constraint preservation through edits, fixed preservation sets and edit reachability already have explicit evaluation. |
| [ReliCAD](https://arxiv.org/html/2609.22325) | Structured intent, dependency planning, runtime evidence, itemwise verification and local repair overlap strongly with the proposed architecture. |
| [CADEngBench](https://arxiv.org/html/2608.09296) | Functional edits must achieve targets and preserve non-target properties, including hidden geometry measurements. |
| [CADIR](https://arxiv.org/html/2608.00891) | Parameter/dependency/constraint/topology construction graphs already support editable reconstruction. |
| [Text2CAD-Bench](https://arxiv.org/html/2605.18430v1) | Advanced-feature/application coverage is needed before broad text-to-CAD comparisons. |
| [ProCAD](https://arxiv.org/html/2602.03045v2) | Specification auditing and clarification before CAD generation are established mechanisms. |
| [CADFS](https://arxiv.org/html/2605.01925v1) | Rich executable design histories and broader operation vocabularies are established directions. |

**Research Checkpoint 1: NO-GO for a novelty claim as currently stated.**
Verification-guided CAD, structured requirements, receipts and preservation
through edits cannot honestly be introduced as new on this evidence. No new
training or confirmatory study follows from this audit.

A possible future question is whether a conservative dependency mechanism can
reuse geometry evidence at lower verification cost with unchanged soundness
relative to rebuilding and rechecking every requirement. This is a hypothesis,
not an approved or novel successor. It first needs an incremental-verification
literature audit, a sound invalidation rule and an operation-level argument.

The strongest simple comparator is full rebuild plus complete frozen requirement
replay after every edit. Match backend, tolerances, requirements and proposals.
For language experiments, add a fixed CADTest+Log-type comparator at equal
call/token/time budgets. A missed dependency allowing a stale acceptance, or no
cost benefit against full replay, falsifies the proposed incremental advantage.

## Observed flaws and repair/evidence checklist

This is the audited set of known flaws and missing evidence. A finite audit
cannot establish that all possible flaws have been found.

| Flaw and cause | Severity | Fix or improvement | Required proof and disposition |
| --- | --- | --- | --- |
| Broad architecture overlaps prior art | P0 research | Narrow a materially distinct mechanism before new science | Primary-source comparison and explicit falsifier; novelty gate currently NO-GO |
| History membership is mistaken for final geometry | P0 correctness | Separately named final-output probes; preserve history semantics | Native counterexamples and correct basis labels; aggregate layer in this pass |
| Missing explicit final solid-count/volume requirements | P1 correctness | Bind aggregate checks to exactly the declared output ids | Analytic native solids, reimported STEP and invalid-evidence rejection |
| Aggregate values cannot identify a hole | P0 claim limit | Add later axis/radius/depth/cavity/topology queries under a new contract | Equal-volume shifted hole must remain a counterexample; not solved by this pass |
| Malformed extent axis raises TypeError | P1 reliability | Type-check before dictionary membership | Array/object rejection regression plus unchanged x/y/z behavior |
| Integer count can round above 2^53 | P1 numerical | Preserve original integer for exact comparison and report | Adversarial exact-integer mismatch; reviewer finding retained |
| Valid B-Rep does not imply intended design | P0 validity | Require every explicit must predicate, including unchanged requirements | Wrong-but-valid geometry must fail declared checks; broad intent still open |
| 9/20 valid authored intents miss semantic exactness | P1 capability | Separately budget paraphrase, relative-edit, negation and history work | Prospective task contract and whole-request/unsafe-acceptance metrics; unchanged here |
| Refusal-status mismatch on two authored cases | P2 behavior | Define clarification/refusal contract before parser changes | Exact status plus safe rejection reported separately |
| Evaluation authored with knowledge of implementation | P0 external validity | Independent authors/adjudicators, clustered deduplication and protected freeze | Real reviewed inputs; absent, no blind-generalization claim |
| No strong compatible comparative outcomes | P0 significance | Match tasks, representation, retry budget and timeout policy | Frozen provider/model/license/cost identities and raw outcomes; absent |
| No trained checkpoint or licensed split | P0 learned claim | Admit licensed data and source-family splits before training | Actual checkpoint, environment, seeds and matched controls; absent |
| Additional compute/info could explain future gains | P0 causality | Same-model mechanism-off and budget-matched comparisons | Whole matrix, failures and uncertainty; not replaced by unit tests |
| Physical accuracy and manufacturing utility unmeasured | P0 physical claim | Execute frozen calibration/measurement protocol with real hardware | Operators, raw measurements, repeats and uncertainty; absent |
| Independent reproduction absent | P0 reproducibility | External executor runs frozen package and adjudicates discrepancies | Their unedited receipts; our CI and AI review do not qualify |
| Intended-user/accessibility benefit unmeasured | P1 usability | Consented representative tasks and observed defect repair | Real participant/device outcomes; browser automation is insufficient |
| Four original historical logs missing | P1 provenance | Recover authentic copies matching original manifest hashes | Missing stays missing if unrecoverable; never reconstruct a fake log |
| Root checkout and top status lag later merges | P1 routing | Isolated main-based candidate and additive current routing note | Exact source/tree identity; do not rewrite historical inventories |
| Native execution blocked locally | P1 infrastructure | Use unchanged admission guard or source-bound hosted jobs | Two stable >=512 MiB samples or retained exact-commit CI; failures retained |
| Main-only fixes are absent from immutable alpha | P1 delivery | Separate reviewed prerelease process if publication is chosen | New tag/checksums/provenance/anonymous install; alpha never overwritten |
| External geometry licenses, tooling and authorship unresolved | P0 external work | Obtain exact assets/rights and responsible review | Real access and supplied evidence, not inferred permission |

## Bounded engineering specification

The new functionality evaluates **explicit aggregate requirements**, not hole
semantics inferred from aggregate values. Existing `feature_presence` and
`feature_count` continue to report `feature_history_*` evidence.

Inputs are Requirement IR `R`, Feature IR `P`, binding set `B` and final
inspection `I=(valid_brep, solid_count, volume_mm3, extents_mm)`. Existing hashes
bind `B` to `R` and `P`. Each new binding uses `geometric_relation`; its probe
contains exactly one key, `kind`. Bound feature ids must equal all output ids
in their declared order; outputs must be nonempty, distinct and present.

Inspection admission requires `valid_brep is True`, positive non-boolean
integer solid count, finite positive volume and three finite positive extents.
Invalid values produce structured binding errors. This prevents malformed
numeric evidence from satisfying a predicate; it does not authenticate a
caller. The verified-export path obtains `I` from the reimported STEP. Direct
API users are responsible for supplying authentic inspection evidence.

`output_solid_count` requires a positive integral unitless target `n`, tolerance
absent or exactly zero, and accepts iff `I.solid_count == n`. Original integer
targets remain integers; converting them to binary floating point before
comparison could change their meaning. The report retains the exact target.

`output_volume` requires positive finite `V` in `mm3` and an explicit finite
nonnegative absolute tolerance `epsilon`. It accepts iff
`abs(I.volume_mm3 - V) <= epsilon`, with relative tolerance zero. No implicit
scale-dependent accuracy promise is introduced. The full must decision still
requires every bound must check and no validation/hash/contract error.

The count/volume checks are O(F+O) for feature/output membership with O(F+O)
auxiliary memory per aggregate binding; scalar comparison is O(1). Native
build/export cost is unchanged. No parameters, optimizer, training loss,
gradient, randomness or learned initialization exist in this deterministic
extension; those model-template fields are not applicable.

## Development matrix and analysis

The prospectively saved `contract.json` fixes this engineering scope, budget,
falsifier and protected boundary. `axis_addendum.json` records the adjacent
input validation fix. Pure-Python tests cover correct/wrong aggregates, strict
units/tolerances, malformed evidence, output scope, exact integer comparison,
unknown keys, stale hashes and unchanged-must protection. These are authored
development fixtures. Baseline failures remain in `baseline.log`/`baseline.xml`.

Native reference: a 40 x 30 x 8 mm box has volume 9600 mm3. A radius-3 mm
through cylinder removes `pi * 3^2 * 8` mm3; a half-depth bore removes half
that volume. The fixed reference tolerance is 1e-6 mm3 for these fixtures only.
Unused cutters and subsequently filled holes retain history but have full box
volume. Two disjoint 10 x 10 x 8 mm prisms have count 2 and volume 1600 mm3.
Moving a radius-3 bore from x=0 to x=8 preserves count/volume while violating
the original location. Both aggregate checks must pass that last example;
the kernel distance from the nominal axis exposes the missing location claim.

No p-value, population confidence interval, sample-size power assertion or SOTA
effect is appropriate for this finite deterministic authored matrix. Report
each attempted case, errors, skipped native jobs, exact source and environment.
All cases stay in the denominator. A changed method or wider applicability
claim requires a new contract; exhausted retries are not reset.

## Ten research checkpoints after this audit

| Checkpoint | This new research direction |
| --- | --- |
| 1 Idea ready | NO-GO: broad mechanism not novel; narrower candidate unproved |
| 2 Model specification ready | Bounded engineering spec present; novel research model not defined |
| 3 Methodology ready | Authored engineering matrix defined; independent comparative methodology not frozen |
| 4 Model implemented | Two aggregate engineering predicates implemented; no trained model |
| 5 Experiment system implemented | Existing test/receipt system extended; no independent scientific dataset |
| 6 Run ready | Pure checks run; native status must come from source-bound execution receipt |
| 7 Confirmatory protocol frozen | NOT_STARTED; no protected outcome access |
| 8 Evidence locked | Per-pass receipts required; predecessor evidence unchanged |
| 9 Verified | Scope limited to retained engineering execution; external reproduction open |
| 10 Research complete | NOT_COMPLETE for a novel successor; predecessor stays terminal MIXED |

The next scientific action is to settle a distinct, falsifiable question with a
credible comparator. The next geometry engineering action is to specify genuine
hole/topology predicates, including equal-aggregate counterexamples. Physical,
independent and user studies require their actual external inputs. None can be
closed by making this checklist longer or rerunning until favorable.
