# Language interpretation evaluation

The runner measures whether interpreted edits match annotated intent. A valid
candidate can still have the wrong dimensions or omit a preservation requirement.
It supports the local parser and an explicitly configured Chat Completions model.
It never applies proposals or changes the supplied projects.

## Development challenge

```bash
neurocad-language-eval docs/examples/conversation/language-challenge-v1.json --output-dir language-local
```

From a checkout, `python -m core.language_evaluation` is equivalent. Exit code 0
means every annotated outcome matched; exit code 2 means a mismatch or setup error.
The supplied challenge has 32 distinct assistant-authored development prompts,
20 valid intents and 12 requests requiring clarification, rejection or unsupported
responses. It covers two enclosure contexts, number words, relative edits,
fragments, negation, corrections, references, history, radius/diameter, preservation,
impossible walls and unsupported physics guarantees. The implementation agent
authored the labels. This is not independent, human-adjudicated, held-out or
confirmatory evidence. The parser is not tuned against this set during introduction.
Retain poor scores; do not weaken annotations or remove hard cases to improve them.

## Live model evaluation

```bash
neurocad-language-eval docs/examples/conversation/language-challenge-v1.json \
  --provider-url https://YOUR_PROVIDER/v1/chat/completions \
  --model YOUR_SCHEMA_CAPABLE_MODEL --timeout-seconds 30 \
  --output-dir language-model
```

Set `NEUROCAD_LANGUAGE_API_KEY` when authentication is required. Keys, endpoint
URLs and exception messages are not saved. Model IDs and proposal content are
retained; review that content before sharing it. HTTP is allowed only for loopback.
An Ollama model can use `http://127.0.0.1:11434/v1/chat/completions` if it supports
the requested strict JSON schema. A service on your laptop is not automatically
reachable from a remote workspace. No live model results accompany this release.

There is one request per case, with original source, current project and optional
history. Labels never enter model context. There are no retries, adaptive repairs
or alternate prompts. Calls can incur provider charges. The socket timeout is not
a guaranteed total wall-clock budget; a 32-case run can take roughly 32 timeout
intervals plus processing. Local parsing does not use conversation history.

## Annotation format

The root has exactly `version`, `provenance`, `projects`, `cases`. Version is
`neurocad-language-challenge-v1`. Projects are embedded ordinary NeuroCAD project
objects keyed by context labels. Each case has the following fields:

| Field | Meaning |
| --- | --- |
| id | Unique case identifier |
| category | Diagnostic group |
| project | Embedded context label |
| source | Original unnormalized request |
| history | Up to ten preceding messages |
| expected.status | proposal, clarification, unsupported, rejected or unchanged |
| expected.spec | Complete valid expected spec for proposals; null otherwise |
| expected.preserve | Required protection fields or existing feature IDs |

Specs are normalized then compared with exact JSON numeric equality. Annotators
must use the declared unit arithmetic; no tolerance is silently introduced.
Container protection implies its child protection: `cutouts` covers a particular
cutout, and `lid` covers a lid field. Unrelated changes fail semantic scoring.

## Evidence and endpoints

All annotations are validated before any inference or output-directory creation.
The new output directory contains the exact challenge and a preoutcome receipt
with dataset, scorer, parser and provider-adapter hashes. Each completed outcome
is flushed to `results.jsonl`, retaining failures if interrupted. `summary.json`
is written only when every case finishes. Existing destinations are refused.

- Semantic exact rate divides correctly resolved full intents by all valid-intent
  cases. Blocking a valid request is a miss. Wrong fields, missing protection and
  stale context fail.
- Fail-closed rate divides non-proposal intents with no candidate by all
  non-proposal cases. Transport errors are failures, not successful rejection.
  Exact clarification/rejection status is scored separately.

These rates are not averaged into a headline score. Unsafe acceptances, wrong
candidates, provider errors, per-category results and baseline immutability are
explicit. Controlled provider tests are not live model accuracy evidence.
`external-annotated` provenance is only a declaration; the summary always records
`independent_authorship_verified=false`. A confirmatory study still needs separate
authorship/adjudication, frozen splits, model configuration, source commit,
dependency identities and the existing external evaluation protocol. This runner
does not authorize that study or close its gate.
