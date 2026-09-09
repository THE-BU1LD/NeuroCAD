from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh

from research.vericodegen.analysis import validate_row as validate_analysis_row
from research.vericodegen.trial_ledger import (
    CAPTURE_VERSION,
    TrialLedgerError,
    evaluate_attempt,
    finalize_cells,
    hash_chain,
    sha256_file,
    validate_capture_matrix,
    validate_capture_row,
    validate_frozen_inputs,
    verify_hash_chain,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
HASH_F = "f" * 64
HASH_0 = "0" * 64
HASH_1 = "1" * 64


def _manifest(*, max_attempts: int = 2) -> dict:
    return {
        "manifest_version": "vericodegen-stage2-v2",
        "stage": "stage2_frozen_pilot",
        "authorized": True,
        "scientific_evidence": False,
        "evaluation_entrypoint": "research.vericodegen.safe_trial_ledger:evaluate_capture",
        "benchmark_manifest_sha256": HASH_A,
        "pilot_selection_sha256": HASH_B,
        "structured_schema_sha256": HASH_C,
        "verifier_sha256": HASH_D,
        "analysis_plan_sha256": HASH_E,
        "pilot_task_ids": ["VCG-001"],
        "provider": "fixture-provider",
        "model": "fixture-model-v1",
        "decoding": {
            "temperature": 0.2,
            "top_p": 1.0,
            "max_output_tokens": 2048,
            "seeds": [101],
        },
        "retry_policy": {
            "max_attempts": max_attempts,
            "feedback_policy": "Frozen symmetric compiler/verifier feedback.",
            "same_attempt_limit_both_arms": True,
            "human_correction_allowed": False,
        },
        "prompt_templates": {
            "direct_sha256": HASH_F,
            "structured_sha256": HASH_0,
            "receipt_sha256": HASH_1,
        },
        "environment": {
            "openscad_version": "OpenSCAD fixture",
            "openscad_fn": 64,
            "compile_timeout_seconds": 60,
        },
        "retention_policy": {
            "retain_raw_outputs": True,
            "retain_failed_trials": True,
            "retain_compile_logs": True,
        },
        "git_commit": "31201f2fbd921e4e3c0b89473d536565ecd793b4",
        "cost_cap_usd": 10.0,
        "estimated_max_calls": 2 * max_attempts,
    }


def _capture(
    arm: str,
    attempt: int,
    *,
    status: str = "completed",
    raw_output: str | None = "cube([2,2,2], center=true);",
    tokens: int = 10,
    seconds: float = 0.5,
    cost: float = 0.01,
) -> dict:
    return {
        "capture_version": CAPTURE_VERSION,
        "prompt_id": "VCG-001",
        "seed": 101,
        "arm": arm,
        "attempt": attempt,
        "generation_status": status,
        "raw_output": raw_output,
        "generated_tokens": tokens,
        "wall_clock_seconds": seconds,
        "estimated_cost_usd": cost,
        "provider_request_id": f"request-{arm}-{attempt}",
    }


def _evaluated(
    arm: str,
    attempt: int,
    *,
    hvr: bool,
    tokens: int = 10,
    seconds: float = 0.5,
    cost: float = 0.01,
    failure_modes: list[str] | None = None,
) -> dict:
    return {
        "prompt_id": "VCG-001",
        "seed": 101,
        "arm": arm,
        "attempt": attempt,
        "task_family": "in_distribution",
        "hvr": hvr,
        "compile_success": hvr,
        "hard_constraints_passed": hvr,
        "generated_tokens": tokens,
        "wall_clock_seconds": seconds,
        "estimated_cost_usd": cost,
        "failure_modes": failure_modes or ([] if hvr else ["syntax_compile_failure"]),
        "artifact_sha256": "d" * 64 if hvr else None,
        "raw_output_sha256": "e" * 64,
    }


def test_valid_completed_capture_row_passes():
    assert validate_capture_row(_capture("direct", 1)) == []


def test_timeout_and_error_must_not_smuggle_output():
    timeout = _capture("direct", 1, status="timeout", raw_output="partial output")
    assert any("must not contain" in error for error in validate_capture_row(timeout))

    timeout["raw_output"] = None
    assert validate_capture_row(timeout) == []


def test_completed_capture_requires_raw_output():
    row = _capture("direct", 1, status="completed", raw_output=None)
    assert any("requires non-empty raw_output" in error for error in validate_capture_row(row))


def test_capture_matrix_requires_every_authorized_arm():
    errors = validate_capture_matrix([_capture("direct", 1)], _manifest())
    assert any("missing 1 authorized" in error for error in errors)


def test_capture_matrix_rejects_duplicate_gapped_and_overbudget_attempts():
    manifest = _manifest(max_attempts=2)
    rows = [
        _capture("direct", 1),
        _capture("direct", 1),
        _capture("structured", 2, raw_output='{"x":1}'),
        _capture("structured", 3, raw_output='{"x":1}'),
    ]
    errors = validate_capture_matrix(rows, manifest)
    assert any("duplicate captured attempt" in error for error in errors)
    assert any("exceeds frozen max_attempts" in error for error in errors)
    assert any("attempts must be contiguous from 1" in error for error in errors)


def test_capture_matrix_rejects_unfrozen_task_seed_or_arm():
    row = _capture("direct", 1)
    row["prompt_id"] = "VCG-999"
    errors = validate_capture_matrix([row], _manifest())
    assert any("not authorized" in error for error in errors)


def test_hash_chain_is_deterministic_and_tamper_evident():
    records = [
        _evaluated("structured", 1, hvr=False),
        _evaluated("direct", 1, hvr=True),
        _evaluated("structured", 2, hvr=True),
    ]
    first = hash_chain(records)
    second = hash_chain(list(reversed(records)))
    assert first == second
    assert verify_hash_chain(first) == []
    assert first[0]["previous_ledger_hash"] == "0" * 64
    assert first[-1]["ledger_hash"] != first[-1]["previous_ledger_hash"]

    tampered = [dict(row) for row in first]
    tampered[1]["generated_tokens"] = 999
    assert any("ledger hash mismatch" in error for error in verify_hash_chain(tampered))


def test_finalize_uses_first_pass_and_aggregates_retry_resources():
    manifest = _manifest(max_attempts=2)
    records = hash_chain(
        [
            _evaluated("direct", 1, hvr=True, tokens=5, seconds=0.5, cost=0.01),
            _evaluated("structured", 1, hvr=False, tokens=7, seconds=0.7, cost=0.02),
            _evaluated("structured", 2, hvr=True, tokens=11, seconds=1.1, cost=0.03),
        ]
    )
    finals = finalize_cells(records, manifest)
    assert len(finals) == 2
    by_arm = {row["arm"]: row for row in finals}
    assert by_arm["direct"]["retry_count"] == 0
    assert by_arm["direct"]["generated_tokens"] == 5
    assert by_arm["structured"]["retry_count"] == 1
    assert by_arm["structured"]["generated_tokens"] == 18
    assert by_arm["structured"]["wall_clock_seconds"] == pytest.approx(1.8)
    assert by_arm["structured"]["estimated_cost_usd"] == pytest.approx(0.05)
    assert by_arm["structured"]["failure_modes"] == []
    assert validate_analysis_row(by_arm["direct"]) == []
    assert validate_analysis_row(by_arm["structured"]) == []


def test_finalize_rejects_retry_after_success():
    manifest = _manifest(max_attempts=2)
    records = hash_chain(
        [
            _evaluated("direct", 1, hvr=True),
            _evaluated("direct", 2, hvr=True),
            _evaluated("structured", 1, hvr=True),
        ]
    )
    with pytest.raises(TrialLedgerError, match="retries after attempt 1 already passed"):
        finalize_cells(records, manifest)


def test_finalize_rejects_early_stop_after_failure():
    manifest = _manifest(max_attempts=2)
    records = hash_chain(
        [
            _evaluated("direct", 1, hvr=False),
            _evaluated("structured", 1, hvr=True),
        ]
    )
    with pytest.raises(TrialLedgerError, match="capture stopped at 1 of frozen max_attempts=2"):
        finalize_cells(records, manifest)


def test_generation_timeout_is_retained_as_hvr_failure(tmp_path: Path):
    row = _capture("direct", 1, status="timeout", raw_output=None)
    task = {
        "prompt_id": "VCG-001",
        "task_family": "in_distribution",
        "hard_constraints": {"watertight": True},
    }
    evaluated = evaluate_attempt(
        row,
        task=task,
        openscad_fn=64,
        timeout_seconds=60,
        outdir=tmp_path,
    )
    assert evaluated["hvr"] is False
    assert evaluated["compile_success"] is False
    assert evaluated["failure_modes"] == ["timeout_retry_exhaustion"]


def test_adapter_rejection_is_retained_without_compile(tmp_path: Path):
    row = _capture("direct", 1, raw_output="$fn=8; cube(2);")
    task = {
        "prompt_id": "VCG-001",
        "task_family": "in_distribution",
        "hard_constraints": {"watertight": True},
    }
    evaluated = evaluate_attempt(
        row,
        task=task,
        openscad_fn=64,
        timeout_seconds=60,
        outdir=tmp_path,
    )
    assert evaluated["adapter_success"] is False
    assert evaluated["hvr"] is False
    assert evaluated["failure_modes"] == ["syntax_compile_failure"]
    assert evaluated["adapter_error"]


def test_real_verifier_can_score_fake_compiler_artifact(tmp_path: Path):
    row = _capture("direct", 1)
    task = {
        "prompt_id": "VCG-001",
        "task_family": "in_distribution",
        "hard_constraints": {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 7.9, "max": 8.1},
            "extents": {
                "x": {"min": 1.99, "max": 2.01},
                "y": {"min": 1.99, "max": 2.01},
                "z": {"min": 1.99, "max": 2.01},
            },
        },
    }

    def fake_compile(scad_text: str, *, scad_path: Path, stl_path: Path, timeout_seconds: int):
        scad_path.write_text(scad_text, encoding="utf-8")
        trimesh.creation.box(extents=(2, 2, 2)).export(stl_path)
        return {
            "compile_success": True,
            "timed_out": False,
            "returncode": 0,
            "stdout": "fixture compile",
            "artifact_sha256": sha256_file(stl_path),
        }

    evaluated = evaluate_attempt(
        row,
        task=task,
        openscad_fn=64,
        timeout_seconds=60,
        outdir=tmp_path,
        compile_function=fake_compile,
    )
    assert evaluated["adapter_success"] is True
    assert evaluated["compile_success"] is True
    assert evaluated["hard_constraints_passed"] is True
    assert evaluated["hvr"] is True
    assert evaluated["failure_modes"] == []
    assert evaluated["measurements"]["volume"] == pytest.approx(8.0)


def test_wrong_geometry_is_classified_as_dimension_failure(tmp_path: Path):
    row = _capture("direct", 1)
    task = {
        "prompt_id": "VCG-001",
        "task_family": "in_distribution",
        "hard_constraints": {"extents": {"x": {"min": 3.9, "max": 4.1}}},
    }

    def fake_compile(scad_text: str, *, scad_path: Path, stl_path: Path, timeout_seconds: int):
        scad_path.write_text(scad_text, encoding="utf-8")
        trimesh.creation.box(extents=(2, 2, 2)).export(stl_path)
        return {
            "compile_success": True,
            "timed_out": False,
            "returncode": 0,
            "stdout": "fixture compile",
            "artifact_sha256": sha256_file(stl_path),
        }

    evaluated = evaluate_attempt(
        row,
        task=task,
        openscad_fn=64,
        timeout_seconds=60,
        outdir=tmp_path,
        compile_function=fake_compile,
    )
    assert evaluated["compile_success"] is True
    assert evaluated["hard_constraints_passed"] is False
    assert evaluated["hvr"] is False
    assert evaluated["failure_modes"] == ["wrong_dimension_unit"]


def test_frozen_input_validator_checks_every_pinned_byte_artifact(tmp_path: Path):
    benchmark = tmp_path / "benchmark.jsonl"
    benchmark.write_text('{"prompt_id":"VCG-001"}\n', encoding="utf-8")
    benchmark_manifest = tmp_path / "benchmark.manifest.json"
    benchmark_manifest.write_text(
        json.dumps({"benchmark_sha256": sha256_file(benchmark)}) + "\n", encoding="utf-8"
    )
    pilot = tmp_path / "pilot.json"
    pilot.write_text(json.dumps({"pilot_task_ids": ["VCG-001"]}) + "\n", encoding="utf-8")
    structured_schema = tmp_path / "structured.json"
    structured_schema.write_text("{}\n", encoding="utf-8")
    verifier = tmp_path / "verifier.py"
    verifier.write_text("# verifier fixture\n", encoding="utf-8")
    analysis_plan = tmp_path / "analysis.json"
    analysis_plan.write_text("{}\n", encoding="utf-8")
    prompt_receipt = tmp_path / "prompt_receipt.json"
    prompt_receipt.write_text(
        json.dumps({"direct_sha256": HASH_F, "structured_sha256": HASH_0}) + "\n",
        encoding="utf-8",
    )

    manifest = _manifest()
    manifest["benchmark_manifest_sha256"] = sha256_file(benchmark_manifest)
    manifest["pilot_selection_sha256"] = sha256_file(pilot)
    manifest["structured_schema_sha256"] = sha256_file(structured_schema)
    manifest["verifier_sha256"] = sha256_file(verifier)
    manifest["analysis_plan_sha256"] = sha256_file(analysis_plan)
    manifest["prompt_templates"]["receipt_sha256"] = sha256_file(prompt_receipt)
    manifest_path = tmp_path / "stage2.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    errors = validate_frozen_inputs(
        manifest=manifest,
        manifest_path=manifest_path,
        benchmark_manifest_path=benchmark_manifest,
        benchmark_path=benchmark,
        pilot_selection_path=pilot,
        structured_schema_path=structured_schema,
        verifier_path=verifier,
        analysis_plan_path=analysis_plan,
        prompt_receipt_path=prompt_receipt,
        repository_root=tmp_path,
        require_git_head=False,
    )
    assert errors == []

    verifier.write_text("# tampered verifier\n", encoding="utf-8")
    errors = validate_frozen_inputs(
        manifest=manifest,
        manifest_path=manifest_path,
        benchmark_manifest_path=benchmark_manifest,
        benchmark_path=benchmark,
        pilot_selection_path=pilot,
        structured_schema_path=structured_schema,
        verifier_path=verifier,
        analysis_plan_path=analysis_plan,
        prompt_receipt_path=prompt_receipt,
        repository_root=tmp_path,
        require_git_head=False,
    )
    assert any("verifier SHA-256 mismatch" in error for error in errors)