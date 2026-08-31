"""Arm-neutral Stage 1 trial runner for the NeuroCAD VeriCodeGen successor study.

This module is intentionally provider-agnostic. It accepts a generation callback,
retains attempt-level provenance, evaluates only final mesh artifacts with the
shared verifier, and applies one retry policy to both experimental arms.

It does not authorize or initiate any external model/API call by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .verifier import VerificationReport, load_mesh, verify_mesh


VALID_ARMS = {"direct", "structured"}


@dataclass(frozen=True)
class GenerationAttempt:
    """One generation/compile attempt supplied by an external arm adapter."""

    compiled: bool
    artifact_path: str | Path | None = None
    raw_response: str = ""
    generated_tokens: int | None = None
    latency_s: float | None = None
    estimated_cost_usd: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class AttemptResult:
    retry_index: int
    compiled: bool
    verifier_passed: bool
    hvr: bool
    failures: tuple[str, ...]
    failure_taxonomy: tuple[str, ...]
    measurements: dict[str, Any]
    artifact_path: str | None
    artifact_sha256: str | None
    raw_response: str
    generated_tokens: int | None
    latency_s: float | None
    estimated_cost_usd: float | None
    error: str | None


@dataclass(frozen=True)
class TrialResult:
    prompt_id: str
    arm: str
    seed: int | None
    hvr: bool
    attempts_used: int
    attempts: tuple[AttemptResult, ...]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Generator = Callable[[Mapping[str, Any], str, int], GenerationAttempt]


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _failure_taxonomy(
    *,
    compiled: bool,
    verifier_report: VerificationReport | None,
    verifier_error: str | None,
    exhausted: bool,
) -> tuple[str, ...]:
    categories: list[str] = []
    if not compiled:
        categories.append("syntax/compile failure")
    if verifier_error:
        categories.append("verifier ambiguity/error")
    if verifier_report is not None and not verifier_report.passed:
        for failure in verifier_report.failures:
            lower = failure.lower()
            if "extent." in lower or "bounds." in lower or "volume=" in lower:
                category = "wrong dimension/unit"
            elif "component_count" in lower or "watertight" in lower:
                category = "disconnected/intersecting geometry when forbidden"
            else:
                category = "hard-constraint violation"
            if category not in categories:
                categories.append(category)
    if exhausted and "timeout/retry exhaustion" not in categories:
        categories.append("timeout/retry exhaustion")
    return tuple(categories)


def run_trial(
    task: Mapping[str, Any],
    *,
    arm: str,
    generator: Generator,
    max_attempts: int,
    seed: int | None = None,
    provider: str = "development-fixture",
    model: str = "development-fixture",
    benchmark_manifest_sha256: str = "development-only",
    git_commit: str = "unknown",
    prompt_template_sha256: str = "development-only",
    verifier_version: str = "research.vericodegen.verifier",
) -> TrialResult:
    """Run one task/arm/seed cell under a frozen retry budget.

    HVR is true only when an attempt compiles and its final mesh satisfies every
    predeclared hard constraint. Failed attempts are retained; the function never
    silently drops retries or verifier failures.
    """

    if arm not in VALID_ARMS:
        raise ValueError(f"arm must be one of {sorted(VALID_ARMS)}")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    prompt_id = str(task.get("prompt_id", "")).strip()
    if not prompt_id:
        raise ValueError("task is missing prompt_id")
    constraints = task.get("hard_constraints", {})
    if not isinstance(constraints, Mapping):
        raise ValueError("task hard_constraints must be an object")

    results: list[AttemptResult] = []

    for retry_index in range(max_attempts):
        generated = generator(task, arm, retry_index)
        report: VerificationReport | None = None
        verifier_error: str | None = None
        artifact_path: str | None = None
        artifact_sha256: str | None = None

        if generated.compiled and generated.artifact_path is not None:
            path = Path(generated.artifact_path)
            artifact_path = str(path)
            try:
                artifact_sha256 = _sha256_file(path)
                report = verify_mesh(load_mesh(path), constraints)
            except Exception as exc:  # preserve verifier/plumbing failures as data
                verifier_error = f"{type(exc).__name__}: {exc}"

        verifier_passed = bool(report and report.passed and not verifier_error)
        hvr = bool(generated.compiled and verifier_passed)
        exhausted = retry_index == max_attempts - 1 and not hvr

        failures: list[str] = []
        if generated.error:
            failures.append(generated.error)
        if generated.compiled and generated.artifact_path is None:
            failures.append("compiled attempt did not provide a final mesh artifact")
        if verifier_error:
            failures.append(verifier_error)
        if report is not None:
            failures.extend(report.failures)

        results.append(
            AttemptResult(
                retry_index=retry_index,
                compiled=bool(generated.compiled),
                verifier_passed=verifier_passed,
                hvr=hvr,
                failures=tuple(failures),
                failure_taxonomy=_failure_taxonomy(
                    compiled=bool(generated.compiled),
                    verifier_report=report,
                    verifier_error=verifier_error,
                    exhausted=exhausted,
                ),
                measurements=dict(report.measurements) if report else {},
                artifact_path=artifact_path,
                artifact_sha256=artifact_sha256,
                raw_response=generated.raw_response,
                generated_tokens=generated.generated_tokens,
                latency_s=generated.latency_s,
                estimated_cost_usd=generated.estimated_cost_usd,
                error=generated.error,
            )
        )

        if hvr:
            break

    provenance = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "provider": provider,
        "model": model,
        "prompt_template_sha256": prompt_template_sha256,
        "verifier_version": verifier_version,
        "max_attempts": max_attempts,
    }

    return TrialResult(
        prompt_id=prompt_id,
        arm=arm,
        seed=seed,
        hvr=bool(results and results[-1].hvr),
        attempts_used=len(results),
        attempts=tuple(results),
        provenance=provenance,
    )


def append_jsonl(path: str | Path, result: TrialResult) -> None:
    """Append one immutable trial record as canonical sorted JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
