"""Fail-closed execution-authorization freezer for the NeuroCAD S3 successor.

The S3 scientific protocol deliberately stops before held-out outcome access. This module
closes the remaining mechanical gate: it validates that the final selection, exact model
identity, four matched baseline families, prompt/schema/verifier/environment identities,
decoding/retry/cost ceilings, human review attestation, and frozen scientific protocol are
all bound into one deterministic authorization receipt.

It does not call a model, inspect an outcome, select prompts, or invent missing identities.
Incomplete or placeholder-bearing manifests are rejected rather than upgraded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "neurocad.s3.execution-authorization.v0"
STATUS = "FROZEN_AUTHORIZED"
HISTORICAL_BOUNDARY = "FALSIFIED_VALIDATION_DOMINANT_UNCHANGED"
FROZEN_PROTOCOL_SHA256 = "49c93a2df61a3adcc98eab89f3dcd610e7f6d2f730d1c960b3989c5866f0b320"
EXPECTED_TRIAL_IDS = (2026090501, 2026090502, 2026090503, 2026090504, 2026090505)
REQUIRED_BINDINGS = (
    "final_selection_sha256",
    "scientific_protocol_sha256",
    "prompt_bundle_sha256",
    "schema_bundle_sha256",
    "shared_verifier_sha256",
    "environment_lock_sha256",
    "analysis_plan_sha256",
)
IDENTITY_FIELDS = ("provider", "model", "revision", "runtime")
PLACEHOLDER_MARKERS = (
    "todo",
    "tbd",
    "pending",
    "placeholder",
    "unknown",
    "fill_me",
    "replace_me",
    "<",
    ">",
)


class AuthorizationError(ValueError):
    """Raised when an S3 authorization manifest is incomplete or unsafe."""


def _canonical_payload(manifest: Mapping[str, Any]) -> bytes:
    payload = dict(manifest)
    payload.pop("authorization_sha256", None)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_authorization_sha256(manifest: Mapping[str, Any]) -> str:
    """Return the deterministic digest for all authorization-relevant fields."""

    return hashlib.sha256(_canonical_payload(manifest)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _is_concrete_text(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.strip().lower()
    return not any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _validate_identity(identity: Any, *, label: str, errors: list[str]) -> dict[str, str] | None:
    if not isinstance(identity, Mapping):
        errors.append(f"{label} must be an object")
        return None
    normalized: dict[str, str] = {}
    for field in IDENTITY_FIELDS:
        value = identity.get(field)
        if not _is_concrete_text(value):
            errors.append(f"{label}.{field} must be an exact non-placeholder string")
        else:
            normalized[field] = str(value).strip()
    return normalized if len(normalized) == len(IDENTITY_FIELDS) else None


def validate_authorization_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return all violations without accessing any scientific outcome."""

    errors: list[str] = []

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    if manifest.get("status") != STATUS:
        errors.append(f"status must equal {STATUS}")
    if manifest.get("execution_authorized") is not True:
        errors.append("execution_authorized must be true only in a complete frozen receipt")
    if manifest.get("outcome_access_allowed") is not True:
        errors.append("outcome_access_allowed must be true only after all authorization gates pass")
    if manifest.get("outcomes_observed") is not False:
        errors.append("outcomes_observed must be false when the authorization receipt is frozen")
    if manifest.get("historical_typed_parser_claim") != HISTORICAL_BOUNDARY:
        errors.append("historical typed-parser falsification boundary changed")

    bindings = manifest.get("artifact_bindings")
    if not isinstance(bindings, Mapping):
        errors.append("artifact_bindings must be an object")
    else:
        if tuple(sorted(bindings)) != tuple(sorted(REQUIRED_BINDINGS)):
            errors.append("artifact_bindings must contain exactly the seven required frozen digests")
        for key in REQUIRED_BINDINGS:
            if not _is_sha256(bindings.get(key)):
                errors.append(f"artifact_bindings.{key} must be a lowercase SHA-256 digest")
        if bindings.get("scientific_protocol_sha256") != FROZEN_PROTOCOL_SHA256:
            errors.append("scientific protocol digest does not match the frozen S3 protocol")

    target = _validate_identity(manifest.get("evaluated_model"), label="evaluated_model", errors=errors)

    baselines = manifest.get("baseline_families")
    if not isinstance(baselines, list) or len(baselines) != 4:
        errors.append("baseline_families must contain exactly four frozen families")
    else:
        ids: list[str] = []
        for index, baseline in enumerate(baselines):
            label = f"baseline_families[{index}]"
            if not isinstance(baseline, Mapping):
                errors.append(f"{label} must be an object")
                continue
            baseline_id = baseline.get("id")
            if not _is_concrete_text(baseline_id):
                errors.append(f"{label}.id must be a concrete non-placeholder string")
            else:
                ids.append(str(baseline_id).strip())
            identity = _validate_identity(baseline.get("identity"), label=f"{label}.identity", errors=errors)
            if baseline.get("matched_provider_model") is not True:
                errors.append(f"{label}.matched_provider_model must be true")
            if target is not None and identity is not None and identity != target:
                errors.append(f"{label}.identity must exactly match evaluated_model identity")
        if len(ids) != len(set(ids)):
            errors.append("baseline family ids must be unique")

    policy = manifest.get("common_validation_policy")
    if not isinstance(policy, Mapping):
        errors.append("common_validation_policy must be an object")
    else:
        if not _is_sha256(policy.get("sha256")):
            errors.append("common_validation_policy.sha256 must be a lowercase SHA-256 digest")
        for field in (
            "applies_to_all_arms",
            "same_final_verifier_all_arms",
            "human_correction_disabled",
            "retain_raw_outputs",
            "retain_failed_trials",
            "retain_compile_logs",
        ):
            if policy.get(field) is not True:
                errors.append(f"common_validation_policy.{field} must be true")

    decoding = manifest.get("decoding_and_budget")
    if not isinstance(decoding, Mapping):
        errors.append("decoding_and_budget must be an object")
    else:
        temperature = decoding.get("temperature")
        top_p = decoding.get("top_p")
        max_tokens = decoding.get("max_output_tokens")
        max_attempts = decoding.get("max_attempts_per_prompt_arm_trial")
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool) or temperature < 0:
            errors.append("decoding_and_budget.temperature must be a non-negative number")
        if not isinstance(top_p, (int, float)) or isinstance(top_p, bool) or not 0 < top_p <= 1:
            errors.append("decoding_and_budget.top_p must be in (0, 1]")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            errors.append("decoding_and_budget.max_output_tokens must be a positive integer")
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts <= 0:
            errors.append("decoding_and_budget.max_attempts_per_prompt_arm_trial must be a positive integer")
        if not _is_concrete_text(decoding.get("feedback_policy")):
            errors.append("decoding_and_budget.feedback_policy must be a concrete frozen description")
        if decoding.get("same_budget_all_arms") is not True:
            errors.append("decoding_and_budget.same_budget_all_arms must be true")
        cost_cap = decoding.get("cost_cap_usd")
        if not isinstance(cost_cap, (int, float)) or isinstance(cost_cap, bool) or cost_cap <= 0:
            errors.append("decoding_and_budget.cost_cap_usd must be a positive number")

    trial_ids = manifest.get("trial_ids")
    if not isinstance(trial_ids, list) or tuple(trial_ids) != EXPECTED_TRIAL_IDS:
        errors.append("trial_ids must equal the five predeclared S3 trial IDs in order")

    counts = manifest.get("execution_counts")
    if not isinstance(counts, Mapping):
        errors.append("execution_counts must be an object")
    else:
        selected = counts.get("selected_prompt_count")
        arm_count = counts.get("arm_count")
        ceiling = counts.get("maximum_call_ceiling")
        max_attempts = decoding.get("max_attempts_per_prompt_arm_trial") if isinstance(decoding, Mapping) else None
        for field, value in (("selected_prompt_count", selected), ("arm_count", arm_count)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"execution_counts.{field} must be a positive integer")
        if (
            isinstance(selected, int)
            and not isinstance(selected, bool)
            and selected > 0
            and isinstance(arm_count, int)
            and not isinstance(arm_count, bool)
            and arm_count > 0
            and isinstance(max_attempts, int)
            and not isinstance(max_attempts, bool)
            and max_attempts > 0
        ):
            expected_ceiling = selected * arm_count * len(EXPECTED_TRIAL_IDS) * max_attempts
            if ceiling != expected_ceiling:
                errors.append(
                    "execution_counts.maximum_call_ceiling must equal "
                    "selected_prompt_count * arm_count * 5 trials * max_attempts"
                )
        elif not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling <= 0:
            errors.append("execution_counts.maximum_call_ceiling must be a positive integer")

    review = manifest.get("independent_manifest_review")
    if not isinstance(review, Mapping):
        errors.append("independent_manifest_review must be an object")
    else:
        if review.get("completed") is not True:
            errors.append("independent_manifest_review.completed must be true")
        if review.get("outcomes_unobserved_at_review") is not True:
            errors.append("independent_manifest_review.outcomes_unobserved_at_review must be true")
        if not _is_sha256(review.get("attestation_sha256")):
            errors.append("independent_manifest_review.attestation_sha256 must be a lowercase SHA-256 digest")

    supplied_hash = manifest.get("authorization_sha256")
    computed_hash = compute_authorization_sha256(manifest)
    if supplied_hash != computed_hash:
        errors.append("authorization_sha256 does not match canonical authorization content")

    return errors


def assert_authorized(manifest: Mapping[str, Any]) -> None:
    errors = validate_authorization_manifest(manifest)
    if errors:
        raise AuthorizationError("S3 authorization invalid:\n- " + "\n- ".join(errors))


def freeze_authorization(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Insert the canonical digest and return a validated frozen authorization receipt."""

    frozen = dict(manifest)
    frozen["authorization_sha256"] = compute_authorization_sha256(frozen)
    assert_authorized(frozen)
    return frozen


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuthorizationError("S3 authorization manifest root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="completed pre-outcome S3 authorization JSON")
    parser.add_argument("--write-frozen", type=Path, default=None)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if "authorization_sha256" in manifest:
        assert_authorized(manifest)
        frozen = manifest
    else:
        frozen = freeze_authorization(manifest)

    if args.write_frozen is not None:
        if args.write_frozen.exists():
            raise AuthorizationError(f"refusing to overwrite existing receipt: {args.write_frozen}")
        args.write_frozen.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"READY_TO_RUN_FROZEN_S3_PROTOCOL {frozen['authorization_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
