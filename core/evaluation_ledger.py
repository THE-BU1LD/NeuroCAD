"""Manifest-first accounting for trusted, separately admitted evaluation adapters.

Integrity checks establish consistency, not benchmark validity or source authenticity.
No data download, model execution, automatic retry or scientific admission occurs here.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import stat
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .json_io import strict_json_loads

VERSION = "neurocad-evaluation-ledger-v2"
MAX_SAMPLES = 100000
MAX_COUNT = 2**63 - 1
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_IDENTITY_PATTERNS = {
    "source_commit": re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}"),
    "dataset_revision": re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}"),
    "dataset_manifest_sha256": _SHA256, "protocol_sha256": _SHA256,
}


def _text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _value_digest(value: Any) -> str:
    return _digest(_text(value).encode("utf-8"))


def _write(path: Path, value: Any) -> None:
    write_text_atomic(path, _text(value), overwrite=False)


def _schedule(sample_ids: Iterable[str]) -> list[str]:
    if isinstance(sample_ids, (str, bytes)):
        raise TypeError("Schedule must contain IDs, not a string")
    # Consume at most the limit plus one, even for an unbounded generator.
    ids = list(itertools.islice(sample_ids, MAX_SAMPLES + 1))
    if (not ids or len(ids) > MAX_SAMPLES
            or any(not isinstance(item, str) or _ID.fullmatch(item) is None for item in ids)
            or len({item.casefold() for item in ids}) != len(ids)
            or any(item.casefold() in {"manifest", "summary"} for item in ids)):
        raise ValueError("Schedule needs unique bounded safe IDs")
    return ids


def _identities(identities: Any) -> dict[str, str]:
    if (not isinstance(identities, dict) or set(identities) != set(_IDENTITY_PATTERNS)
            or any(not isinstance(value, str) or _IDENTITY_PATTERNS[key].fullmatch(value) is None
                   for key, value in identities.items())):
        raise ValueError("Pin source/dataset revisions and 64-character SHA256 manifest/protocol identities")
    return dict(identities)


def _metrics(metrics: Any) -> dict[str, Any]:
    if not isinstance(metrics, dict) or set(metrics) != {"passed", "requirements_passed", "requirements_total"}:
        raise ValueError("Executor returned an invalid endpoint schema")
    passed, satisfied, total = (metrics[key] for key in ("passed", "requirements_passed", "requirements_total"))
    if (type(passed) is not bool or type(satisfied) is not int or type(total) is not int
            or not 0 <= satisfied <= total <= MAX_COUNT
            or (passed and (total == 0 or satisfied != total))):
        raise ValueError("Invalid or internally inconsistent endpoint counts")
    return dict(metrics)


def _manifest(ids: list[str], identities: dict[str, str]) -> dict[str, Any]:
    return {"version": VERSION, "scheduled_ids": ids, "identities": identities,
            "primary_denominator": "all_scheduled_ids",
            "execution_adapter": "caller supplied; isolation and authenticity require separate admission"}


def _read_bytes(path: Path, limit: int | None = None) -> bytes:
    limit = MAX_DOCUMENT_BYTES if limit is None else limit
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Evidence must be a regular non-symlink file")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Evidence document exceeds the byte limit")
    return data


def _read_json(path: Path) -> tuple[Any, str]:
    data = _read_bytes(path)
    return strict_json_loads(data.decode("utf-8")), _digest(data)


def _artifact_issues(output_dir: Path, hashes: dict[str, str]) -> list[str]:
    issues = []
    for name, expected in hashes.items():
        try:
            actual = _digest(_read_bytes(output_dir / name, MAX_DOCUMENT_BYTES if name == "manifest.json" else 65536))
            if actual != expected:
                issues.append(f"{name}: SHA256 mismatch")
        except (OSError, ValueError) as exc:
            issues.append(f"{name}: {type(exc).__name__}")
    return issues


def _summary(manifest: dict[str, Any], outcomes: list[dict[str, Any]],
             hashes: dict[str, str], issues: list[str]) -> dict[str, Any]:
    # One accounting pass; no duplicate filtered lists of all metrics.
    completion, numerator, denominator, available = 0, 0, 0, 0
    complete, no_errors = True, True
    for row in outcomes:
        complete = complete and row["persisted"]
        no_errors = no_errors and row["status"] == "evaluated"
        metrics = row["metrics"]
        if metrics is not None:
            completion += int(metrics["passed"])
            if metrics["requirements_total"] > 0:
                available += 1
                numerator += metrics["requirements_passed"]
                denominator += metrics["requirements_total"]
    count = len(manifest["scheduled_ids"])
    return {
        "version": VERSION, "scheduled_count": count, "outcome_count": len(outcomes),
        "status": "INTEGRITY_ERROR" if issues else ("COMPLETE" if complete and no_errors else "INCOMPLETE_OR_ERROR"),
        "valid_for_inference": bool(not issues and complete and no_errors and available == count),
        "correct_completion_numerator": completion, "correct_completion_denominator": count,
        "requirement_numerator": numerator, "requirement_denominator": denominator,
        "requirement_available_samples": available, "requirement_unavailable_samples": count - available,
        "outcomes": outcomes, "manifest_sha256": hashes["manifest.json"],
        "artifact_sha256": hashes, "integrity_issues": issues,
        "claim_boundary": "Ledger accounting only; scientific validity and adapter authenticity require separate admission",
    }


def run_scheduled_evaluation(
    sample_ids: Iterable[str], output_dir: Path, *, identities: dict[str, str],
    load: Callable[[str], Any], execute: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Persist one terminal outcome per ID for ordinary adapter errors.

    Cancellation, MemoryError, manifest or summary publication failure propagate.
    A manifest without a summary is incomplete and is never silently resumed.
    """
    ids = _schedule(sample_ids)
    manifest = _manifest(ids, _identities(identities))
    output_dir.mkdir(parents=True, exist_ok=False)
    hashes = {"manifest.json": _value_digest(manifest)}
    _write(output_dir / "manifest.json", manifest)
    outcomes = []
    for identifier in ids:
        outcome: dict[str, Any] = {"id": identifier, "status": "load_error", "metrics": None, "persisted": False}
        try:
            sample = load(identifier)
            outcome["status"] = "execution_error"
            outcome.update(status="evaluated", metrics=_metrics(execute(sample)))
        except MemoryError:
            raise
        except Exception as exc:  # noqa: BLE001 - every ordinary adapter failure is a retained outcome
            outcome["error_type"] = type(exc).__name__[:128]
        name = identifier + ".json"
        retained = {**outcome, "persisted": True}
        try:
            _write(output_dir / name, retained)
            outcome["persisted"] = True
            hashes[name] = _value_digest(retained)
        except OSError as exc:
            outcome["persistence_error"] = type(exc).__name__[:128]
        outcomes.append(outcome)
    summary = _summary(manifest, outcomes, hashes, _artifact_issues(output_dir, hashes))
    _write(output_dir / "summary.json", summary)
    return summary


def _validate_outcome(row: Any, identifier: str) -> None:
    if not isinstance(row, dict) or row.get("id") != identifier or type(row.get("persisted")) is not bool:
        raise ValueError("Outcome identity or persistence flag is invalid")
    keys = {"id", "status", "metrics", "persisted"}
    if row.get("status") == "evaluated":
        _metrics(row.get("metrics"))
    elif row.get("status") in {"load_error", "execution_error"}:
        keys.add("error_type")
        if row.get("metrics") is not None:
            raise ValueError("Failed outcome cannot contain endpoint metrics")
    else:
        raise ValueError("Unknown outcome status")
    if not row["persisted"]:
        keys.add("persistence_error")
    if set(row) != keys:
        raise ValueError("Invalid outcome fields")
    for key in ("error_type", "persistence_error"):
        if key in row and (not isinstance(row[key], str) or not 1 <= len(row[key]) <= 128):
            raise ValueError("Invalid error type")


def audit_scheduled_evaluation(
    output_dir: Path, *, expected_manifest_sha256: str | None = None,
    expected_summary_sha256: str | None = None,
) -> dict[str, Any]:
    """Read-only v2 replay; optional externally retained hashes anchor identity.

    Self-consistent hashes alone cannot authenticate an untrusted evidence producer.
    Invalid/missing/legacy evidence returns an explicit failed audit, never a rerun.
    """
    result: dict[str, Any] = {"integrity_verified": False, "valid_for_inference": False,
                              "scheduled_count": None, "issues": [], "recomputed": None}
    try:
        manifest, manifest_hash = _read_json(output_dir / "manifest.json")
        if not isinstance(manifest, dict) or manifest.get("version") != VERSION:
            raise ValueError("Only explicitly versioned v2 ledgers support this audit")
        ids = _schedule(manifest.get("scheduled_ids", []))
        if _text(manifest) != _text(_manifest(ids, _identities(manifest.get("identities")))):
            raise ValueError("Manifest schema differs from the supported contract")
        result["scheduled_count"] = len(ids)
        summary, summary_hash = _read_json(output_dir / "summary.json")
        for expected, actual in ((expected_manifest_sha256, manifest_hash), (expected_summary_sha256, summary_hash)):
            if expected is not None and (not isinstance(expected, str) or _SHA256.fullmatch(expected) is None or expected != actual):
                raise ValueError("External evidence anchor mismatch")
        if not isinstance(summary, dict) or summary.get("version") != VERSION:
            raise ValueError("Missing or invalid v2 summary")
        outcomes = summary.get("outcomes")
        if not isinstance(outcomes, list) or len(outcomes) != len(ids):
            raise ValueError("Summary does not retain exactly one outcome per scheduled ID")
        hashes = {"manifest.json": manifest_hash}
        for identifier, row in zip(ids, outcomes, strict=True):
            _validate_outcome(row, identifier)
            if row["persisted"]:
                hashes[identifier + ".json"] = _value_digest(row)
        issues = _artifact_issues(output_dir, hashes)
        if summary.get("artifact_sha256") != hashes:
            issues.append("Recorded artifact hashes differ from the retained outcome records")
        if summary.get("manifest_sha256") != manifest_hash:
            issues.append("Manifest identity differs from the recorded pre-execution identity")
        recomputed = _summary(manifest, outcomes, hashes, issues)
        # Compare serialized values so booleans cannot masquerade as integer counts.
        if _text(summary) != _text(recomputed):
            issues.append("Summary fields differ from recomputed accounting")
        result.update(integrity_verified=not issues, valid_for_inference=bool(not issues and recomputed["valid_for_inference"]),
                      issues=issues, recomputed={key: value for key, value in recomputed.items()
                                                if key not in {"outcomes", "artifact_sha256"}},
                      manifest_sha256=manifest_hash, summary_sha256=summary_hash)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        result["issues"].append(f"{type(exc).__name__}: {exc}")
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Read-only evaluation ledger v2 integrity audit")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--summary-sha256")
    args = parser.parse_args()
    result = audit_scheduled_evaluation(args.output_dir, expected_manifest_sha256=args.manifest_sha256,
                                        expected_summary_sha256=args.summary_sha256)
    print(_text(result), end="")
    return 0 if result["integrity_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
