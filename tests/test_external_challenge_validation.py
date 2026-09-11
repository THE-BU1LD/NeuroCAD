from __future__ import annotations

import json

import pytest

from core.external_evaluation import (
    ExternalChallengeError,
    canonical_external_challenge_jsonl,
    load_external_challenge,
    validate_external_challenge,
)


def _record(
    task_id: str,
    prompt: str,
    *,
    validity: str = "valid",
    author_id: str = "author-a",
    adjudicator_id: str = "judge-a",
) -> dict[str, object]:
    valid = validity == "valid"
    return {
        "task_id": task_id,
        "prompt": prompt,
        "validity": validity,
        "family": "plate" if valid else "missing-dimension",
        "expected_signature": {"kind": "box", "size": [40, 30, 3]} if valid else None,
        "expected_error_class": None if valid else "missing_required_dimension",
        "author_id": author_id,
        "adjudicator_id": adjudicator_id,
        "license_or_permission": "author granted research-use permission",
        "source_note": "independently authored",
    }


def _toy_challenge() -> list[dict[str, object]]:
    return [
        _record("EXT-001", "a 40 x 30 x 3 mm plate"),
        _record("EXT-002", "a 50 by 35 by 4 mm plate", author_id="author-b"),
        _record(
            "EXT-003",
            "a plate 40 mm wide and 3 mm thick",
            validity="reject",
            adjudicator_id="judge-b",
        ),
        _record(
            "EXT-004",
            "a plate with four 4 mm holes",
            validity="reject",
            author_id="author-b",
            adjudicator_id="judge-b",
        ),
    ]


def test_toy_challenge_can_validate_only_with_explicit_test_thresholds() -> None:
    normalized, manifest = validate_external_challenge(
        _toy_challenge(),
        minimum_records=4,
        minimum_valid=2,
        minimum_reject=2,
    )

    assert len(normalized) == 4
    assert manifest.record_count == 4
    assert manifest.valid_count == 2
    assert manifest.reject_count == 2
    assert len(manifest.sha256) == 64
    assert manifest.authors == {"author-a": 2, "author-b": 2}
    assert manifest.execution_authorized is False
    assert manifest.evidence_status == "MACHINE_VALIDATION_ONLY_HUMAN_PROTOCOL_REVIEW_REQUIRED"
    assert manifest.to_dict()["execution_authorized"] is False


def test_protocol_defaults_reject_toy_challenge() -> None:
    with pytest.raises(ExternalChallengeError, match="protocol requires at least 160"):
        validate_external_challenge(_toy_challenge())


def test_author_cannot_adjudicate_same_record() -> None:
    records = _toy_challenge()
    records[0]["adjudicator_id"] = "author-a"

    with pytest.raises(ExternalChallengeError, match="author_id and adjudicator_id must be different"):
        validate_external_challenge(records, minimum_records=4, minimum_valid=2, minimum_reject=2)


def test_valid_and_reject_labels_require_opposite_reference_fields() -> None:
    valid_records = _toy_challenge()
    valid_records[0]["expected_signature"] = None
    with pytest.raises(ExternalChallengeError, match="valid tasks require a non-empty expected_signature"):
        validate_external_challenge(valid_records, minimum_records=4, minimum_valid=2, minimum_reject=2)

    reject_records = _toy_challenge()
    reject_records[2]["expected_signature"] = {"kind": "box"}
    with pytest.raises(ExternalChallengeError, match="reject tasks require expected_signature=null"):
        validate_external_challenge(reject_records, minimum_records=4, minimum_valid=2, minimum_reject=2)


def test_duplicate_ids_and_prompts_fail_closed() -> None:
    duplicate_id = _toy_challenge()
    duplicate_id[1]["task_id"] = "EXT-001"
    with pytest.raises(ExternalChallengeError, match="duplicate task_id"):
        validate_external_challenge(duplicate_id, minimum_records=4, minimum_valid=2, minimum_reject=2)

    duplicate_prompt = _toy_challenge()
    duplicate_prompt[1]["prompt"] = "  A 40 X 30 X 3 MM PLATE  "
    with pytest.raises(ExternalChallengeError, match="duplicate prompts"):
        validate_external_challenge(duplicate_prompt, minimum_records=4, minimum_valid=2, minimum_reject=2)


def test_canonical_jsonl_hash_is_stable_and_order_sensitive() -> None:
    records = _toy_challenge()
    _, first = validate_external_challenge(records, minimum_records=4, minimum_valid=2, minimum_reject=2)
    _, second = validate_external_challenge(list(records), minimum_records=4, minimum_valid=2, minimum_reject=2)
    _, reversed_manifest = validate_external_challenge(
        list(reversed(records)),
        minimum_records=4,
        minimum_valid=2,
        minimum_reject=2,
    )

    assert first.sha256 == second.sha256
    assert first.sha256 != reversed_manifest.sha256
    assert canonical_external_challenge_jsonl(records).endswith("\n")


def test_loader_rejects_blank_lines_and_duplicate_json_keys(tmp_path) -> None:
    path = tmp_path / "challenge.jsonl"
    path.write_text(json.dumps(_toy_challenge()[0]) + "\n\n", encoding="utf-8")
    with pytest.raises(ExternalChallengeError, match="blank lines are not allowed"):
        load_external_challenge(path, minimum_records=1, minimum_valid=1, minimum_reject=0)

    duplicate = dict(_toy_challenge()[0])
    raw = json.dumps(duplicate)
    duplicate_key_raw = raw[:-1] + ',"task_id":"EXT-999"}'
    path.write_text(duplicate_key_raw + "\n", encoding="utf-8")
    with pytest.raises(ExternalChallengeError, match="invalid JSON"):
        load_external_challenge(path, minimum_records=1, minimum_valid=1, minimum_reject=0)
