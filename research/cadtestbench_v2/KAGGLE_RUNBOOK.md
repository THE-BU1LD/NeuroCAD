# NC-CADTESTBENCH-V2 Kaggle runbook

## Ready artifact

- Upload `neurocad-nc-cadtestbench-v2.ipynb` as a new **private** Kaggle notebook.
- Notebook SHA-256: `3ce9cb4acc36ae860b3cc2093465df1d983fcd3b91263cb207e525ecc66fa730`
- Notebook size: 728,347 bytes (below Kaggle's 1 MiB importer limit).
- Internet: enabled, only for the pinned Python environment and pinned dataset revision.
- Accelerator: none. This deterministic CadQuery B-Rep/CADTest workload is CPU-bound; assigning a GPU would not strengthen the scientific evidence.
- Run mode: **Save Version → Save & Run All**. Do not edit notebook cells after upload.

## Frozen identities

- NeuroCAD implementation commit: `c3050927eac1a4030cdc190de8606da196e5d73f`
- NeuroCAD source archive SHA-256: `6a7d9180a7eb63011c1a9d12cbda50d41e4622d51a0a9b818fa2307df03a74a9`
- CADTestBench evaluator commit: `e29283cc61db7329039d95b429766a50bfd37f89`
- Evaluator archive SHA-256: `70e1881242984ac10bff800838e1c32b003a4f0a4a45b8cf9531d0445153b5e5`
- CADTestBench dataset commit: `2b9a4a972d142d2bc634d072e9d4485f171ced06`
- Locked environment SHA-256: `31cf03a57f39be995e0958e8b6cc845a5de83f60844e0694446e470378c3145c`

The notebook verifies every embedded payload and all four downloaded Parquet files before execution.

## Acceptance checklist

1. The setup cell prints the four payload hashes.
2. The environment cell prints `FROZEN_ENVIRONMENT_INSTALLED` and `FROZEN_DATASET_VERIFIED`.
3. The run cell prints `FROZEN_EXECUTION_RETURN_CODE=0`.
4. Both generation manifests report exactly 200 rows; accepted plus rejected equals 200 for each partition.
5. Both official evaluator commands return zero and retain `evaluation_summary.json`.
6. The package cell prints `NC_CADTESTBENCH_V2_COMPLETE`, bundle bytes, and bundle SHA-256.
7. Download `neurocad_nc_cadtestbench_v2_results.tar.gz`; independently verify its printed SHA-256 before interpreting metrics.

Any missing marker, hash mismatch, exception, nonzero return code, missing record, or missing summary is a retained failed/inconclusive execution—not a scientific result.

## Known flaws and controls

| Flaw | Cause | Severity | Control/fix | Required proof |
|---|---|---:|---|---|
| V1 aborted on one unsupported feature count | A record-local frontend exception escaped the cohort loop | High | V2 converts every record-local frontend/export exception to a deterministic evaluator-visible failure | Unit test plus 200/200 accounting in both generation manifests |
| V2 follows exposure to public prompts in failed V1 | V1 reached prompt loading before aborting | High | Label V2 descriptive; do not present it as unopened confirmation | Contract, execution manifest, and paper wording retain this boundary |
| Public benchmark is not the protected independent external study | CADTestBench is public and its authorship is external, but this successor was built for it | High | Keep the historical protected study and falsified predecessor claim unchanged | No claim that V2 rehabilitates the historical causal hypothesis |
| Local machine failed the 512 MiB admission floor | Insufficient free plus speculative memory | High | Execute the immutable payload on Kaggle CPU | Hosted receipt and downloaded raw artifact |
| Kaggle success status alone is not evidence | UI completion does not establish artifact identity or metric validity | High | Download and independently hash/inspect raw results | Bundle hash, manifests, official summaries, and command receipts |

## Stop rules

- Do not repair, retry, omit, or regenerate any individual record within this V2 execution.
- Do not alter the evaluator, dataset, environment lock, denominator, or metrics after outcomes are visible.
- Preserve every Kaggle version and failure receipt.
- A defect discovered after execution requires a documented successor version; V2 remains immutable.
