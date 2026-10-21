"""Prepare one full NeuroCAD generation cohort for pinned CADTestBench data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from core.cadquery_export import export_cadquery_python
from text_to_cad import TextToCAD


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_sample_id(raw: object) -> str:
    value = str(raw)
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in value):
        raise ValueError(f"unsafe sample_id {value!r}")
    return value


def _rejection_source(reason: str) -> str:
    safe_reason = json.dumps(reason, ensure_ascii=True)
    return "\n".join(
        [
            "# neurocad-cadquery-source-v1",
            "# deterministic fail-closed rejection retained for evaluation",
            f"raise RuntimeError({safe_reason})",
            "",
        ]
    )


def _read_rows(parquet: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "pyarrow is required to read the pinned CADTestBench parquet files"
        ) from exc
    return pq.read_table(parquet).to_pylist()


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
        document = generator.build(prompt)
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
            except ValueError as exc:
                reason = f"NEUROCAD_EXPORT_REJECTED: {exc}"
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
        "study_id": "NC-CADTESTBENCH-V1",
        "partition": partition,
        "dataset_path": str(parquet),
        "dataset_sha256": _sha256(parquet),
        "rows": len(rows),
        "accepted": accepted,
        "rejected": rejected,
        "outcomes_observed": False,
        "records": records,
    }
    manifest_path = run_root / "generation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--partition", choices=("abstract", "detailed", "both"), default="both")
    parser.add_argument("--expected-rows", type=int, default=200)
    args = parser.parse_args()
    partitions = ("abstract", "detailed") if args.partition == "both" else (args.partition,)
    summaries = [
        prepare_partition(
            dataset_root=args.dataset_root,
            partition=partition,
            output_root=args.output_root,
            expected_rows=args.expected_rows,
        )
        for partition in partitions
    ]
    print(json.dumps(summaries, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
