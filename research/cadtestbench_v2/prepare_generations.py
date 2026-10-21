"""Prepare V2 cohorts while converting every per-prompt exception to failure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cadquery_export import export_cadquery_python
from research.cadtestbench_v1.prepare_generations import (
    _read_rows,
    _rejection_source,
    _safe_sample_id,
    _sha256,
)
from text_to_cad import TextToCAD

STUDY_ID = "NC-CADTESTBENCH-V2"


def _exception_reason(exc: Exception) -> str:
    return f"NEUROCAD_FRONTEND_EXCEPTION: {type(exc).__name__}: {exc}"


def prepare_partition(
    *,
    dataset_root: Path,
    partition: str,
    output_root: Path,
    expected_rows: int,
) -> dict[str, Any]:
    parquet = dataset_root / "samples" / f"{partition}.parquet"
    if not parquet.is_file():
        raise FileNotFoundError(f"missing pinned CADTestBench table: {parquet}")
    rows = _read_rows(parquet)
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} {partition} rows, found {len(rows)}")

    run_root = output_root / partition
    if run_root.exists():
        raise FileExistsError(f"refusing to replace generation directory: {run_root}")
    models_root = run_root / "generated_models"
    models_root.mkdir(parents=True)

    generator = TextToCAD()
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    accepted = 0
    rejected = 0
    frontend_exceptions = 0
    for row in rows:
        sample_id = _safe_sample_id(row.get("sample_id"))
        if sample_id in seen:
            raise ValueError(f"duplicate sample_id in {partition}: {sample_id}")
        seen.add(sample_id)
        prompt = row.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"sample {sample_id} has no non-empty prompt")

        sample_dir = models_root / sample_id
        sample_dir.mkdir()
        source_path = sample_dir / "gpt_generated.py"
        reason: str | None
        try:
            document = generator.build(prompt)
        # The successor's frozen intervention is to convert every record-local
        # failure into an evaluator-visible failure rather than aborting the cohort.
        except Exception as exc:  # noqa: BLE001
            reason = _exception_reason(exc)
            source_path.write_text(_rejection_source(reason), encoding="utf-8", newline="\n")
            status = "rejected"
            rejected += 1
            frontend_exceptions += 1
        else:
            if document.program is None or not document.validation.valid:
                errors = list(document.validation.errors)
                reason = "NEUROCAD_REJECTED: " + ("; ".join(errors) if errors else "no canonical program")
                source_path.write_text(_rejection_source(reason), encoding="utf-8", newline="\n")
                status = "rejected"
                rejected += 1
            else:
                try:
                    export_cadquery_python(document.program, source_path)
                    status = "accepted"
                    accepted += 1
                    reason = None
                except Exception as exc:  # noqa: BLE001
                    reason = f"NEUROCAD_EXPORT_EXCEPTION: {type(exc).__name__}: {exc}"
                    source_path.write_text(_rejection_source(reason), encoding="utf-8", newline="\n")
                    status = "rejected"
                    rejected += 1
        records.append(
            {
                "sample_id": sample_id,
                "status": status,
                "reason": reason,
                "generated_source_sha256": _sha256(source_path),
            }
        )

    manifest = {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "partition": partition,
        "dataset_path": str(parquet),
        "dataset_sha256": _sha256(parquet),
        "rows": len(rows),
        "accepted": accepted,
        "rejected": rejected,
        "frontend_exceptions": frontend_exceptions,
        "records": records,
    }
    (run_root / "generation_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
