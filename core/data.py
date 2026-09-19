"""Deterministic preparation and validation for NeuroCAD-owned benchmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .benchmark import (
    BENCHMARK_VERSION,
    DEFAULT_SEED,
    benchmark_summary,
    generate_benchmark,
    load_benchmark,
    write_benchmark,
)

DATASET_ID = "neurocad-controlled-benchmark-v1"
DATASET_LICENSE = "MIT"


def dataset_manifest(path: Path, tasks: list[Any], *, seed: int | None) -> dict[str, Any]:
    summary = benchmark_summary(tasks)
    return {
        "dataset_id": DATASET_ID,
        "benchmark_version": BENCHMARK_VERSION,
        "license": DATASET_LICENSE,
        "source": "project-authored deterministic generator in core.benchmark.generate_benchmark",
        "retrieval": "generated locally; no network download",
        "path": str(path),
        "seed": seed,
        "warnings": (
            ["Exact prompt duplicates exist within a split; they reduce effective task diversity but do not cross split boundaries."]
            if summary["duplicate_prompt_records"]
            else []
        ),
        **summary,
    }


def prepare_dataset(path: Path, *, seed: int = DEFAULT_SEED, force: bool = False) -> dict[str, Any]:
    path = path.expanduser().resolve()
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if not force:
        for candidate in (path, manifest_path):
            if candidate.exists() or candidate.is_symlink():
                raise FileExistsError(f"dataset artifact already exists; choose a new path or pass --force: {candidate}")
    tasks = generate_benchmark(seed)
    write_benchmark(path, tasks)
    manifest = dataset_manifest(path, tasks, seed=seed)
    write_text_atomic(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def validate_dataset(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    tasks = load_benchmark(path)
    return {"valid": True, **dataset_manifest(path, tasks, seed=None)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, validate, or inspect NeuroCAD benchmark data")
    actions = parser.add_subparsers(dest="action", required=True)
    prepare = actions.add_parser("prepare", help="Generate a deterministic benchmark and checksum manifest")
    prepare.add_argument("output")
    prepare.add_argument("--seed", type=int, default=DEFAULT_SEED)
    prepare.add_argument("--force", action="store_true")
    for name in ("validate", "inspect"):
        command = actions.add_parser(name, help=f"{name.title()} a frozen benchmark without modifying it")
        command.add_argument("dataset")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.action == "prepare":
            result = prepare_dataset(Path(args.output), seed=args.seed, force=args.force)
        else:
            result = validate_dataset(Path(args.dataset))
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from None
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
