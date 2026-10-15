# Scalar intent repair — 15 October 2026

**239 focused tests and lint pass. Type checking, full/native/installed verification, integration and scientific completion remain open.** This local candidate extends `910d80939385f61246b768749a16487a5d09b8b7`, which itself preserves quantity candidate `b12812a`. No predecessor budget or outcome is reset.

## Flaws, repairs and evidence

| Flaw or introduced risk | Cause | Severity | Repair | Evidence |
|---|---|---|---|---|
| Valid scalar-preservation phrases refused | Existing preservation grammar covers outer boundary/holes, not individual scalar fields | Medium | Map complete keep/preserve/do-not-change clauses to existing protected fields | New complete-spec and preservation-only tests; language-15 recovered |
| ONLY scope unsupported | No representation of all other fields remaining unchanged | Medium | Protect every other specification field, including sibling lid properties | Complete candidate equality, full protection-set check, conflicting floor/profile/title/lid cases |
| Rejected-value correction refused | No source-local target or excluded-value context | Medium | Require an adjacent same-scalar assignment; retain excluded stored values through subsequent corrections | language-16 recovered; missing/mismatched replacement, equivalent units, rounding equivalence and restoration counterexamples |
| Bare correction reverses increase/decrease | Old correction branch retained the label but discarded direction | High | Typed quantity context carries direction; every bare correction compares with immutable baseline | Three confirmed incorrect baseline proposals now refuse; valid directional control passes |
| Repeated ONLY clauses could exceed collection bound | Naive protection expansion duplicates fields | Medium implementation risk | Deduplicate protections from repeated ONLY clauses | Three identical nested-lid clauses retain unique protections and succeed |
| Saved proposal or stale application bypasses intent | Cross-revision replay risk | High preserved invariant | Keep shared review, candidate/action validation and baseline hashing | Saved review/apply, explicit consent and stale rejection test |

The baseline collected all **47 new cases**: **18 failed / 29 passed**, without fixture errors. Eleven failures were unsupported valid phrases; other failures were preservation/review behavior and three opposite/no-direction bare corrections. Not all failures were unsafe acceptance. The first candidate run passed **239/239** tests across the six explicitly selected parser, quantity, directional and evaluator files, including all 47 new cases. It took about **1.62 seconds** wall time and **72.38 MiB** peak child RSS. These figures describe execution cost, not a speed comparison.

Ruff passed on the changed parser and new test file. Scoped mypy was terminated at the declared **96 MiB** cap (sampled 98.5 MiB; child peak 98.86 MiB). This is a retained resource block, not a type-check pass or a demonstrated type defect. The cap was not raised and the attempt was not repeated.

## Development result and limits

The exact same 32-case observed development dataset and unchanged scorer produce:

| Endpoint | Previous retained candidate | Current candidate |
|---|---:|---:|
| Exact valid requests | 14/20 | 16/20 |
| Complete annotated outcomes | 24/32 | 26/32 |
| Fail-closed rejection | 12/12 | 12/12 |
| Wrong candidate | 0 | 0 |
| Unsafe acceptance | 0 | 0 |
| Provider errors | 0 | 0 |

Only language-15 and language-16 improve; no retained case regresses. The diagnostic returns exit **2**, correctly preserving remaining failures. Earlier 11/20 results and subsequent quantity/directional evidence remain unchanged.

These prompts were already observed and motivated the repair; this is in-sample maintenance evidence. The copied dataset's historical statement about no tuning in its original sprint does not describe this session. No independent authorship, generalization, SOTA advantage, physical accuracy or research checkpoint is established. No benchmark was rerun to seek a favorable speed result; prior efficiency evidence remains inconclusive.

## Conditional correctness argument

For ONLY target `t`, let `S` be the original serialized specification and `S'` the final specification. `_other_fields` enumerates every top-level specification field except the target's root and fixed schema/unit tags. For a nested lid target it also enumerates every sibling lid field. The existing validator compares every enumerated field with its original value and emits no candidate if any differs. Thus an emitted candidate satisfies `S'[f] = S[f]` for every protected field in this declared schema. This argument assumes the serialized specification enumerates the relevant state; it does not cover native geometry or physical behavior.

A rejected quantity is converted to the same stored numeric representation as the replacement. The parser checks membership in the retained excluded-value set before accepting assignments and again against the final candidate. A bare correction carries the original direction and must satisfy a strict stored-value inequality relative to the baseline. These are implementation invariants supported by counterexample tests, not a proof that arbitrary natural language is understood perfectly.

## Remaining flaw checklist

| Work | Cause | Planned repair | Required evidence / gate |
|---|---|---|---|
| Fragmented edits (language-13, language-17) | Current clause grammar requires complete target/value structure | Separately specified segmentation and typed clause grouping, with full original span coverage | Reordered clauses, omitted punctuation, malformed unit/target swaps and complete-spec checks; new independently authored cases |
| Informal context (language-14) | Physical goal and preservation wording remain unresolved | Distinguish explicit dimensions from unverified strength goals; represent external-size preservation explicitly | Goal/geometry counterfactuals; never report strength from a thickness edit |
| History reference (language-18) | Local parser receives no dialogue history | Revision-bound reference context and a versioned runner/interface change | Missing, multiple, deleted and stale referents; no future-message leakage; matched history-off controls |
| Clarification labels (language-28, language-32) | Safe refusal does not yet ask the needed layout/objective question | Typed missing-slot questions with reviewed status labels | Real task trajectories and independent adjudication |
| Type/full/native/install validation | Resource admission fails; scoped mypy exceeded its cap | Resume exact-source checks on an admitted host | Successful retained checks on this candidate; no inference from previous CI |
| Final exported-feature geometry | Aggregate candidate and feature-level checks have separate open gates | Preserve candidate 941eed7; verify exported/reimported actual geometry | Native counterexamples, explicit destination/payload approval where required |
| Scientific contribution and comparison | Recovery review remains Checkpoint 1 blocked | Defensible distinct question, independent task-compatible scoring and strong matched comparators | Contribution review and frozen development/confirmatory methodology before new research implementation |
| Physical/reproduction/usability claims | No real external evidence supplied | Existing physical/reproduction/user protocols | Apparatus/calibration measurements, distinct executor and intended users |

## Integrity, budget and reproduction

58 protected baseline files match their recorded hashes. This is a sparse worktree: omitted protected files were checked by immutable Git blob contents; staged-delta inspection must additionally show no protected paths changed. Only `core/conversational_parser.py` changes among existing production sources. The quantity module, project validator, challenge labels and scorer remain unchanged.

Consumed: one baseline batch, one candidate batch, one lint/type batch, one observed diagnostic and one static integrity audit. No native/full/hosted/training/paid/protected run. The initial sparse checkout needed index initialization, and `sparse-checkout add --no-cone` was rejected because add inherits the configured mode; both setup corrections happened without source loss. No scientific execution or outcome was retried after seeing the diagnostic.

The source and raw results are local. Use the existing environment with the six explicit test paths from `candidate-1.json`; do not broaden into native tests under the current resource conditions. `run_guarded.py` retains command, source identity, timing, memory and exit state. `diagnostic-difference.json` identifies every remaining miss. The local evidence manifest seals the artifacts; the candidate Git commit identifies the source. This package is not an independent reproduction or release.
