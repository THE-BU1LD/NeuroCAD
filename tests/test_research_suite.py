from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh

from core.research_suite import (
    ResearchConfig,
    _reuse_kernel_artifacts,
    _run_invalid_taxonomy,
    _run_ir_stress,
    generate_compiler_stress_tasks,
    run_research_suite,
)


def test_release_sized_ir_stress_records_export_rejections() -> None:
    result, encoded, programs = _run_ir_stress(ResearchConfig(ir_programs=1000))
    assert len(programs) == len(encoded.splitlines()) == 1000
    assert result["passed"] + len(result["failures"]) == 1000
    assert result["failures"]
    assert all(row["evaluation"]["export_error"] for row in result["failures"])
    assert all(not row["evaluation"]["deterministic_export"] for row in result["failures"])


def test_invalid_taxonomy_uses_unique_traceable_fixtures_without_fake_interval() -> None:
    result, encoded = _run_invalid_taxonomy(ResearchConfig(invalid_cases=240))
    records = [json.loads(line) for line in encoded.splitlines()]
    assert result["cases"] == 240
    assert result["unique_source_count"] == 240
    assert result["category_count"] == 8
    assert result["statistical_interval"] is None
    assert "wilson_95" not in result
    assert len({record["source_sha256"] for record in records}) == 240
    assert all(record["rejected"] for record in records)


def test_stress_dataset_is_deterministic_and_system_is_exact() -> None:
    first = generate_compiler_stress_tasks(70, 20260902)
    second = generate_compiler_stress_tasks(70, 20260902)
    assert first == second
    assert {task.split for task in first} == {"train", "validation", "test"}
    assert {task.family for task in first} == {"plate", "holes", "slots", "enclosure", "box", "cylinder", "sphere"}


def test_small_research_suite_writes_traceable_artifacts(tmp_path: Path) -> None:
    config = ResearchConfig(
        compiler_tasks=35,
        ir_programs=36,
        invalid_cases=16,
        edit_cases=12,
        constraint_ablation_cases=12,
        kernel_samples=2,
        fn=12,
        openscad_timeout_seconds=30,
    )
    results = run_research_suite(tmp_path, config)
    assert results["experiments"]["NC-EXP-001"]["systems"]["neurocad"]["overall_semantic_exact_rate"] == 1.0
    assert results["experiments"]["NC-EXP-002"]["success_rate"] == 1.0
    assert results["experiments"]["NC-EXP-003"]["rejection_rate"] == 1.0
    assert results["experiments"]["NC-EXP-004"]["corruption_detection_with_constraints"] == 1.0
    assert results["experiments"]["NC-EXP-005"]["parameter_edit_success_rate"] == 1.0
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_checkpoint"] is None
    assert (tmp_path / manifest["results"]).is_file()
    assert "metrics/results.json" in manifest["artifact_sha256"]
    assert (tmp_path / "figures" / "compiler_accuracy.svg").is_file()


def test_research_run_id_is_recorded_and_kernel_count_is_bounded(tmp_path: Path) -> None:
    config = ResearchConfig(
        compiler_tasks=30,
        ir_programs=1,
        invalid_cases=1,
        edit_cases=1,
        constraint_ablation_cases=1,
        kernel_samples=31,
    )
    try:
        run_research_suite(tmp_path, config, run_id="NC-TEST-RUN")
    except ValueError as exc:
        assert "kernel_samples cannot exceed compiler_tasks" in str(exc)
    else:
        raise AssertionError("invalid kernel sample count was accepted")


def test_research_config_rejects_wrong_types_without_crashing() -> None:
    with pytest.raises(ValueError, match="seed must be an integer"):
        ResearchConfig(seed=True).validate()  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ir_programs must be positive"):
        ResearchConfig(ir_programs=1.5).validate()  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fn must be between"):
        ResearchConfig(fn=True).validate()  # type: ignore[arg-type]


def test_interrupted_kernel_artifact_resume_is_identity_and_hash_checked(tmp_path: Path) -> None:
    ir_path = tmp_path / "program.ncad.json"
    scad_path = tmp_path / "program.scad"
    stl_path = tmp_path / "program.stl"
    render_path = tmp_path / "preview.png"
    validation_path = tmp_path / "validation.json"
    ir_text, scad_text = '{"version":"test"}\n', "cube([10,20,30]);\n"
    ir_path.write_text(ir_text, encoding="utf-8")
    scad_path.write_text(scad_text, encoding="utf-8")
    trimesh.creation.box(extents=(10, 20, 30)).export(stl_path)
    render_path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    identity = {"task_id": "NCR-0001", "family": "box", "prompt": "test"}
    validation_path.write_text(json.dumps({**identity, "passed": True}), encoding="utf-8")

    reused = _reuse_kernel_artifacts(
        validation_path=validation_path,
        ir_path=ir_path,
        scad_path=scad_path,
        stl_path=stl_path,
        render_path=render_path,
        ir_text=ir_text,
        scad_text=scad_text,
        base_record=identity,
        expected_extents=[10, 20, 30],
    )
    assert reused is not None
    assert reused["resumed_verified_artifact"] is True
    assert set(reused["artifact_sha256"]) == {"ir", "scad", "stl", "render"}

    scad_path.write_text("cube([1,1,1]);\n", encoding="utf-8")
    assert (
        _reuse_kernel_artifacts(
            validation_path=validation_path,
            ir_path=ir_path,
            scad_path=scad_path,
            stl_path=stl_path,
            render_path=render_path,
            ir_text=ir_text,
            scad_text=scad_text,
            base_record=identity,
            expected_extents=[10, 20, 30],
        )
        is None
    )
