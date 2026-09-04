# NeuroCAD S3 external benchmark adapters — v0

Status: **PRE-FREEZE / PROMPT-ONLY / NOT_EVALUATED / NOT_AUTHORIZED**

This registry materializes two external-source adapter paths required by `THE-BU1LD/NeuroCAD#36`. It does **not** import held-out outcomes, create a final benchmark, evaluate NeuroCAD, or change the historical typed-parser falsification.

## Adapter A — CADTestBench

- source project: `dimitrismallis/CADTestBench`
- pinned source-code revision: `e29283cc61db7329039d95b429766a50bfd37f89`
- repository license: MIT
- external benchmark shape: prompt/test benchmark for text-to-CAD; prompt-only exports may be adapted here
- accepted prompt fields: exactly one of `prompt`, `abstract_prompt`, `detailed_prompt`
- accepted ID fields: exactly one of `sample_id`, `id`
- output category: `external_unmapped`
- output status: `CANDIDATE_NOT_EVALUATED`

The adapter does not ingest CADTests, paper baseline outputs, pass/fail results, scores, model generations, or any other evaluation-bearing field. Those remain outside candidate-pool construction.

## Adapter B — CADGenBench

- source project: `huggingface/cadgenbench`
- pinned source-code revision: `33304cf771fc5639144b1df9611e347251052cf8`
- repository license: Apache-2.0
- external benchmark shape: CAD generation/editing benchmark; prompt/description-only exports may be adapted here
- accepted prompt fields: exactly one of `prompt`, `description`, `instruction`, `edit_request`
- accepted ID fields: exactly one of `sample_id`, `id`, `name`
- output category: `external_unmapped`
- output status: `CANDIDATE_NOT_EVALUATED`

The adapter intentionally does not load private ground truth, benchmark scores, submitted models, generated outputs, or leaderboard results.

## Fail-closed import contract

`research/s3/external_adapters.py` requires a prompt-only JSONL export. For every record it:

1. requires exactly one source ID and one allowed prompt field;
2. normalizes line endings/outer whitespace only and rejects empty/NUL-bearing text;
3. rejects duplicate source IDs;
4. rejects conservative outcome-bearing fields including `score`, `metrics`, `result`, `prediction`, `output`, `ground_truth`, `cadtest_results`, and related keys;
5. binds repository, pinned revision, SPDX license, source ID, prompt field, and normalized prompt into a canonical SHA-256 receipt;
6. emits only `external_unmapped` / `CANDIDATE_NOT_EVALUATED` records;
7. refuses to overwrite an existing adapted output file.

Example, after independently producing a **prompt-only** source export without results:

```bash
python research/s3/external_adapters.py \
  --source cadtestbench \
  --input /path/to/cadtestbench-prompts-only.jsonl \
  --output /new/path/cadtestbench-s3-candidates.jsonl
```

and equivalently with `--source cadgenbench`.

## Scientific boundary

These adapters establish provenance-bearing ingestion plumbing only. They do not authorize final selection or evaluation. External records remain unmapped until a separate pre-outcome taxonomy mapping rule is frozen. Final inclusion/exclusion, deduplication, split membership, exact data-file digests, model/provider identities, baseline families, hypotheses/ablations, metrics/seeds/falsifiers, and an execution-authorization hash must still be frozen before held-out outcome access.

No benchmark result was inspected to choose these sources or implement these adapters.
