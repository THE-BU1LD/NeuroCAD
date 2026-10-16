# Quantity maintenance and efficiency result — 15 October 2026

Local product candidate from main `e1c09a80a58b0d883be9091a1bd5cb8b9b47aea1`, branch `codex/conversation-quantities-20261015`. Bounded engineering tests pass; performance benefit remains inconclusive. This work does not implement the blocked research successor or change the historical scientific dispositions.

## Completed work

| Flaw | Cause | Repair | Evidence |
|---|---|---|---|
| Number words refused | Numeric-only quantity grammar | Complete-clause zero–ninety-nine and spoken decimal parsing | New regression suite; language-11 recovered |
| Relative requests refused | No explicit baseline-relative operator | Decimal addition/subtraction against immutable baseline; repeated mixed/relative assignments refused | Exact 0.3 + 0.1 case, context/replay/conflict checks; language-12 recovered |
| Hole radius wording refused | Storage expects diameter | Resolve one existing circular ID and explicitly double radius | Position/identity, case ambiguity and noncircular checks; language-20 recovered |
| Repeated grammar construction and typo passes | Six scalar patterns rebuilt in loop; six substitutions per clause | Precompile patterns, combined scalar dispatch, single typo pass | Source diff; paired timing and five old-case candidate/preservation/hash parity checks |
| CLI exit test required a capability to remain broken | Case-index dependency | Test incomplete and invalid-integrity summaries explicitly | Real success/output path retained; two negative exit branches exercised |

48 authored quantity cases: corrected baseline **20 failed / 28 passed**; candidate **48 passed** within the **170-test focused suite**. The production source was unchanged after that suite; a later test-only closure-binding lint repair passed its affected test. Ruff passes on all four changed source/test files. Scoped mypy (`--follow-imports=skip`) passes on the two production modules. Full package, installed release and native verification are not complete.

## Development diagnostic

Same retained dataset bytes and unchanged scorer: exact valid intents **11/20 → 14/20**; complete expected outcomes **21/32 → 24/32**. Fail-closed rejection **12/12**, unsafe acceptance **0**, wrong candidates **0**, provider errors **0**, regressions **0**. Exit code remains **2**, correctly representing unresolved cases.

These already observed assistant-authored prompts were explicitly used to motivate the repairs. The copied challenge description's historical “no parser tuning within this sprint” language refers to its originating sprint, not this maintenance session. This replay is in-sample development evidence, not a protected test, independent comparison, SOTA result or efficacy estimate. The old receipt used Python 3.12.14; this local run used Python 3.14.0. No statistical superiority claim follows.

Remaining valid requests: fragmented edits (2), informal context, scalar preservation/negation, negation correction, and history resolution (6 total). Two safe rejections still use `unsupported` where the annotation expects `clarification`. See `diagnostic-difference.json` for exact IDs and `diagnostic-run/results.jsonl` for all outcomes.

## Efficiency measurement

Five existing supported requests, five alternating base/candidate rounds, 100 repetitions per request per round. All five preserved identical candidates, preserved-field declarations and baseline hashes. Two newly supported requests are timed separately in the raw rows and excluded from the comparable aggregate.

Median of per-round mean latency: base **0.614159 ms**, candidate **0.575714 ms** (6.26% lower). Candidate is faster in only **1 of 5 paired rounds**; the host is under memory pressure and timing varies substantially. Therefore **no reliable runtime speedup is established**. The code removes repeated grammar work, but Decimal arithmetic and unchanged project validation still cost time. Retain all timings; no favorable-result rerun. The benchmark process peak RSS was 50.66 MiB, with no separately measured baseline/candidate memory advantage. No throughput, cold-start or native-CAD speed claim.

## Retained failures and execution deviations

- Initial baseline: 48 fixture setup errors (required profile omitted), not parser failures. One prospective fixture-recovery allowance preserved this attempt and produced the valid baseline above.
- Candidate attempt 1 accidentally selected native workbench tests, contrary to the zero-native scope. The 30-second process-group guard terminated it. No complete result or native success is claimed. A subsequent process check found no remaining OpenSCAD/pytest/guard worker. The reported RSS tracks the guarded Python child, not all transient descendants. All later runs exclude the workbench module.
- Candidate attempt 2: 169 passed / 1 failed because the CLI exit test treated number-word support as a failure. Candidate attempt 3: 170 passed after decoupling that unit test from a specific grammar limitation.
- Lint attempt 1: two constant-list warnings. Attempt 2: loop-closure binding warning in the test. A separately recorded one-lint/one-affected-test repair allowance fixed the latter without changing production source or repeating diagnostic/timing outcomes.

Original contract and all addenda/attempt logs remain intact. 58 protected files match their pre-session hashes. The dataset, scorer, original product checkout, pending output-geometry candidate `941eed7`, and immutable alpha are unchanged by production edits in this isolated worktree. The shared research owner independently closed its admission review with Checkpoint 1 still blocked; this maintenance does not advance that checkpoint.

## Remaining gates

- C02: local bounded implementation complete; independent prompts and integration evidence still open.
- C12: parser work reduced structurally; stable complete-path efficiency evidence still open.
- C03–C06: remaining language coverage requires separately bounded design/implementation and adversarial cases.
- Full/native/install checks require resource admission or the pending explicitly approved hosted path. No merge, push or release occurred here.
- Research novelty, protected evaluation, physical measurement, independent reproduction and intended-user evidence remain separate open gates.

## Reproduction and artifacts

Run the focused suite with an existing development environment:

```sh
python -m pytest -q tests/test_conversation_quantities.py tests/test_conversational_parser.py tests/test_language_evaluation.py tests/test_verified_intent.py
python -m ruff check core/conversation_quantities.py core/conversational_parser.py tests/test_conversation_quantities.py tests/test_language_evaluation.py
python -m mypy --follow-imports=skip core/conversation_quantities.py core/conversational_parser.py
```

`contract.json` and the two addenda define consumed budgets; do not silently restart them. Each guarded receipt stores command, source hashes, timing, RSS and exit code. `timings.json` retains every timing row. `integrity-audit.json` records preserved files. `SHA256SUMS.json` seals this local evidence package; the Git commit identifies final source.
