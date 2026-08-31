import copy
import json
from pathlib import Path

import pytest

from research.vericodegen.stage2_manifest import (
    ManifestError,
    assert_executable,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64


def _valid_manifest():
    return {
        "manifest_version": "vericodegen-stage2-v1",
        "stage": "stage2_frozen_pilot",
        "authorized": True,
        "scientific_evidence": False,
        "benchmark_manifest_sha256": HASH_A,
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
        },
        "prompt_templates": {
            "direct_sha256": HASH_B,
            "structured_sha256": HASH_C,
        },
        "verifier_sha256": HASH_D,
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


def test_missing_provenance_hashes_fail_closed():
    manifest = _valid_manifest()
    manifest["benchmark_manifest_sha256"] = None
    manifest["verifier_sha256"] = "short"
    manifest["prompt_templates"]["direct_sha256"] = None

    errors = validate_manifest(manifest, require_authorized=True)
    assert any(error.startswith("benchmark_manifest_sha256") for error in errors)
    assert any(error.startswith("verifier_sha256") for error in errors)
    assert any(error.startswith("prompt_templates.direct_sha256") for error in errors)


def test_example_manifest_is_explicitly_non_authorized_and_non_executable():
    path = ROOT / "research" / "vericodegen" / "stage2_run_manifest.example.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert manifest["authorized"] is False
    assert manifest["scientific_evidence"] is False
    with pytest.raises(ManifestError):
        assert_executable(manifest)
