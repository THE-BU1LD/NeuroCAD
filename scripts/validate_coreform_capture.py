"""Validate a Coreform-style dirty-CAD capture manifest without running CAD software.

The validator is intentionally structural. It verifies provenance fields, path safety,
file sizes, hashes, baseline/repair separation, and stage consistency. It does not
interpret Cubit output or decide whether a scientific claim is correct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

MAX_EVIDENCE_BYTES = 256 * 1024 * 1024
STATUSES = {"NOT_RUN", "REPORTED_PASS", "REPORTED_FAIL", "INCONCLUSIVE"}
PURPOSES = {"DEVELOPMENT_CAPTURE", "SYNTHETIC_SOFTWARE_TEST"}
STAGE_NAMES = ("geometry_before", "geometry_after", "tet_meshing")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_file(root: Path, rel: str, expected_hash: str) -> Path:
    if not isinstance(rel, str) or not rel.strip():
        raise TypeError("file path must be a non-empty string")
    candidate = root / rel
    if candidate.is_symlink():
        raise ValueError(f"symlinks are not allowed: {rel}")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"missing evidence file: {rel}") from exc
    root_resolved = root.resolve(strict=True)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path escapes capture directory: {rel}") from exc
    if not resolved.is_file():
        raise ValueError(f"evidence path is not a regular file: {rel}")
    if resolved.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError(f"evidence file exceeds {MAX_EVIDENCE_BYTES} bytes: {rel}")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError(f"invalid sha256 for {rel}")
    observed = sha256(resolved)
    if observed != expected_hash.lower():
        raise ValueError(f"sha256 mismatch for {rel}: expected {expected_hash}, observed {observed}")
    return resolved


def require_file_record(root: Path, record: Any, *, label: str) -> dict[str, str]:
    if not isinstance(record, dict):
        raise TypeError(f"{label} must be an object")
    path = record.get("path")
    digest = record.get("sha256")
    safe_file(root, path, digest)
    return {"path": path, "sha256": digest.lower()}


def validate_stage(root: Path, name: str, stage: Any, *, repaired_present: bool) -> dict[str, Any]:
    if not isinstance(stage, dict):
        raise TypeError(f"stage {name} must be an object")
    status = stage.get("status")
    if status not in STATUSES:
        raise ValueError(f"stage {name} has invalid status {status!r}")
    command = stage.get("command")
    interpretation = stage.get("interpretation")
    evidence = stage.get("evidence")

    if status == "NOT_RUN":
        if evidence not in (None, {}):
            raise ValueError(f"stage {name}: NOT_RUN must not carry evidence")
        if command not in (None, "", []):
            raise ValueError(f"stage {name}: NOT_RUN must not claim a command")
        return {"status": status}

    if not isinstance(command, (str, list)) or command in ("", []):
        raise ValueError(f"stage {name}: non-NOT_RUN requires command/procedure")
    if not isinstance(interpretation, str) or not interpretation.strip():
        raise ValueError(f"stage {name}: non-NOT_RUN requires interpretation")
    evidence_record = require_file_record(root, evidence, label=f"stage {name}.evidence")

    if name == "geometry_after" and not repaired_present:
        raise ValueError("geometry_after cannot run without repaired_model")
    if name == "tet_meshing":
        basis = stage.get("model_basis")
        if basis not in {"as_imported_model", "repaired_model"}:
            raise ValueError("tet_meshing.model_basis must name as_imported_model or repaired_model")
        if basis == "repaired_model" and not repaired_present:
            raise ValueError("tet_meshing cannot use repaired_model when none is recorded")

    return {
        "status": status,
        "command": command,
        "interpretation": interpretation,
        "evidence": evidence_record,
        **({"model_basis": stage["model_basis"]} if name == "tet_meshing" else {}),
    }


def validate_capture(manifest_path: Path) -> dict[str, Any]:
    if manifest_path.is_symlink():
        raise ValueError("manifest must not be a symlink")
    manifest_path = manifest_path.resolve(strict=True)
    root = manifest_path.parent
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("capture manifest must be an object")

    required = {
        "schema_version", "case_id", "purpose", "cubit_version", "input_format", "units",
        "source_reference", "rights_status", "import_settings", "target_mesh_size",
        "interface_assumptions", "repair_description", "mesh_settings",
        "as_imported_model", "repaired_model", "stages",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    if data["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    if data["purpose"] not in PURPOSES:
        raise ValueError(f"purpose must be one of {sorted(PURPOSES)}")
    for key in ("case_id", "cubit_version", "input_format", "units", "source_reference",
                "rights_status", "interface_assumptions", "repair_description"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if not isinstance(data["import_settings"], dict):
        raise TypeError("import_settings must be an object")
    mesh_size = data["target_mesh_size"]
    if isinstance(mesh_size, bool) or not isinstance(mesh_size, (int, float)):
        raise TypeError("target_mesh_size must be numeric")
    if not math.isfinite(mesh_size) or mesh_size <= 0:
        raise ValueError("target_mesh_size must be finite and positive")
    if not isinstance(data["mesh_settings"], (dict, str)):
        raise TypeError("mesh_settings must be an object or explicit not-run string")

    baseline = require_file_record(root, data["as_imported_model"], label="as_imported_model")
    repaired_raw = data["repaired_model"]
    repaired = None
    if repaired_raw is not None:
        repaired = require_file_record(root, repaired_raw, label="repaired_model")
        if repaired["path"] == baseline["path"] or repaired["sha256"] == baseline["sha256"]:
            raise ValueError("repaired_model must be distinct from the as-imported baseline")

    stages = data["stages"]
    if not isinstance(stages, dict):
        raise TypeError("stages must be an object")
    if set(stages) != set(STAGE_NAMES):
        raise ValueError(f"stages must contain exactly {', '.join(STAGE_NAMES)}")
    validated_stages = {
        name: validate_stage(root, name, stages[name], repaired_present=repaired is not None)
        for name in STAGE_NAMES
    }

    return {
        "schema_version": 1,
        "case_id": data["case_id"],
        "purpose": data["purpose"],
        "baseline": baseline,
        "repaired": repaired,
        "stages": validated_stages,
        "integrity_passed": True,
        "claim_boundary": (
            "Manifest integrity only; this validator does not establish geometry validity, "
            "meshability, simulation suitability, manufacturability, or endorsement."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    result = validate_capture(args.manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
