from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.benchmark import benchmark_hash, generate_benchmark, load_benchmark, write_benchmark
from core.data import prepare_dataset, validate_dataset


def test_frozen_benchmark_round_trip_and_summary(tmp_path: Path) -> None:
    path = tmp_path / "benchmark.jsonl"
    tasks = generate_benchmark()
    write_benchmark(path, tasks)
    loaded = load_benchmark(path)
    assert loaded == tasks
    summary = validate_dataset(path)
    assert summary["valid"] is True
    assert summary["sha256"] == benchmark_hash(tasks)
    assert summary["task_count"] == 48
    assert summary["unique_prompt_count"] == 46
    assert summary["duplicate_prompt_records"] == 2
    assert summary["split_counts"] == {"train": 20, "validation": 12, "test": 16}


def test_loader_rejects_cross_split_duplicate_prompts_and_unknown_fields(tmp_path: Path) -> None:
    tasks = generate_benchmark()
    duplicate = tasks[1].to_dict()
    duplicate["prompt"] = tasks[0].prompt
    duplicate["split"] = "validation"
    duplicate_path = tmp_path / "duplicate.jsonl"
    duplicate_path.write_text(
        "".join(json.dumps(task.to_dict()) + "\n" for task in tasks[:1]) + json.dumps(duplicate) + "\n"
        + "".join(json.dumps(task.to_dict()) + "\n" for task in tasks[2:]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicated across splits"):
        load_benchmark(duplicate_path)

    unknown_path = tmp_path / "unknown.jsonl"
    value = tasks[0].to_dict()
    value["leaked_label"] = True
    unknown_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown fields"):
        load_benchmark(unknown_path)


def test_prepare_refuses_overwrite_and_writes_manifest(tmp_path: Path) -> None:
    path = tmp_path / "benchmark.jsonl"
    manifest = prepare_dataset(path)
    assert path.is_file()
    assert path.with_suffix(".jsonl.manifest.json").is_file()
    assert manifest["sha256"] == benchmark_hash(load_benchmark(path))
    with pytest.raises(FileExistsError):
        prepare_dataset(path)


def test_benchmark_cli_evaluates_existing_dataset_without_mutating_it(tmp_path: Path) -> None:
    dataset = tmp_path / "frozen.jsonl"
    write_benchmark(dataset, generate_benchmark())
    before = dataset.read_bytes()
    output = tmp_path / "results.json"
    completed = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "benchmark", "--dataset", str(dataset), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert dataset.read_bytes() == before
    results = json.loads(output.read_text(encoding="utf-8"))
    assert results["benchmark_sha256"] == benchmark_hash(generate_benchmark())
