"""Validation and execution gate for the VeriCodeGen Stage 2 frozen pilot.

This module does not call any provider. It checks that benchmark, pilot selection,
prompt templates, structured schema, verifier, analysis plan, environment, retry
symmetry, retention policy, call budget, cost cap, and explicit authorization are
all frozen before an external runner may execute Stage 2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Mapping


MANIFEST_VERSION = "vericodegen-stage2-v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
PROMPT_ID_RE = re.compile(r"^VCG-[0-9]{3}$")


class ManifestError(ValueError):
    """Raised when a Stage 2 run manifest is incomplete or unsafe to execute."""


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_hash(name: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{name} must be a lowercase 64-character SHA-256 hex digest")


def validate_manifest(manifest: Mapping[str, Any], *, require_authorized: bool) -> list[str]:
    """Return all manifest violations instead of failing at the first one."""

    errors: list[str] = []

    if manifest.get("manifest_version") != MANIFEST_VERSION:
        errors.append(f"manifest_version must equal {MANIFEST_VERSION}")
    if manifest.get("stage") != "stage2_frozen_pilot":
        errors.append("stage must equal stage2_frozen_pilot")
    if manifest.get("scientific_evidence") is not False:
        errors.append("scientific_evidence must remain false for the Stage 2 pilot")

    if require_authorized and manifest.get("authorized") is not True:
        errors.append("authorized must be true before any external Stage 2 execution")
    elif not isinstance(manifest.get("authorized"), bool):
        errors.append("authorized must be a boolean")

    for field in (
        "benchmark_manifest_sha256",
        "pilot_selection_sha256",
        "structured_schema_sha256",
        "verifier_sha256",
        "analysis_plan_sha256",
    ):
        _require_hash(field, manifest.get(field), errors)

    git_commit = manifest.get("git_commit")
    if not isinstance(git_commit, str) or not GIT_SHA_RE.fullmatch(git_commit):
        errors.append("git_commit must be a 7-40 character lowercase git SHA")

    for field in ("provider", "model"):
        if not _nonempty_string(manifest.get(field)):
            errors.append(f"{field} must be a non-empty exact identifier")

    tasks = manifest.get("pilot_task_ids")
    if not isinstance(tasks, list) or not tasks:
        errors.append("pilot_task_ids must be a non-empty list")
        task_count = 0
    else:
        task_count = len(tasks)
        if len(set(tasks)) != task_count:
            errors.append("pilot_task_ids must not contain duplicates")
        for task_id in tasks:
            if not isinstance(task_id, str) or not PROMPT_ID_RE.fullmatch(task_id):
                errors.append(f"invalid pilot task id: {task_id!r}")

    decoding = manifest.get("decoding")
    if not isinstance(decoding, Mapping):
        errors.append("decoding must be an object")
        seeds: list[Any] = []
    else:
        temperature = decoding.get("temperature")
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool) or temperature < 0:
            errors.append("decoding.temperature must be a number >= 0")

        top_p = decoding.get("top_p")
        if (
            not isinstance(top_p, (int, float))
            or isinstance(top_p, bool)
            or not (0 < float(top_p) <= 1)
        ):
            errors.append("decoding.top_p must be a number in (0, 1]")

        max_output_tokens = decoding.get("max_output_tokens")
        if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool) or max_output_tokens < 1:
            errors.append("decoding.max_output_tokens must be an integer >= 1")

        seeds = decoding.get("seeds")
        if not isinstance(seeds, list) or not seeds:
            errors.append("decoding.seeds must be a non-empty list")
            seeds = []
        else:
            if len(set(seeds)) != len(seeds):
                errors.append("decoding.seeds must not contain duplicates")
            if any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds):
                errors.append("every decoding seed must be an integer")

    retry = manifest.get("retry_policy")
    if not isinstance(retry, Mapping):
        errors.append("retry_policy must be an object")
        max_attempts = None
    else:
        max_attempts = retry.get("max_attempts")
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
            errors.append("retry_policy.max_attempts must be an integer >= 1")
        if not _nonempty_string(retry.get("feedback_policy")):
            errors.append("retry_policy.feedback_policy must be a non-empty frozen policy description")
        if retry.get("same_attempt_limit_both_arms") is not True:
            errors.append("retry_policy.same_attempt_limit_both_arms must be true")
        if retry.get("human_correction_allowed") is not False:
            errors.append("retry_policy.human_correction_allowed must be false")

    prompts = manifest.get("prompt_templates")
    if not isinstance(prompts, Mapping):
        errors.append("prompt_templates must be an object")
    else:
        for field in ("direct_sha256", "structured_sha256", "receipt_sha256"):
            _require_hash(f"prompt_templates.{field}", prompts.get(field), errors)

    environment = manifest.get("environment")
    if not isinstance(environment, Mapping):
        errors.append("environment must be an object")
    else:
        if not _nonempty_string(environment.get("openscad_version")):
            errors.append("environment.openscad_version must be a non-empty exact version")
        openscad_fn = environment.get("openscad_fn")
        if not isinstance(openscad_fn, int) or isinstance(openscad_fn, bool) or not 12 <= openscad_fn <= 360:
            errors.append("environment.openscad_fn must be an integer in [12, 360]")
        timeout = environment.get("compile_timeout_seconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
            errors.append("environment.compile_timeout_seconds must be an integer >= 1")

    retention = manifest.get("retention_policy")
    if not isinstance(retention, Mapping):
        errors.append("retention_policy must be an object")
    else:
        if retention.get("retain_raw_outputs") is not True:
            errors.append("retention_policy.retain_raw_outputs must be true")
        if retention.get("retain_failed_trials") is not True:
            errors.append("retention_policy.retain_failed_trials must be true")
        if retention.get("retain_compile_logs") is not True:
            errors.append("retention_policy.retain_compile_logs must be true")

    cost_cap = manifest.get("cost_cap_usd")
    if (
        not isinstance(cost_cap, (int, float))
        or isinstance(cost_cap, bool)
        or not (0 <= float(cost_cap) < 10_000)
    ):
        errors.append("cost_cap_usd must be a finite numeric cap in [0, 10000)")

    estimated_max_calls = manifest.get("estimated_max_calls")
    if not isinstance(estimated_max_calls, int) or isinstance(estimated_max_calls, bool) or estimated_max_calls < 1:
        errors.append("estimated_max_calls must be an integer >= 1")
    elif task_count and seeds and isinstance(max_attempts, int) and max_attempts >= 1:
        expected = task_count * 2 * len(seeds) * max_attempts
        if estimated_max_calls != expected:
            errors.append(
                "estimated_max_calls must equal task_count × 2 arms × seed_count × max_attempts "
                f"({expected})"
            )

    return errors


def assert_executable(manifest: Mapping[str, Any]) -> None:
    """Fail closed unless the manifest is complete and explicitly authorized."""

    errors = validate_manifest(manifest, require_authorized=True)
    if errors:
        raise ManifestError("Stage 2 execution blocked:\n- " + "\n- ".join(errors))


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ManifestError("Stage 2 manifest root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--template-check",
        action="store_true",
        help="Check that a template remains non-authorized; does not make it executable.",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if args.template_check:
        if manifest.get("authorized") is not False:
            raise ManifestError("template must keep authorized=false")
        print("Stage 2 template is non-authorized as required.")
        return 0

    assert_executable(manifest)
    print("Stage 2 manifest is complete and explicitly authorized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
