"""Transactional high-level enclosure project workflow."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import compile_scad_verified, verify_stl, write_text_atomic
from .enclosure import EnclosureBuild, build_enclosure
from .enclosure_verification import verify_enclosure_mesh
from .ir_export import program_to_scad
from .ir_parser import parse_ir_json, serialize_ir_json
from .json_io import strict_json_loads
from .manufacturing import fabrication_preflight
from .natural_language import IntentInterpretation, interpret_enclosure
from .project import MAX_PROJECT_BYTES, EnclosureProject, PhraseMapping, parse_project, serialize_project

BUNDLE_VERSION = "neurocad-bundle-v1"
BUNDLE_VERIFICATION_VERSION = "neurocad-bundle-verification-v1"
MAX_BUNDLE_MANIFEST_BYTES = 1_048_576
MAX_BUNDLE_ARTIFACT_BYTES = 64 * 1_048_576
MAX_BUNDLE_ARTIFACTS = 32


@dataclass(frozen=True)
class BundleArtifact:
    path: str
    media_type: str
    sha256: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "bytes": self.bytes,
        }


@dataclass(frozen=True)
class BuildBundle:
    directory: Path
    project: EnclosureProject
    build: EnclosureBuild
    artifacts: tuple[BundleArtifact, ...]
    manifest: dict[str, Any]


def _safe_project_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("project id must be non-empty")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    if not safe or len(safe) > 80:
        raise ValueError("project id must produce a safe name of at most 80 characters")
    return safe


def project_from_interpretation(project_id: str, interpretation: IntentInterpretation) -> EnclosureProject:
    spec = interpretation.require_spec()
    return EnclosureProject(
        project_id=_safe_project_id(project_id),
        spec=spec,
        source_text=interpretation.source,
        phrase_mappings=tuple(
            PhraseMapping(mapping.text, mapping.field, mapping.start, mapping.end) for mapping in interpretation.mappings
        ),
    )


def project_from_text(project_id: str, source: str) -> tuple[IntentInterpretation, EnclosureProject | None]:
    interpretation = interpret_enclosure(source)
    project = project_from_interpretation(project_id, interpretation) if interpretation.ready else None
    return interpretation, project


def _hash_file(path: Path, root: Path, media_type: str) -> BundleArtifact:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return BundleArtifact(path.relative_to(root).as_posix(), media_type, digest, path.stat().st_size)


def build_project_bundle(
    project: EnclosureProject,
    output_directory: Path,
    *,
    compile_stl: bool = False,
    fn: int = 64,
    timeout: int = 120,
) -> BuildBundle:
    """Create a collision-refusing project bundle and publish it atomically.

    Existing output directories are never replaced.  Callers must choose a new
    revision directory, which makes accidental destruction of evidence harder.
    The returned directory remains an ordinary writable filesystem directory;
    artifact hashes detect later changes but do not make it physically immutable.
    """

    output = output_directory.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"output bundle already exists: {output}")
    if not 3 <= fn <= 1000:
        raise ValueError("fn must be between 3 and 1000")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        build = build_enclosure(project.spec)
        preflight = fabrication_preflight(project.spec)
        write_text_atomic(staging / "project.ncad.json", serialize_project(project))
        write_text_atomic(staging / "preflight.json", json.dumps(preflight.to_dict(), indent=2, sort_keys=True) + "\n")
        verification_by_part: dict[str, Any] = {}
        for part, program in build.parts.items():
            write_text_atomic(staging / f"{part}.ncad.json", serialize_ir_json(program))
            scad_path = staging / f"{part}.scad"
            write_text_atomic(scad_path, program_to_scad(program, fn=fn))
            if compile_stl:
                stl_path = staging / f"{part}.stl"
                compile_scad_verified(scad_path, stl_path, timeout=timeout)
                feature_verification = verify_enclosure_mesh(stl_path, project.spec, part=part)
                if not feature_verification.valid:
                    raise RuntimeError(f"compiled {part} failed request-level feature verification")
                verification_by_part[part] = feature_verification.to_dict()
        if compile_stl:
            write_text_atomic(
                staging / "mesh-verification.json",
                json.dumps(verification_by_part, indent=2, sort_keys=True) + "\n",
            )

        media_types = {
            ".scad": "application/x-openscad",
            ".stl": "model/stl",
            ".json": "application/json",
        }
        artifacts = tuple(
            _hash_file(path, staging, media_types.get(path.suffix, "application/octet-stream"))
            for path in sorted(staging.iterdir())
            if path.is_file() and path.name != "manifest.json"
        )
        manifest = {
            "schema_version": BUNDLE_VERSION,
            "project_id": project.project_id,
            "revision": project.revision,
            "spec_version": project.spec.version,
            "compiled_stl": compile_stl,
            "generator": {"fn": fn},
            "parts": sorted(build.parts),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
            "verification": verification_by_part,
        }
        write_text_atomic(staging / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    final_artifacts = tuple(BundleArtifact(artifact.path, artifact.media_type, artifact.sha256, artifact.bytes) for artifact in artifacts)
    return BuildBundle(output, project, build, final_artifacts, manifest)


def _read_direct_bundle_file(root: Path, filename: str, *, maximum_bytes: int) -> tuple[Path, bytes]:
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        raise ValueError(f"unsafe bundle filename: {filename!r}")
    candidate = root / filename
    if candidate.is_symlink():
        raise ValueError(f"bundle files must not be symbolic links: {filename!r}")
    path = candidate.resolve()
    if path.parent != root or not path.is_file():
        raise ValueError(f"bundle file is missing or escapes its root: {filename!r}")
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ValueError(f"bundle file has an invalid size: {filename!r}")
    return path, path.read_bytes()


def _strict_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        decoded = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not strict JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise TypeError(f"{label} must be a JSON object")
    return decoded


def verify_project_bundle(directory: Path) -> dict[str, Any]:
    """Rebuild and verify every source and artifact in an enclosure bundle."""

    root = directory.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"bundle directory does not exist: {root}")
    _, manifest_raw = _read_direct_bundle_file(
        root, "manifest.json", maximum_bytes=MAX_BUNDLE_MANIFEST_BYTES
    )
    manifest = _strict_object(manifest_raw, label="bundle manifest")
    expected_manifest_keys = {
        "schema_version",
        "project_id",
        "revision",
        "spec_version",
        "compiled_stl",
        "generator",
        "parts",
        "artifacts",
        "verification",
    }
    if set(manifest) != expected_manifest_keys or manifest.get("schema_version") != BUNDLE_VERSION:
        raise ValueError("bundle manifest has an unsupported schema")

    generator = manifest.get("generator")
    if not isinstance(generator, dict) or set(generator) != {"fn"}:
        raise ValueError("bundle manifest must declare exactly one generator fn value")
    fn = generator["fn"]
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("bundle generator fn must be an integer between 3 and 1000")
    compiled_stl = manifest.get("compiled_stl")
    if not isinstance(compiled_stl, bool):
        raise TypeError("bundle compiled_stl flag must be boolean")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_BUNDLE_ARTIFACTS:
        raise ValueError(f"bundle must contain between 1 and {MAX_BUNDLE_ARTIFACTS} artifacts")
    records: dict[str, dict[str, Any]] = {}
    files: dict[str, Path] = {}
    expected_media_types = {
        ".json": "application/json",
        ".scad": "application/x-openscad",
        ".stl": "model/stl",
    }
    for record in artifacts:
        if not isinstance(record, dict) or set(record) != {"path", "media_type", "sha256", "bytes"}:
            raise ValueError("bundle artifact record has an unsupported schema")
        filename = record.get("path")
        if not isinstance(filename, str) or filename in records:
            raise ValueError("bundle artifact paths must be unique strings")
        path, raw = _read_direct_bundle_file(root, filename, maximum_bytes=MAX_BUNDLE_ARTIFACT_BYTES)
        digest = hashlib.sha256(raw).hexdigest()
        if record.get("sha256") != digest or record.get("bytes") != len(raw):
            raise ValueError(f"bundle artifact hash or size mismatch: {filename!r}")
        if record.get("media_type") != expected_media_types.get(path.suffix):
            raise ValueError(f"bundle artifact media type mismatch: {filename!r}")
        records[filename] = record
        files[filename] = path

    expected_core = {"project.ncad.json", "preflight.json"}
    project_path = files.get("project.ncad.json")
    if project_path is None:
        raise ValueError("bundle is missing project.ncad.json")
    if project_path.stat().st_size > MAX_PROJECT_BYTES:
        raise ValueError("bundled project exceeds the project input limit")
    try:
        project = parse_project(project_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"bundled project is invalid: {exc}") from exc
    build = build_enclosure(project.spec)
    part_ids = sorted(build.parts)
    if (
        manifest.get("project_id") != project.project_id
        or manifest.get("revision") != project.revision
        or manifest.get("spec_version") != project.spec.version
        or manifest.get("parts") != part_ids
    ):
        raise ValueError("bundle metadata does not match its project source")

    expected_names = set(expected_core)
    for part, program in build.parts.items():
        ir_name = f"{part}.ncad.json"
        scad_name = f"{part}.scad"
        expected_names.update({ir_name, scad_name})
        if ir_name not in files or scad_name not in files:
            raise ValueError(f"bundle is missing canonical artifacts for part {part!r}")
        try:
            recovered = parse_ir_json(files[ir_name].read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f"bundled IR is invalid for part {part!r}: {exc}") from exc
        if recovered.to_dict() != program.to_dict():
            raise ValueError(f"bundled IR does not match project source for part {part!r}")
        try:
            actual_scad = files[scad_name].read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"bundled OpenSCAD cannot be read for part {part!r}: {exc}") from exc
        if actual_scad != program_to_scad(program, fn=fn):
            raise ValueError(f"bundled OpenSCAD does not match project source for part {part!r}")
        if compiled_stl:
            expected_names.add(f"{part}.stl")

    preflight_path = files.get("preflight.json")
    if preflight_path is None:
        raise ValueError("bundle is missing preflight.json")
    preflight = _strict_object(preflight_path.read_bytes(), label="bundled preflight")
    if preflight != fabrication_preflight(project.spec).to_dict():
        raise ValueError("bundled preflight does not match project source")

    current_mesh_verification: dict[str, Any] = {}
    stored_verification = manifest.get("verification")
    if not isinstance(stored_verification, dict):
        raise TypeError("bundle verification field must be an object")
    if compiled_stl:
        expected_names.add("mesh-verification.json")
        mesh_path = files.get("mesh-verification.json")
        if mesh_path is None:
            raise ValueError("compiled bundle is missing mesh-verification.json")
        stored_mesh = _strict_object(mesh_path.read_bytes(), label="mesh verification")
        if stored_mesh != stored_verification or set(stored_mesh) != set(part_ids):
            raise ValueError("stored mesh verification does not match the bundle manifest")
        for part in part_ids:
            stl_path = files.get(f"{part}.stl")
            if stl_path is None:
                raise ValueError(f"compiled bundle is missing STL for part {part!r}")
            verify_stl(stl_path)
            report = verify_enclosure_mesh(stl_path, project.spec, part=part)
            if not report.valid:
                raise ValueError(f"STL fails request-level verification for part {part!r}")
            if report.to_dict() != stored_mesh[part]:
                raise ValueError(f"stored mesh verification is stale for part {part!r}")
            current_mesh_verification[part] = report.to_dict()
    elif stored_verification:
        raise ValueError("source-only bundle cannot claim mesh verification")

    if set(records) != expected_names:
        unexpected = sorted(set(records) - expected_names)
        missing = sorted(expected_names - set(records))
        raise ValueError(f"bundle artifact inventory mismatch; missing={missing}, unexpected={unexpected}")
    actual_entries = {path.name for path in root.iterdir()}
    expected_entries = expected_names | {"manifest.json"}
    if actual_entries != expected_entries:
        unexpected = sorted(actual_entries - expected_entries)
        missing = sorted(expected_entries - actual_entries)
        raise ValueError(f"bundle directory inventory mismatch; missing={missing}, unexpected={unexpected}")

    return {
        "schema_version": BUNDLE_VERIFICATION_VERSION,
        "valid": True,
        "project_id": project.project_id,
        "revision": project.revision,
        "parts": part_ids,
        "compiled_stl": compiled_stl,
        "artifact_count": len(records),
        "checks": {
            "manifest_schema": True,
            "source_hashes_and_sizes": True,
            "project_schema_and_metadata": True,
            "preflight_matches_source": True,
            "canonical_ir_matches_source": True,
            "openscad_matches_source": True,
            "mesh_verification": True if compiled_stl else None,
        },
        "current_mesh_verification": current_mesh_verification,
    }
