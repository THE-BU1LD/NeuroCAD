from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess  # OpenSCAD uses a fixed argument vector.  # nosec B404
import tempfile
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .design_graph import DesignGraph
from .ir import CADProgram, IRValidationReport
from .topology import analyze_triangle_complex
from .validation import ValidationReport

_NATIVE_RENDER_AVAILABLE: bool | None = None


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


@dataclass(frozen=True)
class OpenSCADCapabilities:
    executable: str | None
    mesh: bool
    preview: bool
    mesh_detail: str
    preview_detail: str


@lru_cache(maxsize=1)
def probe_openscad_capabilities(timeout: int = 60) -> OpenSCADCapabilities:
    """Exercise mesh and image paths instead of treating binary presence as health."""

    executable = find_openscad()
    if executable is None:
        detail = "not installed"
        return OpenSCADCapabilities(None, False, False, detail, detail)
    with tempfile.TemporaryDirectory(prefix="neurocad-openscad-probe-") as directory:
        root = Path(directory)
        source = write_text_atomic(root / "probe.scad", "cube([1, 1, 1], center=true);\n")
        # Exercise the lightweight renderer first so a cold OpenSCAD process can
        # initialize before the stricter mesh capability check.
        try:
            render_scad_png(source, root / "probe.png", timeout=timeout, width=64, height=64)
            preview = True
            preview_detail = (
                "native image rendering passed"
                if _NATIVE_RENDER_AVAILABLE
                else "verified STL fallback passed; native image rendering is unavailable"
            )
        except (OSError, RuntimeError, ValueError) as exc:
            preview, preview_detail = False, str(exc)
        try:
            compile_scad(source, root / "probe.stl", timeout=timeout)
            mesh, mesh_detail = True, "mesh compilation passed"
        except (OSError, RuntimeError, ValueError) as exc:
            mesh, mesh_detail = False, str(exc)
    return OpenSCADCapabilities(executable, mesh, preview, mesh_detail, preview_detail)


def preview_renderer_backend() -> str:
    """Report the backend used by the most recent preview in this process."""

    if _NATIVE_RENDER_AVAILABLE is True:
        return "openscad-native"
    if _NATIVE_RENDER_AVAILABLE is False:
        return "verified-stl-wireframe"
    return "not-run"


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


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def render_stl_png(source: Path, output: Path, *, width: int = 960, height: int = 720) -> Path:
    """Render a deterministic isometric wireframe from verified STL triangles."""

    import numpy as np
    import trimesh

    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("STL preview source must be an existing non-empty file")
    if not 64 <= width <= 4096 or not 64 <= height <= 4096:
        raise ValueError("render dimensions must be between 64 and 4096 pixels")
    mesh = trimesh.load_mesh(source, force="mesh", process=True)
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
        raise ValueError("STL preview source has no finite triangle mesh")
    vertices = mesh.vertices
    projection = np.column_stack(
        (
            (vertices[:, 0] - vertices[:, 1]) * 0.70710678,
            (vertices[:, 0] + vertices[:, 1]) * 0.40824829 - vertices[:, 2] * 0.81649658,
        )
    )
    lower, upper = projection.min(axis=0), projection.max(axis=0)
    margin = max(8, min(width, height) // 16)
    scale = min(
        (width - 2 * margin) / max(float(upper[0] - lower[0]), 1e-12),
        (height - 2 * margin) / max(float(upper[1] - lower[1]), 1e-12),
    )
    points = (projection - lower) * scale + margin
    points[:, 1] = height - points[:, 1]
    pixels = bytearray((8, 16, 24) * (width * height))

    def draw_line(start: np.ndarray[Any, Any], end: np.ndarray[Any, Any], color: tuple[int, int, int]) -> None:
        x0, y0 = (round(float(value)) for value in start)
        x1, y1 = (round(float(value)) for value in end)
        dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
        dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            if 0 <= x0 < width and 0 <= y0 < height:
                offset = (y0 * width + x0) * 3
                pixels[offset : offset + 3] = bytes(color)
            if x0 == x1 and y0 == y1:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x0 += sx
            if doubled <= dx:
                error += dx
                y0 += sy

    depths = vertices[:, 0] + vertices[:, 1] + vertices[:, 2]
    for index in np.argsort(depths[mesh.faces].mean(axis=1)):
        face = mesh.faces[index]
        shade = int(145 + 90 * abs(float(mesh.face_normals[index][2])))
        color = (35, min(shade, 235), 210)
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            draw_line(points[first], points[second], color)

    raw = b"".join(b"\x00" + bytes(pixels[row * width * 3 : (row + 1) * width * 3]) for row in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    temporary = _temporary_artifact_path(output)
    try:
        temporary.write_bytes(png)
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output


def _render_mesh_fallback(source: Path, output: Path, *, timeout: int, mesh_source: Path | None, width: int, height: int) -> Path:
    if mesh_source is not None:
        return render_stl_png(mesh_source, output, width=width, height=height)
    with tempfile.TemporaryDirectory(prefix="neurocad-preview-fallback-") as directory:
        temporary_mesh = Path(directory) / "preview.stl"
        compile_scad(source, temporary_mesh, timeout=timeout)
        return render_stl_png(temporary_mesh, output, width=width, height=height)


class CompilerTimeoutError(RuntimeError):
    """The kernel exceeded its explicit deadline; no new artifact was published."""


class CompilerUnavailableError(RuntimeError):
    """No supported OpenSCAD executable could be found."""


def compile_scad(source: Path, output: Path, *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("OpenSCAD timeout must be a positive integer number of seconds")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("OpenSCAD source must be an existing non-empty file")
    if source.resolve() == output.resolve():
        raise ValueError("OpenSCAD source and output paths must be different")
    executable = find_openscad()
    if not executable:
        raise CompilerUnavailableError("OpenSCAD is required for compiled validation and STL export")
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
        raise CompilerTimeoutError(f"OpenSCAD timed out after {timeout} seconds") from exc
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


def render_scad_png(
    source: Path,
    output: Path,
    *,
    timeout: int = 120,
    width: int = 960,
    height: int = 720,
    fallback_mesh: Path | None = None,
) -> Path:
    global _NATIVE_RENDER_AVAILABLE

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
    if _NATIVE_RENDER_AVAILABLE is False:
        return _render_mesh_fallback(source, output, timeout=timeout, mesh_source=fallback_mesh, width=width, height=height)
    renderer_timeout = min(timeout, 15)
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
            timeout=renderer_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        _NATIVE_RENDER_AVAILABLE = False
        temporary.unlink(missing_ok=True)
        try:
            return _render_mesh_fallback(source, output, timeout=timeout, mesh_source=fallback_mesh, width=width, height=height)
        except Exception as fallback_exc:  # noqa: BLE001 - preserve both external renderer failures
            raise RuntimeError(
                f"OpenSCAD image render timed out after {renderer_timeout} seconds; mesh fallback failed: {fallback_exc}"
            ) from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    diagnostics = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0 or "ERROR:" in diagnostics:
        _NATIVE_RENDER_AVAILABLE = False
        temporary.unlink(missing_ok=True)
        try:
            return _render_mesh_fallback(source, output, timeout=timeout, mesh_source=fallback_mesh, width=width, height=height)
        except Exception as fallback_exc:
            raise RuntimeError(
                f"OpenSCAD image render failed with exit code {completed.returncode}: {diagnostics}; "
                f"mesh fallback failed: {fallback_exc}"
            ) from fallback_exc
    if not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        _NATIVE_RENDER_AVAILABLE = False
        return _render_mesh_fallback(source, output, timeout=timeout, mesh_source=fallback_mesh, width=width, height=height)
    _NATIVE_RENDER_AVAILABLE = True
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
