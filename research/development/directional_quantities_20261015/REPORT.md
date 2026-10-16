# Directional quantity repair — 15 October 2026

**Local engineering checks pass; integration and research completion remain open.** This repair extends the clean quantity candidate `b12812ac4b652aac01d179ab66f1bc963167ace4`. It does not alter that closed candidate, the original dirty checkout, its diagnostic/scorer, old evidence or research gates.

## Problem and repair

The existing scalar SET pattern treated `increase` and `decrease` as optional wording, allowing the final value to contradict the direction. For example, with a 2 mm wall, `decrease wall thickness three mm` could propose a 3 mm wall. Explicit TO requests could also contradict their verb; zero or sub-resolution BY deltas could claim a directional change while storing the same value.

The repair distinguishes the verb and relation. Increase/decrease requests require explicit TO for an absolute target or BY for a delta. The result is checked against the original project value after conversion to the stored numeric representation. An ambiguous direction, opposite-direction result or unchanged stored result produces clarification and no candidate. Existing SET requests can still intentionally retain the same value. Existing manufacturing and project validators remain authoritative.

| Flaw | Cause | Severity | Implemented repair | Evidence |
|---|---|---|---|---|
| Ambiguous directional quantity becomes SET | Optional relation loses TO/BY distinction | High | Require explicit TO/BY for directional verbs | Adversarial ambiguity cases |
| “Decrease” can enlarge a feature | Verb discarded before canonical SET | High | Compare target against immutable baseline | Both direction contradictions tested |
| Tiny or zero delta claims a change | Decimal result can round to the same stored float | Medium | Require a strict stored-value change for increase/decrease | Zero and sub-resolution cases |
| One bad clause could coexist with valid edits | Partial interpretation is unsafe | High | Existing atomic refusal path remains in force | Mixed valid/contradictory request produces no candidate |

## Results and retained failures

- Baseline: 22 new cases, 14 failures and 8 passes. One failure was an invalid expected-success fixture: the 1 mm wall violated the unchanged FDM profile. The raw attempt and original test source are retained; it is not counted as a parser defect. Other failures include status differences as well as incorrect/no-change proposals; do not call all failures unsafe acceptance.
- Corrected control: use a supported 1.5 mm target. No baseline rerun was performed.
- Candidate: **111/111 tests pass**, comprising 22 directional cases and 89 existing quantity/conversation cases. No skips. Ruff passes on the changed production module and new test file.
- Candidate test execution: about 1.22 seconds wall time; child peak RSS 66.09 MiB. These are execution receipts, not a speed comparison. Baseline and candidate include different case counts, so their timings cannot measure speedup.
- All commands were parser-only, sequential and guarded at 20 seconds / 96 MiB child RSS. No dependency installation, native CAD, full suite, hosted CI, model training, provider call or protected evaluation ran.

The parent quantity candidate reports 14/20 exact valid intents versus the earlier 11/20 on already observed authored cases. This session did not rerun that diagnostic or establish a new generalization result. Its source-bound improvement remains a development result, and its runtime-speedup claim remains inconclusive.

## Scope and remaining work

This is a correctness repair to C02/C04, not a complete implementation of multi-clause semantics or negation. Remaining language work includes fragmented clauses, informal wording, preservation/negation, correction semantics and history resolution. Final-feature geometry, independent task labels/comparators, physical measurement and intended-user evidence remain open.

The research successor remains Checkpoint 1 BLOCKED. No novel learned mechanism or scientific advantage has been demonstrated. The user request's contribution gate is unchanged; this narrowly scoped maintenance fixes existing product behavior.

Full regression, installed-package/native verification, integration and release remain unexecuted. Heavy-work admission failed at 98.30 and 133.30 MiB free-plus-speculative memory, with increasing pageouts. A local branch can retain this candidate without changing either existing checkout or publishing anything.

## Reproduce and inspect

`candidate.patch` applies to the exact parent candidate. `candidate/core/conversational_parser.py` and `candidate/tests/test_directional_quantities.py` retain the verified files. `baseline.json`, `baseline.xml`, `baseline_test_directional_quantities.py` and `deviations.json` retain the earlier failure. `candidate-1.json`, `candidate-1.xml` and `lint.json` identify executed commands and source hashes.

In an admitted environment at the candidate source, run the three explicit parser test files: `tests/test_directional_quantities.py`, `tests/test_conversation_quantities.py`, `tests/test_conversational_parser.py`. Do not broaden to native or full suites without resource admission. The working snapshot used for these checks was `/tmp/neurocad-directional-20261015`; it is a same-host source copy, not independent reproduction.
