"""Deterministic OpenSCAD bundles and neutral application exchange manifests."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..artifacts import compile_scad_verified, write_text_atomic
from ..enclosure import EnclosureBuild, build_enclosure, validate_enclosure_spec
from ..enclosure_verification import verify_enclosure_mesh
from ..ir import validate_program
from ..ir_export import program_to_scad
from ..ir_parser import serialize_ir_json
from ..project import enclosure_spec_to_dict
from .common import canonical_json, safe_filename_stem, sha256_bytes, sha256_file, write_json_atomic
from .model import CapabilityState, IntegrationUnavailableError
from .registry import AdapterRegistry, default_registry

EXCHANGE_VERSION = "neurocad-exchange-v2"


@dataclass(frozen=True)
class ExchangeBundle:
    root: Path
    manifest_path: Path
    manifest: dict[str, Any]

    @property
    def compiled_meshes(self) -> bool:
        return any(
            artifact.get("format") == "stl"
            for part in self.manifest.get("parts", [])
            for artifact in part.get("artifacts", [])
        )


def _validated_parts(build: EnclosureBuild) -> dict[str, Any]:
    if not isinstance(build, EnclosureBuild):
        raise TypeError("build must be an EnclosureBuild")
    fresh_spec_report = validate_enclosure_spec(build.spec)
    if not build.validation.valid or not fresh_spec_report.valid:
        raise ValueError("cannot exchange an invalid enclosure build")
    parts = build.parts
    if not parts or set(parts) - {"body", "lid"}:
        raise ValueError("enclosure build must contain only named body/lid parts")
    for name, program in parts.items():
        report = validate_program(program)
        if not report.valid:
            raise ValueError(
                f"cannot exchange invalid {name} IR: "
                + "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
            )
    canonical_parts = build_enclosure(build.spec).parts
    if set(parts) != set(canonical_parts) or any(
        serialize_ir_json(parts[name]) != serialize_ir_json(canonical_parts[name]) for name in canonical_parts
    ):
        raise ValueError("enclosure programs do not match a fresh deterministic build of the declared specification")
    return parts


def _artifact_record(path: Path, *, part: str, artifact_format: str, state: CapabilityState) -> dict[str, Any]:
    return {
        "part": part,
        "format": artifact_format,
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "state": state.value,
    }


def export_openscad_bundle(
    build: EnclosureBuild,
    destination: Path,
    *,
    fn: int = 96,
    compile_meshes: bool = False,
    timeout: int = 120,
) -> ExchangeBundle:
    """Create a new all-or-nothing bundle; never overwrite an existing path."""

    parts = _validated_parts(build)
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("fn must be an integer between 3 and 1000")
    if not isinstance(compile_meshes, bool):
        raise TypeError("compile_meshes must be a boolean")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("timeout must be a positive integer number of seconds")
    if compile_meshes:
        compile_capability = default_registry().get("openscad").capability("compile_verified_stl")
        if compile_capability.state is CapabilityState.UNAVAILABLE:
            raise IntegrationUnavailableError(compile_capability.detail)
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"exchange destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    bundle_stem = safe_filename_stem(build.spec.title)
    staging = Path(tempfile.mkdtemp(prefix=f".{bundle_stem}-bundle.", dir=destination.parent))
    try:
        spec_dict = enclosure_spec_to_dict(build.spec)
        spec_path = staging / f"{bundle_stem}.enclosure.json"
        write_json_atomic(spec_path, spec_dict)
        part_records: list[dict[str, Any]] = []
        for part_name in sorted(parts):
            program = parts[part_name]
            artifact_stem = f"{bundle_stem}-{part_name}"
            ir_path = staging / f"{artifact_stem}.ncad.json"
            scad_path = staging / f"{artifact_stem}.scad"
            write_text_atomic(ir_path, serialize_ir_json(program))
            write_text_atomic(scad_path, program_to_scad(program, fn=fn))
            artifacts = [
                _artifact_record(ir_path, part=part_name, artifact_format="ncad.json", state=CapabilityState.NATIVE),
                _artifact_record(scad_path, part=part_name, artifact_format="scad", state=CapabilityState.NATIVE),
            ]
            mesh_verification: dict[str, Any] | None = None
            if compile_meshes:
                stl_path = staging / f"{artifact_stem}.stl"
                _, kernel_verification = compile_scad_verified(scad_path, stl_path, timeout=timeout)
                request_verification = verify_enclosure_mesh(stl_path, build.spec, part=part_name)
                if not request_verification.valid:
                    raise RuntimeError(f"compiled {part_name} failed request-level enclosure verification")
                mesh_verification = {
                    **kernel_verification,
                    "request_verification": request_verification.to_dict(),
                }
                artifacts.append(
                    _artifact_record(stl_path, part=part_name, artifact_format="stl", state=CapabilityState.VERIFIED)
                )
            part_records.append(
                {
                    "id": part_name,
                    "program_title": program.title,
                    "artifacts": artifacts,
                    "mesh_verification": mesh_verification,
                }
            )

        spec_hash = sha256_bytes(canonical_json(spec_dict).encode("utf-8"))
        manifest: dict[str, Any] = {
            "schema_version": EXCHANGE_VERSION,
            "bundle_kind": "openscad_enclosure",
            "title": build.spec.title,
            "units": "mm",
            "source": {
                "spec_version": build.spec.version,
                "spec_sha256": spec_hash,
                "spec_filename": spec_path.name,
                "profile": build.spec.profile,
            },
            "generator": {"fn": fn},
            "capability": {
                "state": (CapabilityState.VERIFIED if compile_meshes else CapabilityState.NATIVE).value,
                "native_format": "scad",
                "mesh_kernel_verified": compile_meshes,
            },
            "external_operation": {
                "application": "OpenSCAD",
                "executed": compile_meshes,
                "native_document_opened": False,
            },
            "parts": part_records,
            "limitations": [
                "SCAD is parametric source but not a BREP feature tree",
                "STL artifacts are present only when compile_meshes was requested and kernel verification passed",
                "No slicer, CAD editor, or manufacturing operation was executed",
            ],
        }
        manifest_path = staging / "manifest.json"
        write_json_atomic(manifest_path, manifest)
        if destination.exists():
            raise FileExistsError(f"exchange destination appeared during export: {destination}")
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return ExchangeBundle(destination, destination / "manifest.json", manifest)


def create_neutral_manifest(
    build: EnclosureBuild,
    *,
    bundle: ExchangeBundle | None = None,
    targets: Iterable[str] | None = None,
    registry: AdapterRegistry | None = None,
) -> dict[str, Any]:
    """Describe interoperable artifacts without claiming an external import occurred."""

    parts = _validated_parts(build)
    selected_registry = registry or default_registry()
    adapters = selected_registry.describe(targets)
    artifact_parts = bundle.manifest.get("parts", []) if bundle is not None else []
    return {
        "schema_version": EXCHANGE_VERSION,
        "manifest_kind": "neutral_application_exchange",
        "title": build.spec.title,
        "units": "mm",
        "source": {
            "spec_version": build.spec.version,
            "part_ids": sorted(parts),
            "canonical_ir_available": True,
        },
        "bundle": {
            "available": bundle is not None,
            "mesh_artifacts_available": bool(bundle and bundle.compiled_meshes),
            "parts": artifact_parts,
        },
        "applications": [adapter.to_dict() for adapter in adapters],
        "external_operation_performed": False,
        "native_documents_created": [],
        "limitations": [
            "A ready handoff is not evidence that an application imported the files",
            "STL exchange loses editable parametric feature history",
            "STEP, BREP, 3MF, slicer projects, and native CAD documents are not produced",
        ],
    }


def write_neutral_manifest(
    path: Path,
    build: EnclosureBuild,
    *,
    bundle: ExchangeBundle | None = None,
    targets: Iterable[str] | None = None,
    registry: AdapterRegistry | None = None,
) -> Path:
    manifest = create_neutral_manifest(build, bundle=bundle, targets=targets, registry=registry)
    return write_json_atomic(Path(path), manifest)
