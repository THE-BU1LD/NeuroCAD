from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core import research_suite
from core.research_suite import (
    ResearchConfig,
    _deterministic_copy,
    _prepare_fresh_output_dir,
    _require_archival_provenance,
    _research_provenance,
    _source_snapshot,
    _timing_measurements,
    run_research_suite,
)

ROOT = Path(__file__).resolve().parents[1]


def test_source_snapshot_binds_relative_paths_and_contents(tmp_path: Path) -> None:
    source = tmp_path / "core" / "example.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0"\n', encoding="utf-8")

    first = _source_snapshot(tmp_path)
    second = _source_snapshot(tmp_path)
    assert first == second
    assert first["files"]["core/example.py"] == hashlib.sha256(b"value = 1\n").hexdigest()

    source.write_text("value = 2\n", encoding="utf-8")
    changed = _source_snapshot(tmp_path)
    assert changed["sha256"] != first["sha256"]


def test_research_output_must_be_new_or_empty(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    marker = output / "do-not-overwrite.txt"
    marker.write_text("retained", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to overwrite or resume"):
        _prepare_fresh_output_dir(output)
    assert marker.read_text(encoding="utf-8") == "retained"

    fresh = tmp_path / "fresh"
    _prepare_fresh_output_dir(fresh)
    assert fresh.is_dir()
    _prepare_fresh_output_dir(fresh)


def test_research_config_forces_fresh_kernel_compilation_by_default() -> None:
    config = ResearchConfig()
    config.validate()
    assert config.force_recompile is True
    with pytest.raises((TypeError, ValueError), match="force_recompile must be a boolean"):
        ResearchConfig(force_recompile=1).validate()  # type: ignore[arg-type]


def test_deterministic_results_exclude_timing_but_retain_outcomes() -> None:
    value = {
        "passed": 12,
        "total_runtime_seconds": 1.2,
        "records": [
            {"task_id": "one", "passed": True, "details": {"latency_ms": 0.5}},
            {"task_id": "two", "passed": False, "elapsed_seconds": 0.7},
        ],
    }
    deterministic = _deterministic_copy(value)
    timings = _timing_measurements(value)

    assert deterministic == {
        "passed": 12,
        "records": [
            {"task_id": "one", "passed": True, "details": {}},
            {"task_id": "two", "passed": False},
        ],
    }
    assert timings == {
        "$.total_runtime_seconds": 1.2,
        "$.records[0].details.latency_ms": 0.5,
        "$.records[1].elapsed_seconds": 0.7,
    }


def test_provenance_records_current_source_lock_package_and_kernel() -> None:
    source = _source_snapshot(ROOT)
    provenance = _research_provenance(ROOT, source)

    assert provenance["source"] == source
    assert {
        "MANIFEST.in",
        "README.md",
        "docs/PRODUCT_WORKFLOW.md",
        "research/VERICODEGEN_2026_PROTOCOL.md",
    } <= set(source["files"])
    assert provenance["package"]["declared_version"]
    assert provenance["requirements_lock"]["path"] == "requirements-research.lock"
    assert len(provenance["requirements_lock"]["sha256"]) == 64
    assert provenance["python"]["version"]
    assert "version_output" in provenance["openscad"]
    if provenance["openscad"]["executable"] is not None:
        assert len(provenance["openscad"]["executable_sha256"]) == 64
    assert set(provenance["git"]) >= {"commit", "dirty"}


def test_archival_kernel_run_requires_lock_and_matching_package_version() -> None:
    valid = {
        "requirements_lock": {"sha256": "a" * 64},
        "package": {"declared_version": "1.2.3", "installed_distribution_version": "1.2.3"},
    }
    _require_archival_provenance(valid)

    missing_lock = {**valid, "requirements_lock": {"sha256": None}}
    with pytest.raises(RuntimeError, match="requirements-research.lock"):
        _require_archival_provenance(missing_lock)

    mismatch = {
        **valid,
        "package": {"declared_version": "1.2.3", "installed_distribution_version": "1.2.2"},
    }
    with pytest.raises(RuntimeError, match="matching declared and installed"):
        _require_archival_provenance(mismatch)


def test_completed_manifest_separates_deterministic_results_and_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def kernel_not_run(config: ResearchConfig, tasks: object, output_dir: Path) -> dict[str, object]:
        return {
            "experiment_id": "NC-EXP-006",
            "status": "not_run",
            "reason": "unit test",
            "samples_requested": config.kernel_samples,
            "force_recompile": config.force_recompile,
            "artifact_reuse_enabled": not config.force_recompile,
            "resumed_verified_samples": 0,
            "records": [],
        }

    monkeypatch.setattr(research_suite, "_run_kernel", kernel_not_run)
    config = ResearchConfig(
        compiler_tasks=30,
        ir_programs=1,
        invalid_cases=8,
        edit_cases=1,
        constraint_ablation_cases=1,
        kernel_samples=1,
    )
    run_research_suite(tmp_path, config, run_id="NC-PROVENANCE-TEST")

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    deterministic = json.loads((tmp_path / manifest["deterministic_results"]).read_text(encoding="utf-8"))
    runtime = json.loads((tmp_path / manifest["runtime_receipt"]).read_text(encoding="utf-8"))

    assert manifest["force_recompile"] is True
    assert manifest["artifact_reuse_allowed"] is False
    assert set(manifest["scientific_sha256"]) == {
        "config",
        "compiler_dataset",
        "ir_programs",
        "deterministic_results",
        "maintained_source",
        "requirements_lock",
    }
    assert manifest["provenance"]["source"]["sha256"]
    assert deterministic["timing_fields_excluded"] is True
    assert "matching maintained-source" in deterministic["comparison_scope"]
    ir_stress = deterministic["results"]["experiments"]["NC-EXP-002"]
    assert ir_stress["kernel_evaluated_programs"] == 0
    assert "static structural validity" in ir_stress["validity_scope"]
    assert "timing and environment" in runtime["claim_boundary"].lower()
    assert runtime["timing_measurements"]
