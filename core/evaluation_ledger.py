"""Manifest-first accounting for trusted, separately admitted evaluation adapters.

This module never downloads data or executes model-produced code. Callers must
supply an isolated execution adapter and authenticated source/data identities.
Fault-injection unit tests are not external benchmark results.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic


def _write(path: Path, value: Any) -> None:
    write_text_atomic(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", overwrite=False)


def run_scheduled_evaluation(
    sample_ids: Sequence[str], output_dir: Path, *, identities: dict[str, str],
    load: Callable[[str], Any], execute: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Retain exactly one terminal outcome per scheduled ID, including every error."""
    if isinstance(sample_ids, (str, bytes)):
        raise TypeError("Schedule must be a sequence of IDs, not a string")
    ids = list(sample_ids)
    if (not ids or len(ids) > 100000
            or any(not isinstance(item, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", item) is None for item in ids) or len({item.casefold() for item in ids}) != len(ids) or any(item.casefold() in {"manifest", "summary"} for item in ids)):
        raise ValueError("Schedule needs unique bounded safe IDs")
    if (set(identities) != {"source_commit", "dataset_revision", "dataset_manifest_sha256", "protocol_sha256"}
            or any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) is None for value in identities.values())):
        raise ValueError("Pin source, dataset revision, dataset manifest and protocol identities")
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"version": "neurocad-evaluation-ledger-v1", "scheduled_ids": ids,
                "identities": identities, "primary_denominator": "all_scheduled_ids",
                "execution_adapter": "caller supplied; isolation and authenticity require separate admission"}
    _write(output_dir / "manifest.json", manifest)
    outcomes = []
    for identifier in ids:
        outcome: dict[str, Any] = {"id": identifier, "status": "load_error", "metrics": None,
                                   "persisted": False}
        try:
            sample = load(identifier)
            outcome["status"] = "execution_error"
            metrics = execute(sample)
            if not isinstance(metrics, dict) or set(metrics) != {"passed", "requirements_passed", "requirements_total"}:
                raise ValueError("Executor returned an invalid endpoint schema")
            passed, satisfied, total = (metrics[key] for key in ("passed", "requirements_passed", "requirements_total"))
            if (type(passed) is not bool or type(satisfied) is not int or type(total) is not int
                    or not 0 <= satisfied <= total or total < 0 or (passed and (total == 0 or satisfied != total))):
                raise ValueError("Invalid or internally inconsistent endpoint counts")
            outcome.update(status="evaluated", metrics=dict(metrics))
        except (ValueError, TypeError, OSError, RuntimeError, ArithmeticError, LookupError) as exc:
            outcome["error_type"] = type(exc).__name__
        try:
            _write(output_dir / (identifier + ".json"), {**outcome, "persisted": True})
            outcome["persisted"] = True
        except OSError as exc:
            outcome["persistence_error"] = type(exc).__name__
        outcomes.append(outcome)
    evaluated = [row["metrics"] for row in outcomes if row["metrics"] is not None]
    available = [row for row in evaluated if row["requirements_total"] > 0]
    complete = all(row["persisted"] for row in outcomes)
    no_errors = all(row["status"] == "evaluated" for row in outcomes)
    total_requirements = sum(row["requirements_total"] for row in available)
    summary = {
        "version": manifest["version"], "scheduled_count": len(ids), "outcome_count": len(outcomes),
        "status": "COMPLETE" if complete and no_errors else "INCOMPLETE_OR_ERROR",
        "valid_for_inference": complete and no_errors and len(available) == len(ids),
        "correct_completion_numerator": sum(row["passed"] for row in evaluated),
        "correct_completion_denominator": len(ids),
        "requirement_numerator": sum(row["requirements_passed"] for row in available),
        "requirement_denominator": total_requirements,
        "requirement_available_samples": len(available), "requirement_unavailable_samples": len(ids) - len(available),
        "outcomes": outcomes,
        "manifest_sha256": hashlib.sha256((output_dir / "manifest.json").read_bytes()).hexdigest(),
    }
    # If persistence fails again, propagate the error. No completion marker exists.
    _write(output_dir / "summary.json", summary)
    return summary
