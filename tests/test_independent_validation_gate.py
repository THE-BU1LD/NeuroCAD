from __future__ import annotations

import copy

import pytest

from core.independent_validation_gate import (
    PROTOCOL_VERSION,
    canonical_manifest_sha256,
    validate_preoutcome_manifest,
)

SHA = "a" * 64
GIT_SHA = "b" * 40


def _manifest() -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "source": {
            "git_commit": GIT_SHA,
            "clean_tree": True,
            "source_surface_sha256": SHA,
            "environment_sha256": SHA,
            "openscad_identity": "OpenSCAD 2021.01; executable receipt retained",
            "output_directory_empty": True,
        },
        "challenge": {
            "dataset_sha256": SHA,
            "provenance": "independently authored challenge; provenance receipt retained",
            "license_or_permission": "written evaluation permission retained",
            "independent_author_role": "challenge author did not inspect case-level system outcomes",
            "coverage_summary_sha256": SHA,
            "adjudication_receipt_sha256": SHA,
            "no_post_outcome_case_editing": True,
        },
        "comparator": {
            "mode": "frozen_comparator",
            "receipt_sha256": SHA,
            "matched_information": True,
            "matched_failure_accounting": True,
            "claim_boundary": None,
        },
        "endpoint": {
            "primary_name": "semantic_validity_rate",
            "aggregation_rule": "successful cases / all frozen confirmatory cases",
            "failure_rule": "timeouts, exceptions, invalid, missing, and verifier failures count as failures",
            "manifest_sha256": SHA,
        },
        "leakage_review": {
            "reviewer": "independent outcome-blind reviewer",
            "receipt_sha256": SHA,
            "outcome_blind": True,
            "passed": True,
        },
        "retention": {
            "immutable_attempts": True,
            "resume_allowed": False,
            "overwrite_allowed": False,
        },
        "outcome_access": {
            "execution_authorized": False,
            "outcomes_observed": False,
            "adjudication_unlocked": False,
        },
    }


def test_complete_packet_is_ready_for_human_review_but_never_machine_authorized() -> None:
    manifest = _manifest()
    report = validate_preoutcome_manifest(manifest)

    assert report.ready_for_human_authorization is True
    assert report.blockers == ()
    assert report.machine_execution_authorized is False
    assert report.manifest_sha256 == canonical_manifest_sha256(manifest)


def test_incomplete_packet_reports_blockers_without_granting_authority() -> None:
    manifest = _manifest()
    manifest["source"]["clean_tree"] = False
    manifest["source"]["environment_sha256"] = None
    manifest["challenge"]["no_post_outcome_case_editing"] = False
    manifest["leakage_review"]["passed"] = False
    manifest["retention"]["resume_allowed"] = True
    manifest["retention"]["overwrite_allowed"] = True

    report = validate_preoutcome_manifest(manifest)

    assert report.ready_for_human_authorization is False
    assert report.machine_execution_authorized is False
    assert "source.environment_sha256 is not frozen" in report.blockers
    assert "source.clean_tree must be true" in report.blockers
    assert "challenge.no_post_outcome_case_editing must be true" in report.blockers
    assert "leakage_review.passed must be true" in report.blockers
    assert "retention.resume_allowed must be false" in report.blockers
    assert "retention.overwrite_allowed must be false" in report.blockers


@pytest.mark.parametrize("field", ["execution_authorized", "outcomes_observed", "adjudication_unlocked"])
def test_preoutcome_validator_rejects_any_open_outcome_access(field: str) -> None:
    manifest = _manifest()
    manifest["outcome_access"][field] = True

    with pytest.raises(ValueError, match="pre-outcome manifest must keep"):
        validate_preoutcome_manifest(manifest)


def test_extra_fields_are_rejected_to_prevent_outcome_smuggling() -> None:
    manifest = _manifest()
    manifest["challenge"]["observed_score"] = 0.91

    with pytest.raises(ValueError, match="challenge keys mismatch"):
        validate_preoutcome_manifest(manifest)


def test_invalid_hash_is_rejected_instead_of_silently_normalized() -> None:
    manifest = _manifest()
    manifest["challenge"]["dataset_sha256"] = "ABC123"

    with pytest.raises(ValueError, match="lowercase 64-hex"):
        validate_preoutcome_manifest(manifest)


def test_frozen_comparator_requires_matched_information_and_failure_accounting() -> None:
    manifest = _manifest()
    manifest["comparator"]["matched_information"] = False
    manifest["comparator"]["matched_failure_accounting"] = False

    report = validate_preoutcome_manifest(manifest)

    assert report.ready_for_human_authorization is False
    assert "frozen comparator requires comparator.matched_information=true" in report.blockers
    assert "frozen comparator requires comparator.matched_failure_accounting=true" in report.blockers


def test_claim_narrowed_mode_does_not_fake_comparator_fairness() -> None:
    manifest = _manifest()
    manifest["comparator"] = {
        "mode": "claim_narrowed",
        "receipt_sha256": SHA,
        "matched_information": False,
        "matched_failure_accounting": False,
        "claim_boundary": "Report exact-source-bound NeuroCAD behavior only; make no superiority claim.",
    }

    report = validate_preoutcome_manifest(manifest)

    assert report.ready_for_human_authorization is True
    assert report.machine_execution_authorized is False


def test_claim_narrowed_mode_requires_explicit_claim_boundary() -> None:
    manifest = _manifest()
    manifest["comparator"] = {
        "mode": "claim_narrowed",
        "receipt_sha256": SHA,
        "matched_information": False,
        "matched_failure_accounting": False,
        "claim_boundary": None,
    }

    report = validate_preoutcome_manifest(manifest)

    assert report.ready_for_human_authorization is False
    assert "claim_narrowed mode requires a non-empty comparator.claim_boundary" in report.blockers


def test_manifest_hash_is_order_independent() -> None:
    manifest = _manifest()
    reordered = copy.deepcopy(manifest)
    reordered["source"] = dict(reversed(list(reordered["source"].items())))

    assert canonical_manifest_sha256(manifest) == canonical_manifest_sha256(reordered)
