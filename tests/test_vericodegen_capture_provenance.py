from __future__ import annotations

from copy import deepcopy

from research.vericodegen.capture_provenance import (
    CAPTURE_VERSION,
    expected_request_fingerprint,
    normalize_to_ledger_v1,
    parse_offset_timestamp,
    request_fingerprint_payload,
    validate_capture_provenance,
    validate_capture_row_v2,
)
from research.vericodegen.trial_ledger import validate_capture_matrix


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
HASH_F = "f" * 64


def _manifest() -> dict:
    return {
        "provider": "fixture-provider",
        "model": "fixture-model-v1",
        "pilot_task_ids": ["VCG-001"],
        "decoding": {
            "temperature": 0.2,
            "top_p": 1.0,
            "max_output_tokens": 2048,
            "seeds": [101],
        },
        "retry_policy": {"max_attempts": 2},
        "prompt_templates": {
            "direct_sha256": HASH_A,
            "structured_sha256": HASH_B,
        },
    }


def _benchmark_manifest() -> dict:
    return {"task_sha256": {"VCG-001": HASH_C}}


def _row(
    arm: str = "direct",
    *,
    attempt: int = 1,
    retry_feedback_sha256: str | None = None,
    status: str = "completed",
) -> dict:
    row = {
        "capture_version": CAPTURE_VERSION,
        "prompt_id": "VCG-001",
        "seed": 101,
        "arm": arm,
        "attempt": attempt,
        "captured_at": "2026-08-31T03:45:00+00:00",
        "provider": "fixture-provider",
        "model": "fixture-model-v1",
        "system_prompt_sha256": HASH_A if arm == "direct" else HASH_B,
        "benchmark_task_sha256": HASH_C,
        "request_fingerprint_sha256": "0" * 64,
        "retry_feedback_sha256": retry_feedback_sha256,
        "decoding": {
            "temperature": 0.2,
            "top_p": 1.0,
            "max_output_tokens": 2048,
        },
        "generation_status": status,
        "raw_output": "cube(1);" if status == "completed" else None,
        "generated_tokens": 32,
        "wall_clock_seconds": 0.75,
        "estimated_cost_usd": 0.01,
        "provider_request_id": f"req-{arm}-{attempt}",
        "provider_error": None if status == "completed" else "fixture failure",
        "finish_reason": "stop" if status == "completed" else None,
    }
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    return row


def test_valid_capture_v2_passes_structural_and_frozen_provenance_checks():
    row = _row()
    assert validate_capture_row_v2(row) == []
    assert validate_capture_provenance(
        [row], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    ) == []


def test_offset_aware_timestamp_is_required():
    assert parse_offset_timestamp("2026-08-31T03:45:00Z") is not None
    assert parse_offset_timestamp("2026-08-31T03:45:00+05:30") is not None
    assert parse_offset_timestamp("2026-08-31T03:45:00") is None

    row = _row()
    row["captured_at"] = "2026-08-31T03:45:00"
    assert any("offset-aware" in error for error in validate_capture_row_v2(row))


def test_first_attempt_cannot_claim_retry_feedback():
    row = _row(retry_feedback_sha256=HASH_D)
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    assert any("attempt 1" in error for error in validate_capture_row_v2(row))


def test_retry_attempt_can_bind_exact_feedback_hash():
    row = _row(attempt=2, retry_feedback_sha256=HASH_D)
    assert validate_capture_row_v2(row) == []
    payload = request_fingerprint_payload(row)
    assert payload["retry_feedback_sha256"] == HASH_D


def test_request_fingerprint_detects_metadata_tampering():
    row = _row()
    original = row["request_fingerprint_sha256"]
    row["model"] = "different-model"
    assert row["request_fingerprint_sha256"] == original
    assert any("request_fingerprint_sha256" in error for error in validate_capture_row_v2(row))


def test_provider_and_model_must_match_frozen_manifest():
    row = _row()
    row["provider"] = "wrong-provider"
    row["model"] = "wrong-model"
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    errors = validate_capture_provenance(
        [row], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    )
    assert any("provider mismatch" in error for error in errors)
    assert any("model mismatch" in error for error in errors)


def test_arm_specific_system_prompt_hash_must_match():
    row = _row("structured")
    row["system_prompt_sha256"] = HASH_A
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    errors = validate_capture_provenance(
        [row], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    )
    assert any("system_prompt_sha256 mismatch for structured arm" in error for error in errors)


def test_benchmark_task_hash_must_match_frozen_task_bytes():
    row = _row()
    row["benchmark_task_sha256"] = HASH_E
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    errors = validate_capture_provenance(
        [row], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    )
    assert any("benchmark_task_sha256 mismatch" in error for error in errors)


def test_decoding_settings_must_match_frozen_manifest():
    row = _row()
    row["decoding"] = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 1024,
    }
    row["request_fingerprint_sha256"] = expected_request_fingerprint(row)
    errors = validate_capture_provenance(
        [row], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    )
    assert any("decoding.temperature mismatch" in error for error in errors)
    assert any("decoding.top_p mismatch" in error for error in errors)
    assert any("decoding.max_output_tokens mismatch" in error for error in errors)


def test_duplicate_provider_request_ids_are_rejected():
    direct = _row("direct")
    structured = _row("structured")
    structured["provider_request_id"] = direct["provider_request_id"]
    errors = validate_capture_provenance(
        [direct, structured], manifest=_manifest(), benchmark_manifest=_benchmark_manifest()
    )
    assert any("provider_request_id values must be unique" in error for error in errors)


def test_timeout_and_error_rows_require_null_output():
    row = _row(status="timeout")
    assert validate_capture_row_v2(row) == []
    row["raw_output"] = "partial response"
    assert any("raw_output=null" in error for error in validate_capture_row_v2(row))


def test_completed_row_cannot_contain_provider_error():
    row = _row()
    row["provider_error"] = "should not coexist with completion"
    assert any("must not contain provider_error" in error for error in validate_capture_row_v2(row))


def test_normalization_preserves_evidence_fields_needed_by_lower_ledger():
    rows = [_row("direct"), _row("structured")]
    normalized = normalize_to_ledger_v1(rows)
    assert all(row["capture_version"] == "vericodegen-captured-attempt-v1" for row in normalized)
    assert normalized[0]["provider_request_id"] == rows[0]["provider_request_id"]
    assert normalized[0]["raw_output"] == rows[0]["raw_output"]
    assert validate_capture_matrix(normalized, _manifest()) == []


def test_request_fingerprint_is_deterministic_for_same_request_metadata():
    first = _row()
    second = deepcopy(first)
    second["captured_at"] = "2026-08-31T03:46:00+00:00"
    second["raw_output"] = "different completion bytes"
    second["generated_tokens"] = 999
    second["wall_clock_seconds"] = 4.5
    second["estimated_cost_usd"] = 2.0
    assert expected_request_fingerprint(first) == expected_request_fingerprint(second)


def test_request_fingerprint_changes_with_seed_attempt_or_feedback():
    base = _row()
    changed_seed = deepcopy(base)
    changed_seed["seed"] = 202
    changed_attempt = _row(attempt=2, retry_feedback_sha256=HASH_F)
    assert expected_request_fingerprint(base) != expected_request_fingerprint(changed_seed)
    assert expected_request_fingerprint(base) != expected_request_fingerprint(changed_attempt)
