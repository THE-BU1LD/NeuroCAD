# Conversational enclosure parser

The parser turns an edit request and an existing enclosure project into a
reviewable proposal. It preserves the original text, source evidence, baseline
context hash, proposed actions, protected fields and unresolved questions.
It never changes the original project or executes generated code.

## Local use

```bash
neurocad enclosure understand docs/examples/conversation/baseline.json \
  "please make the wals like 3mm thick and dont move the outside and dont lose that hole" \
  -o proposal.json
```

Read the proposal before explicitly applying it to a new project file:

```bash
neurocad enclosure apply-proposal docs/examples/conversation/baseline.json \
  proposal.json --confirm -o reviewed.json
neurocad enclosure build reviewed.json --output-dir reviewed-build
```

The local path supports wall/floor/lid dimensions, corner radius, mixed-unit
enclosure dimensions, documented canonical feature edits, selected spelling
errors, filler, multi-clause requests, preservation statements and explicit
`actually` self-corrections. It is a conservative grammar, not a general language
model. Unrecognized clauses block the entire candidate; partial changes are not
applied. Missing units, vague changes, conflicting values and ambiguous cutout
references produce clarification. Invalid specifications are rejected.

`keep the outside dimensions` protects outer dimensions. `keep the outside`
also protects corner radius, cutouts, vents and lid. These are typed specification
checks; equal fields do not independently establish exact B-Rep equivalence.

## Model-backed interpretation

An explicitly configured Chat Completions provider handles broader wording,
number words, relative edits and contextual references by proposing the same
bounded canonical edits. It receives the current project, feature IDs, face-local
coordinate convention and optional recent messages. It must account for the
source text and ask questions rather than invent parameters. A strict JSON schema
constrains structure; it does not guarantee semantic understanding.

```bash
export NEUROCAD_LANGUAGE_API_KEY='your-provider-key'
neurocad enclosure understand docs/examples/conversation/baseline.json \
  "nah make those walls three millimeters, leave the outside and power hole alone" \
  --provider-url https://api.openai.com/v1/chat/completions \
  --model YOUR_SCHEMA_CAPABLE_MODEL -o model-proposal.json
```

For a compatible local service, supply its full loopback endpoint, for example
`http://127.0.0.1:11434/v1/chat/completions`, and an installed schema-capable model.
Compatibility must be checked with that service; unsupported schemas fail
explicitly. The key is optional for local services. No automatic provider calls
occur in the local mode. No model or paid service is silently selected.

`--history history.json` accepts a JSON array of at most ten messages, each at
most 2048 characters. It is model context, not a separate source of authorization.
Provider metadata records requested/returned model IDs, response ID, recent
messages and request hash, without the API key. Source offsets use Python Unicode
characters, not byte or UTF-16 offsets.

Transport rejects redirects, non-HTTPS remote endpoints, oversized responses,
invalid JSON, refusals and truncated completions. A socket timeout is not a whole
command deadline. Canonical actions pass the existing enclosure validator and
preservation checks. Every successful result still requires explicit review.
Applying a saved proposal revalidates its actions and candidate and rejects a
changed project baseline or altered candidate.

## Scope and evidence

This is an existing-enclosure edit workflow. It does not implement arbitrary new
CAD families, unconstrained design synthesis, assemblies, simulation inference or
general geometric proofs. Use `enclosure interpret` for the existing supported
new-enclosure clause grammar. Actions are validated in sequence; coordinated
edits requiring invalid intermediate specifications need a different contract.

The shipped evaluation is a constructed regression set, not human-reviewed NLP
accuracy or held-out evidence of general understanding. Provider unit tests use
controlled responses to verify the protocol. A real configured model must still
be evaluated on independently reviewed messy requests before claiming broad
language accuracy. No live provider was configured in the implementation
environment.

```bash
python scripts/evaluate_conversational_parser.py \
  --output-dir conversational-evaluation
```
