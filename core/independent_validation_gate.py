"""Fail-closed pre-outcome validation for independent NeuroCAD evaluation.

This module validates only the metadata needed *before* confirmatory outcome access.
It deliberately cannot authorize execution, inspect outcomes, or unlock adjudication.
A successful report means the machine-checkable preconditions are complete enough
for a separate human authorization review; it is not itself that authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "neurocad-independent-validation-v0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_COMPARATOR_MODES = frozenset({"frozen_comparator", "claim_narrowed"})
_TOP_LEVEL_KEYS = {
    "protocol_version",
    "source",
    "challenge",
    "comparator",
    "endpoint",
    "leakage_review",
    "retention",
    "outcome_access",
}
_SECTION_KEYS = {
    "source": {
        "git_commit",
        "clean_tree",
        "source_surface_sha256",
        "environment_sha256",
        "openscad_identity",
        "output_directory_empty",
    },
    "challenge": {
        "dataset_sha256",
        "provenance",
        "license_or_permission",
        "independent_author_role",
        "coverage_summary_sha256",
        "adjudication_receipt_sha256",
        "no_post_outcome_case_editing",
    },
    "comparator": {
        "mode",
        "receipt_sha256",
        "matched_information",
        "matched_failure_accounting",
        "claim_boundary",
    },
    "endpoint": {
        "primary_name",
        "aggregation_rule",
        "failure_rule",
        "manifest_sha256",
    },
    "leakage_review": {
        "reviewer",
        "receipt_sha256",
        "outcome_blind",
        "passed",
    },
    "retention": {
        "immutable_attempts",
        "resume_allowed",
        "overwrite_allowed",
    },
    "outcome_access": {
        "execution_authorized",
        "outcomes_observed",
        "adjudication_unlocked",
    },
}


@dataclass(frozen=True)
class GateReport:
    """Machine-checkable preauthorization result.

    ``machine_execution_authorized`` is intentionally hard-coded false. The
    validator can establish completeness of a pre-outcome packet, never grant
    scientific execution authority.
    """

    manifest_sha256: str
    ready_for_human_authorization: bool
    blockers: tuple[str, ...]
    machine_execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "ready_for_human_authorization": self.ready_for_human_authorization,
            "blockers": list(self.blockers),
            "machine_execution_authorized": self.machine_execution_authorized,
            "protocol_version": PROTOCOL_VERSION,
        }


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _require_exact_keys(name: str, value: Any, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{name} keys mismatch; missing={missing}, extra={extra}")
    return value


def _require_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def _require_optional_text(name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or null")
    return value.strip() or None


def _require_optional_sha256(name: str, value: Any) -> str | None:
    text = _require_optional_text(name, value)
    if text is not None and not _SHA256.fullmatch(text):
        raise ValueError(f"{name} must be lowercase 64-hex SHA-256 or null")
    return text


def _require_optional_git_sha(name: str, value: Any) -> str | None:
    text = _require_optional_text(name, value)
    if text is not None and not _GIT_SHA.fullmatch(text):
        raise ValueError(f"{name} must be lowercase 40-hex Git commit or null")
    return text


def canonical_manifest_sha256(manifest: dict[str, Any]) -> str:
    """Return the deterministic SHA-256 of the strict JSON manifest."""

    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_preoutcome_manifest(manifest: dict[str, Any]) -> GateReport:
    """Validate a pre-outcome packet without authorizing or executing anything."""

    root = _require_exact_keys("manifest", manifest, _TOP_LEVEL_KEYS)
    if root["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError(f"protocol_version must equal {PROTOCOL_VERSION!r}")

    sections = {
        name: _require_exact_keys(name, root[name], expected)
        for name, expected in _SECTION_KEYS.items()
    }
    source = sections["source"]
    challenge = sections["challenge"]
    comparator = sections["comparator"]
    endpoint = sections["endpoint"]
    leakage = sections["leakage_review"]
    retention = sections["retention"]
    outcome = sections["outcome_access"]

    source_git_commit = _require_optional_git_sha("source.git_commit", source["git_commit"])
    source_surface_sha256 = _require_optional_sha256("source.source_surface_sha256", source["source_surface_sha256"])
    environment_sha256 = _require_optional_sha256("source.environment_sha256", source["environment_sha256"])
    openscad_identity = _require_optional_text("source.openscad_identity", source["openscad_identity"])
    clean_tree = _require_bool("source.clean_tree", source["clean_tree"])
    output_directory_empty = _require_bool("source.output_directory_empty", source["output_directory_empty"])

    dataset_sha256 = _require_optional_sha256("challenge.dataset_sha256", challenge["dataset_sha256"])
    provenance = _require_optional_text("challenge.provenance", challenge["provenance"])
    license_or_permission = _require_optional_text("challenge.license_or_permission", challenge["license_or_permission"])
    independent_author_role = _require_optional_text("challenge.independent_author_role", challenge["independent_author_role"])
    coverage_summary_sha256 = _require_optional_sha256("challenge.coverage_summary_sha256", challenge["coverage_summary_sha256"])
    adjudication_receipt_sha256 = _require_optional_sha256(
        "challenge.adjudication_receipt_sha256", challenge["adjudication_receipt_sha256"]
    )
    no_post_outcome_case_editing = _require_bool(
        "challenge.no_post_outcome_case_editing", challenge["no_post_outcome_case_editing"]
    )

    mode = _require_optional_text("comparator.mode", comparator["mode"])
    if mode not in _COMPARATOR_MODES:
        raise ValueError(f"comparator.mode must be one of {sorted(_COMPARATOR_MODES)}")
    comparator_receipt_sha256 = _require_optional_sha256("comparator.receipt_sha256", comparator["receipt_sha256"])
    matched_information = _require_bool("comparator.matched_information", comparator["matched_information"])
    matched_failure_accounting = _require_bool(
        "comparator.matched_failure_accounting", comparator["matched_failure_accounting"]
    )
    claim_boundary = _require_optional_text("comparator.claim_boundary", comparator["claim_boundary"])

    primary_name = _require_optional_text("endpoint.primary_name", endpoint["primary_name"])
    aggregation_rule = _require_optional_text("endpoint.aggregation_rule", endpoint["aggregation_rule"])
    failure_rule = _require_optional_text("endpoint.failure_rule", endpoint["failure_rule"])
    endpoint_manifest_sha256 = _require_optional_sha256("endpoint.manifest_sha256", endpoint["manifest_sha256"])

    reviewer = _require_optional_text("leakage_review.reviewer", leakage["reviewer"])
    leakage_receipt_sha256 = _require_optional_sha256("leakage_review.receipt_sha256", leakage["receipt_sha256"])
    outcome_blind = _require_bool("leakage_review.outcome_blind", leakage["outcome_blind"])
    leakage_passed = _require_bool("leakage_review.passed", leakage["passed"])

    immutable_attempts = _require_bool("retention.immutable_attempts", retention["immutable_attempts"])
    resume_allowed = _require_bool("retention.resume_allowed", retention["resume_allowed"])
    overwrite_allowed = _require_bool("retention.overwrite_allowed", retention["overwrite_allowed"])

    execution_authorized = _require_bool("outcome_access.execution_authorized", outcome["execution_authorized"])
    outcomes_observed = _require_bool("outcome_access.outcomes_observed", outcome["outcomes_observed"])
    adjudication_unlocked = _require_bool("outcome_access.adjudication_unlocked", outcome["adjudication_unlocked"])
    if execution_authorized or outcomes_observed or adjudication_unlocked:
        raise ValueError(
            "pre-outcome manifest must keep execution_authorized, outcomes_observed, and adjudication_unlocked false"
        )

    blockers: list[str] = []

    required_values = (
        ("source.git_commit", source_git_commit),
        ("source.source_surface_sha256", source_surface_sha256),
        ("source.environment_sha256", environment_sha256),
        ("source.openscad_identity", openscad_identity),
        ("challenge.dataset_sha256", dataset_sha256),
        ("challenge.provenance", provenance),
        ("challenge.license_or_permission", license_or_permission),
        ("challenge.independent_author_role", independent_author_role),
        ("challenge.coverage_summary_sha256", coverage_summary_sha256),
        ("challenge.adjudication_receipt_sha256", adjudication_receipt_sha256),
        ("comparator.receipt_sha256", comparator_receipt_sha256),
        ("endpoint.primary_name", primary_name),
        ("endpoint.aggregation_rule", aggregation_rule),
        ("endpoint.failure_rule", failure_rule),
        ("endpoint.manifest_sha256", endpoint_manifest_sha256),
        ("leakage_review.reviewer", reviewer),
        ("leakage_review.receipt_sha256", leakage_receipt_sha256),
    )
    for name, value in required_values:
        if value is None:
            blockers.append(f"{name} is not frozen")

    if not clean_tree:
        blockers.append("source.clean_tree must be true")
    if not output_directory_empty:
        blockers.append("source.output_directory_empty must be true")
    if not no_post_outcome_case_editing:
        blockers.append("challenge.no_post_outcome_case_editing must be true")

    if mode == "frozen_comparator":
        if not matched_information:
            blockers.append("frozen comparator requires comparator.matched_information=true")
        if not matched_failure_accounting:
            blockers.append("frozen comparator requires comparator.matched_failure_accounting=true")
    elif not claim_boundary:
        blockers.append("claim_narrowed mode requires a non-empty comparator.claim_boundary")

    if not outcome_blind:
        blockers.append("leakage_review.outcome_blind must be true")
    if not leakage_passed:
        blockers.append("leakage_review.passed must be true")
    if not immutable_attempts:
        blockers.append("retention.immutable_attempts must be true")
    if resume_allowed:
        blockers.append("retention.resume_allowed must be false")
    if overwrite_allowed:
        blockers.append("retention.overwrite_allowed must be false")

    unique_blockers = tuple(dict.fromkeys(blockers))
    return GateReport(
        manifest_sha256=canonical_manifest_sha256(root),
        ready_for_human_authorization=not unique_blockers,
        blockers=unique_blockers,
    )


def load_preoutcome_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"manifest does not exist: {path}")
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("pre-outcome manifest is limited to 1 MiB")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid pre-outcome manifest JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("pre-outcome manifest root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate NeuroCAD independent-validation pre-outcome metadata without authorizing execution"
    )
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        report = validate_preoutcome_manifest(load_preoutcome_manifest(args.manifest))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0 if report.ready_for_human_authorization else 2


if __name__ == "__main__":
    raise SystemExit(main())
