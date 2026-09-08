from __future__ import annotations

import json
import math
import os
import shutil
import subprocess  # OpenSCAD uses a fixed argument vector.  # nosec B404
import tempfile
from pathlib import Path
from typing import Any

from .design_graph import DesignGraph
from .ir import CADProgram, IRValidationReport
from .topology import analyze_triangle_complex
from .validation import ValidationReport


def write_text_atomic(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            temporary = ""
        raise
    return path


def design_manifest(
    design: DesignGraph,
    report: ValidationReport,
    program: CADProgram | None = None,
    ir_report: IRValidationReport | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "1.0",
        "title": design.title,
        "units": "mm",
        "metadata": dict(design.metadata),
        "validation": report.as_dict(),
        "components": [
            {
                "name": component.name,
                "role": component.role,
                "operation": component.operation,
                "geometry": dict(component.geometry()),
                "transform": {key: list(value) for key, value in component.transform.items()},
            }
            for component in design.components
        ],
        "connections": [
            {"a": connection.a.name, "b": connection.b.name, "relation": connection.relation}
            for connection in design.connections
        ],
    }
    if program is not None:
        manifest["canonical_ir"] = program.to_dict()
    if ir_report is not None:
        manifest["ir_validation"] = ir_report.to_dict()
    return manifest


def write_manifest(
    path: Path,
    design: DesignGraph,
    report: ValidationReport,
    program: CADProgram | None = None,
    ir_report: IRValidationReport | None = None,
) -> Path:
    return write_text_atomic(
        path,
        json.dumps(design_manifest(design, report, program, ir_report), indent=2, sort_keys=True) + "\n",
    )


def find_openscad() -> str | None:
    return shutil.which("openscad")


def _temporary_artifact_path(output: Path) -> Path:
    """Reserve a same-filesystem staging path for an external artifact writer."""

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{output.stem}.",
        suffix=output.suffix,
        dir=output.parent,
    )
    os.close(descriptor)
    return Path(temporary)


def compile_scad(source: Path, output: Path, *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("OpenSCAD timeout must be a positive integer number of seconds")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("OpenSCAD source must be an existing non-empty file")
    if source.resolve() == output.resolve():
        raise ValueError("OpenSCAD source and output paths must be different")
    executable = find_openscad()
    if not executable:
        raise RuntimeError("OpenSCAD is required for compiled validation and STL export")
    temporary = _temporary_artifact_path(output)
    try:
        completed = subprocess.run(  # Executable is from shutil.which; paths are separate argv entries.  # nosec B603
            [executable, "-o", str(temporary), str(source)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD timed out after {timeout} seconds") from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    diagnostics = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD failed with exit code {completed.returncode}: {diagnostics}")
    if not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD did not create a non-empty {output.suffix} artifact")
    if "ERROR:" in diagnostics:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD reported an error: {diagnostics}")
    try:
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return completed


def compile_scad_verified(
    source: Path,
    output: Path,
    *,
    timeout: int = 120,
    expected_extents_mm: tuple[float, float, float] | list[float] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """Compile and kernel-verify an STL before atomically publishing it."""

    if source.resolve() == output.resolve():
        raise ValueError("OpenSCAD source and output paths must be different")
    temporary = _temporary_artifact_path(output)
    try:
        completed = compile_scad(source, temporary, timeout=timeout)
        verification = verify_stl(temporary, expected_extents_mm=expected_extents_mm)
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return completed, verification


def render_scad_png(source: Path, output: Path, *, timeout: int = 120, width: int = 960, height: int = 720) -> Path:
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("OpenSCAD timeout must be a positive integer number of seconds")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("OpenSCAD source must be an existing non-empty file")
    if source.resolve() == output.resolve():
        raise ValueError("OpenSCAD source and render paths must be different")
    executable = find_openscad()
    if not executable:
        raise RuntimeError("OpenSCAD is required for rendered CAD figures")
    if not 64 <= width <= 4096 or not 64 <= height <= 4096:
        raise ValueError("render dimensions must be between 64 and 4096 pixels")
    temporary = _temporary_artifact_path(output)
    try:
        completed = subprocess.run(  # Fixed executable and separate argv entries.  # nosec B603
            [
                executable,
                "-o",
                str(temporary),
                f"--imgsize={width},{height}",
                "--viewall",
                "--autocenter",
                str(source),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD image render timed out after {timeout} seconds") from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    diagnostics = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0 or "ERROR:" in diagnostics:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"OpenSCAD image render failed with exit code {completed.returncode}: {diagnostics}")
    if not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("OpenSCAD did not create a non-empty PNG render")
    try:
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output


def verify_stl(
    path: Path,
    *,
    expected_extents_mm: tuple[float, float, float] | list[float] | None = None,
    extent_relative_tolerance: float = 0.01,
    extent_absolute_tolerance_mm: float = 0.2,
) -> dict[str, Any]:
    import trimesh

    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("STL path must identify an existing non-empty file")
    for name, value in (
        ("extent_relative_tolerance", extent_relative_tolerance),
        ("extent_absolute_tolerance_mm", extent_absolute_tolerance_mm),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"{name} must be a finite non-negative number")

    mesh = trimesh.load_mesh(path, force="mesh", process=True)
    if mesh.is_empty:
        raise RuntimeError("the generated STL mesh is empty")
    extents = [float(value) for value in mesh.extents]
    finite_vertices = bool(mesh.vertices.size) and all(math.isfinite(float(value)) for value in mesh.vertices.flat)
    if not finite_vertices:
        raise RuntimeError("the generated STL contains non-finite vertices")
    if any(value <= 0 for value in extents):
        raise RuntimeError("the generated STL has a zero-size extent")
    parents = list(range(len(mesh.faces)))

    def find(face: int) -> int:
        while parents[face] != face:
            parents[face] = parents[parents[face]]
            face = parents[face]
        return face

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(mesh.faces):
        vertices = [int(value) for value in face]
        for left, right in (
            (vertices[0], vertices[1]),
            (vertices[1], vertices[2]),
            (vertices[2], vertices[0]),
        ):
            edge = (left, right) if left < right else (right, left)
            edge_faces.setdefault(edge, []).append(face_index)
    # A volume is connected through manifold face edges, not merely through a
    # shared point or non-manifold contact edge.
    for incident_faces in edge_faces.values():
        if len(incident_faces) == 2:
            union(incident_faces[0], incident_faces[1])
    body_count = len({find(face) for face in range(len(mesh.faces))})
    if body_count != 1:
        raise RuntimeError(f"the generated STL contains {body_count} disconnected bodies; expected exactly one")
    if not bool(mesh.is_watertight):
        raise RuntimeError("the generated STL is not watertight")
    if not bool(mesh.is_winding_consistent):
        raise RuntimeError("the generated STL has inconsistent face winding")
    topology = analyze_triangle_complex(mesh.vertices, mesh.faces)
    if not topology["manifold"]:
        raise RuntimeError("the generated STL has non-manifold vertex links or edges")
    if not bool(mesh.is_volume):
        raise RuntimeError("the generated STL does not bound a valid volume")
    volume = float(abs(mesh.volume))
    if not math.isfinite(volume) or volume <= 0:
        raise RuntimeError("the generated STL has non-positive or non-finite volume")
    extent_errors: list[float] | None = None
    if expected_extents_mm is not None:
        if len(expected_extents_mm) != 3 or any(not math.isfinite(float(value)) or float(value) <= 0 for value in expected_extents_mm):
            raise ValueError("expected_extents_mm must contain three positive finite dimensions")
        extent_errors = [abs(actual - float(expected)) for actual, expected in zip(extents, expected_extents_mm, strict=True)]
        tolerances = [
            max(extent_absolute_tolerance_mm, float(expected) * extent_relative_tolerance)
            for expected in expected_extents_mm
        ]
        if any(error > tolerance for error, tolerance in zip(extent_errors, tolerances, strict=True)):
            raise RuntimeError(
                f"the generated STL extents {extents} do not match expected extents {list(expected_extents_mm)} "
                f"within tolerances {tolerances}"
            )
    return {
        "verification_kind": "kernel_mesh",
        "kernel_validity": True,
        "watertight": True,
        "winding_consistent": True,
        "finite_vertices": True,
        "is_volume": True,
        "body_count": body_count,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "extents_mm": extents,
        "extent_absolute_errors_mm": extent_errors,
        "volume_mm3": volume,
        "topology": topology,
    }
