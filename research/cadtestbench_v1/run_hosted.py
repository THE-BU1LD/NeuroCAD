"""Run the frozen full-cohort CADTestBench evaluation and retain receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.cadtestbench_v1.prepare_generations import prepare_partition

PARTITIONS = ("abstract", "detailed")
STUDY_ID = "NC-CADTESTBENCH-V1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _new_evaluation_dir(eval_root: Path, before: set[Path]) -> Path:
    after = {path.resolve() for path in eval_root.iterdir() if path.is_dir()}
    created = sorted(after - before)
    if len(created) != 1:
        raise RuntimeError(f"expected exactly one new evaluation directory, found {created}")
    summary = created[0] / "evaluation_summary.json"
    if not summary.is_file():
        raise RuntimeError(f"CADTestBench did not retain its summary: {summary}")
    return created[0]


def evaluate_partition(
    *,
    dataset_root: Path,
    generation_root: Path,
    eval_root: Path,
    receipt_root: Path,
    partition: str,
) -> dict[str, Any]:
    before = {path.resolve() for path in eval_root.iterdir() if path.is_dir()}
    command = [
        sys.executable,
        "-m",
        "cadtestbench",
        "evaluate",
        str(generation_root / partition),
        "--partition",
        partition,
        "--dataset",
        str(dataset_root),
        "--eval-root",
        str(eval_root),
        "--run-label",
        f"NeuroCAD-{STUDY_ID}",
    ]
    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    receipt: dict[str, Any] = {
        "partition": partition,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    receipt_path = receipt_root / f"cadtestbench_{partition}_command.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(receipt, indent=2, sort_keys=True))
    evaluation_dir = _new_evaluation_dir(eval_root, before)
    summary_path = evaluation_dir / "evaluation_summary.json"
    receipt.update(
        {
            "evaluation_dir": str(evaluation_dir),
            "evaluation_summary": str(summary_path),
            "evaluation_summary_sha256": _sha256(summary_path),
        }
    )
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"refusing to replace prior study output: {output_root}")
    generation_root = output_root / "generations"
    eval_root = output_root / "evaluations"
    eval_root.mkdir(parents=True)

    generation_manifests = [
        prepare_partition(
            dataset_root=dataset_root,
            partition=partition,
            output_root=generation_root,
            expected_rows=200,
        )
        for partition in PARTITIONS
    ]
    evaluation_receipts = [
        evaluate_partition(
            dataset_root=dataset_root,
            generation_root=generation_root,
            eval_root=eval_root,
            receipt_root=output_root,
            partition=partition,
        )
        for partition in PARTITIONS
    ]
    receipt = {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(dataset_root),
        "generation_manifests": generation_manifests,
        "evaluation_receipts": evaluation_receipts,
    }
    receipt_path = output_root / "execution_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
