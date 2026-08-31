"""Provider-neutral evaluation ledger for captured VeriCodeGen Stage 2 attempts.

This module NEVER calls a model provider. It consumes already-captured raw outputs
from an explicitly authorized frozen Stage 2 run, validates that the capture
matches the exact task × seed × arm × retry matrix, sends both arms through the
same local OpenSCAD/verifier boundary, retains every failed attempt, hash-chains
the evaluated ledger, and emits paired-analysis-ready final rows.

The Stage 2 pilot remains exploratory and ``scientific_evidence`` stays false.
This module does not revive the falsified historical NeuroCAD typed-parser claim.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Sequence

from research.vericodegen.arm_adapter import (
    ArmAdapterError,
    compile_openscad,
    prepare_arm_scad,
    sha256_text,
)
from research.vericodegen.benchmark_freeze import load_jsonl as load_benchmark_jsonl
from research.vericodegen.stage2_manifest import assert_executable, load_manifest
from research.vericodegen.verifier import load_mesh, verify_mesh


CAPTURE_VERSION = "vericodegen-captured-attempt-v1"
LEDGER_VERSION = "vericodegen-trial-ledger-v1"
GENERATION_STATUSES = {"completed", "timeout", "error"}
ARMS = ("direct", "structured")
FAILURE_MODES = {
    "syntax_compile_failure",
    "unsupported_operation",
    "missing_required_object",
    "wrong_dimension_unit",
    "spatial_relation_violation",
    "forbidden_connectivity_or_intersection",
    "semantic_misinterpretation",
    "verifier_ambiguity_error",
    "timeout_retry_exhaustion",
    "missing_final_artifact",
}


class TrialLedgerError(ValueError):
    """Raised when frozen inputs or captured trial evidence fail closed."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_capture_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TrialLedgerError(f"capture line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise TrialLedgerError(f"capture line {line_number}: row must be a JSON object")
        rows.append(value)
    if not rows:
        raise TrialLedgerError("capture contains no attempts")
    return rows


def _finite_nonnegative(name: str, value: Any, errors: list[str]) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        errors.append(f"{name} must be a finite number >= 0")


def validate_capture_row(row: Mapping[str, Any]) -> list[str]:
    """Validate provider capture metadata without interpreting CAD content."""

    errors: list[str] = []
    allowed = {
        "capture_version",
        "prompt_id",
        "seed",
        "arm",
        "attempt",
        "generation_status",
        "raw_output",
        "generated_tokens",
        "wall_clock_seconds",
        "estimated_cost_usd",
        "provider_request_id",
        "provider_error",
    }
    required = {
        "capture_version",
        "prompt_id",
        "seed",
        "arm",
        "attempt",
        "generation_status",
        "raw_output",
        "generated_tokens",
        "wall_clock_seconds",
        "estimated_cost_usd",
    }
    missing = sorted(required - set(row))
    if missing:
        errors.append(f"missing capture fields: {', '.join(missing)}")
    unknown = sorted(set(row) - allowed)
    if unknown:
        errors.append(f"unsupported capture fields: {', '.join(unknown)}")

    if row.get("capture_version") != CAPTURE_VERSION:
        errors.append(f"capture_version must equal {CAPTURE_VERSION}")
    prompt_id = row.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id.startswith("VCG-"):
        errors.append("prompt_id must be a VeriCodeGen task id")
    if not isinstance(row.get("seed"), int) or isinstance(row.get("seed"), bool):
        errors.append("seed must be an integer")
    if row.get("arm") not in ARMS:
        errors.append("arm must be direct or structured")
    attempt = row.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        errors.append("attempt must be an integer >= 1")

    status = row.get("generation_status")
    if status not in GENERATION_STATUSES:
        errors.append("generation_status must be completed, timeout, or error")
    raw_output = row.get("raw_output")
    if status == "completed":
        if not isinstance(raw_output, str) or not raw_output.strip():
            errors.append("completed generation requires non-empty raw_output")
    elif status in {"timeout", "error"}:
        if raw_output not in (None, ""):
            errors.append("timeout/error generation must not contain a raw_output artifact")

    tokens = row.get("generated_tokens")
    if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
        errors.append("generated_tokens must be an integer >= 0")
    _finite_nonnegative("wall_clock_seconds", row.get("wall_clock_seconds"), errors)
    _finite_nonnegative("estimated_cost_usd", row.get("estimated_cost_usd"), errors)

    for field in ("provider_request_id", "provider_error"):
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be a string or null")
    return errors


def allowed_cells(manifest: Mapping[str, Any]) -> set[tuple[str, int, str]]:
    return {
        (prompt_id, seed, arm)
        for prompt_id in manifest["pilot_task_ids"]
        for seed in manifest["decoding"]["seeds"]
        for arm in ARMS
    }


def validate_capture_matrix(
    rows: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> list[str]:
    """Validate exact cells, retry range, uniqueness, and contiguous attempt numbering."""

    errors: list[str] = []
    allowed = allowed_cells(manifest)
    max_attempts = int(manifest["retry_policy"]["max_attempts"])
    by_cell: dict[tuple[Any, Any, Any], list[int]] = defaultdict(list)
    seen_attempts: set[tuple[Any, Any, Any, Any]] = set()

    for index, row in enumerate(rows):
        row_errors = validate_capture_row(row)
        errors.extend(f"row[{index}]: {error}" for error in row_errors)
        cell = (row.get("prompt_id"), row.get("seed"), row.get("arm"))
        if cell not in allowed:
            errors.append(f"row[{index}]: capture cell {cell!r} is not authorized by the frozen manifest")
        attempt = row.get("attempt")
        if isinstance(attempt, int) and not isinstance(attempt, bool):
            if attempt > max_attempts:
                errors.append(
                    f"row[{index}]: attempt {attempt} exceeds frozen max_attempts={max_attempts}"
                )
            key = (*cell, attempt)
            if key in seen_attempts:
                errors.append(f"row[{index}]: duplicate captured attempt {key!r}")
            seen_attempts.add(key)
            by_cell[cell].append(attempt)

    missing_cells = sorted(allowed - set(by_cell))
    if missing_cells:
        errors.append(f"capture is missing {len(missing_cells)} authorized task/seed/arm cells")

    for cell, attempts in sorted(by_cell.items(), key=lambda item: repr(item[0])):
        ordered = sorted(attempts)
        expected = list(range(1, len(ordered) + 1))
        if ordered != expected:
            errors.append(
                f"cell {cell!r} attempts must be contiguous from 1; found {ordered}, expected {expected}"
            )
    return errors


def _require_file_hash(name: str, path: Path, expected: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{name} file not found: {path}")
        return
    actual = sha256_file(path)
    if actual != expected:
        errors.append(f"{name} SHA-256 mismatch: expected {expected}, got {actual}")


def _git_head(repository_root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def validate_frozen_inputs(
    *,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    benchmark_manifest_path: Path,
    benchmark_path: Path,
    pilot_selection_path: Path,
    structured_schema_path: Path,
    verifier_path: Path,
    analysis_plan_path: Path,
    prompt_receipt_path: Path,
    repository_root: Path,
    require_git_head: bool = True,
) -> list[str]:
    """Verify all pinned methodology bytes before interpreting captured outcomes."""

    errors: list[str] = []
    try:
        assert_executable(manifest)
    except Exception as exc:
        errors.append(str(exc))

    if not manifest_path.is_file():
        errors.append(f"Stage 2 manifest file not found: {manifest_path}")

    _require_file_hash(
        "benchmark_manifest",
        benchmark_manifest_path,
        str(manifest.get("benchmark_manifest_sha256")),
        errors,
    )
    _require_file_hash(
        "pilot_selection",
        pilot_selection_path,
        str(manifest.get("pilot_selection_sha256")),
        errors,
    )
    _require_file_hash(
        "structured_schema",
        structured_schema_path,
        str(manifest.get("structured_schema_sha256")),
        errors,
    )
    _require_file_hash(
        "verifier",
        verifier_path,
        str(manifest.get("verifier_sha256")),
        errors,
    )
    _require_file_hash(
        "analysis_plan",
        analysis_plan_path,
        str(manifest.get("analysis_plan_sha256")),
        errors,
    )
    _require_file_hash(
        "prompt_receipt",
        prompt_receipt_path,
        str(manifest.get("prompt_templates", {}).get("receipt_sha256")),
        errors,
    )

    if benchmark_manifest_path.is_file():
        try:
            benchmark_manifest = json.loads(benchmark_manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"benchmark manifest cannot be read: {exc}")
        else:
            if not isinstance(benchmark_manifest, Mapping):
                errors.append("benchmark manifest root must be an object")
            elif not benchmark_path.is_file():
                errors.append(f"benchmark file not found: {benchmark_path}")
            else:
                expected_benchmark = benchmark_manifest.get("benchmark_sha256")
                actual_benchmark = sha256_file(benchmark_path)
                if expected_benchmark != actual_benchmark:
                    errors.append(
                        "frozen benchmark SHA-256 does not match its benchmark manifest: "
                        f"expected {expected_benchmark}, got {actual_benchmark}"
                    )

    if pilot_selection_path.is_file():
        try:
            pilot = json.loads(pilot_selection_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"pilot selection cannot be read: {exc}")
        else:
            if not isinstance(pilot, Mapping):
                errors.append("pilot selection root must be an object")
            elif pilot.get("pilot_task_ids") != manifest.get("pilot_task_ids"):
                errors.append("pilot selection task ids do not exactly match the Stage 2 manifest")

    if prompt_receipt_path.is_file():
        try:
            prompt_receipt = json.loads(prompt_receipt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"prompt receipt cannot be read: {exc}")
        else:
            if not isinstance(prompt_receipt, Mapping):
                errors.append("prompt receipt root must be an object")
            else:
                for field in ("direct_sha256", "structured_sha256"):
                    expected = manifest.get("prompt_templates", {}).get(field)
                    actual = prompt_receipt.get(field)
                    if actual != expected:
                        errors.append(
                            f"prompt receipt {field} mismatch: expected {expected}, got {actual}"
                        )

    if require_git_head:
        head = _git_head(repository_root)
        expected_head = manifest.get("git_commit")
        if head is None:
            errors.append("could not resolve repository git HEAD")
        elif head != expected_head:
            errors.append(f"repository git HEAD mismatch: expected {expected_head}, got {head}")
    return errors


def _raw_output_sha256(row: Mapping[str, Any]) -> str | None:
    raw = row.get("raw_output")
    return sha256_text(raw) if isinstance(raw, str) and raw else None


def _classify_verifier_failures(failures: Sequence[str]) -> list[str]:
    modes: set[str] = set()
    for failure in failures:
        lowered = failure.lower()
        if any(token in lowered for token in ("extent.", "volume=", "bounds.")):
            modes.add("wrong_dimension_unit")
        if "component_count=" in lowered or "watertight=" in lowered:
            modes.add("forbidden_connectivity_or_intersection")
    if not modes and failures:
        modes.add("verifier_ambiguity_error")
    return sorted(modes)


def _classify_adapter_error(exc: ArmAdapterError) -> str:
    lowered = str(exc).lower()
    if "unsupported" in lowered:
        return "unsupported_operation"
    return "syntax_compile_failure"


def evaluate_attempt(
    row: Mapping[str, Any],
    *,
    task: Mapping[str, Any],
    openscad_fn: int,
    timeout_seconds: int,
    outdir: Path,
    compile_function: Callable[..., Mapping[str, Any]] = compile_openscad,
) -> dict[str, Any]:
    """Evaluate exactly one captured attempt without repair or arm-specific state."""

    stem = f"{row['prompt_id']}-seed{row['seed']}-{row['arm']}-attempt{row['attempt']}"
    attempt_dir = outdir / "artifacts" / stem
    attempt_dir.mkdir(parents=True, exist_ok=True)
    raw_path = attempt_dir / "raw_output.txt"
    scad_path = attempt_dir / "prepared.scad"
    stl_path = attempt_dir / "artifact.stl"
    compile_log_path = attempt_dir / "openscad.log"

    raw = row.get("raw_output")
    if isinstance(raw, str):
        raw_path.write_text(raw, encoding="utf-8")

    evaluated: dict[str, Any] = {
        "ledger_version": LEDGER_VERSION,
        "prompt_id": row["prompt_id"],
        "seed": row["seed"],
        "arm": row["arm"],
        "attempt": row["attempt"],
        "task_family": task["task_family"],
        "generation_status": row["generation_status"],
        "generated_tokens": row["generated_tokens"],
        "wall_clock_seconds": row["wall_clock_seconds"],
        "estimated_cost_usd": row["estimated_cost_usd"],
        "provider_request_id": row.get("provider_request_id"),
        "provider_error": row.get("provider_error"),
        "raw_output_sha256": _raw_output_sha256(row),
        "raw_output_path": str(raw_path) if isinstance(raw, str) else None,
        "adapter_success": False,
        "compile_success": False,
        "hard_constraints_passed": False,
        "hvr": False,
        "failure_modes": [],
        "adapter_error": None,
        "compile_returncode": None,
        "compile_timed_out": False,
        "compile_log_path": None,
        "scad_sha256": None,
        "artifact_sha256": None,
        "verifier_failures": [],
        "measurements": None,
    }

    if row["generation_status"] != "completed":
        evaluated["failure_modes"] = ["timeout_retry_exhaustion"]
        return evaluated

    try:
        scad = prepare_arm_scad(row["arm"], str(raw), fn=openscad_fn)
    except ArmAdapterError as exc:
        evaluated["adapter_error"] = str(exc)
        evaluated["failure_modes"] = [_classify_adapter_error(exc)]
        return evaluated

    evaluated["adapter_success"] = True
    evaluated["scad_sha256"] = sha256_text(scad)
    compilation = dict(
        compile_function(
            scad,
            scad_path=scad_path,
            stl_path=stl_path,
            timeout_seconds=timeout_seconds,
        )
    )
    compile_log_path.write_text(str(compilation.get("stdout", "")), encoding="utf-8")
    evaluated["compile_log_path"] = str(compile_log_path)
    evaluated["compile_success"] = bool(compilation.get("compile_success"))
    evaluated["compile_returncode"] = compilation.get("returncode")
    evaluated["compile_timed_out"] = bool(compilation.get("timed_out"))
    evaluated["artifact_sha256"] = compilation.get("artifact_sha256")

    if evaluated["compile_timed_out"]:
        evaluated["failure_modes"] = ["timeout_retry_exhaustion"]
        return evaluated
    if not evaluated["compile_success"]:
        evaluated["failure_modes"] = ["syntax_compile_failure"]
        return evaluated
    if not stl_path.is_file() or stl_path.stat().st_size == 0:
        evaluated["failure_modes"] = ["missing_final_artifact"]
        evaluated["compile_success"] = False
        return evaluated

    try:
        report = verify_mesh(load_mesh(stl_path), task["hard_constraints"])
    except Exception as exc:
        evaluated["verifier_failures"] = [f"{type(exc).__name__}: {exc}"]
        evaluated["failure_modes"] = ["verifier_ambiguity_error"]
        return evaluated

    evaluated["hard_constraints_passed"] = bool(report.passed)
    evaluated["verifier_failures"] = list(report.failures)
    evaluated["measurements"] = report.measurements
    evaluated["hvr"] = bool(evaluated["compile_success"] and report.passed)
    if not report.passed:
        evaluated["failure_modes"] = _classify_verifier_failures(report.failures)
    return evaluated


def _ledger_sort_key(row: Mapping[str, Any]) -> tuple[str, int, int, int]:
    arm_rank = 0 if row["arm"] == "direct" else 1
    return (str(row["prompt_id"]), int(row["seed"]), arm_rank, int(row["attempt"]))


def hash_chain(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Create a deterministic append-style SHA-256 chain over evaluated attempts."""

    previous = "0" * 64
    chained: list[dict[str, Any]] = []
    for sequence, source in enumerate(sorted(records, key=_ledger_sort_key), 1):
        record = dict(source)
        record["ledger_sequence"] = sequence
        record["previous_ledger_hash"] = previous
        payload = canonical_json(record)
        current = sha256_text(payload)
        record["ledger_hash"] = current
        chained.append(record)
        previous = current
    return chained


def verify_hash_chain(records: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    previous = "0" * 64
    for expected_sequence, record in enumerate(records, 1):
        if record.get("ledger_sequence") != expected_sequence:
            errors.append(
                f"ledger sequence mismatch at row {expected_sequence}: {record.get('ledger_sequence')}"
            )
        if record.get("previous_ledger_hash") != previous:
            errors.append(f"ledger previous hash mismatch at row {expected_sequence}")
        without_hash = dict(record)
        claimed = without_hash.pop("ledger_hash", None)
        actual = sha256_text(canonical_json(without_hash))
        if claimed != actual:
            errors.append(f"ledger hash mismatch at row {expected_sequence}")
        previous = str(claimed)
    return errors


def finalize_cells(
    evaluated_attempts: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Select first HVR pass or frozen retry exhaustion and aggregate retry resources."""

    max_attempts = int(manifest["retry_policy"]["max_attempts"])
    groups: dict[tuple[str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in evaluated_attempts:
        groups[(row["prompt_id"], row["seed"], row["arm"])].append(row)

    finals: list[dict[str, Any]] = []
    for cell in sorted(allowed_cells(manifest)):
        attempts = sorted(groups.get(cell, []), key=lambda row: int(row["attempt"]))
        if not attempts:
            raise TrialLedgerError(f"authorized cell {cell!r} has no evaluated attempts")

        passing = [row for row in attempts if row["hvr"]]
        if passing:
            final_attempt = passing[0]
            if any(int(row["attempt"]) > int(final_attempt["attempt"]) for row in attempts):
                raise TrialLedgerError(
                    f"cell {cell!r} contains retries after attempt {final_attempt['attempt']} already passed HVR"
                )
        else:
            if len(attempts) != max_attempts:
                raise TrialLedgerError(
                    f"cell {cell!r} has no HVR pass but capture stopped at {len(attempts)} of "
                    f"frozen max_attempts={max_attempts}"
                )
            final_attempt = attempts[-1]

        aggregate_failure_modes = sorted(
            {mode for attempt in attempts for mode in attempt["failure_modes"]}
        )
        finals.append(
            {
                "prompt_id": final_attempt["prompt_id"],
                "seed": final_attempt["seed"],
                "arm": final_attempt["arm"],
                "task_family": final_attempt["task_family"],
                "hvr": bool(final_attempt["hvr"]),
                "compile_success": bool(final_attempt["compile_success"]),
                "hard_constraints_passed": bool(final_attempt["hard_constraints_passed"]),
                "retry_count": int(final_attempt["attempt"]) - 1,
                "generated_tokens": sum(int(attempt["generated_tokens"]) for attempt in attempts),
                "wall_clock_seconds": sum(float(attempt["wall_clock_seconds"]) for attempt in attempts),
                "estimated_cost_usd": sum(float(attempt["estimated_cost_usd"]) for attempt in attempts),
                "failure_modes": aggregate_failure_modes if not final_attempt["hvr"] else [],
                "final_attempt": int(final_attempt["attempt"]),
                "final_ledger_hash": final_attempt.get("ledger_hash"),
                "artifact_sha256": final_attempt.get("artifact_sha256"),
                "raw_output_sha256": final_attempt.get("raw_output_sha256"),
            }
        )
    return finals


def _load_benchmark_map(path: Path) -> dict[str, dict[str, Any]]:
    tasks = load_benchmark_jsonl(path)
    by_id = {task["prompt_id"]: task for task in tasks}
    if len(by_id) != len(tasks):
        raise TrialLedgerError("benchmark contains duplicate prompt ids")
    return by_id


def evaluate_capture(
    *,
    manifest_path: Path,
    benchmark_manifest_path: Path,
    benchmark_path: Path,
    pilot_selection_path: Path,
    structured_schema_path: Path,
    verifier_path: Path,
    analysis_plan_path: Path,
    prompt_receipt_path: Path,
    capture_path: Path,
    repository_root: Path,
    outdir: Path,
    require_git_head: bool = True,
) -> dict[str, Any]:
    """Evaluate a complete frozen capture and write immutable-ish evidence receipts."""

    manifest = load_manifest(manifest_path)
    frozen_errors = validate_frozen_inputs(
        manifest=manifest,
        manifest_path=manifest_path,
        benchmark_manifest_path=benchmark_manifest_path,
        benchmark_path=benchmark_path,
        pilot_selection_path=pilot_selection_path,
        structured_schema_path=structured_schema_path,
        verifier_path=verifier_path,
        analysis_plan_path=analysis_plan_path,
        prompt_receipt_path=prompt_receipt_path,
        repository_root=repository_root,
        require_git_head=require_git_head,
    )
    if frozen_errors:
        raise TrialLedgerError("frozen input validation failed:\n- " + "\n- ".join(frozen_errors))

    capture_rows = load_capture_jsonl(capture_path)
    matrix_errors = validate_capture_matrix(capture_rows, manifest)
    if matrix_errors:
        raise TrialLedgerError("captured attempt matrix rejected:\n- " + "\n- ".join(matrix_errors))

    benchmark = _load_benchmark_map(benchmark_path)
    missing_tasks = sorted(set(manifest["pilot_task_ids"]) - set(benchmark))
    if missing_tasks:
        raise TrialLedgerError(
            "pilot task ids missing from frozen benchmark: " + ", ".join(missing_tasks)
        )

    outdir.mkdir(parents=True, exist_ok=True)
    evaluated: list[dict[str, Any]] = []
    for row in sorted(capture_rows, key=_ledger_sort_key):
        evaluated.append(
            evaluate_attempt(
                row,
                task=benchmark[row["prompt_id"]],
                openscad_fn=int(manifest["environment"]["openscad_fn"]),
                timeout_seconds=int(manifest["environment"]["compile_timeout_seconds"]),
                outdir=outdir,
            )
        )

    chained = hash_chain(evaluated)
    chain_errors = verify_hash_chain(chained)
    if chain_errors:
        raise TrialLedgerError("internal ledger hash-chain validation failed:\n- " + "\n- ".join(chain_errors))
    finals = finalize_cells(chained, manifest)

    attempts_path = outdir / "attempts_evaluated.jsonl"
    finals_path = outdir / "finals_for_analysis.jsonl"
    attempts_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in chained), encoding="utf-8"
    )
    finals_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in finals), encoding="utf-8"
    )

    total_cost = sum(float(row["estimated_cost_usd"]) for row in capture_rows)
    if total_cost > float(manifest["cost_cap_usd"]):
        raise TrialLedgerError(
            f"captured cost ${total_cost:.6f} exceeds frozen cost cap ${float(manifest['cost_cap_usd']):.6f}"
        )

    summary = {
        "ledger_version": LEDGER_VERSION,
        "stage": "stage2_frozen_pilot_offline_evaluation",
        "scientific_evidence": False,
        "claim_boundary": (
            "Exploratory Stage 2 pilot evidence only. This evaluates captured outputs without "
            "provider calls or human repair and does not establish the Stage 3 primary claim."
        ),
        "manifest_sha256": sha256_file(manifest_path),
        "benchmark_manifest_sha256": sha256_file(benchmark_manifest_path),
        "benchmark_sha256": sha256_file(benchmark_path),
        "pilot_selection_sha256": sha256_file(pilot_selection_path),
        "capture_sha256": sha256_file(capture_path),
        "attempts_evaluated_sha256": sha256_file(attempts_path),
        "finals_for_analysis_sha256": sha256_file(finals_path),
        "ledger_tip_sha256": chained[-1]["ledger_hash"],
        "authorized_cells": len(allowed_cells(manifest)),
        "captured_attempts": len(capture_rows),
        "final_cells": len(finals),
        "hvr_pass_cells": sum(int(row["hvr"]) for row in finals),
        "total_generated_tokens": sum(int(row["generated_tokens"]) for row in capture_rows),
        "total_wall_clock_seconds": sum(float(row["wall_clock_seconds"]) for row in capture_rows),
        "total_estimated_cost_usd": total_cost,
        "cost_cap_usd": float(manifest["cost_cap_usd"]),
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


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
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    summary = evaluate_capture(
        manifest_path=args.manifest,
        benchmark_manifest_path=args.benchmark_manifest,
        benchmark_path=args.benchmark,
        pilot_selection_path=args.pilot_selection,
        structured_schema_path=args.structured_schema,
        verifier_path=args.verifier,
        analysis_plan_path=args.analysis_plan,
        prompt_receipt_path=args.prompt_receipt,
        capture_path=args.capture,
        repository_root=args.repository_root,
        outdir=args.outdir,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
