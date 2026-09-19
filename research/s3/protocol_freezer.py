"""Fail-closed validator for the frozen NeuroCAD S3 scientific protocol.

This module validates only pre-outcome protocol structure. It never authorizes execution,
calls a provider, opens held-out outcomes, or changes the historical typed-parser verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "neurocad.s3.scientific-protocol.v0"
STATUS = "FROZEN_NOT_AUTHORIZED"
HISTORICAL_BOUNDARY = "FALSIFIED_VALIDATION_DOMINANT_UNCHANGED"
EXPECTED_HYPOTHESES = ("H1", "H2", "H3")
EXPECTED_PRIMARY_ARMS = ("direct_generation", "full_structured_neurocad")
EXPECTED_ABLATIONS = (
    "no_schema_compiler_retained",
    "typed_intermediate_no_internal_validation",
    "full_structured_no_model_facing_feedback",
    "direct_generation_equal_verifier_feedback",
)
EXPECTED_SECONDARY_METRICS = (
    "compile_success_rate",
    "hard_constraint_satisfaction_rate",
    "blinded_semantic_task_satisfaction_rate",
    "invalid_underspecified_response_policy_correctness_rate",
    "retry_count",
    "generated_tokens",
    "wall_clock_seconds",
    "estimated_cost_usd",
)
EXPECTED_TRIAL_IDS = (2026090501, 2026090502, 2026090503, 2026090504, 2026090505)
EXPECTED_ERROR_TAXONOMY = (
    "syntax_compile_failure",
    "unsupported_operation",
    "missing_required_object",
    "wrong_dimension_or_unit",
    "spatial_relation_violation",
    "forbidden_disconnected_or_intersecting_geometry",
    "semantic_misinterpretation",
    "verifier_ambiguity_or_error",
    "timeout_or_retry_exhaustion",
    "infrastructure_failure",
)
EXPECTED_FALSIFIERS = (
    "F1_PRIMARY_NO_HVR_GAIN",
    "F2_BUDGET_OR_FEEDBACK_ASYMMETRY",
    "F3_SEMANTIC_DEGRADATION",
    "F4_NO_EXTERNAL_OR_OOD_GAIN",
    "F5_VERIFIER_DIFFERENTIAL_BIAS",
    "F6_MECHANISM_ABLATION_FAILURE",
)
EXPECTED_AUTHORIZATION_DEPENDENCIES = (
    "final_selection_sha256",
    "exact_neurocad_provider_model_revision_runtime_identity",
    "four_matched_baseline_family_identities_and_common_validation_policy",
    "prompt_and_schema_hashes",
    "shared_verifier_hash_and_environment_identity",
    "decoding_retry_budget_and_cost_ceiling",
    "this_scientific_protocol_sha256",
)


class ProtocolError(ValueError):
    """Raised when the S3 protocol is incomplete, mutated, or unsafe."""


def _canonical_payload(protocol: Mapping[str, Any]) -> bytes:
    payload = dict(protocol)
    payload.pop("protocol_sha256", None)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_protocol_sha256(protocol: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(protocol)).hexdigest()


def _ids(records: Any, *, field: str, errors: list[str]) -> list[str]:
    if not isinstance(records, list):
        errors.append(f"{field} must be a list")
        return []
    result: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            errors.append(f"{field}[{index}] must be an object")
            continue
        value = record.get("id")
        if not isinstance(value, str) or not value:
            errors.append(f"{field}[{index}].id must be a non-empty string")
            continue
        result.append(value)
    if len(set(result)) != len(result):
        errors.append(f"{field} ids must be unique")
    return result


def validate_protocol(protocol: Mapping[str, Any]) -> list[str]:
    """Return every protocol violation without inspecting any outcome."""
    errors: list[str] = []

    if protocol.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    if protocol.get("status") != STATUS:
        errors.append(f"status must equal {STATUS}")
    if protocol.get("execution_authorized") is not False:
        errors.append("execution_authorized must remain false")
    if protocol.get("outcomes_observed") is not False:
        errors.append("outcomes_observed must remain false")
    if protocol.get("historical_typed_parser_claim") != HISTORICAL_BOUNDARY:
        errors.append("historical typed-parser falsification boundary changed")

    hypotheses = protocol.get("hypotheses")
    hypothesis_ids = _ids(hypotheses, field="hypotheses", errors=errors)
    if tuple(hypothesis_ids) != EXPECTED_HYPOTHESES:
        errors.append("hypotheses must freeze exactly H1, H2, H3 in order")
    if isinstance(hypotheses, list):
        roles = {record.get("id"): record.get("role") for record in hypotheses if isinstance(record, Mapping)}
        if roles.get("H1") != "primary":
            errors.append("H1 must remain the sole primary hypothesis")
        for record in hypotheses:
            if isinstance(record, Mapping):
                for field in ("claim", "support_gate"):
                    if not isinstance(record.get(field), str) or not record[field].strip():
                        errors.append(f"hypothesis {record.get('id')!r}.{field} must be non-empty")

    arms = protocol.get("arms")
    if not isinstance(arms, Mapping):
        errors.append("arms must be an object")
    else:
        primary_ids = _ids(arms.get("primary"), field="arms.primary", errors=errors)
        if tuple(primary_ids) != EXPECTED_PRIMARY_ARMS:
            errors.append("primary arms must freeze direct_generation and full_structured_neurocad")
        ablations = arms.get("mechanism_ablations")
        ablation_ids = _ids(ablations, field="arms.mechanism_ablations", errors=errors)
        if tuple(ablation_ids) != EXPECTED_ABLATIONS:
            errors.append("mechanism ablations must freeze exactly the four preregistered ablations")
        if isinstance(ablations, list):
            for arm in ablations:
                if not isinstance(arm, Mapping):
                    continue
                for field in (
                    "same_provider_model",
                    "same_decoding_budget",
                    "same_retry_budget",
                    "shared_independent_final_verifier",
                ):
                    if arm.get(field) is not True:
                        errors.append(f"ablation {arm.get('id')!r}.{field} must remain true")
                if arm.get("outcome_access_allowed") is not False:
                    errors.append(f"ablation {arm.get('id')!r}.outcome_access_allowed must remain false")

    metrics = protocol.get("metrics")
    if not isinstance(metrics, Mapping):
        errors.append("metrics must be an object")
    else:
        primary = metrics.get("primary")
        if not isinstance(primary, Mapping):
            errors.append("metrics.primary must be an object")
        else:
            if primary.get("id") != "hard_verifiability_rate":
                errors.append("hard_verifiability_rate must remain the primary metric")
            if primary.get("unit") != "binary_per_prompt_trial":
                errors.append("primary HVR unit must remain binary_per_prompt_trial")
            if primary.get("higher_is_better") is not True:
                errors.append("primary HVR higher_is_better must remain true")
            success_requires = primary.get("success_requires")
            if not isinstance(success_requires, list) or len(success_requires) != 3:
                errors.append("primary HVR success_requires must retain exactly three frozen requirements")
        secondary = metrics.get("secondary")
        if not isinstance(secondary, list) or tuple(secondary) != EXPECTED_SECONDARY_METRICS:
            errors.append("secondary metric set/order changed")
        if metrics.get("stratified_reporting") != [
            "taxonomy_class",
            "source_benchmark",
            "evaluation_stratum",
        ]:
            errors.append("stratified reporting dimensions changed")
        policy = metrics.get("secondary_claim_policy")
        if not isinstance(policy, str) or "cannot rescue" not in policy:
            errors.append("secondary_claim_policy must explicitly forbid rescuing H1")

    trials = protocol.get("trials")
    if not isinstance(trials, Mapping):
        errors.append("trials must be an object")
    else:
        trial_ids = trials.get("predeclared_trial_ids")
        if not isinstance(trial_ids, list) or tuple(trial_ids) != EXPECTED_TRIAL_IDS:
            errors.append("predeclared trial IDs changed")
        if trials.get("count_per_prompt_arm") != 5:
            errors.append("count_per_prompt_arm must remain 5")
        seed_policy = trials.get("provider_seed_policy")
        if not isinstance(seed_policy, str) or "provider seeding is unsupported" not in seed_policy:
            errors.append("provider_seed_policy must preserve the unsupported-seed disclosure rule")
        if trials.get("drop_or_replace_after_outcome_access") is not False:
            errors.append("trial drop/replacement after outcome access must remain false")

    uncertainty = protocol.get("uncertainty_and_tests")
    if not isinstance(uncertainty, Mapping):
        errors.append("uncertainty_and_tests must be an object")
    else:
        if uncertainty.get("paired_unit") != "prompt_x_trial_id":
            errors.append("paired_unit must remain prompt_x_trial_id")
        primary_test = uncertainty.get("primary_test")
        if not isinstance(primary_test, Mapping) or primary_test.get("name") != "exact_mcnemar_two_sided" or primary_test.get("alpha") != 0.05:
            errors.append("primary test must remain two-sided exact McNemar at alpha 0.05")
        ci = uncertainty.get("primary_confidence_interval")
        if (
            not isinstance(ci, Mapping)
            or ci.get("name") != "paired_cluster_bootstrap_percentile"
            or ci.get("cluster_unit") != "prompt"
            or ci.get("confidence") != 0.95
            or ci.get("replicates") != 10000
            or ci.get("bootstrap_seed") != 2026090506
        ):
            errors.append("primary confidence-interval contract changed")
        multiplicity = uncertainty.get("multiplicity")
        if not isinstance(multiplicity, str) or "sole confirmatory primary endpoint" not in multiplicity:
            errors.append("multiplicity rule must keep H1 as the sole confirmatory primary endpoint")

    failure_policy = protocol.get("failure_policy")
    if not isinstance(failure_policy, Mapping):
        errors.append("failure_policy must be an object")
    else:
        for field in (
            "compile_failure_hvr",
            "verifier_failure_hvr",
            "timeout_hvr",
            "retry_exhaustion_hvr",
            "missing_final_artifact_hvr",
        ):
            if failure_policy.get(field) is not False:
                errors.append(f"failure_policy.{field} must remain false")
        for field in ("retain_raw_failed_trials", "distinguish_infrastructure_from_scientific_failure"):
            if failure_policy.get(field) is not True:
                errors.append(f"failure_policy.{field} must remain true")

    taxonomy = protocol.get("error_taxonomy")
    if not isinstance(taxonomy, list) or tuple(taxonomy) != EXPECTED_ERROR_TAXONOMY:
        errors.append("error taxonomy changed")

    falsifiers = protocol.get("falsifiers")
    falsifier_ids = _ids(falsifiers, field="falsifiers", errors=errors)
    if tuple(falsifier_ids) != EXPECTED_FALSIFIERS:
        errors.append("falsifiers must freeze exactly F1-F6")
    if isinstance(falsifiers, list):
        for record in falsifiers:
            if isinstance(record, Mapping):
                for field in ("condition", "effect"):
                    if not isinstance(record.get(field), str) or not record[field].strip():
                        errors.append(f"falsifier {record.get('id')!r}.{field} must be non-empty")

    reporting = protocol.get("reporting_rules")
    if not isinstance(reporting, Mapping):
        errors.append("reporting_rules must be an object")
    else:
        for field in (
            "retain_every_raw_response_and_failed_attempt",
            "retain_final_artifact_hashes",
            "retain_verifier_identity_and_logs",
            "report_effect_sizes_and_uncertainty",
            "report_negative_mixed_inconclusive_results_unchanged",
            "no_post_outcome_threshold_seed_metric_or_arm_changes",
            "no_result_rescue",
        ):
            if reporting.get(field) is not True:
                errors.append(f"reporting_rules.{field} must remain true")

    dependencies = protocol.get("authorization_dependencies")
    if not isinstance(dependencies, list) or tuple(dependencies) != EXPECTED_AUTHORIZATION_DEPENDENCIES:
        errors.append("authorization dependencies changed")

    supplied_hash = protocol.get("protocol_sha256")
    computed_hash = compute_protocol_sha256(protocol)
    if supplied_hash != computed_hash:
        errors.append("protocol_sha256 does not match canonical protocol content")

    return errors


def assert_frozen_protocol(protocol: Mapping[str, Any]) -> None:
    errors = validate_protocol(protocol)
    if errors:
        raise ProtocolError("S3 protocol invalid:\n- " + "\n- ".join(errors))


def load_protocol(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProtocolError("S3 protocol root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    args = parser.parse_args()
    payload = load_protocol(args.protocol)
    assert_frozen_protocol(payload)
    print(f"S3 protocol frozen and non-authorized: {payload['protocol_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
