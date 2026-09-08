"""External-application handoff manifests that never imply an import ran."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..artifacts import verify_stl
from ..enclosure import EnclosureSpec, build_enclosure
from ..enclosure_verification import verify_enclosure_mesh
from ..ir_export import program_to_scad
from ..ir_parser import parse_ir_json
from ..json_io import read_bounded_utf8, strict_json_loads
from ..project import MAX_PROJECT_BYTES, enclosure_spec_from_dict
from .common import sha256_file, write_json_atomic
from .exchange import EXCHANGE_VERSION, ExchangeBundle
from .model import CapabilityState
from .registry import AdapterRegistry, default_registry

HANDOFF_VERSION = "neurocad-application-handoff-v2"
VERIFICATION_VERSION = "neurocad-exchange-verification-v1"
MAX_MANIFEST_BYTES = 1_048_576
MAX_SOURCE_ARTIFACT_BYTES = 10 * 1_048_576


def _load_bundle_manifest(bundle: ExchangeBundle) -> dict[str, Any]:
    root = bundle.root.resolve()
    manifest_path = bundle.manifest_path.resolve()
    if manifest_path.parent != root or not manifest_path.is_file():
        raise ValueError("bundle manifest must be an existing direct child of the bundle root")
    size = manifest_path.stat().st_size
    if size <= 0 or size > MAX_MANIFEST_BYTES:
        raise ValueError("bundle manifest must be non-empty and no larger than 1 MiB")
    try:
        raw = strict_json_loads(read_bounded_utf8(manifest_path, max_bytes=MAX_MANIFEST_BYTES, label="bundle manifest"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"bundle manifest cannot be read safely: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != EXCHANGE_VERSION:
        raise ValueError("bundle manifest has an unsupported schema")
    return raw


def _verified_spec(manifest: dict[str, Any], root: Path) -> EnclosureSpec:
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise TypeError("bundle manifest source must be an object")
    filename = source.get("spec_filename")
    digest = source.get("spec_sha256")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ValueError("bundle specification filename is unsafe")
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file():
        raise ValueError("bundle specification is missing or escapes its root")
    with path.open("rb") as handle:
        raw = handle.read(MAX_PROJECT_BYTES + 1)
    if not raw or len(raw) > MAX_PROJECT_BYTES:
        raise ValueError("bundle specification must be non-empty and no larger than 1 MiB")
    if not isinstance(digest, str) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("bundle specification hash mismatch")
    try:
        decoded = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"bundle specification cannot be parsed safely: {exc}") from exc
    spec = enclosure_spec_from_dict(decoded)
    if source.get("spec_version") != spec.version or source.get("profile") != spec.profile:
        raise ValueError("bundle specification metadata does not match its parsed content")
    if manifest.get("title") != spec.title or manifest.get("units") != spec.units:
        raise ValueError("bundle title or units do not match the parsed specification")
    return spec


def _verified_artifacts(bundle: ExchangeBundle) -> tuple[dict[str, Any], list[dict[str, Any]], EnclosureSpec]:
    manifest = _load_bundle_manifest(bundle)
    root = bundle.root.resolve()
    spec = _verified_spec(manifest, root)
    generator = manifest.get("generator")
    if not isinstance(generator, dict) or set(generator) != {"fn"}:
        raise ValueError("bundle manifest must declare exactly one generator fn value")
    fn = generator["fn"]
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("bundle generator fn must be an integer between 3 and 1000")
    canonical_parts = build_enclosure(spec).parts
    files: list[dict[str, Any]] = []
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("bundle manifest contains no parts")
    part_ids = [part.get("id") for part in parts if isinstance(part, dict)]
    if len(part_ids) != len(parts) or any(not isinstance(part_id, str) for part_id in part_ids):
        raise TypeError("bundle part records must contain string ids")
    if len(set(part_ids)) != len(part_ids):
        raise ValueError("bundle manifest contains duplicate part ids")
    if set(part_ids) != set(canonical_parts):
        raise ValueError("bundle part inventory does not match the declared enclosure specification")
    seen_filenames: set[str] = set()
    mesh_presence: set[bool] = set()
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("id"), str):
            raise TypeError("bundle part record is malformed")
        artifacts = part.get("artifacts")
        if not isinstance(artifacts, list):
            raise TypeError(f"bundle part {part['id']!r} has no artifact list")
        formats = [artifact.get("format") for artifact in artifacts if isinstance(artifact, dict)]
        if len(formats) != len(artifacts) or any(not isinstance(value, str) for value in formats):
            raise TypeError(f"bundle part {part['id']!r} has malformed artifact formats")
        if len(set(formats)) != len(formats):
            raise ValueError(f"bundle part {part['id']!r} contains duplicate artifact formats")
        if set(formats) not in ({"ncad.json", "scad"}, {"ncad.json", "scad", "stl"}):
            raise ValueError(f"bundle part {part['id']!r} has an incomplete or unsupported artifact inventory")
        mesh_presence.add("stl" in formats)
        mesh_verification = part.get("mesh_verification")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise TypeError("bundle artifact record is malformed")
            filename = artifact.get("filename")
            digest = artifact.get("sha256")
            if not isinstance(filename, str) or Path(filename).name != filename:
                raise ValueError("bundle artifact filename is unsafe")
            path = (root / filename).resolve()
            if path.parent != root or not path.is_file():
                raise ValueError(f"bundle artifact is missing or escapes its root: {filename!r}")
            if not isinstance(digest, str) or sha256_file(path) != digest:
                raise ValueError(f"bundle artifact hash mismatch: {filename!r}")
            if filename in seen_filenames:
                raise ValueError(f"bundle artifact filename is duplicated: {filename!r}")
            seen_filenames.add(filename)
            if artifact.get("part") != part["id"] or artifact.get("bytes") != path.stat().st_size:
                raise ValueError(f"bundle artifact metadata mismatch: {filename!r}")
            state = artifact.get("state")
            artifact_format = artifact.get("format")
            expected_state = CapabilityState.VERIFIED.value if artifact_format == "stl" else CapabilityState.NATIVE.value
            if state != expected_state:
                raise ValueError(f"bundle artifact has invalid capability state: {filename!r}")
            if artifact_format == "stl" and (
                state != CapabilityState.VERIFIED.value
                or not isinstance(mesh_verification, dict)
                or mesh_verification.get("kernel_validity") is not True
            ):
                raise ValueError(f"STL artifact lacks kernel verification: {filename!r}")
            if artifact_format == "stl":
                try:
                    verify_stl(path)
                except (OSError, RuntimeError, ValueError) as exc:
                    raise ValueError(f"STL artifact fails current kernel verification: {filename!r}: {exc}") from exc
                try:
                    request_verification = verify_enclosure_mesh(path, spec, part=part["id"])
                except (OSError, RuntimeError, ValueError) as exc:
                    raise ValueError(
                        f"STL artifact fails current request-level verification: {filename!r}: {exc}"
                    ) from exc
                if not request_verification.valid:
                    raise ValueError(f"STL artifact fails current request-level verification: {filename!r}")
            elif artifact_format == "ncad.json":
                if path.stat().st_size > MAX_SOURCE_ARTIFACT_BYTES:
                    raise ValueError(f"canonical IR artifact is too large: {filename!r}")
                try:
                    recovered = parse_ir_json(read_bounded_utf8(path, max_bytes=MAX_SOURCE_ARTIFACT_BYTES, label="IR artifact"))
                except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
                    raise ValueError(f"canonical IR artifact cannot be parsed: {filename!r}: {exc}") from exc
                if recovered.to_dict() != canonical_parts[part["id"]].to_dict():
                    raise ValueError(f"canonical IR artifact does not match the declared specification: {filename!r}")
            elif artifact_format == "scad":
                if path.stat().st_size > MAX_SOURCE_ARTIFACT_BYTES:
                    raise ValueError(f"OpenSCAD artifact is too large: {filename!r}")
                try:
                    actual_scad = read_bounded_utf8(path, max_bytes=MAX_SOURCE_ARTIFACT_BYTES, label="OpenSCAD artifact")
                except (OSError, UnicodeError) as exc:
                    raise ValueError(f"OpenSCAD artifact cannot be read safely: {filename!r}: {exc}") from exc
                if actual_scad != program_to_scad(canonical_parts[part["id"]], fn=fn):
                    raise ValueError(f"OpenSCAD artifact does not match the declared specification: {filename!r}")
            files.append(
                {
                    "part": part["id"],
                    "filename": filename,
                    "format": artifact_format,
                    "sha256": digest,
                    "state": state,
                }
            )
    if len(mesh_presence) != 1:
        raise ValueError("bundle must include verified STL artifacts for every part or for no parts")
    return manifest, files, spec


def verify_exchange_bundle(bundle: ExchangeBundle) -> dict[str, Any]:
    """Rebuild and verify every source and artifact in an exchange bundle.

    A returned report is positive evidence for the checks named in the report.
    Invalid bundles raise instead of returning a partially successful result.
    """

    manifest, files, spec = _verified_artifacts(bundle)
    formats = sorted({str(item["format"]) for item in files})
    part_ids = sorted(str(part["id"]) for part in manifest["parts"])
    return {
        "schema_version": VERIFICATION_VERSION,
        "valid": True,
        "source": {
            "title": spec.title,
            "units": spec.units,
            "spec_version": spec.version,
            "spec_filename": manifest["source"]["spec_filename"],
            "spec_sha256": manifest["source"]["spec_sha256"],
        },
        "bundle": {
            "schema_version": manifest["schema_version"],
            "generator_fn": manifest["generator"]["fn"],
            "part_ids": part_ids,
            "part_count": len(part_ids),
            "artifact_count": len(files),
            "formats": formats,
            "compiled_meshes": "stl" in formats,
        },
        "checks": {
            "manifest_schema": True,
            "spec_hash_and_schema": True,
            "canonical_part_inventory": True,
            "artifact_hashes_and_metadata": True,
            "canonical_ir_matches_spec": True,
            "openscad_matches_spec": True,
            "kernel_and_request_mesh_verification": True if "stl" in formats else None,
        },
        "external_operation_executed": False,
    }


def _target_contract(application_id: str) -> dict[str, Any]:
    contracts: dict[str, dict[str, Any]] = {
        "openscad": {
            "accepted_formats": ("scad",),
            "required_state": CapabilityState.NATIVE,
            "mode": CapabilityState.NATIVE,
            "action": "Open each SCAD file in OpenSCAD and review the rendered geometry.",
            "native_editability": True,
        },
        "fusion": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each STL as a mesh body; no parametric Fusion feature tree is provided.",
            "native_editability": False,
        },
        "onshape": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Upload each STL for mesh translation; no Part Studio operation is performed.",
            "native_editability": False,
        },
        "freecad": {
            "accepted_formats": ("stl", "scad"),
            "required_state": None,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import verified STL meshes or open SCAD through a user-configured OpenSCAD workflow.",
            "native_editability": False,
        },
        "blender": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each STL for visualization; do not treat the Blender scene as authoritative CAD.",
            "native_editability": False,
        },
        "prusaslicer": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each verified STL, then select and review printer/material settings.",
            "native_editability": False,
        },
        "orcaslicer": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each verified STL, then select and review printer/material settings.",
            "native_editability": False,
        },
        "bambu_studio": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each verified STL, then select and review printer/material settings.",
            "native_editability": False,
        },
        "cura": {
            "accepted_formats": ("stl",),
            "required_state": CapabilityState.VERIFIED,
            "mode": CapabilityState.FILE_EXCHANGE,
            "action": "Import each verified STL, then select and review printer/material settings.",
            "native_editability": False,
        },
    }
    if application_id == "kicad":
        return {
            "accepted_formats": (),
            "required_state": None,
            "mode": CapabilityState.UNAVAILABLE,
            "action": "No enclosure push-back format is implemented for KiCad.",
            "native_editability": False,
        }
    return contracts[application_id]


def create_application_handoff(
    application_id: str,
    bundle: ExchangeBundle,
    *,
    registry: AdapterRegistry | None = None,
) -> dict[str, Any]:
    """Create a file handoff receipt; never launch or call the target app."""

    selected_registry = registry or default_registry()
    adapter = selected_registry.get(application_id)
    contract = _target_contract(adapter.id)
    bundle_manifest, files, spec = _verified_artifacts(bundle)
    accepted = set(contract["accepted_formats"])
    required_state = contract["required_state"]
    selected_files = [
        item
        for item in files
        if item["format"] in accepted and (required_state is None or item["state"] == required_state.value)
    ]
    part_ids = {str(part["id"]) for part in bundle_manifest["parts"]}
    selected_parts = {str(item["part"]) for item in selected_files}
    ready = bool(accepted) and selected_parts == part_ids
    mode = contract["mode"] if ready else CapabilityState.UNAVAILABLE
    prerequisites_available = all(item.available for item in adapter.prerequisites)
    return {
        "schema_version": HANDOFF_VERSION,
        "application": adapter.to_dict(),
        "source": {
            "title": spec.title,
            "units": spec.units,
            "spec_version": spec.version,
            "spec_filename": bundle_manifest["source"]["spec_filename"],
            "spec_sha256": bundle_manifest["source"]["spec_sha256"],
        },
        "handoff": {
            "state": mode.value,
            "ready": ready,
            "files": selected_files,
            "accepted_formats": sorted(accepted),
            "required_user_action": contract["action"],
            "application_prerequisites_available": prerequisites_available,
        },
        "external_operation_executed": False,
        "native_document_created": False,
        "native_editability": contract["native_editability"] if ready else False,
        "blocked_reason": None if ready else "the bundle lacks a supported artifact for every part",
        "limitations": list(adapter.limitations),
    }


def write_application_handoff(
    path: Path,
    application_id: str,
    bundle: ExchangeBundle,
    *,
    registry: AdapterRegistry | None = None,
) -> Path:
    payload = create_application_handoff(application_id, bundle, registry=registry)
    return write_json_atomic(Path(path), payload)
