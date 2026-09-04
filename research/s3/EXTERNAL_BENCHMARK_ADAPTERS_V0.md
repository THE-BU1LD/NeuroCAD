# NeuroCAD S3 external benchmark adapters — v0

Status: **PRE-FREEZE / PROMPT-ONLY / NOT_EVALUATED / NOT_AUTHORIZED**

This registry materializes two external-source adapter paths required by `THE-BU1LD/NeuroCAD#36`. It does **not** import held-out outcomes, create a final benchmark, evaluate NeuroCAD, or change the historical typed-parser falsification.

## Adapter A — CADTestBench

- source code: `dimitrismallis/CADTestBench@e29283cc61db7329039d95b429766a50bfd37f89` (MIT)
- canonical public dataset: `dimitrismallis/CADTestBench@2b9a4a972d142d2bc634d072e9d4485f171ced06` (MIT)
- public prompt table `samples/abstract.parquet`: SHA-256 `67a5779bc5114ce4db6bc9be89bf22c25e707bc83e7431214cddfac23f980536`, 17,545 bytes
- public prompt table `samples/detailed.parquet`: SHA-256 `76b2d20def7946e1e3216b72a8acb83825c489c373b23ac514b77885ae275b37`, 33,726 bytes
- accepted prompt fields: exactly one of `prompt`, `abstract_prompt`, `detailed_prompt`
- accepted ID fields: exactly one of `sample_id`, `id`
- output category/status: `external_unmapped` / `CANDIDATE_NOT_EVALUATED`

The two SHA-256 values above are the Git-LFS object identities recorded by the frozen dataset commit for the two `samples/*` Parquet files. The adapter does not ingest the separate `cadtests/*` files, paper baseline outputs, pass/fail results, scores, model generations, or any other evaluation-bearing field.

## Adapter B — CADGenBench

- source code: `huggingface/cadgenbench@33304cf771fc5639144b1df9611e347251052cf8` (Apache-2.0)
- canonical public input dataset: `HuggingAI4Engineering/cadgenbench-data@569ea565cef25ee690e39bf89941f940027633d6` (ODC-By-1.0)
- dataset boundary: public fixture inputs only (`description.yaml`, drawings and, for editing, the starting solid/instruction); private ground truth lives in a separate repository and is outside this adapter
- accepted prompt fields: exactly one of `prompt`, `description`, `instruction`, `edit_request`
- accepted ID fields: exactly one of `sample_id`, `id`, `name`
- output category/status: `external_unmapped` / `CANDIDATE_NOT_EVALUATED`

The pinned dataset revision is content-addressed and identifies the full public fixture tree after the unused `category` field was removed. Later public-dataset commits only changed dataset-card/leaderboard prose, so this data-bearing revision is used deliberately. The adapter never loads the private ground-truth repository, benchmark scores, submitted models, generated outputs, or leaderboard results.

## Fail-closed import contract

`research/s3/external_adapters.py` requires a prompt-only JSONL export. For every record it:

1. requires exactly one source ID and one allowed prompt field;
2. normalizes line endings/outer whitespace only and rejects empty/NUL-bearing text;
3. rejects duplicate source IDs;
4. rejects conservative outcome-bearing fields including `score`, `metrics`, `result`, `prediction`, `output`, `ground_truth`, `cadtest_results`, and related keys;
5. binds source-code repository/revision/license **and** public-dataset repository/revision/license into a canonical dataset receipt;
6. for CADTestBench, additionally binds the exact SHA-256/size identities of both public prompt Parquet files;
7. hashes the exact input JSONL bytes and binds that `source_export_sha256` into every adapted record;
8. binds source ID, prompt field and normalized prompt into a canonical row SHA-256;
9. emits only `external_unmapped` / `CANDIDATE_NOT_EVALUATED` records;
10. refuses to overwrite an existing adapted output file.

Example, after independently producing a **prompt-only** source export without results:

```bash
python research/s3/external_adapters.py \
  --source cadtestbench \
  --input /path/to/cadtestbench-prompts-only.jsonl \
  --output /new/path/cadtestbench-s3-candidates.jsonl
```

and equivalently with `--source cadgenbench`.

## Scientific boundary

These adapters establish provenance-bearing ingestion plumbing only. They do not authorize final selection or evaluation. External records remain unmapped until a separate pre-outcome taxonomy mapping rule is frozen. Final inclusion/exclusion, deduplication, split membership, model/provider identities, baseline families, hypotheses/ablations, metrics/seeds/falsifiers, and an execution-authorization hash must still be frozen before held-out outcome access.

No benchmark result was inspected to choose these sources or implement these adapters. The historical `VALIDATION_DOMINANT` / typed-parser-mechanism falsification remains unchanged.
