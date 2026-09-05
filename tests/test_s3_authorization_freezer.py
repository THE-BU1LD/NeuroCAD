from __future__ import annotations

import copy

import pytest

from research.s3.authorization_freezer import (
    FROZEN_PROTOCOL_SHA256,
    AuthorizationError,
    assert_authorized,
    compute_authorization_sha256,
    freeze_authorization,
    validate_authorization_manifest,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64
HEX_1 = "1" * 64
HEX_2 = "2" * 64
HEX_3 = "3" * 64


def _identity() -> dict[str, str]:
    return {
        "provider": "provider.example",
        "model": "model-family-v1",
        "revision": "revision-20260905",
        "runtime": "runtime-build-20260905",
    }


def complete_manifest() -> dict:
    identity = _identity()
    return {
        "schema_version": "neurocad.s3.execution-authorization.v0",
        "status": "FROZEN_AUTHORIZED",
        "execution_authorized": True,
        "outcome_access_allowed": True,
        "outcomes_observed": False,
        "historical_typed_parser_claim": "FALSIFIED_VALIDATION_DOMINANT_UNCHANGED",
        "artifact_bindings": {
            "final_selection_sha256": HEX_A,
            "scientific_protocol_sha256": FROZEN_PROTOCOL_SHA256,
            "prompt_bundle_sha256": HEX_B,
            "schema_bundle_sha256": HEX_C,
            "shared_verifier_sha256": HEX_D,
            "environment_lock_sha256": HEX_E,
            "analysis_plan_sha256": HEX_F,
        },
        "evaluated_model": identity,
        "baseline_families": [
            {
                "id": f"baseline_family_{index}",
                "identity": dict(identity),
                "matched_provider_model": True,
            }
            for index in range(1, 5)
        ],
        "common_validation_policy": {
            "sha256": HEX_1,
            "applies_to_all_arms": True,
            "same_final_verifier_all_arms": True,
            "human_correction_disabled": True,
            "retain_raw_outputs": True,
            "retain_failed_trials": True,
            "retain_compile_logs": True,
        },
        "decoding_and_budget": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 4096,
            "max_attempts_per_prompt_arm_trial": 2,
            "feedback_policy": "identical frozen retry and feedback policy across all compared arms",
            "same_budget_all_arms": True,
            "cost_cap_usd": 250.0,
        },
        "trial_ids": [2026090501, 2026090502, 2026090503, 2026090504, 2026090505],
        "execution_counts": {
            "selected_prompt_count": 120,
            "arm_count": 6,
            "maximum_call_ceiling": 120 * 6 * 5 * 2,
        },
        "independent_manifest_review": {
            "completed": True,
            "outcomes_unobserved_at_review": True,
            "attestation_sha256": HEX_2,
        },
    }


def test_freeze_authorization_builds_deterministic_valid_receipt() -> None:
    manifest = complete_manifest()
    frozen = freeze_authorization(manifest)

    assert frozen["authorization_sha256"] == compute_authorization_sha256(frozen)
    assert validate_authorization_manifest(frozen) == []
    assert_authorized(frozen)


def test_existing_hash_is_part_of_no_scientific_payload() -> None:
    manifest = complete_manifest()
    first = freeze_authorization(manifest)
    second_input = dict(first)
    second_input["authorization_sha256"] = HEX_3

    assert compute_authorization_sha256(second_input) == first["authorization_sha256"]


def test_rejects_placeholder_model_identity() -> None:
    manifest = complete_manifest()
    manifest["evaluated_model"]["revision"] = "TBD"
    for baseline in manifest["baseline_families"]:
        baseline["identity"]["revision"] = "TBD"

    with pytest.raises(AuthorizationError, match="non-placeholder"):
        freeze_authorization(manifest)


def test_rejects_nonmatched_baseline_identity() -> None:
    manifest = complete_manifest()
    manifest["baseline_families"][2]["identity"]["model"] = "different-model"

    with pytest.raises(AuthorizationError, match="exactly match evaluated_model"):
        freeze_authorization(manifest)


def test_rejects_wrong_baseline_family_count() -> None:
    manifest = complete_manifest()
    manifest["baseline_families"] = manifest["baseline_families"][:3]

    with pytest.raises(AuthorizationError, match="exactly four"):
        freeze_authorization(manifest)


def test_rejects_duplicate_baseline_family_ids() -> None:
    manifest = complete_manifest()
    manifest["baseline_families"][3]["id"] = manifest["baseline_families"][0]["id"]

    with pytest.raises(AuthorizationError, match="ids must be unique"):
        freeze_authorization(manifest)


def test_rejects_protocol_digest_drift() -> None:
    manifest = complete_manifest()
    manifest["artifact_bindings"]["scientific_protocol_sha256"] = HEX_A

    with pytest.raises(AuthorizationError, match="frozen S3 protocol"):
        freeze_authorization(manifest)


def test_rejects_outcome_access_after_outcomes_already_observed() -> None:
    manifest = complete_manifest()
    manifest["outcomes_observed"] = True

    with pytest.raises(AuthorizationError, match="outcomes_observed must be false"):
        freeze_authorization(manifest)


def test_rejects_call_ceiling_that_does_not_match_frozen_budget() -> None:
    manifest = complete_manifest()
    manifest["execution_counts"]["maximum_call_ceiling"] -= 1

    with pytest.raises(AuthorizationError, match="maximum_call_ceiling"):
        freeze_authorization(manifest)


def test_rejects_asymmetric_budget_policy() -> None:
    manifest = complete_manifest()
    manifest["decoding_and_budget"]["same_budget_all_arms"] = False

    with pytest.raises(AuthorizationError, match="same_budget_all_arms"):
        freeze_authorization(manifest)


def test_rejects_missing_independent_review() -> None:
    manifest = complete_manifest()
    manifest["independent_manifest_review"]["completed"] = False

    with pytest.raises(AuthorizationError, match="independent_manifest_review.completed"):
        freeze_authorization(manifest)


def test_tampering_after_freeze_invalidates_receipt() -> None:
    frozen = freeze_authorization(complete_manifest())
    tampered = copy.deepcopy(frozen)
    tampered["decoding_and_budget"]["max_output_tokens"] = 8192

    errors = validate_authorization_manifest(tampered)
    assert "authorization_sha256 does not match canonical authorization content" in errors
