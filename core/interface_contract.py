"""Source-bound interface locks and deterministic project change-impact reports.

Interface contracts are deliberately external to the project format.  They can
therefore protect an accepted project without changing it, and every check can
be recomputed from the exact source and candidate projects.  Numeric tolerance
is an engineering comparison threshold, not a manufacturing or fit claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .json_io import strict_json_loads
from .project import EnclosureProject, enclosure_spec_to_dict, parse_project, serialize_project

INTERFACE_CONTRACT_VERSION = "neurocad-interface-contract-v1"
CHANGE_IMPACT_VERSION = "neurocad-change-impact-v1"
MAX_INTERFACE_DOCUMENT_BYTES = 1_048_576
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
_LIMITATIONS = (
    "A passing lock check establishes equality of selected project fields within the declared numeric tolerance only.",
    "It does not establish physical fit, manufacturing accuracy, material stability, or compatibility with an unmodeled part.",
    "Any changed geometry still requires regenerated artifacts and rerun verification; affected empirical evidence is reported as invalidated.",
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_hash(project: EnclosureProject) -> str:
    canonical = parse_project(serialize_project(project))
    return _sha256(serialize_project(canonical).encode("utf-8"))


def _finite_tolerance(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("interface tolerance must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 5:
        raise ValueError("interface tolerance must be between 0 and 5 mm")
    return result


def _unique_ids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    if any(not isinstance(value, str) or _ID.fullmatch(value) is None for value in values):
        raise ValueError(f"{label} IDs must contain only letters, digits, underscores, and hyphens")
    if len(set(values)) != len(values):
        raise ValueError(f"{label} IDs must be unique")
    return tuple(sorted(values))


def _find_feature(items: list[dict[str, Any]], identifier: str, *, kind: str) -> dict[str, Any]:
    matches = [item for item in items if item.get("id") == identifier]
    if len(matches) != 1:
        raise ValueError(f"{kind} {identifier!r} does not resolve uniquely in the source project")
    return matches[0]


def _lock_snapshot(
    project: EnclosureProject,
    *,
    cutout_ids: tuple[str, ...],
    standoff_ids: tuple[str, ...],
    lock_pcb_mounting: bool,
    lock_lid_interface: bool,
) -> list[dict[str, Any]]:
    spec = enclosure_spec_to_dict(project.spec)
    locks: list[dict[str, Any]] = []
    for identifier in cutout_ids:
        item = _find_feature(spec["cutouts"], identifier, kind="cutout")
        locks.append(
            {
                "selector": {"kind": "cutout", "id": identifier},
                "snapshot": {
                    key: item[key]
                    for key in (
                        "kind",
                        "face",
                        "center_uv_mm",
                        "size_mm",
                        "diameter_mm",
                        "corner_radius_mm",
                        "purpose",
                    )
                },
            }
        )
    for identifier in standoff_ids:
        item = _find_feature(spec["standoffs"], identifier, kind="standoff")
        locks.append(
            {
                "selector": {"kind": "standoff", "id": identifier},
                "snapshot": {
                    key: item[key]
                    for key in (
                        "center_xy_mm",
                        "height_mm",
                        "outer_diameter_mm",
                        "hole_diameter_mm",
                        "hardware",
                    )
                },
            }
        )
    if lock_pcb_mounting:
        if spec["pcb"] is None:
            raise ValueError("cannot lock PCB mounting because the source project has no PCB")
        locks.append(
            {
                "selector": {"kind": "pcb_mounting", "id": "pcb"},
                "snapshot": {
                    "origin_xy_mm": spec["pcb"]["origin_xy_mm"],
                    "mounting_holes_xy_mm": spec["pcb"]["mounting_holes_xy_mm"],
                },
            }
        )
    if lock_lid_interface:
        if spec["lid"]["kind"] == "none":
            raise ValueError("cannot lock a lid interface when the source project has no lid")
        locks.append(
            {
                "selector": {"kind": "lid_interface", "id": "lid"},
                "snapshot": {
                    "outer_size_xy_mm": spec["outer_size_mm"][:2],
                    "wall_mm": spec["wall_mm"],
                    "corner_radius_mm": spec["corner_radius_mm"],
                    "profile": spec["profile"],
                    "lid": spec["lid"],
                },
            }
        )
    return locks


def create_interface_contract(
    project: EnclosureProject,
    *,
    contract_id: str,
    cutout_ids: tuple[str, ...] = (),
    standoff_ids: tuple[str, ...] = (),
    lock_pcb_mounting: bool = False,
    lock_lid_interface: bool = False,
    tolerance_mm: float = 0.0,
) -> dict[str, Any]:
    """Capture selected source interfaces in a deterministic external contract."""

    if not isinstance(project, EnclosureProject):
        raise TypeError("project must be an EnclosureProject")
    if not isinstance(contract_id, str) or _ID.fullmatch(contract_id) is None:
        raise ValueError("contract ID must contain 1 to 128 letters, digits, underscores, or hyphens")
    cutouts = _unique_ids(cutout_ids, label="cutout")
    standoffs = _unique_ids(standoff_ids, label="standoff")
    tolerance = _finite_tolerance(tolerance_mm)
    locks = _lock_snapshot(
        project,
        cutout_ids=cutouts,
        standoff_ids=standoffs,
        lock_pcb_mounting=lock_pcb_mounting,
        lock_lid_interface=lock_lid_interface,
    )
    if not locks:
        raise ValueError("an interface contract requires at least one selected interface")
    return {
        "schema_version": INTERFACE_CONTRACT_VERSION,
        "contract_id": contract_id,
        "source": {
            "project_id": project.project_id,
            "project_revision": project.revision,
            "project_sha256": _project_hash(project),
        },
        "tolerance_mm": tolerance,
        "locks": locks,
        "limitations": list(_LIMITATIONS),
        "physical_compatibility_certified": False,
    }


def _contract_selection(contract: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], bool, bool]:
    locks = contract.get("locks")
    if not isinstance(locks, list) or not locks:
        raise ValueError("interface contract locks must be a non-empty array")
    cutouts: list[str] = []
    standoffs: list[str] = []
    pcb = False
    lid = False
    for index, lock in enumerate(locks):
        if not isinstance(lock, dict) or set(lock) != {"selector", "snapshot"}:
            raise ValueError(f"interface contract lock {index} has an invalid schema")
        selector = lock["selector"]
        if not isinstance(selector, dict) or set(selector) != {"kind", "id"}:
            raise ValueError(f"interface contract lock {index} selector has an invalid schema")
        kind, identifier = selector["kind"], selector["id"]
        if kind == "cutout" and isinstance(identifier, str):
            cutouts.append(identifier)
        elif kind == "standoff" and isinstance(identifier, str):
            standoffs.append(identifier)
        elif kind == "pcb_mounting" and identifier == "pcb" and not pcb:
            pcb = True
        elif kind == "lid_interface" and identifier == "lid" and not lid:
            lid = True
        else:
            raise ValueError(f"interface contract lock {index} has an unsupported or duplicate selector")
    return tuple(cutouts), tuple(standoffs), pcb, lid


def verify_interface_contract(project: EnclosureProject, contract: object) -> dict[str, Any]:
    """Recompute a contract from its exact source project and selection."""

    if not isinstance(contract, dict):
        raise TypeError("interface contract must be an object")
    required = {
        "schema_version",
        "contract_id",
        "source",
        "tolerance_mm",
        "locks",
        "limitations",
        "physical_compatibility_certified",
    }
    if set(contract) != required or contract.get("schema_version") != INTERFACE_CONTRACT_VERSION:
        raise ValueError("interface contract has an unsupported schema")
    if contract.get("physical_compatibility_certified") is not False:
        raise ValueError("interface contract contains an unsupported physical compatibility claim")
    cutouts, standoffs, pcb, lid = _contract_selection(contract)
    expected = create_interface_contract(
        project,
        contract_id=contract["contract_id"],
        cutout_ids=cutouts,
        standoff_ids=standoffs,
        lock_pcb_mounting=pcb,
        lock_lid_interface=lid,
        tolerance_mm=contract["tolerance_mm"],
    )
    if contract != expected:
        raise ValueError("interface contract does not recompute from the exact source project")
    return {
        "valid": True,
        "schema_version": INTERFACE_CONTRACT_VERSION,
        "contract_id": expected["contract_id"],
        "contract_sha256": _sha256(_canonical_json(expected).encode("utf-8")),
        "source_project_sha256": expected["source"]["project_sha256"],
        "lock_count": len(expected["locks"]),
        "physical_compatibility_certified": False,
    }


def _candidate_snapshot(project: EnclosureProject, selector: dict[str, str]) -> object:
    kind, identifier = selector["kind"], selector["id"]
    try:
        locks = _lock_snapshot(
            project,
            cutout_ids=(identifier,) if kind == "cutout" else (),
            standoff_ids=(identifier,) if kind == "standoff" else (),
            lock_pcb_mounting=kind == "pcb_mounting",
            lock_lid_interface=kind == "lid_interface",
        )
    except ValueError:
        return None
    return locks[0]["snapshot"]


def _compare_values(
    before: object,
    after: object,
    *,
    path: str,
    selector: dict[str, str],
    tolerance: float,
    violations: list[dict[str, Any]],
) -> None:
    if isinstance(before, dict) and isinstance(after, dict) and set(before) == set(after):
        for key in sorted(before):
            _compare_values(
                before[key], after[key], path=f"{path}.{key}", selector=selector,
                tolerance=tolerance, violations=violations,
            )
        return
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for index, (old, new) in enumerate(zip(before, after, strict=True)):
            _compare_values(
                old, new, path=f"{path}[{index}]", selector=selector,
                tolerance=tolerance, violations=violations,
            )
        return
    if (
        isinstance(before, (int, float))
        and not isinstance(before, bool)
        and isinstance(after, (int, float))
        and not isinstance(after, bool)
    ):
        delta = abs(float(after) - float(before))
        if delta <= tolerance:
            return
        code = "numeric_tolerance_exceeded"
    elif before == after:
        return
    else:
        delta = None
        code = "interface_value_changed"
    violations.append(
        {
            "selector": selector,
            "path": path,
            "code": code,
            "before": before,
            "after": after,
            "absolute_delta_mm": delta,
            "tolerance_mm": tolerance,
        }
    )


def _lineage(source: EnclosureProject, candidate: EnclosureProject) -> tuple[bool, str]:
    if source.project_id != candidate.project_id:
        return False, "candidate project_id differs from the source project"
    if candidate.revision < source.revision:
        return False, "candidate revision predates the source revision"
    if candidate.changes[: len(source.changes)] != source.changes:
        return False, "candidate revision history does not preserve the source ancestry"
    if candidate.revision == source.revision and serialize_project(candidate) != serialize_project(source):
        return False, "candidate reuses the source revision number with different content"
    return True, "candidate preserves the exact source project ancestry"


def _detailed_changes(source: EnclosureProject, candidate: EnclosureProject) -> list[dict[str, Any]]:
    """Diff specifications with stable feature IDs and coordinate-level paths."""

    before = enclosure_spec_to_dict(source.spec)
    after = enclosure_spec_to_dict(candidate.spec)
    changes: list[dict[str, Any]] = []

    def walk(path: str, old: object, new: object) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new)):
                child = f"{path}.{key}" if path else key
                walk(child, old.get(key), new.get(key))
            return
        if isinstance(old, list) and isinstance(new, list):
            if path in {"cutouts", "standoffs", "vents"} and all(
                isinstance(item, dict) and isinstance(item.get("id"), str) for item in [*old, *new]
            ):
                old_by_id = {str(item["id"]): item for item in old}
                new_by_id = {str(item["id"]): item for item in new}
                for identifier in sorted(set(old_by_id) | set(new_by_id)):
                    walk(f"{path}.{identifier}", old_by_id.get(identifier), new_by_id.get(identifier))
                return
            if len(old) == len(new):
                for index, (old_item, new_item) in enumerate(zip(old, new, strict=True)):
                    walk(f"{path}[{index}]", old_item, new_item)
                return
        if old != new:
            changes.append({"field": path, "before": old, "after": new})

    walk("", before, after)
    return changes


def _impact_for_field(field: str) -> dict[str, Any]:
    root = field.split(".", 1)[0].split("[", 1)[0]
    invalidated = ["artifact_bundle", "exact_geometry_verification", "manufacturing_preflight"]
    affected = ["body_geometry", "lid_geometry"]
    reason = "project geometry changed"
    if root == "title":
        invalidated, affected, reason = [], ["project_metadata"], "project title changed without geometry"
    elif root == "cutouts":
        invalidated += ["cutout_fit_samples", "cutout_fit_studies", "cutout_fit_evidence"]
        affected, reason = ["body_or_lid_openings"], "cutout geometry or identity changed"
    elif root in {"standoffs", "pcb"}:
        invalidated += ["mounting_compatibility_evidence", "assembly_clearance_checks"]
        affected, reason = ["mounting_pattern", "board_placement"], "mounting interface changed"
    elif root == "lid":
        invalidated += ["lid_body_compatibility_evidence", "lid_fit_evidence"]
        affected, reason = ["lid_interface", "lid_geometry"], "lid interface changed"
    elif root in {"outer_size_mm", "wall_mm", "corner_radius_mm"}:
        invalidated += ["lid_body_compatibility_evidence", "external_envelope_checks"]
        affected, reason = ["body_envelope", "lid_interface", "feature_clearances"], "enclosure envelope changed"
    elif root == "profile":
        invalidated += ["compiled_aperture_evidence", "process_profile_evidence", "fit_evidence"]
        affected, reason = ["manufacturing_compensation", "minimum_feature_rules"], "manufacturing profile changed"
    elif root == "vents":
        invalidated += ["airflow_assumptions"]
        affected, reason = ["vent_geometry"], "vent pattern changed"
    elif root == "floor_mm":
        invalidated += ["internal_height_checks", "mounting_height_checks"]
        affected, reason = ["body_floor", "internal_vertical_clearance"], "floor thickness changed"
    return {
        "field": field,
        "affected_scopes": affected,
        "invalidated_evidence": sorted(set(invalidated)),
        "reason": reason,
    }


def evaluate_project_change(
    source: EnclosureProject,
    candidate: EnclosureProject,
    *,
    contract: object | None = None,
) -> dict[str, Any]:
    """Report ancestry, semantic impact, invalidated evidence, and lock status."""

    if not isinstance(source, EnclosureProject) or not isinstance(candidate, EnclosureProject):
        raise TypeError("source and candidate must be EnclosureProject values")
    lineage_valid, lineage_reason = _lineage(source, candidate)
    differences = _detailed_changes(source, candidate)
    contract_result: dict[str, Any] | None = None
    violations: list[dict[str, Any]] = []
    if contract is not None:
        verified = verify_interface_contract(source, contract)
        if not isinstance(contract, dict):
            raise TypeError("verified interface contract must be an object")
        tolerance = float(contract["tolerance_mm"])
        for lock in contract["locks"]:
            selector = lock["selector"]
            current = _candidate_snapshot(candidate, selector)
            if current is None:
                violations.append(
                    {
                        "selector": selector,
                        "path": "snapshot",
                        "code": "locked_interface_missing",
                        "before": lock["snapshot"],
                        "after": None,
                        "absolute_delta_mm": None,
                        "tolerance_mm": tolerance,
                    }
                )
                continue
            _compare_values(
                lock["snapshot"], current, path="snapshot", selector=selector,
                tolerance=tolerance, violations=violations,
            )
        contract_result = {
            "contract_id": verified["contract_id"],
            "contract_sha256": verified["contract_sha256"],
            "lock_count": verified["lock_count"],
            "valid": not violations,
            "violations": violations,
        }
    accepted = lineage_valid and not violations
    return {
        "schema_version": CHANGE_IMPACT_VERSION,
        "source": {
            "project_id": source.project_id,
            "revision": source.revision,
            "sha256": _project_hash(source),
        },
        "candidate": {
            "project_id": candidate.project_id,
            "revision": candidate.revision,
            "sha256": _project_hash(candidate),
        },
        "lineage": {"valid": lineage_valid, "reason": lineage_reason},
        "changes": differences,
        "impacts": [_impact_for_field(item["field"]) for item in differences],
        "interface_contract": contract_result,
        "decision": "ACCEPTED" if accepted else "REJECTED",
        "regeneration_required": any(item["field"] != "title" for item in differences),
        "physical_compatibility_certified": False,
        "limitations": list(_LIMITATIONS),
    }


def require_protected_interfaces(
    source: EnclosureProject,
    candidate: EnclosureProject,
    contract: object,
) -> dict[str, Any]:
    """Return the impact report or reject a stale lineage or lock violation."""

    report = evaluate_project_change(source, candidate, contract=contract)
    if report["decision"] != "ACCEPTED":
        lock_result = report["interface_contract"]
        count = len(lock_result["violations"]) if isinstance(lock_result, dict) else 0
        raise ValueError(
            f"candidate violates the protected interface contract or source ancestry ({count} lock violation(s))"
        )
    return report


def verify_change_impact_report(
    source: EnclosureProject,
    candidate: EnclosureProject,
    report: object,
    *,
    contract: object | None = None,
) -> dict[str, Any]:
    """Independently recompute a saved change-impact report."""

    expected = evaluate_project_change(source, candidate, contract=contract)
    if report != expected:
        raise ValueError("change-impact report does not recompute from the exact projects and contract")
    return {
        "valid": True,
        "schema_version": CHANGE_IMPACT_VERSION,
        "report_sha256": _sha256(_canonical_json(expected).encode("utf-8")),
        "decision": expected["decision"],
        "change_count": len(expected["changes"]),
        "physical_compatibility_certified": False,
    }


def serialize_interface_document(document: object) -> str:
    if not isinstance(document, dict):
        raise TypeError("interface document must be an object")
    if document.get("schema_version") not in {INTERFACE_CONTRACT_VERSION, CHANGE_IMPACT_VERSION}:
        raise ValueError("unsupported interface document version")
    return _canonical_json(document)


def parse_interface_document(text: str, *, expected_version: str) -> dict[str, Any]:
    raw = text.encode("utf-8")
    if len(raw) > MAX_INTERFACE_DOCUMENT_BYTES:
        raise ValueError(f"interface document exceeds {MAX_INTERFACE_DOCUMENT_BYTES} bytes")
    try:
        document = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid interface JSON at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != expected_version:
        raise ValueError(f"interface document must use {expected_version}")
    return document
