import json
from pathlib import Path

import pytest

from research.vericodegen.stage2_manifest import (
    MANIFEST_VERSION,
    SAFE_EVALUATION_ENTRYPOINT,
    ManifestError,
    assert_executable,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
HASH_F = "f" * 64
HASH_0 = "0" * 64
HASH_1 = "1" * 64


def _valid_manifest():
    return {
        "manifest_version": MANIFEST_VERSION,
        "stage": "stage2_frozen_pilot",
        "authorized": True,
        "scientific_evidence": False,
        "evaluation_entrypoint": SAFE_EVALUATION_ENTRYPOINT,
        "benchmark_manifest_sha256": HASH_A,
        "pilot_selection_sha256": HASH_B,
        "structured_schema_sha256": HASH_C,
        "verifier_sha256": HASH_D,
        "analysis_plan_sha256": HASH_E,
        "pilot_task_ids": ["VCG-001", "VCG-041", "VCG-081"],
        "provider": "fixture-provider",
        "model": "fixture-model-v1",
        "decoding": {
            "temperature": 0.2,
            "top_p": 1.0,
            "max_output_tokens": 2048,
            "seeds": [101, 202],
        },
        "retry_policy": {
            "max_attempts": 2,
            "feedback_policy": "One compiler/verifier error may be returned symmetrically to either arm.",
            "same_attempt_limit_both_arms": True,
            "human_correction_allowed": False,
        },
        "prompt_templates": {
            "direct_sha256": HASH_F,
            "structured_sha256": HASH_0,
            "receipt_sha256": HASH_1,
        },
        "environment": {
            "openscad_version": "OpenSCAD 2021.01",
            "openscad_fn": 64,
            "compile_timeout_seconds": 60,
        },
        "retention_policy": {
            "retain_raw_outputs": True,
            "retain_failed_trials": True,
            "retain_compile_logs": True,
        },
        "git_commit": "6e04ecf6d2f8633da2f19dcff251239307520d00",
        "cost_cap_usd": 25.0,
        "estimated_max_calls": 24,
        "notes": "fixture only",
    }


def test_complete_authorized_manifest_is_executable():
    manifest = _valid_manifest()
    assert validate_manifest(manifest, require_authorized=True) == []
    assert_executable(manifest)


def test_authorization_is_a_hard_execution_gate():
    manifest = _valid_manifest()
    manifest["authorized"] = False

    structural = validate_manifest(manifest, require_authorized=False)
    assert "authorized must be true before any external Stage 2 execution" not in structural

    with pytest.raises(ManifestError, match="authorized must be true"):
        assert_executable(manifest)


def test_safe_evaluation_entrypoint_is_a_hard_execution_gate():
    manifest = _valid_manifest()
    manifest["evaluation_entrypoint"] = "research.vericodegen.trial_ledger:evaluate_capture"

    errors = validate_manifest(manifest, require_authorized=True)
    assert any("evaluation_entrypoint must equal" in error for error in errors)
    assert any("direct legacy trial_ledger evaluation is forbidden" in error for error in errors)

    with pytest.raises(ManifestError, match="evaluation_entrypoint must equal"):
        assert_executable(manifest)


def test_missing_evaluation_entrypoint_is_rejected():
    manifest = _valid_manifest()
    manifest.pop("evaluation_entrypoint")
    errors = validate_manifest(manifest, require_authorized=True)
    assert any("evaluation_entrypoint must equal" in error for error in errors)


def test_protocol_v1_is_no_longer_executable():
    manifest = _valid_manifest()
    manifest["manifest_version"] = "vericodegen-stage2-v1"
    errors = validate_manifest(manifest, require_authorized=True)
    assert any(MANIFEST_VERSION in error for error in errors)


def test_call_budget_must_match_tasks_arms_seeds_and_retries():
    manifest = _valid_manifest()
    manifest["estimated_max_calls"] = 23

    errors = validate_manifest(manifest, require_authorized=True)
    assert any("estimated_max_calls must equal" in error for error in errors)


def test_duplicate_tasks_and_seeds_are_rejected():
    manifest = _valid_manifest()
    manifest["pilot_task_ids"].append("VCG-001")
    manifest["decoding"]["seeds"].append(101)
    manifest["estimated_max_calls"] = 32

    errors = validate_manifest(manifest, require_authorized=True)
    assert "pilot_task_ids must not contain duplicates" in errors
    assert "decoding.seeds must not contain duplicates" in errors


def test_all_scientific_provenance_hashes_fail_closed_when_missing():
    manifest = _valid_manifest()
    for field in (
        "benchmark_manifest_sha256",
        "pilot_selection_sha256",
        "structured_schema_sha256",
        "verifier_sha256",
        "analysis_plan_sha256",
    ):
        manifest[field] = None
    manifest["prompt_templates"]["direct_sha256"] = None
    manifest["prompt_templates"]["receipt_sha256"] = "short"

    errors = validate_manifest(manifest, require_authorized=True)
    for field in (
        "benchmark_manifest_sha256",
        "pilot_selection_sha256",
        "structured_schema_sha256",
        "verifier_sha256",
        "analysis_plan_sha256",
        "prompt_templates.direct_sha256",
        "prompt_templates.receipt_sha256",
    ):
        assert any(error.startswith(field) for error in errors)


def test_retry_symmetry_and_no_human_correction_are_hard_gates():
    manifest = _valid_manifest()
    manifest["retry_policy"]["same_attempt_limit_both_arms"] = False
    manifest["retry_policy"]["human_correction_allowed"] = True
    errors = validate_manifest(manifest, require_authorized=True)
    assert "retry_policy.same_attempt_limit_both_arms must be true" in errors
    assert "retry_policy.human_correction_allowed must be false" in errors


def test_environment_freezes_openscad_resolution_and_timeout():
    manifest = _valid_manifest()
    manifest["environment"]["openscad_version"] = None
    manifest["environment"]["openscad_fn"] = 4
    manifest["environment"]["compile_timeout_seconds"] = 0
    errors = validate_manifest(manifest, require_authorized=True)
    assert any("openscad_version" in error for error in errors)
    assert any("openscad_fn" in error for error in errors)
    assert any("compile_timeout_seconds" in error for error in errors)


def test_raw_failure_and_compile_log_retention_are_required():
    manifest = _valid_manifest()
    manifest["retention_policy"]["retain_raw_outputs"] = False
    manifest["retention_policy"]["retain_failed_trials"] = False
    manifest["retention_policy"]["retain_compile_logs"] = False
    errors = validate_manifest(manifest, require_authorized=True)
    assert "retention_policy.retain_raw_outputs must be true" in errors
    assert "retention_policy.retain_failed_trials must be true" in errors
    assert "retention_policy.retain_compile_logs must be true" in errors


def test_example_manifest_is_explicitly_non_authorized_and_non_executable():
    path = ROOT / "research" / "vericodegen" / "stage2_run_manifest.example.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == MANIFEST_VERSION
    assert manifest["authorized"] is False
    assert manifest["scientific_evidence"] is False
    assert manifest["evaluation_entrypoint"] == SAFE_EVALUATION_ENTRYPOINT
    assert manifest["retention_policy"] == {
        "retain_raw_outputs": True,
        "retain_failed_trials": True,
        "retain_compile_logs": True,
    }
    with pytest.raises(ManifestError):
        assert_executable(manifest)