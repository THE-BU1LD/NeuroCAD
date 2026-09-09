from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .json_io import strict_json_loads

EXTERNAL_EVALUATION_VERSION = "neurocad-external-evaluation-v0"
DEFAULT_MINIMUM_RECORDS = 160
DEFAULT_MINIMUM_VALID = 120
DEFAULT_MINIMUM_REJECT = 40
_REQUIRED_FIELDS = {
    "task_id",
    "prompt",
    "validity",
    "family",
    "expected_signature",
    "expected_error_class",
    "author_id",
    "adjudicator_id",
    "license_or_permission",
    "source_note",
}


class ExternalChallengeError(ValueError):
    """Raised when a challenge violates a machine-checkable pre-outcome constraint."""


@dataclass(frozen=True)
class ExternalChallengeManifest:
    version: str
    sha256: str
    record_count: int
    valid_count: int
    reject_count: int
    families: dict[str, int]
    authors: dict[str, int]
    adjudicators: dict[str, int]
    execution_authorized: bool = False
    evidence_status: str = "MACHINE_VALIDATION_ONLY_HUMAN_PROTOCOL_REVIEW_REQUIRED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sha256": self.sha256,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "reject_count": self.reject_count,
            "families": dict(self.families),
            "authors": dict(self.authors),
            "adjudicators": dict(self.adjudicators),
            "execution_authorized": self.execution_authorized,
            "evidence_status": self.evidence_status,
        }


def _nonempty_string(record: Mapping[str, Any], key: str, index: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ExternalChallengeError(f"record {index}: {key} must be a non-empty string")
    return value.strip()


def _validate_record(record: Mapping[str, Any], index: int) -> dict[str, Any]:
    missing = sorted(_REQUIRED_FIELDS - set(record))
    if missing:
        raise ExternalChallengeError(f"record {index}: missing required fields: {', '.join(missing)}")

    normalized = dict(record)
    for key in (
        "task_id",
        "prompt",
        "family",
        "author_id",
        "adjudicator_id",
        "license_or_permission",
        "source_note",
    ):
        normalized[key] = _nonempty_string(record, key, index)

    validity = record.get("validity")
    if validity not in {"valid", "reject"}:
        raise ExternalChallengeError(f"record {index}: validity must be 'valid' or 'reject'")
    normalized["validity"] = validity

    if normalized["author_id"] == normalized["adjudicator_id"]:
        raise ExternalChallengeError(f"record {index}: author_id and adjudicator_id must be different")

    expected_signature = record.get("expected_signature")
    expected_error_class = record.get("expected_error_class")
    if validity == "valid":
        if not isinstance(expected_signature, dict) or not expected_signature:
            raise ExternalChallengeError(f"record {index}: valid tasks require a non-empty expected_signature object")
        if expected_error_class is not None:
            raise ExternalChallengeError(f"record {index}: valid tasks require expected_error_class=null")
    else:
        if expected_signature is not None:
            raise ExternalChallengeError(f"record {index}: reject tasks require expected_signature=null")
        if not isinstance(expected_error_class, str) or not expected_error_class.strip():
            raise ExternalChallengeError(f"record {index}: reject tasks require a non-empty expected_error_class")
        normalized["expected_error_class"] = expected_error_class.strip()

    # Canonical JSON serialization later uses allow_nan=False, but fail here with
    # a record-local error rather than relying on a less-informative encoder error.
    try:
        json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ExternalChallengeError(f"record {index}: record is not canonical-JSON serializable: {exc}") from exc
    return normalized


def validate_external_challenge(
    records: Iterable[Mapping[str, Any]],
    *,
    minimum_records: int = DEFAULT_MINIMUM_RECORDS,
    minimum_valid: int = DEFAULT_MINIMUM_VALID,
    minimum_reject: int = DEFAULT_MINIMUM_REJECT,
) -> tuple[list[dict[str, Any]], ExternalChallengeManifest]:
    """Validate the machine-checkable envelope and canonicalize challenge data.

    Defaults implement only the minimum population sizes and structural rules
    that can be checked without scientific judgment. They do not establish
    author independence, adjudication quality, licensing validity, leakage
    absence, family-quota compliance, comparator fairness, or execution
    authorization. Those remain separate human/provenance gates in
    ``research/protocols/EXTERNAL_EVALUATION_V0.md``.

    Smaller thresholds are accepted only as explicit arguments so unit tests
    can exercise the validator without pretending a toy fixture satisfies the
    scientific protocol.
    """

    for name, value in (
        ("minimum_records", minimum_records),
        ("minimum_valid", minimum_valid),
        ("minimum_reject", minimum_reject),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ExternalChallengeError(f"{name} must be a non-negative integer")
    if minimum_valid + minimum_reject > minimum_records:
        raise ExternalChallengeError("minimum_valid + minimum_reject cannot exceed minimum_records")

    normalized = [_validate_record(record, index) for index, record in enumerate(records, start=1)]
    if len(normalized) < minimum_records:
        raise ExternalChallengeError(
            f"challenge has {len(normalized)} records; protocol requires at least {minimum_records}"
        )

    task_ids = [record["task_id"] for record in normalized]
    duplicate_ids = sorted(task_id for task_id, count in Counter(task_ids).items() if count > 1)
    if duplicate_ids:
        raise ExternalChallengeError(f"duplicate task_id values: {', '.join(duplicate_ids)}")

    prompt_keys = [record["prompt"].casefold().strip() for record in normalized]
    if len(prompt_keys) != len(set(prompt_keys)):
        raise ExternalChallengeError("challenge contains duplicate prompts after case/whitespace normalization")

    valid_count = sum(record["validity"] == "valid" for record in normalized)
    reject_count = len(normalized) - valid_count
    if valid_count < minimum_valid:
        raise ExternalChallengeError(f"challenge has {valid_count} valid tasks; protocol requires at least {minimum_valid}")
    if reject_count < minimum_reject:
        raise ExternalChallengeError(f"challenge has {reject_count} reject tasks; protocol requires at least {minimum_reject}")

    if len({record["author_id"] for record in normalized}) < 2:
        raise ExternalChallengeError("challenge requires at least two distinct author identifiers")

    canonical = canonical_external_challenge_jsonl(normalized)
    manifest = ExternalChallengeManifest(
        version=EXTERNAL_EVALUATION_VERSION,
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        record_count=len(normalized),
        valid_count=valid_count,
        reject_count=reject_count,
        families=dict(sorted(Counter(record["family"] for record in normalized).items())),
        authors=dict(sorted(Counter(record["author_id"] for record in normalized).items())),
        adjudicators=dict(sorted(Counter(record["adjudicator_id"] for record in normalized).items())),
    )
    return normalized, manifest


def canonical_external_challenge_jsonl(records: Iterable[Mapping[str, Any]]) -> str:
    """Serialize challenge records deterministically without reordering tasks."""

    return "".join(
        json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
        for record in records
    )


def load_external_challenge(
    path: Path,
    *,
    minimum_records: int = DEFAULT_MINIMUM_RECORDS,
    minimum_valid: int = DEFAULT_MINIMUM_VALID,
    minimum_reject: int = DEFAULT_MINIMUM_REJECT,
) -> tuple[list[dict[str, Any]], ExternalChallengeManifest]:
    """Load strict JSONL after machine checks; never authorize scientific execution."""

    records: list[Mapping[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            raise ExternalChallengeError(f"line {line_number}: blank lines are not allowed")
        try:
            value = strict_json_loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ExternalChallengeError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ExternalChallengeError(f"line {line_number}: each JSONL record must be an object")
        records.append(value)
    return validate_external_challenge(
        records,
        minimum_records=minimum_records,
        minimum_valid=minimum_valid,
        minimum_reject=minimum_reject,
    )
