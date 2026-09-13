"""One atomic prompt-to-artifact implementation shared by CLI and daemon."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from text_to_cad import TextToCAD

from .artifacts import compile_scad_verified, preview_renderer_backend, render_scad_png, write_text_atomic
from .ir import program_bounds, program_bounds_are_exact
from .ir_export import program_to_scad
from .ir_parser import serialize_ir_json
from .program_evaluation import evaluate_program

GENERATION_VERSION = "neurocad-generation-v1"
ALLOWED_FORMATS = frozenset({"ir", "scad", "stl", "preview"})
MAX_MANIFEST_BYTES = 1_048_576
MAX_BUNDLE_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    output_dir: str
    formats: tuple[str, ...] = ("ir", "scad", "stl", "preview")
    fn: int = 64
    timeout_seconds: int = 120

    def validate(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be non-empty")
        if len(self.prompt) > 4096:
            raise ValueError("prompt is limited to 4096 characters")
        output = Path(self.output_dir).expanduser()
        if not output.is_absolute():
            raise ValueError("output_dir must be absolute")
        if not self.formats or len(self.formats) != len(set(self.formats)):
            raise ValueError("formats must be non-empty and unique")
        unknown = set(self.formats) - ALLOWED_FORMATS
        if unknown:
            raise ValueError(f"unsupported formats: {sorted(unknown)}")
        if isinstance(self.fn, bool) or not isinstance(self.fn, int) or not 3 <= self.fn <= 1000:
            raise ValueError("fn must be an integer from 3 through 1000")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or not 1 <= self.timeout_seconds <= 3600
        ):
            raise ValueError("timeout_seconds must be an integer from 1 through 3600")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact_bundle(directory: Path) -> dict[str, Any]:
    """Verify a generation bundle is complete, bounded, and byte-identical to its manifest."""

    from .json_io import read_bounded_utf8, strict_json_loads

    root = directory.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"artifact bundle does not exist: {root}")
    manifest_path = root / "manifest.json"
    manifest = strict_json_loads(
        read_bounded_utf8(manifest_path, max_bytes=MAX_MANIFEST_BYTES, label="generation manifest")
    )
    if not isinstance(manifest, dict) or manifest.get("generation_version") != GENERATION_VERSION:
        raise ValueError("artifact bundle has an unsupported generation manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("generation manifest has no artifact map")
    verified: dict[str, dict[str, Any]] = {}
    declared_paths: set[str] = set()
    for name, entry in artifacts.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise TypeError("generation artifact entries must be named objects")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        if not isinstance(relative, str) or Path(relative).is_absolute() or Path(relative).name != relative:
            raise ValueError(f"artifact {name!r} has an unsafe path")
        if relative in declared_paths:
            raise ValueError(f"artifact path is declared more than once: {relative}")
        declared_paths.add(relative)
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"artifact {name!r} is missing or not a regular file: {path}")
        actual_bytes = path.stat().st_size
        actual_hash = _sha256(path)
        if expected_bytes != actual_bytes or expected_hash != actual_hash:
            raise ValueError(f"artifact {name!r} does not match its recorded bytes/hash")
        verified[name] = {"path": relative, "bytes": actual_bytes, "sha256": actual_hash}
    actual_paths = {
        str(path.relative_to(root))
        for path in root.iterdir()
        if path.name != "manifest.json"
    }
    if actual_paths != declared_paths:
        raise ValueError(
            f"artifact directory differs from manifest: missing={sorted(declared_paths - actual_paths)}, "
            f"undeclared={sorted(actual_paths - declared_paths)}"
        )
    return {
        "status": "verified",
        "directory": str(root),
        "generation_version": GENERATION_VERSION,
        "artifact_count": len(verified),
        "artifacts": verified,
        "manifest_sha256": _sha256(manifest_path),
    }


def _git_receipt(project_root: Path) -> dict[str, Any]:
    if not (project_root / ".git").exists():
        return {"commit": None, "dirty": None}
    try:
        commit = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(project_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return {"commit": commit, "dirty": bool(status.strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def _extents(program: Any) -> list[float] | None:
    if not program_bounds_are_exact(program):
        return None
    lower, upper = program_bounds(program)
    return [upper[index] - lower[index] for index in range(3)]


def generate_artifacts(request: GenerationRequest) -> dict[str, Any]:
    """Generate a complete directory or publish nothing at the destination."""

    request.validate()
    output_dir = Path(request.output_dir).expanduser().resolve()
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    artifacts: dict[str, dict[str, Any]] = {}
    try:
        prompt = request.prompt.strip()
        document = TextToCAD(fn=request.fn).build(prompt)
        if not document.validation.valid:
            raise ValueError(f"prompt {prompt!r} was rejected: " + "; ".join(document.validation.errors))
        program = document.require_program()
        ir_validation = document.ir_validation
        if ir_validation is None:
            raise RuntimeError("validated generation returned no IR validation report")
        ir_text = serialize_ir_json(program)
        scad_text = program_to_scad(program, fn=request.fn)
        ir_path = staging / "design.ncad.json"
        scad_path = staging / "design.scad"
        validation_path = staging / "validation.json"
        request_path = staging / "request.json"
        write_text_atomic(request_path, json.dumps(asdict(request), indent=2, sort_keys=True) + "\n")
        write_text_atomic(
            validation_path,
            json.dumps(
                {
                    "valid": True,
                    "warnings": document.validation.warnings,
                    "ir_validation": ir_validation.to_dict(),
                    "evaluation": evaluate_program(program).to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        if "ir" in request.formats:
            write_text_atomic(ir_path, ir_text)
            artifacts["ir"] = {"path": ir_path.name}
        if set(request.formats) & {"scad", "stl", "preview"}:
            write_text_atomic(scad_path, scad_text)
            artifacts["scad"] = {
                "path": scad_path.name,
                "role": "requested" if "scad" in request.formats else "reproducibility_dependency",
            }
        if "stl" in request.formats:
            stl_path = staging / "design.stl"
            _, verification = compile_scad_verified(
                scad_path,
                stl_path,
                timeout=request.timeout_seconds,
                expected_extents_mm=_extents(program),
            )
            artifacts["stl"] = {"path": stl_path.name, "verification": verification}
        if "preview" in request.formats:
            preview_path = staging / "preview.png"
            fallback_mesh = stl_path if "stl" in request.formats else None
            render_scad_png(scad_path, preview_path, timeout=request.timeout_seconds, fallback_mesh=fallback_mesh)
            artifacts["preview"] = {"path": preview_path.name, "renderer": preview_renderer_backend()}
        for value in artifacts.values():
            artifact_path = staging / value["path"]
            value["sha256"] = _sha256(artifact_path)
            value["bytes"] = artifact_path.stat().st_size
        for supporting in (request_path, validation_path):
            artifacts[supporting.stem] = {
                "path": supporting.name,
                "sha256": _sha256(supporting),
                "bytes": supporting.stat().st_size,
            }
        bundle_bytes = sum(int(value["bytes"]) for value in artifacts.values())
        if bundle_bytes > MAX_BUNDLE_BYTES:
            raise RuntimeError(f"generated artifacts exceed the {MAX_BUNDLE_BYTES}-byte bundle limit")
        project_root = Path(__file__).resolve().parents[1]
        manifest = {
            "generation_version": GENERATION_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "prompt_sha256": hashlib.sha256(request.prompt.strip().encode("utf-8")).hexdigest(),
            "request": asdict(request),
            "git": _git_receipt(project_root),
            "runtime": {
                "python": platform.python_version(),
                "executable": sys.executable,
                "platform": platform.platform(),
                "pid": os.getpid(),
                "elapsed_seconds": perf_counter() - started,
            },
            "artifacts": artifacts,
            "artifact_bytes": bundle_bytes,
            "claim_boundary": "validated program and requested artifacts; not manufacturing or safety certification",
        }
        manifest_path = staging / "manifest.json"
        write_text_atomic(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        os.replace(staging, output_dir)
        return {"status": "complete", "output_dir": str(output_dir), "manifest": str(output_dir / "manifest.json"), **manifest}
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
