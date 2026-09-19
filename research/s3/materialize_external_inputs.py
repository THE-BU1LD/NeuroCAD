"""Materialize prompt-only external S3 benchmark inputs from exact public dataset revisions.

This utility deliberately downloads only public input metadata needed to construct prompts.
It never downloads CADGenBench private ground truth, model outputs, scores, leaderboard
artifacts, or CADTest executable result records. Outputs are deterministic and non-overwriting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from research.s3.external_adapters import SOURCES, adapt_rows


RECEIPT_SCHEMA = "neurocad.s3.external-materialization.v1"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _normalize_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if "\x00" in value:
        raise ValueError(f"{field} must not contain NUL bytes")
    return value


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[int, str]:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    raw = path.read_bytes()
    return count, _sha256_bytes(raw)


def _write_json(path: Path, value: Mapping[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return _sha256_bytes(raw)


def _verify_artifact(path: Path, *, expected_sha256: str, expected_size: int) -> None:
    raw = path.read_bytes()
    actual_sha256 = _sha256_bytes(raw)
    if len(raw) != expected_size:
        raise ValueError(f"{path} size drift: expected {expected_size}, got {len(raw)}")
    if actual_sha256 != expected_sha256:
        raise ValueError(f"{path} sha256 drift: expected {expected_sha256}, got {actual_sha256}")


def _load_parquet_rows(path: Path, partition: str) -> list[dict[str, str]]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in materialization workflow
        raise RuntimeError("pyarrow is required for CADTestBench materialization") from exc

    table = pq.read_table(path, columns=["sample_id", "partition", "prompt"])
    rows = table.to_pylist()
    if len(rows) != 200:
        raise ValueError(f"{path} must contain exactly 200 sample rows; got {len(rows)}")

    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"{path} row {index} is not a mapping")
        source_partition = _normalize_text(row.get("partition"), f"{path} row {index} partition")
        if source_partition != partition:
            raise ValueError(
                f"{path} row {index} partition drift: expected {partition}, got {source_partition}"
            )
        sample_id = _normalize_text(row.get("sample_id"), f"{path} row {index} sample_id")
        if sample_id in seen:
            raise ValueError(f"{path} duplicate sample_id: {sample_id}")
        seen.add(sample_id)
        prompt = _normalize_text(row.get("prompt"), f"{path} row {index} prompt")
        output.append({"sample_id": f"{partition}:{sample_id}", "prompt": prompt})
    return output


def _materialize_cadtestbench(snapshot: Path, output_dir: Path) -> dict[str, Any]:
    spec = SOURCES["cadtestbench"]
    artifacts_by_path = {artifact.path: artifact for artifact in spec.dataset_artifacts}
    rows: list[dict[str, str]] = []
    verified_artifacts: list[dict[str, Any]] = []

    for partition in ("abstract", "detailed"):
        relative = f"samples/{partition}.parquet"
        artifact = artifacts_by_path[relative]
        source_path = snapshot / relative
        if not source_path.is_file():
            raise FileNotFoundError(f"missing pinned CADTestBench source artifact: {source_path}")
        _verify_artifact(
            source_path,
            expected_sha256=artifact.sha256,
            expected_size=artifact.size_bytes,
        )
        verified_artifacts.append(
            {"path": relative, "sha256": artifact.sha256, "size_bytes": artifact.size_bytes}
        )
        rows.extend(_load_parquet_rows(source_path, partition))

    if len(rows) != 400:
        raise ValueError(f"CADTestBench prompt universe must be exactly 400 rows; got {len(rows)}")

    raw_path = output_dir / "cadtestbench.prompt-only.jsonl"
    raw_count, raw_sha256 = _write_jsonl(raw_path, rows)
    adapted_rows = adapt_rows("cadtestbench", rows, source_export_sha256=raw_sha256)
    adapted_path = output_dir / "cadtestbench.adapted.jsonl"
    adapted_count, adapted_sha256 = _write_jsonl(adapted_path, adapted_rows)
    if adapted_count != raw_count:
        raise ValueError("CADTestBench adapter changed record count")

    return {
        "source": "cadtestbench",
        "dataset_repository": spec.dataset_repository,
        "dataset_revision": spec.dataset_revision,
        "dataset_license": spec.dataset_license_spdx,
        "verified_source_artifacts": verified_artifacts,
        "prompt_only_export": {
            "path": raw_path.name,
            "records": raw_count,
            "sha256": raw_sha256,
        },
        "adapted_export": {
            "path": adapted_path.name,
            "records": adapted_count,
            "sha256": adapted_sha256,
        },
    }


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in materialization workflow
        raise RuntimeError("PyYAML is required for CADGenBench materialization") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must decode to a mapping")
    return value


def _materialize_cadgenbench(snapshot: Path, output_dir: Path) -> dict[str, Any]:
    spec = SOURCES["cadgenbench"]
    fixture_dirs = sorted(
        (path for path in snapshot.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    )
    if not fixture_dirs:
        raise ValueError("CADGenBench snapshot contains no numeric fixture directories")

    rows: list[dict[str, str]] = []
    modality_ledger: list[dict[str, Any]] = []
    for fixture in fixture_dirs:
        description_path = fixture / "description.yaml"
        if not description_path.is_file():
            raise FileNotFoundError(f"missing public description.yaml for fixture {fixture.name}")
        record = _load_yaml_mapping(description_path)
        description = _normalize_text(record.get("description"), f"fixture {fixture.name} description")
        input_type = _normalize_text(record.get("input_type"), f"fixture {fixture.name} input_type")
        input_files = record.get("input_files")
        if not isinstance(input_files, list) or not input_files or not all(
            isinstance(item, str) and item.strip() for item in input_files
        ):
            raise ValueError(f"fixture {fixture.name} input_files must be a non-empty string list")

        edit_path = fixture / "edit_description.txt"
        if input_type == "text+step":
            if not edit_path.is_file():
                raise FileNotFoundError(f"editing fixture {fixture.name} missing edit_description.txt")
            edit_request = _normalize_text(
                edit_path.read_text(encoding="utf-8"), f"fixture {fixture.name} edit request"
            )
            prompt = f"{description}\n\nEdit request: {edit_request}"
            task_type = "editing"
        elif input_type == "text+image":
            if edit_path.exists():
                raise ValueError(f"generation fixture {fixture.name} unexpectedly has edit_description.txt")
            prompt = description
            task_type = "generation"
        else:
            raise ValueError(f"fixture {fixture.name} unsupported public input_type: {input_type}")

        rows.append({"sample_id": fixture.name, "prompt": prompt})
        modality_ledger.append(
            {
                "sample_id": fixture.name,
                "task_type": task_type,
                "input_type": input_type,
                "input_files": [str(item).strip() for item in input_files],
                "description_sha256": _sha256_bytes(description_path.read_bytes()),
                "edit_description_sha256": _sha256_bytes(edit_path.read_bytes()) if edit_path.is_file() else None,
                "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
            }
        )

    raw_path = output_dir / "cadgenbench.prompt-only.jsonl"
    raw_count, raw_sha256 = _write_jsonl(raw_path, rows)
    adapted_rows = adapt_rows("cadgenbench", rows, source_export_sha256=raw_sha256)
    adapted_path = output_dir / "cadgenbench.adapted.jsonl"
    adapted_count, adapted_sha256 = _write_jsonl(adapted_path, adapted_rows)
    if adapted_count != raw_count:
        raise ValueError("CADGenBench adapter changed record count")

    modality_path = output_dir / "cadgenbench.public-input-ledger.json"
    modality_sha256 = _write_json(
        modality_path,
        {
            "dataset_repository": spec.dataset_repository,
            "dataset_revision": spec.dataset_revision,
            "records": modality_ledger,
        },
    )

    return {
        "source": "cadgenbench",
        "dataset_repository": spec.dataset_repository,
        "dataset_revision": spec.dataset_revision,
        "dataset_license": spec.dataset_license_spdx,
        "private_ground_truth_repository_accessed": False,
        "download_scope": ["*/description.yaml", "*/edit_description.txt"],
        "prompt_only_export": {
            "path": raw_path.name,
            "records": raw_count,
            "sha256": raw_sha256,
        },
        "adapted_export": {
            "path": adapted_path.name,
            "records": adapted_count,
            "sha256": adapted_sha256,
        },
        "public_input_ledger": {
            "path": modality_path.name,
            "records": len(modality_ledger),
            "sha256": modality_sha256,
        },
    }


def _snapshot_download(repo_id: str, revision: str, allow_patterns: Sequence[str], cache_dir: Path) -> Path:
    try:
        from huggingface_hub import snapshot_download  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in materialization workflow
        raise RuntimeError("huggingface_hub is required for external materialization") from exc

    path = snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        allow_patterns=list(allow_patterns),
        cache_dir=str(cache_dir),
    )
    return Path(path)


def materialize(output_dir: Path, cache_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite materialization directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cadtest = SOURCES["cadtestbench"]
    cadtest_snapshot = _snapshot_download(
        cadtest.dataset_repository,
        cadtest.dataset_revision,
        [artifact.path for artifact in cadtest.dataset_artifacts],
        cache_dir,
    )
    cadgen = SOURCES["cadgenbench"]
    cadgen_snapshot = _snapshot_download(
        cadgen.dataset_repository,
        cadgen.dataset_revision,
        ["*/description.yaml", "*/edit_description.txt"],
        cache_dir,
    )

    sources = [
        _materialize_cadtestbench(cadtest_snapshot, output_dir),
        _materialize_cadgenbench(cadgen_snapshot, output_dir),
    ]
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "PROMPT_ONLY_MATERIALIZED_NOT_EVALUATED",
        "execution_authorized": False,
        "outcomes_observed": False,
        "private_ground_truth_accessed": False,
        "sources": sources,
    }
    receipt_path = output_dir / "MATERIALIZATION_RECEIPT.json"
    receipt_sha256 = _write_json(receipt_path, receipt)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "receipt": str(receipt_path),
                "receipt_sha256": receipt_sha256,
                "records": {source["source"]: source["adapted_export"]["records"] for source in sources},
            },
            sort_keys=True,
        )
    )
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize exact public prompt-only S3 benchmark inputs")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    materialize(args.output_dir, args.cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
