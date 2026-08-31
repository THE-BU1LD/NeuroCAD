"""Strict provenance envelope for captured VeriCodeGen Stage 2 attempts.

The Stage 2 manifest states what was intended to run. Captured-attempt v2 records
state what was actually sent/observed for each provider call. This module checks
that the actual provider/model, task hash, arm-specific system-template hash,
decoding settings, seed, retry attempt, and request fingerprint agree with the
frozen manifest before delegating local CAD evaluation to ``trial_ledger``.

No provider API is called here. The source capture is retained byte-for-byte and
hashed before normalization into the lower-level provider-neutral ledger format.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from research.vericodegen.stage2_manifest import load_manifest
from research.vericodegen.trial_ledger import (
    CAPTURE_VERSION as LEDGER_CAPTURE_VERSION,
    TrialLedgerError,
    canonical_json,
    evaluate_capture,
    load_capture_jsonl,
    sha256_file,
    validate_capture_matrix,
)


CAPTURE_VERSION = "vericodegen-captured-attempt-v2"
PROVENANCE_RECEIPT_VERSION = "vericodegen-capture-provenance-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARMS = ("direct", "structured")
GENERATION_STATUSES = {"completed", "timeout", "error"}


class CaptureProvenanceError(ValueError):
    """Raised when actual captured-call provenance disagrees with frozen intent."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _finite_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def parse_offset_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def request_fingerprint_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical metadata that must be fixed before/at each provider request."""

    return {
        "provider": row.get("provider"),
        "model": row.get("model"),
        "prompt_id": row.get("prompt_id"),
        "arm": row.get("arm"),
        "attempt": row.get("attempt"),
        "seed": row.get("seed"),
        "system_prompt_sha256": row.get("system_prompt_sha256"),
        "benchmark_task_sha256": row.get("benchmark_task_sha256"),
        "retry_feedback_sha256": row.get("retry_feedback_sha256"),
        "decoding": row.get("decoding"),
    }


def expected_request_fingerprint(row: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(request_fingerprint_payload(row)))


def validate_capture_row_v2(row: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {
        "capture_version",
        "prompt_id",
        "seed",
        "arm",
        "attempt",
        "captured_at",
        "provider",
        "model",
        "system_prompt_sha256",
        "benchmark_task_sha256",
        "request_fingerprint_sha256",
        "retry_feedback_sha256",
        "decoding",
        "generation_status",
        "raw_output",
        "generated_tokens",
        "wall_clock_seconds",
        "estimated_cost_usd",
        "provider_request_id",
        "provider_error",
        "finish_reason",
    }
    required = {
        "capture_version",
        "prompt_id",
        "seed",
        "arm",
        "attempt",
        "captured_at",
        "provider",
        "model",
        "system_prompt_sha256",
        "benchmark_task_sha256",
        "request_fingerprint_sha256",
        "retry_feedback_sha256",
        "decoding",
        "generation_status",
        "raw_output",
        "generated_tokens",
        "wall_clock_seconds",
        "estimated_cost_usd",
    }
    missing = sorted(required - set(row))
    if missing:
        errors.append(f"missing provenance fields: {', '.join(missing)}")
    unknown = sorted(set(row) - allowed)
    if unknown:
        errors.append(f"unsupported provenance fields: {', '.join(unknown)}")

    if row.get("capture_version") != CAPTURE_VERSION:
        errors.append(f"capture_version must equal {CAPTURE_VERSION}")
    prompt_id = row.get("prompt_id")
    if not isinstance(prompt_id, str) or not re.fullmatch(r"VCG-[0-9]{3}", prompt_id):
        errors.append("prompt_id must match VCG-000")
    if not isinstance(row.get("seed"), int) or isinstance(row.get("seed"), bool):
        errors.append("seed must be an integer")
    if row.get("arm") not in ARMS:
        errors.append("arm must be direct or structured")
    attempt = row.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        errors.append("attempt must be an integer >= 1")
    if parse_offset_timestamp(row.get("captured_at")) is None:
        errors.append("captured_at must be an offset-aware ISO 8601 date-time")
    for field in ("provider", "model"):
        if not _nonempty(row.get(field)):
            errors.append(f"{field} must be a non-empty exact identifier")
    for field in (
        "system_prompt_sha256",
        "benchmark_task_sha256",
        "request_fingerprint_sha256",
    ):
        if not _valid_hash(row.get(field)):
            errors.append(f"{field} must be a lowercase 64-character SHA-256 digest")
    retry_feedback = row.get("retry_feedback_sha256")
    if retry_feedback is not None and not _valid_hash(retry_feedback):
        errors.append("retry_feedback_sha256 must be null or a lowercase SHA-256 digest")
    if attempt == 1 and retry_feedback is not None:
        errors.append("attempt 1 must have retry_feedback_sha256=null")

    decoding = row.get("decoding")
    if not isinstance(decoding, Mapping):
        errors.append("decoding must be an object")
    else:
        if set(decoding) != {"temperature", "top_p", "max_output_tokens"}:
            errors.append("decoding must contain only temperature, top_p, and max_output_tokens")
        temperature = decoding.get("temperature")
        if not _finite_nonnegative(temperature):
            errors.append("decoding.temperature must be a finite number >= 0")
        top_p = decoding.get("top_p")
        if (
            not isinstance(top_p, (int, float))
            or isinstance(top_p, bool)
            or not math.isfinite(float(top_p))
            or not 0 < float(top_p) <= 1
        ):
            errors.append("decoding.top_p must be a finite number in (0, 1]")
        max_tokens = decoding.get("max_output_tokens")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
            errors.append("decoding.max_output_tokens must be an integer >= 1")

    status = row.get("generation_status")
    if status not in GENERATION_STATUSES:
        errors.append("generation_status must be completed, timeout, or error")
    raw = row.get("raw_output")
    if status == "completed":
        if not isinstance(raw, str) or not raw.strip():
            errors.append("completed generation requires non-empty raw_output")
        if row.get("provider_error") not in (None, ""):
            errors.append("completed generation must not contain provider_error")
    elif status in {"timeout", "error"}:
        if raw is not None:
            errors.append("timeout/error generation requires raw_output=null")

    tokens = row.get("generated_tokens")
    if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
        errors.append("generated_tokens must be an integer >= 0")
    if not _finite_nonnegative(row.get("wall_clock_seconds")):
        errors.append("wall_clock_seconds must be a finite number >= 0")
    if not _finite_nonnegative(row.get("estimated_cost_usd")):
        errors.append("estimated_cost_usd must be a finite number >= 0")
    for field in ("provider_request_id", "provider_error", "finish_reason"):
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be a string or null")

    if _valid_hash(row.get("request_fingerprint_sha256")):
        expected = expected_request_fingerprint(row)
        if row["request_fingerprint_sha256"] != expected:
            errors.append(
                "request_fingerprint_sha256 does not match the canonical captured request metadata"
            )
    return errors


def validate_capture_provenance(
    rows: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any],
    benchmark_manifest: Mapping[str, Any],
) -> list[str]:
    """Compare actual per-call provenance to all frozen manifest expectations."""

    errors: list[str] = []
    request_ids: list[str] = []
    task_hashes = benchmark_manifest.get("task_sha256")
    if not isinstance(task_hashes, Mapping):
        errors.append("benchmark manifest must contain task_sha256 map")
        task_hashes = {}

    frozen_decoding = manifest.get("decoding", {})
    for index, row in enumerate(rows):
        row_errors = validate_capture_row_v2(row)
        errors.extend(f"row[{index}]: {error}" for error in row_errors)

        if row.get("provider") != manifest.get("provider"):
            errors.append(
                f"row[{index}]: provider mismatch; expected {manifest.get('provider')!r}, got {row.get('provider')!r}"
            )
        if row.get("model") != manifest.get("model"):
            errors.append(
                f"row[{index}]: model mismatch; expected {manifest.get('model')!r}, got {row.get('model')!r}"
            )
        arm = row.get("arm")
        if arm in ARMS:
            expected_system = manifest.get("prompt_templates", {}).get(f"{arm}_sha256")
            if row.get("system_prompt_sha256") != expected_system:
                errors.append(
                    f"row[{index}]: system_prompt_sha256 mismatch for {arm} arm"
                )
        prompt_id = row.get("prompt_id")
        expected_task_hash = task_hashes.get(prompt_id) if isinstance(prompt_id, str) else None
        if expected_task_hash is None:
            errors.append(f"row[{index}]: {prompt_id!r} has no frozen benchmark task hash")
        elif row.get("benchmark_task_sha256") != expected_task_hash:
            errors.append(f"row[{index}]: benchmark_task_sha256 mismatch for {prompt_id}")

        actual_decoding = row.get("decoding")
        if isinstance(actual_decoding, Mapping) and isinstance(frozen_decoding, Mapping):
            for field in ("temperature", "top_p"):
                if field in actual_decoding and field in frozen_decoding:
                    if float(actual_decoding[field]) != float(frozen_decoding[field]):
                        errors.append(
                            f"row[{index}]: decoding.{field} mismatch; expected {frozen_decoding[field]!r}, "
                            f"got {actual_decoding[field]!r}"
                        )
            if actual_decoding.get("max_output_tokens") != frozen_decoding.get("max_output_tokens"):
                errors.append(
                    f"row[{index}]: decoding.max_output_tokens mismatch; expected "
                    f"{frozen_decoding.get('max_output_tokens')!r}, got {actual_decoding.get('max_output_tokens')!r}"
                )

        request_id = row.get("provider_request_id")
        if isinstance(request_id, str) and request_id:
            request_ids.append(request_id)

    duplicates = sorted({value for value in request_ids if request_ids.count(value) > 1})
    if duplicates:
        errors.append("provider_request_id values must be unique when present: " + ", ".join(duplicates))
    return errors


def normalize_to_ledger_v1(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Strip provider provenance only after it has been verified and source-hashed."""

    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "capture_version": LEDGER_CAPTURE_VERSION,
                "prompt_id": row["prompt_id"],
                "seed": row["seed"],
                "arm": row["arm"],
                "attempt": row["attempt"],
                "generation_status": row["generation_status"],
                "raw_output": row["raw_output"] if row["generation_status"] == "completed" else None,
                "generated_tokens": row["generated_tokens"],
                "wall_clock_seconds": row["wall_clock_seconds"],
                "estimated_cost_usd": row["estimated_cost_usd"],
                "provider_request_id": row.get("provider_request_id"),
                "provider_error": row.get("provider_error"),
            }
        )
    return normalized


def load_v2_capture(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CaptureProvenanceError(
                f"capture-v2 line {line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise CaptureProvenanceError(f"capture-v2 line {line_number}: row must be an object")
        rows.append(value)
    if not rows:
        raise CaptureProvenanceError("capture-v2 contains no attempts")
    return rows


def evaluate_provenance_capture(
    *,
    manifest_path: Path,
    benchmark_manifest_path: Path,
    benchmark_path: Path,
    pilot_selection_path: Path,
    structured_schema_path: Path,
    verifier_path: Path,
    analysis_plan_path: Path,
    prompt_receipt_path: Path,
    capture_v2_path: Path,
    repository_root: Path,
    outdir: Path,
    require_git_head: bool = True,
) -> dict[str, Any]:
    """Strict top-level evaluation entrypoint for actual captured Stage 2 calls."""

    manifest = load_manifest(manifest_path)
    try:
        benchmark_manifest = json.loads(benchmark_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureProvenanceError(f"cannot read benchmark manifest: {exc}") from exc
    if not isinstance(benchmark_manifest, Mapping):
        raise CaptureProvenanceError("benchmark manifest root must be an object")

    source_rows = load_v2_capture(capture_v2_path)
    provenance_errors = validate_capture_provenance(
        source_rows,
        manifest=manifest,
        benchmark_manifest=benchmark_manifest,
    )
    if provenance_errors:
        raise CaptureProvenanceError(
            "captured provider provenance rejected:\n- " + "\n- ".join(provenance_errors)
        )

    normalized = normalize_to_ledger_v1(source_rows)
    matrix_errors = validate_capture_matrix(normalized, manifest)
    if matrix_errors:
        raise CaptureProvenanceError(
            "captured attempt matrix rejected after provenance validation:\n- "
            + "\n- ".join(matrix_errors)
        )

    outdir.mkdir(parents=True, exist_ok=True)
    normalized_path = outdir / "normalized_capture_v1.jsonl"
    normalized_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in normalized),
        encoding="utf-8",
    )

    evaluation_dir = outdir / "evaluation"
    ledger_summary = evaluate_capture(
        manifest_path=manifest_path,
        benchmark_manifest_path=benchmark_manifest_path,
        benchmark_path=benchmark_path,
        pilot_selection_path=pilot_selection_path,
        structured_schema_path=structured_schema_path,
        verifier_path=verifier_path,
        analysis_plan_path=analysis_plan_path,
        prompt_receipt_path=prompt_receipt_path,
        capture_path=normalized_path,
        repository_root=repository_root,
        outdir=evaluation_dir,
        require_git_head=require_git_head,
    )

    timestamps = [parse_offset_timestamp(row["captured_at"]) for row in source_rows]
    parsed_timestamps = [value for value in timestamps if value is not None]
    unique_request_ids = {
        row["provider_request_id"]
        for row in source_rows
        if isinstance(row.get("provider_request_id"), str) and row["provider_request_id"]
    }
    receipt = {
        "provenance_receipt_version": PROVENANCE_RECEIPT_VERSION,
        "scientific_evidence": False,
        "provider": manifest["provider"],
        "model": manifest["model"],
        "captured_attempts": len(source_rows),
        "unique_provider_request_ids": len(unique_request_ids),
        "capture_v2_sha256": sha256_file(capture_v2_path),
        "normalized_capture_v1_sha256": sha256_file(normalized_path),
        "benchmark_manifest_sha256": sha256_file(benchmark_manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "earliest_captured_at": min(parsed_timestamps).isoformat() if parsed_timestamps else None,
        "latest_captured_at": max(parsed_timestamps).isoformat() if parsed_timestamps else None,
        "ledger_tip_sha256": ledger_summary["ledger_tip_sha256"],
        "finals_for_analysis_sha256": ledger_summary["finals_for_analysis_sha256"],
        "final_cells": ledger_summary["final_cells"],
        "hvr_pass_cells": ledger_summary["hvr_pass_cells"],
        "claim_boundary": (
            "Capture provenance and offline evaluation evidence only. A Stage 2 pilot remains exploratory; "
            "the Stage 3 frozen benchmark is required for the primary successor claim."
        ),
    }
    receipt_path = outdir / "capture_provenance_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--benchmark-manifest", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--pilot-selection", type=Path, required=True)
    parser.add_argument("--structured-schema", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--analysis-plan", type=Path, required=True)
    parser.add_argument("--prompt-receipt", type=Path, required=True)
    parser.add_argument("--capture-v2", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    receipt = evaluate_provenance_capture(
        manifest_path=args.manifest,
        benchmark_manifest_path=args.benchmark_manifest,
        benchmark_path=args.benchmark,
        pilot_selection_path=args.pilot_selection,
        structured_schema_path=args.structured_schema,
        verifier_path=args.verifier,
        analysis_plan_path=args.analysis_plan,
        prompt_receipt_path=args.prompt_receipt,
        capture_v2_path=args.capture_v2,
        repository_root=args.repository_root,
        outdir=args.outdir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
