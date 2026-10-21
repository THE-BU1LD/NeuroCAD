from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from research.cadtestbench_v1 import run_hosted


def test_evaluate_partition_invokes_full_official_evaluator_and_retains_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_root = tmp_path / "dataset"
    generation_root = tmp_path / "generations"
    eval_root = tmp_path / "evaluations"
    receipt_root = tmp_path / "receipt"
    for path in (dataset_root, generation_root / "abstract", eval_root, receipt_root):
        path.mkdir(parents=True)

    def fake_run(command: list[str], **_: object) -> CompletedProcess[str]:
        output = eval_root / "frozen-abstract"
        output.mkdir()
        (output / "evaluation_summary.json").write_text('{"statistics":{"total_samples":200}}\n')
        return CompletedProcess(command, 0, stdout="official evaluator completed", stderr="")

    monkeypatch.setattr(run_hosted.subprocess, "run", fake_run)
    receipt = run_hosted.evaluate_partition(
        dataset_root=dataset_root,
        generation_root=generation_root,
        eval_root=eval_root,
        receipt_root=receipt_root,
        partition="abstract",
    )

    command = receipt["command"]
    assert "--limit" not in command
    assert command[command.index("--partition") + 1] == "abstract"
    assert command[command.index("--dataset") + 1] == str(dataset_root)
    assert receipt["returncode"] == 0
    assert len(receipt["evaluation_summary_sha256"]) == 64
    persisted = json.loads((receipt_root / "cadtestbench_abstract_command.json").read_text())
    assert persisted["evaluation_summary_sha256"] == receipt["evaluation_summary_sha256"]


def test_evaluate_partition_retains_failure_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_root = tmp_path / "dataset"
    generation_root = tmp_path / "generations"
    eval_root = tmp_path / "evaluations"
    receipt_root = tmp_path / "receipt"
    for path in (dataset_root, generation_root / "detailed", eval_root, receipt_root):
        path.mkdir(parents=True)

    monkeypatch.setattr(
        run_hosted.subprocess,
        "run",
        lambda command, **_: CompletedProcess(command, 2, stdout="", stderr="retained failure"),
    )
    with pytest.raises(RuntimeError, match="retained failure"):
        run_hosted.evaluate_partition(
            dataset_root=dataset_root,
            generation_root=generation_root,
            eval_root=eval_root,
            receipt_root=receipt_root,
            partition="detailed",
        )

    persisted = json.loads((receipt_root / "cadtestbench_detailed_command.json").read_text())
    assert persisted["returncode"] == 2
    assert persisted["stderr"] == "retained failure"
