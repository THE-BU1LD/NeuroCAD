from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research.vericodegen.benchmark_freeze import (
    BenchmarkError,
    benchmark_jsonl,
    freeze_benchmark,
    jaccard_similarity,
    select_stratified_pilot,
    sha256_text,
    validate_benchmark,
    validate_task,
)


def _task(number: int, family: str, *, wording: str | None = None) -> dict:
    axis = (number - 1) % 3
    dimensions = [10 + number, 20 + number, 30 + number]
    prompt = wording or (
        f"Create benchmark object {number} as a watertight rectangular solid with exact "
        f"dimensions {dimensions[0]} by {dimensions[1]} by {dimensions[2]} millimeters."
    )
    return {
        "prompt_id": f"VCG-{number:03d}",
        "prompt_text": prompt,
        "task_family": family,
        "required_relations": [f"axis-{axis}-dimension-fixed"],
        "hard_constraints": {
            "watertight": True,
            "max_components": 1,
            "extents": {
                "xyz"[axis]: {
                    "min": dimensions[axis] - 0.1,
                    "max": dimensions[axis] + 0.1,
                }
            },
        },
        "semantic_rubric": [
            {
                "criterion": "object_identity",
                "description": f"Output represents benchmark object {number} as requested.",
            }
        ],
    }


def _balanced_six() -> list[dict]:
    return [
        _task(1, "in_distribution"),
        _task(2, "in_distribution"),
        _task(3, "compositional"),
        _task(4, "compositional"),
        _task(5, "ood_constraint_stress"),
        _task(6, "ood_constraint_stress"),
    ]


def test_valid_task_accepts_machine_checkable_constraints():
    assert validate_task(_task(1, "in_distribution")) == []


def test_invalid_numeric_ranges_fail_closed():
    task = _task(1, "in_distribution")
    task["hard_constraints"]["volume"] = {"min": 20, "max": 10}
    task["hard_constraints"]["bounds"] = {
        "min": [1, 0, 0],
        "max": [0, 0, 0],
    }
    errors = validate_task(task)
    assert any("volume.min" in error for error in errors)
    assert any("bounds min.x" in error for error in errors)


def test_empty_hard_constraints_are_rejected():
    task = _task(1, "in_distribution")
    task["hard_constraints"] = {}
    assert any("at least one machine-checkable" in error for error in validate_task(task))


def test_balanced_sequence_passes_exact_size_gate():
    errors = validate_benchmark(
        _balanced_six(),
        expected_total=6,
        expected_per_family=2,
        near_duplicate_threshold=1.0,
    )
    assert errors == []


def test_family_imbalance_and_missing_contiguous_id_are_rejected():
    tasks = _balanced_six()
    tasks[-1]["task_family"] = "in_distribution"
    tasks[-1]["prompt_id"] = "VCG-009"
    errors = validate_benchmark(
        tasks,
        expected_total=6,
        expected_per_family=2,
        near_duplicate_threshold=1.0,
    )
    assert any("complete contiguous" in error for error in errors)
    assert any("family in_distribution" in error for error in errors)
    assert any("family ood_constraint_stress" in error for error in errors)


def test_exact_normalized_duplicate_prompt_is_rejected():
    tasks = _balanced_six()
    tasks[1]["prompt_text"] = tasks[0]["prompt_text"].upper() + "!!!"
    errors = validate_benchmark(tasks, near_duplicate_threshold=1.0)
    assert any("exact normalized prompt duplicates" in error for error in errors)


def test_near_duplicate_detection_is_conservative_and_auditable():
    left = "Create a watertight plate with four corner holes and exact width forty millimeters"
    right = "Create a watertight plate with four corner holes and exact width forty five millimeters"
    unrelated = "Build a centered sphere constrained to one connected component and fixed radius"
    assert jaccard_similarity(left, right) > 0.8
    assert jaccard_similarity(left, unrelated) < 0.4

    tasks = _balanced_six()
    tasks[0]["prompt_text"] = left
    tasks[1]["prompt_text"] = right
    errors = validate_benchmark(tasks, near_duplicate_threshold=0.8)
    assert any("near-duplicate prompts: VCG-001 vs VCG-002" in error for error in errors)


def test_canonical_jsonl_is_order_independent():
    tasks = _balanced_six()
    forward = benchmark_jsonl(tasks)
    reverse = benchmark_jsonl(list(reversed(tasks)))
    assert forward == reverse
    assert forward.startswith('{"hard_constraints"')
    assert forward.endswith("\n")


def test_freeze_writes_deterministic_benchmark_and_manifest(tmp_path: Path):
    tasks = _balanced_six()
    source = tmp_path / "authored.jsonl"
    source.write_text("\n".join(json.dumps(task) for task in reversed(tasks)) + "\n", encoding="utf-8")
    schema = tmp_path / "schema.json"
    schema.write_text('{"schema":"fixture"}\n', encoding="utf-8")
    frozen = tmp_path / "frozen.jsonl"
    manifest_path = tmp_path / "manifest.json"

    manifest = freeze_benchmark(
        source,
        schema=schema,
        output_jsonl=frozen,
        output_manifest=manifest_path,
        expected_total=6,
        expected_per_family=2,
        near_duplicate_threshold=1.0,
    )

    canonical = benchmark_jsonl(tasks)
    assert frozen.read_text(encoding="utf-8") == canonical
    assert manifest["benchmark_sha256"] == sha256_text(canonical)
    assert manifest["schema_sha256"] == hashlib.sha256(schema.read_bytes()).hexdigest()
    assert manifest["task_count"] == 6
    assert manifest["family_counts"] == {
        "compositional": 2,
        "in_distribution": 2,
        "ood_constraint_stress": 2,
    }
    assert manifest["frozen"] is True
    assert manifest["outcomes_observed"] is False
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == manifest


def test_freeze_blocks_before_writing_if_duplicate_exists(tmp_path: Path):
    tasks = _balanced_six()
    tasks[1]["prompt_text"] = tasks[0]["prompt_text"]
    source = tmp_path / "bad.jsonl"
    source.write_text("\n".join(json.dumps(task) for task in tasks) + "\n", encoding="utf-8")
    schema = tmp_path / "schema.json"
    schema.write_text("{}\n", encoding="utf-8")
    output = tmp_path / "must-not-exist.jsonl"
    manifest = tmp_path / "must-not-exist.json"

    with pytest.raises(BenchmarkError, match="freeze blocked"):
        freeze_benchmark(
            source,
            schema=schema,
            output_jsonl=output,
            output_manifest=manifest,
            expected_total=6,
            expected_per_family=2,
            near_duplicate_threshold=1.0,
        )

    assert not output.exists()
    assert not manifest.exists()


def test_pilot_selection_is_deterministic_and_stratified():
    tasks = _balanced_six()
    first = select_stratified_pilot(tasks, per_family=1, selection_salt="frozen-salt-v1")
    second = select_stratified_pilot(list(reversed(tasks)), per_family=1, selection_salt="frozen-salt-v1")
    assert first == second
    assert len(first) == 3

    by_id = {task["prompt_id"]: task for task in tasks}
    families = {by_id[prompt_id]["task_family"] for prompt_id in first}
    assert families == {
        "in_distribution",
        "compositional",
        "ood_constraint_stress",
    }


def test_pilot_selection_changes_with_salt_but_is_stable_per_salt():
    families = [
        "in_distribution",
        "in_distribution",
        "in_distribution",
        "compositional",
        "compositional",
        "compositional",
        "ood_constraint_stress",
        "ood_constraint_stress",
        "ood_constraint_stress",
    ]
    tasks = [_task(index + 1, family) for index, family in enumerate(families)]
    a = select_stratified_pilot(tasks, per_family=1, selection_salt="salt-a")
    b = select_stratified_pilot(tasks, per_family=1, selection_salt="salt-b")
    assert a == select_stratified_pilot(tasks, per_family=1, selection_salt="salt-a")
    assert b == select_stratified_pilot(tasks, per_family=1, selection_salt="salt-b")
    assert a != b


def test_pilot_selection_rejects_underfilled_family():
    with pytest.raises(BenchmarkError, match="pilot needs 3"):
        select_stratified_pilot(_balanced_six(), per_family=3, selection_salt="fixed")
