from __future__ import annotations

from pathlib import Path

import pytest

from research.s3.protocol_freezer import (
    ProtocolError,
    assert_frozen_protocol,
    compute_protocol_sha256,
    load_protocol,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "research" / "s3" / "S3_SCIENTIFIC_PROTOCOL_V0.json"


def canonical() -> dict:
    return load_protocol(PROTOCOL_PATH)


def rehash(payload: dict) -> dict:
    payload["protocol_sha256"] = compute_protocol_sha256(payload)
    return payload


def test_checked_in_protocol_is_frozen_and_hash_bound() -> None:
    payload = canonical()
    assert payload["execution_authorized"] is False
    assert payload["outcomes_observed"] is False
    assert payload["historical_typed_parser_claim"] == "FALSIFIED_VALIDATION_DOMINANT_UNCHANGED"
    assert payload["protocol_sha256"] == compute_protocol_sha256(payload)
    assert validate_protocol(payload) == []
    assert_frozen_protocol(payload)


@pytest.mark.parametrize("field", ["execution_authorized", "outcomes_observed"])
def test_outcome_or_authorization_flip_fails_even_when_rehashed(field: str) -> None:
    payload = canonical()
    payload[field] = True
    rehash(payload)
    with pytest.raises(ProtocolError):
        assert_frozen_protocol(payload)


def test_hypothesis_or_ablation_drift_fails_when_rehashed() -> None:
    payload = canonical()
    payload["hypotheses"].pop()
    payload["arms"]["mechanism_ablations"][0]["same_retry_budget"] = False
    rehash(payload)
    errors = validate_protocol(payload)
    assert any("H1, H2, H3" in error for error in errors)
    assert any("same_retry_budget" in error for error in errors)


def test_trial_seed_and_uncertainty_drift_fails_when_rehashed() -> None:
    payload = canonical()
    payload["trials"]["predeclared_trial_ids"][-1] = 7
    payload["uncertainty_and_tests"]["primary_confidence_interval"]["replicates"] = 9999
    rehash(payload)
    errors = validate_protocol(payload)
    assert any("trial IDs changed" in error for error in errors)
    assert any("confidence-interval contract changed" in error for error in errors)


def test_failure_policy_and_falsifier_removal_fail_when_rehashed() -> None:
    payload = canonical()
    payload["failure_policy"]["timeout_hvr"] = True
    payload["falsifiers"].pop()
    rehash(payload)
    errors = validate_protocol(payload)
    assert any("timeout_hvr" in error for error in errors)
    assert any("F1-F6" in error for error in errors)


def test_historical_typed_parser_boundary_cannot_be_rescued() -> None:
    payload = canonical()
    payload["historical_typed_parser_claim"] = "SUPPORTED"
    rehash(payload)
    assert any("falsification boundary changed" in error for error in validate_protocol(payload))


def test_content_tampering_without_hash_update_is_detected() -> None:
    payload = canonical()
    original_hash = payload["protocol_sha256"]
    payload["metrics"]["secondary"][0] = "made_up_metric"
    assert payload["protocol_sha256"] == original_hash
    errors = validate_protocol(payload)
    assert any("secondary metric set/order changed" in error for error in errors)
    assert any("protocol_sha256" in error for error in errors)


def test_provider_seed_policy_does_not_fake_determinism() -> None:
    payload = canonical()
    assert "provider seeding is unsupported" in payload["trials"]["provider_seed_policy"]
    assert payload["trials"]["drop_or_replace_after_outcome_access"] is False
