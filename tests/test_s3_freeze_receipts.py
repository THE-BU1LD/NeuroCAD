from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S3 = ROOT / "research" / "s3"


def _load(name: str) -> dict:
    return json.loads((S3 / name).read_text(encoding="utf-8"))


def _canonical_sha256(payload: dict, hash_field: str) -> str:
    scientific = {key: value for key, value in payload.items() if key != hash_field}
    encoded = json.dumps(
        scientific,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_common_validation_policy_freeze_is_self_consistent() -> None:
    policy = _load("COMMON_VALIDATION_POLICY_V0.json")
    assert policy["status"] == "FROZEN_PREOUTCOME"
    assert policy["outcomes_observed"] is False
    assert policy["same_final_verifier_all_arms"] is True
    assert policy["human_correction_disabled"] is True
    assert policy["retain_raw_outputs"] is True
    assert policy["retain_failed_trials"] is True
    assert policy["retain_compile_logs"] is True
    assert policy["retry_policy"]["same_attempt_limit_all_arms"] is True
    assert policy["policy_sha256"] == _canonical_sha256(policy, "policy_sha256")


def test_model_and_four_controls_match_frozen_protocol() -> None:
    protocol = _load("S3_SCIENTIFIC_PROTOCOL_V0.json")
    freeze = _load("S3_MODEL_BASELINE_FREEZE_V0.json")

    expected_controls = [arm["id"] for arm in protocol["arms"]["mechanism_ablations"]]
    frozen_controls = [arm["id"] for arm in freeze["baseline_families"]]
    expected_primary = [arm["id"] for arm in protocol["arms"]["primary"]]

    assert freeze["status"] == "FROZEN_PREOUTCOME"
    assert freeze["outcomes_observed"] is False
    assert frozen_controls == expected_controls
    assert freeze["primary_arms"] == expected_primary
    assert freeze["arm_count"] == len(expected_primary) + len(expected_controls) == 6
    assert freeze["trial_ids"] == protocol["trials"]["predeclared_trial_ids"]
    assert all(arm["matched_provider_model"] is True for arm in freeze["baseline_families"])
    assert freeze["evaluated_model"]["revision"] == "gpt-5.4-2026-03-05"
    assert freeze["freeze_sha256"] == _canonical_sha256(freeze, "freeze_sha256")


def test_s3_analysis_plan_matches_frozen_protocol() -> None:
    protocol = _load("S3_SCIENTIFIC_PROTOCOL_V0.json")
    plan = _load("S3_ANALYSIS_PLAN_V0.json")

    uncertainty = protocol["uncertainty_and_tests"]
    assert plan["status"] == "FROZEN_PREOUTCOME"
    assert plan["outcomes_observed"] is False
    assert plan["scientific_protocol_sha256"] == protocol["protocol_sha256"]
    assert plan["paired_unit"] == uncertainty["paired_unit"]
    assert plan["primary_test"] == uncertainty["primary_test"]
    assert plan["primary_confidence_interval"] == uncertainty["primary_confidence_interval"]
    assert plan["analysis_plan_sha256"] == _canonical_sha256(
        plan, "analysis_plan_sha256"
    )


def test_preauthorization_cannot_open_outcome_access() -> None:
    protocol = _load("S3_SCIENTIFIC_PROTOCOL_V0.json")
    freeze = _load("S3_MODEL_BASELINE_FREEZE_V0.json")
    policy = _load("COMMON_VALIDATION_POLICY_V0.json")
    plan = _load("S3_ANALYSIS_PLAN_V0.json")
    receipt = _load("S3_PREAUTHORIZATION_V0.json")

    assert receipt["status"] == "PREOUTCOME_LOCKED_NOT_AUTHORIZED"
    assert receipt["execution_authorized"] is False
    assert receipt["outcome_access_allowed"] is False
    assert receipt["outcomes_observed"] is False
    assert receipt["historical_typed_parser_claim"] == (
        "FALSIFIED_VALIDATION_DOMINANT_UNCHANGED"
    )
    assert receipt["scientific_protocol_sha256"] == protocol["protocol_sha256"]
    assert receipt["model_baseline_freeze_sha256"] == freeze["freeze_sha256"]
    assert receipt["common_validation_policy"]["sha256"] == policy["policy_sha256"]
    assert receipt["analysis_plan_sha256"] == plan["analysis_plan_sha256"]
    assert len(receipt["baseline_families"]) == 4
    assert all(
        arm["identity"] == receipt["evaluated_model"]
        and arm["matched_provider_model"] is True
        for arm in receipt["baseline_families"]
    )
    assert receipt["execution_counts"]["selected_prompt_count"] is None
    assert receipt["execution_counts"]["maximum_call_ceiling"] is None
    assert receipt["remaining_fail_closed_authorization_gates"]
    assert receipt["preauthorization_sha256"] == _canonical_sha256(
        receipt, "preauthorization_sha256"
    )
