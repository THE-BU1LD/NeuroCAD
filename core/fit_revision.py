"""Evidence-bound project revisions derived from sealed physical-fit studies.

The workflow in this module deliberately separates a reviewable plan from its
application.  A fit report can justify a bounded design revision, but it does
not certify the resulting part or establish transfer to another process.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

from .fit_sample import cutout_fit_sample
from .fit_study import verify_fit_evidence_bundle, verify_fit_study_bundle
from .json_io import strict_json_loads
from .project import (
    EnclosureProject,
    enclosure_spec_to_dict,
    parse_project,
    semantic_diff,
    serialize_project,
    update_project,
)

FIT_REVISION_PLAN_VERSION = "neurocad-fit-revision-plan-v1"
MAX_FIT_REVISION_JSON_BYTES = 1_048_576
SUPPORTED_DISPOSITION = "BRACKETED_OBSERVED_TRANSITION"
LIMITATIONS = (
    "The revision is a deterministic translation of one sealed, process-specific fit study; it is not a fit certification.",
    "The recommended adjustment changes the named nominal cutout so its compiled aperture changes by the same amount.",
    "Only the named cutout dimensions may change; position, purpose, profile, and all other project fields are preserved.",
    "A new fit study on the revised design is required to confirm the revision under the intended manufacturing process.",
    "The sealed attachments are hash-bound but their authorship and truthfulness are not authenticated by NeuroCAD.",
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _read_json(path: Path, *, label: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file")
    raw = path.read_bytes()
    if len(raw) > MAX_FIT_REVISION_JSON_BYTES:
        raise ValueError(f"{label} exceeds {MAX_FIT_REVISION_JSON_BYTES} bytes")
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8") from exc


def _exact_object(value: object, keys: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    missing = sorted(keys - set(value))
    extra = sorted(set(value) - keys)
    if missing:
        raise ValueError(f"{label} is missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported keys: {', '.join(extra)}")
    return value


def _finite_adjustment(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("fit-study recommended adjustment must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not -5 <= result <= 5:
        raise ValueError("fit-study recommended adjustment must be between -5 and 5 mm")
    return result


def _project_hash(project: EnclosureProject) -> str:
    canonical = parse_project(serialize_project(project))
    return _sha256(serialize_project(canonical).encode("utf-8"))


def _verified_inputs(
    project: EnclosureProject,
    study_bundle: Path,
    evidence_bundle: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    if not isinstance(project, EnclosureProject):
        raise TypeError("project must be an EnclosureProject")
    study_verification = verify_fit_study_bundle(study_bundle, expected_project=project)
    evidence_verification = verify_fit_evidence_bundle(study_bundle, evidence_bundle)
    evidence_root_input = evidence_bundle.expanduser()
    if evidence_root_input.is_symlink():
        raise ValueError("fit-evidence bundle directory must not be a symbolic link")
    evidence_root = evidence_root_input.resolve()
    report = _read_json(evidence_root / "report.json", label="fit-evidence report")
    report = _exact_object(
        report,
        {
            "schema_version",
            "fit_study_manifest_sha256",
            "fit_study_binding_sha256",
            "canonical_observations_sha256",
            "source_project_sha256",
            "passport",
            "observations",
            "variant_results",
            "acceptance_rule",
            "disposition",
            "observed_failure_edge_mm",
            "observed_success_edge_mm",
            "recommended_tested_adjustment_mm",
            "non_monotone_violations",
            "limitations",
            "physical_fit_certified",
        },
        label="fit-evidence report",
    )
    if report["disposition"] != SUPPORTED_DISPOSITION:
        raise ValueError(
            "fit revision requires a bracketed observed transition; "
            f"received {report['disposition']!r}"
        )
    if report["physical_fit_certified"] is not False:
        raise ValueError("fit-evidence report contains an unsupported certification claim")
    if report["source_project_sha256"] != _project_hash(project):
        raise ValueError("fit-evidence report does not match the exact source project revision")
    return study_verification, evidence_verification, report, evidence_root


def _proposed_dimensions(
    project: EnclosureProject,
    cutout_id: str,
    adjustment: float,
) -> tuple[dict[str, object], dict[str, object], EnclosureProject]:
    raw_cutouts = deepcopy(enclosure_spec_to_dict(project.spec)["cutouts"])
    matches = [(index, item) for index, item in enumerate(raw_cutouts) if item["id"] == cutout_id]
    if len(matches) != 1:
        raise ValueError("fit-study source cutout does not resolve uniquely in the project")
    index, cutout = matches[0]
    before: dict[str, object]
    after: dict[str, object]
    if cutout["kind"] == "circular":
        diameter = cutout.get("diameter_mm")
        if isinstance(diameter, bool) or not isinstance(diameter, (int, float)):
            raise ValueError("circular fit-study cutout has no numeric nominal diameter")
        revised = float(diameter) + adjustment
        before = {"diameter_mm": float(diameter)}
        after = {"diameter_mm": revised}
        raw_cutouts[index]["diameter_mm"] = revised
    elif cutout["kind"] == "rectangular":
        size = cutout.get("size_mm")
        if not isinstance(size, list) or len(size) != 2 or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) for value in size
        ):
            raise ValueError("rectangular fit-study cutout has no numeric nominal size")
        revised_size = [float(size[0]) + adjustment, float(size[1]) + adjustment]
        before = {"size_mm": [float(size[0]), float(size[1])]}
        after = {"size_mm": revised_size}
        raw_cutouts[index]["size_mm"] = revised_size
    else:
        raise ValueError("fit-study cutout kind is not supported for a project revision")
    reason = f"apply sealed fit-study adjustment to cutout {cutout_id}"
    revised_project = update_project(project, "cutouts", raw_cutouts, reason=reason)
    return before, after, revised_project


def create_fit_revision_plan(
    project: EnclosureProject,
    study_bundle: Path,
    evidence_bundle: Path,
) -> dict[str, Any]:
    """Create a deterministic, review-only plan from sealed fit evidence."""

    study_verification, evidence_verification, report, evidence_root = _verified_inputs(
        project, study_bundle, evidence_bundle
    )
    study = _read_json(study_bundle.expanduser().resolve() / "study.json", label="fit-study document")
    cutout_id = study.get("source_cutout_id") if isinstance(study, dict) else None
    if not isinstance(cutout_id, str) or not cutout_id:
        raise ValueError("fit-study document has no source cutout ID")
    adjustment = _finite_adjustment(report["recommended_tested_adjustment_mm"])
    if adjustment == 0:
        raise ValueError("fit-study recommends zero adjustment; no project revision is necessary")
    before, after, revised_project = _proposed_dimensions(project, cutout_id, adjustment)

    baseline_sample = cutout_fit_sample(project, cutout_id, aperture_adjustment_mm=0)
    revised_sample = cutout_fit_sample(revised_project, cutout_id, aperture_adjustment_mm=0)
    baseline_aperture = [float(value) for value in baseline_sample.metadata["aperture_size_mm"]]
    proposed_aperture = [float(value) for value in revised_sample.metadata["aperture_size_mm"]]
    expected_aperture = [value + adjustment for value in baseline_aperture]
    if any(
        not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
        for actual, expected in zip(proposed_aperture, expected_aperture, strict=True)
    ):
        raise ValueError("proposed nominal edit does not produce the evidence-recommended compiled aperture")

    report_bytes = (evidence_root / "report.json").read_bytes()
    plan = {
        "schema_version": FIT_REVISION_PLAN_VERSION,
        "source": {
            "project_id": project.project_id,
            "project_revision": project.revision,
            "project_sha256": _project_hash(project),
            "fit_study_manifest_sha256": study_verification["manifest_sha256"],
            "fit_study_binding_sha256": study_verification["study_binding_sha256"],
            "fit_evidence_manifest_sha256": evidence_verification["manifest_sha256"],
            "fit_report_sha256": _sha256(report_bytes),
        },
        "evidence": {
            "disposition": report["disposition"],
            "observed_failure_edge_mm": report["observed_failure_edge_mm"],
            "observed_success_edge_mm": report["observed_success_edge_mm"],
            "recommended_tested_adjustment_mm": adjustment,
            "process_passport": report["passport"],
            "attachment_count": evidence_verification["evidence_file_count"],
            "evidence_authenticity_verified": False,
            "physical_fit_certified": False,
        },
        "revision": {
            "cutout_id": cutout_id,
            "cutout_kind": next(item.kind for item in project.spec.cutouts if item.id == cutout_id),
            "field": "cutouts",
            "nominal_before_mm": before,
            "nominal_after_mm": after,
            "compiled_aperture_before_mm": baseline_aperture,
            "compiled_aperture_after_mm": proposed_aperture,
            "project_revision_after": revised_project.revision,
        },
        "review": {
            "automatically_applied": False,
            "explicit_application_required": True,
            "held_out_confirmation_required": True,
            "limitations": list(LIMITATIONS),
        },
    }
    return plan


def verify_fit_revision_plan(
    project: EnclosureProject,
    study_bundle: Path,
    evidence_bundle: Path,
    plan_document: object,
) -> dict[str, Any]:
    """Recompute a plan from all bound inputs and require byte-semantic equality."""

    expected = create_fit_revision_plan(project, study_bundle, evidence_bundle)
    if plan_document != expected:
        raise ValueError("fit-revision plan does not recompute from the exact project and sealed evidence")
    return {
        "valid": True,
        "schema_version": FIT_REVISION_PLAN_VERSION,
        "plan_sha256": _sha256(_canonical_json(expected).encode("utf-8")),
        "project_sha256": expected["source"]["project_sha256"],
        "cutout_id": expected["revision"]["cutout_id"],
        "automatically_applied": False,
        "physical_fit_certified": False,
    }


def apply_fit_revision(
    project: EnclosureProject,
    study_bundle: Path,
    evidence_bundle: Path,
    plan_document: object,
) -> EnclosureProject:
    """Apply one reviewed plan as one auditable project revision."""

    verify_fit_revision_plan(project, study_bundle, evidence_bundle, plan_document)
    if not isinstance(plan_document, dict):
        raise TypeError("verified fit-revision plan must be an object")
    plan = plan_document
    revision = plan["revision"]
    if not isinstance(revision, dict):
        raise TypeError("verified fit-revision revision must be an object")
    evidence = plan["evidence"]
    source = plan["source"]
    if not isinstance(evidence, dict) or not isinstance(source, dict):
        raise TypeError("verified fit-revision source and evidence must be objects")
    adjustment = float(evidence["recommended_tested_adjustment_mm"])
    cutout_id = str(revision["cutout_id"])
    _, _, candidate = _proposed_dimensions(project, cutout_id, adjustment)
    audit_reason = (
        f"apply reviewed fit revision {source['fit_report_sha256']} "
        f"to cutout {cutout_id}"
    )
    return update_project(
        project,
        "cutouts",
        enclosure_spec_to_dict(candidate.spec)["cutouts"],
        reason=audit_reason,
    )


def verify_applied_fit_revision(
    source_project: EnclosureProject,
    revised_project: EnclosureProject,
    study_bundle: Path,
    evidence_bundle: Path,
    plan_document: object,
) -> dict[str, Any]:
    """Verify exact ancestry, one-field mutation, and compiled target geometry."""

    verify_fit_revision_plan(source_project, study_bundle, evidence_bundle, plan_document)
    if not isinstance(plan_document, dict):
        raise TypeError("verified fit-revision plan must be an object")
    plan = plan_document
    expected = apply_fit_revision(source_project, study_bundle, evidence_bundle, plan)
    if serialize_project(revised_project) != serialize_project(expected):
        raise ValueError("revised project is not the exact application of this fit-revision plan")
    differences = semantic_diff(source_project, revised_project)
    cutout_id = str(plan["revision"]["cutout_id"])
    allowed_prefix = "cutouts"
    if not differences or any(not item["field"].startswith(allowed_prefix) for item in differences):
        raise ValueError("fit revision changed fields outside the named cutout collection")
    sample = cutout_fit_sample(revised_project, cutout_id, aperture_adjustment_mm=0)
    aperture = [float(value) for value in sample.metadata["aperture_size_mm"]]
    if aperture != plan["revision"]["compiled_aperture_after_mm"]:
        raise ValueError("revised project does not compile to the planned aperture")
    return {
        "valid": True,
        "schema_version": FIT_REVISION_PLAN_VERSION,
        "source_project_sha256": _project_hash(source_project),
        "revised_project_sha256": _project_hash(revised_project),
        "source_revision": source_project.revision,
        "revised_revision": revised_project.revision,
        "cutout_id": cutout_id,
        "compiled_aperture_mm": aperture,
        "held_out_confirmation_required": True,
        "physical_fit_certified": False,
    }


def serialize_fit_revision_plan(plan: object) -> str:
    """Serialize a plan deterministically after basic closed-schema admission."""

    _exact_object(
        plan,
        {"schema_version", "source", "evidence", "revision", "review"},
        label="fit-revision plan",
    )
    if not isinstance(plan, dict) or plan["schema_version"] != FIT_REVISION_PLAN_VERSION:
        raise ValueError("unsupported fit-revision plan version")
    return _canonical_json(plan)


def parse_fit_revision_plan(text: str) -> dict[str, Any]:
    """Parse bounded strict JSON; full semantic verification needs bound inputs."""

    raw = text.encode("utf-8")
    if len(raw) > MAX_FIT_REVISION_JSON_BYTES:
        raise ValueError(f"fit-revision plan exceeds {MAX_FIT_REVISION_JSON_BYTES} bytes")
    try:
        document = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid fit-revision JSON at line {exc.lineno}, column {exc.colno}") from exc
    plan = _exact_object(
        document,
        {"schema_version", "source", "evidence", "revision", "review"},
        label="fit-revision plan",
    )
    if plan["schema_version"] != FIT_REVISION_PLAN_VERSION:
        raise ValueError("unsupported fit-revision plan version")
    return plan
