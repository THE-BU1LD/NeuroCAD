# NeuroCAD prompt challenge v1

This 24-case set was written during the 2026-09-08 audit after inspecting the
implementation. It is therefore **development evidence**, not independent or
confirmatory evidence. It was stored before its first execution and must remain
unchanged; revisions require a new filename/version and retained prior results.
Its SHA-256 is
`08325ac375bb1e337d0bb760fe2d86e3638e74e13a1df3857e781d046ac48b64`.

The set tests documented aliases, named dimensions, mixed units, unit words,
Unicode multiplication, singular features, and explicit rejection of incomplete,
unsupported, invalid, ambiguous, or lossy-character prompts. Cases are unique and
include development, validation, and test labels; the labels do not imply training.

Run once into a new output path:

```bash
python -m core.challenge \
  research/benchmarks/neurocad_prompt_challenge_v1.jsonl \
  /tmp/neurocad-prompt-challenge-v1-results.json
```
