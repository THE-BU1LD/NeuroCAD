"""Parser-only fixtures: no benchmark materialization, labels, or outcome execution."""

from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from core.external_evaluation import (
    ExternalChallengeError,
    canonical_external_challenge_jsonl,
    load_external_challenge,
    validate_external_challenge,
)

_TEST_THRESHOLDS = {"minimum_records": 2, "minimum_valid": 1, "minimum_reject": 1}


def _records():
    return [
        {
            "task_id": "parser-valid",
            "prompt": "parser fixture one",
            "validity": "valid",
            "family": "parser-only",
            "expected_signature": {"kind": "fixture", "size": [1, 2, 3]},
            "expected_error_class": None,
            "author_id": "fixture-author-a",
            "adjudicator_id": "fixture-reviewer",
            "license_or_permission": "test fixture only",
            "source_note": "not benchmark data",
        },
        {
            "task_id": "parser-reject",
            "prompt": "parser fixture two",
            "validity": "reject",
            "family": "parser-only",
            "expected_signature": None,
            "expected_error_class": "fixture_error",
            "author_id": "fixture-author-b",
            "adjudicator_id": "fixture-reviewer",
            "license_or_permission": "test fixture only",
            "source_note": "not benchmark data",
        },
    ]


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("line_ending", ["\n", "\r\n", "no-final-lf"])
def test_canonical_jsonl_round_trips_embedded_unicode_separators(tmp_path, separator, line_ending):
    records = _records()
    records[0]["prompt"] = f"first{separator}second"
    normalized, before = validate_external_challenge(records, **_TEST_THRESHOLDS)
    canonical = canonical_external_challenge_jsonl(normalized)
    text = canonical.rstrip("\n") if line_ending == "no-final-lf" else canonical.replace("\n", line_ending)
    path = tmp_path / "parser.jsonl"
    path.write_bytes(text.encode("utf-8"))

    loaded, after = load_external_challenge(path, **_TEST_THRESHOLDS)

    assert loaded == normalized
    assert after.sha256 == before.sha256
    assert after.execution_authorized is False


@pytest.mark.parametrize("record", [None, 42, True, [], "invalid"])
def test_direct_api_rejects_non_object_records_with_record_context(record):
    records = _records()
    records[0] = record
    with pytest.raises(ExternalChallengeError, match="record 1:.*object"):
        validate_external_challenge(records, **_TEST_THRESHOLDS)


@pytest.mark.parametrize("records", [None, 42, "invalid", b"invalid", {}])
def test_direct_api_rejects_non_record_containers(records):
    with pytest.raises(ExternalChallengeError, match="records must be an iterable of objects"):
        validate_external_challenge(records, **_TEST_THRESHOLDS)


@pytest.mark.parametrize("validity", [[], {}, {"valid"}])
def test_unhashable_validity_produces_domain_error(validity):
    records = _records()
    records[0]["validity"] = validity
    with pytest.raises(ExternalChallengeError, match="record 1: validity"):
        validate_external_challenge(records, **_TEST_THRESHOLDS)


@pytest.mark.parametrize("payload", [b"\xff", b"{\"prompt\":\"\xc3\"}\n"])
def test_non_utf8_input_produces_domain_error(tmp_path, payload):
    path = tmp_path / "invalid.jsonl"
    path.write_bytes(payload)
    with pytest.raises(ExternalChallengeError, match="valid UTF-8"):
        load_external_challenge(path, **_TEST_THRESHOLDS)


@pytest.mark.parametrize("field", ["prompt", "source_note"])
def test_unpaired_surrogate_produces_record_local_domain_error(field):
    records = _records()
    records[0][field] = "invalid-\ud800-text"
    with pytest.raises(ExternalChallengeError, match="record 1:.*serializable"):
        validate_external_challenge(records, **_TEST_THRESHOLDS)


def test_direct_api_uses_same_nesting_limit_as_jsonl_loader():
    records = _records()
    nested = "leaf"
    for _ in range(257):
        nested = [nested]
    records[0]["extra"] = nested
    with pytest.raises(ExternalChallengeError, match="record 1:.*nesting"):
        validate_external_challenge(records, **_TEST_THRESHOLDS)


def test_normalized_snapshot_does_not_alias_caller_nested_values():
    records = _records()
    normalized, manifest = validate_external_challenge(records, **_TEST_THRESHOLDS)
    snapshot = deepcopy(normalized)
    records[0]["expected_signature"]["size"][0] = 999
    assert normalized == snapshot
    assert hashlib.sha256(canonical_external_challenge_jsonl(normalized).encode("utf-8")).hexdigest() == manifest.sha256
    assert manifest.execution_authorized is False


def test_existing_canonical_bytes_and_default_protocol_thresholds_are_unchanged():
    records = _records()
    original_bytes = canonical_external_challenge_jsonl(records).encode("utf-8")
    normalized, manifest = validate_external_challenge(iter(records), **_TEST_THRESHOLDS)
    assert canonical_external_challenge_jsonl(normalized).encode("utf-8") == original_bytes
    assert manifest.sha256 == hashlib.sha256(original_bytes).hexdigest()
    assert manifest.execution_authorized is False
    with pytest.raises(ExternalChallengeError, match="protocol requires at least 160"):
        validate_external_challenge(records)


@pytest.mark.parametrize("suffix", ["\n\n", "\n \n", "\r\n\r\n"])
def test_physical_blank_lines_still_fail_closed(tmp_path, suffix):
    text = canonical_external_challenge_jsonl(_records()).rstrip("\n") + suffix
    path = tmp_path / "blank.jsonl"
    path.write_bytes(text.encode("utf-8"))
    with pytest.raises(ExternalChallengeError, match="blank lines are not allowed"):
        load_external_challenge(path, **_TEST_THRESHOLDS)
