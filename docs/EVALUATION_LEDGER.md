# Evaluation ledger v2

The ledger records a predeclared schedule and one outcome per scheduled ID for ordinary adapter failures. Its offline audit detects missing or changed evidence and recomputes the summary. It does not execute a benchmark, establish independent labels, authenticate a producer, or grant scientific admission.

The existing `valid_for_inference` field is retained for compatibility. It means only that the declared ledger has persisted, internally consistent, nonzero endpoint counts for every scheduled sample. A valid scientific inference additionally requires the frozen protocol, correct independent scoring, source/data provenance, appropriate statistics and the separate research gates.

## Contract and process

1. Consume at most 100,001 schedule items; admit 1–100,000 unique, case-insensitive safe IDs. Reject a string schedule, unsafe/reserved IDs and duplicates before creating the output directory. Iterator execution itself remains caller-controlled and can block; this is not a timeout sandbox.
2. Copy and validate source/dataset revision identities (40 or 64 lowercase hexadecimal characters), plus dataset-manifest and protocol SHA256 identities (exactly 64). Format validation does not prove authenticity.
3. Refuse an existing output directory. Atomically publish the v2 manifest before the first load, and keep its intended UTF-8 byte hash in memory.
4. For each scheduled ID, invoke the admitted loader and executor. Retain ordinary `Exception` failures, including custom adapter errors and assertions, as `load_error` or `execution_error`. Keep the exception class, not potentially private exception text. The admitted adapter must separately retain its diagnostic/raw artifacts where the protocol requires them.
5. Accept exactly three metric fields: boolean `passed`, integer `requirements_passed`, integer `requirements_total`. Require `0 <= passed_count <= total <= 2**63 - 1`. A completion pass requires a positive total and all requirements satisfied. Zero-total samples remain visibly unavailable. Other task-completion constraints may cause `passed=False` despite all requirements being satisfied.
6. Atomically publish each outcome without overwriting. Record its intended serialized hash. A failed outcome write is retained in the eventual summary; it prevents inference admission. No callback error removes an ID from the completion denominator.
7. Compare the retained manifest/outcome bytes with those intended hashes before writing the summary. Changed, missing or symlink evidence produces `INTEGRITY_ERROR`. Compute endpoint totals in one accounting pass and publish the summary without overwrite.
8. `KeyboardInterrupt`, `SystemExit`, `MemoryError` and manifest/summary publication errors propagate. A manifest without a summary is incomplete. This module never silently resumes or reruns scientific cases.

## Read-only audit

From the candidate checkout, with its Python environment:

```sh
python -m core.evaluation_ledger /absolute/path/to/run \
  --manifest-sha256 EXTERNALLY_RETAINED_MANIFEST_SHA256 \
  --summary-sha256 EXTERNALLY_RETAINED_SUMMARY_SHA256
```

The hashes are optional for an internal-consistency check, but a trusted external record is needed to anchor provenance. A party able to replace the whole ledger can create another self-consistent ledger; unanchored hashes cannot detect that. This reader is intended for a quiescent evidence directory, not a hostile process concurrently changing files.

The audit reads no more than 64 MiB per top-level document and 64 KiB per outcome. It rejects duplicate JSON keys, excessive nesting, non-finite numbers, unsupported schemas and non-regular/symlink files. It requires exactly one ordered outcome for every scheduled ID, checks canonical outcome byte hashes, and independently recomputes totals and the completion status. It never invokes loader/executor callbacks or changes run files.

Exit 0 means integrity checks passed, including for honestly retained execution failures. It does **not** mean the model passed or that `valid_for_inference` is true. Exit 2 means the audit failed. Inspect both booleans and the recomputed status. Legacy v1 artifacts are preserved and rejected as unsupported by this v2 reader; they are not silently migrated.

## Efficiency and limits

Schedule admission is bounded even for an infinite iterator that continues yielding. Accounting is O(N) with one pass and no auxiliary filtered metric lists. Total persistence/audit work is O(N + B), where B is serialized evidence size, and memory is O(N + J), where J is the largest admitted JSON document. Checksums add a read of retained artifacts; durability still uses atomic writes and fsync. No latency improvement or 100,000-case scale performance has been measured. Run the cost profile on admitted resources before a large study.

Fault injection establishes behavior for the tested errors; it does not prove that the executor's metrics are correct, that hardware never fails, or that CAD predictions are physically accurate. Adapter isolation, external evidence, protected evaluation and exact-source full/native/install checks remain separate gates.
