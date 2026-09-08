"""Bounded previews and downloads derived from the same verified STL bytes."""
from __future__ import annotations

import base64
import hashlib
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .artifacts import compile_scad_verified
from .enclosure_verification import verify_enclosure_mesh
from .natural_language import interpret_enclosure

_COMPILER_SLOT = threading.Lock()
MAX_PREVIEW_FACES = 20000
MAX_STL_BYTES = 8 * 1024 * 1024


class MeshDownloadStore:
    """Short-lived, bounded in-memory downloads; no filesystem paths are exposed."""

    def __init__(self, max_bytes: int = 32 * 1024 * 1024, ttl_seconds: float = 600) -> None:
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._files: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        now = time.monotonic()
        self._files = {key: value for key, value in self._files.items() if value[0] > now}

    def publish(self, artifacts: dict[str, Any]) -> None:
        token = secrets.token_hex(16)
        files = {f'/api/mesh/{token}/{part}.stl': base64.b64decode(item['stl_base64'], validate=True)
                 for part, item in artifacts.items()}
        total = sum(map(len, files.values()))
        if total > self.max_bytes:
            raise ValueError('Downloads exceed local storage budget; use the CLI')
        with self._lock:
            self._expire()
            while self._files and sum(len(value[1]) for value in self._files.values()) + total > self.max_bytes:
                del self._files[next(iter(self._files))]
            for path, raw in files.items():
                self._files[path] = (time.monotonic() + self.ttl_seconds, raw)
        for part, item in artifacts.items():
            item['download_url'] = f'/api/mesh/{token}/{part}.stl'
            del item['stl_base64']

    def get(self, path: str) -> bytes | None:
        with self._lock:
            self._expire()
            value = self._files.get(path)
            return value[1] if value else None


DOWNLOADS = MeshDownloadStore()


def _mesh_svg(path: Path) -> str:
    import numpy as np
    import trimesh

    mesh = trimesh.load_mesh(path, force="mesh", process=True)
    if len(mesh.faces) > MAX_PREVIEW_FACES:
        raise ValueError("Mesh exceeds the interactive preview limit of 20,000 triangles; use the CLI")
    # Orthographic isometric projection of the actual Boolean-result triangles.
    vertices = mesh.vertices
    projection = np.column_stack(((vertices[:, 0] - vertices[:, 1]) * .70710678,
                                  (vertices[:, 0] + vertices[:, 1]) * .40824829 - vertices[:, 2] * .81649658))
    lower, upper = projection.min(axis=0), projection.max(axis=0)
    scale = min(680 / max(float(upper[0]-lower[0]), 1), 350 / max(float(upper[1]-lower[1]), 1))
    points = (projection-lower) * scale + [40, 35]
    depths = vertices[:, 0] + vertices[:, 1] + vertices[:, 2]
    order = np.argsort(depths[mesh.faces].mean(axis=1))
    polygons = []
    for index in order:
        face = mesh.faces[index]
        coords = " ".join(f"{points[v][0]:.3f},{points[v][1]:.3f}" for v in face)
        shade = int(100 + 110 * abs(float(mesh.face_normals[index][2])))
        polygons.append(f'<polygon points="{coords}" fill="rgb(35,{shade},190)"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 440" role="img" '
            'aria-label="Compiled STL isometric mesh preview"><rect width="760" height="440" fill="#081018"/>'
            + "".join(polygons) + '<text x="20" y="422" fill="#c4d7e8" font-size="12">'
            'Actual compiled mesh — geometry verification does not certify physical fit.</text></svg>')


def compile_payload_meshes(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if not _COMPILER_SLOT.acquire(blocking=False):
        raise ValueError("The local compiler is busy. Retry after the current compilation finishes.")
    try:
        parts = payload['scad'] if isinstance(payload['scad'], dict) else {'model': payload['scad']}
        spec = interpret_enclosure(payload['prompt']).spec if payload['mode'] == 'enclosure' else None
        artifacts = {}
        with tempfile.TemporaryDirectory(prefix='neurocad-preview-') as directory:
            for part, scad in parts.items():
                if part not in {'body', 'lid', 'model'}:
                    raise ValueError("Unsupported preview part")
                source, output = Path(directory)/f'{part}.scad', Path(directory)/f'{part}.stl'
                source.write_text(scad, encoding='utf-8')
                _, report = compile_scad_verified(source, output, timeout=30)
                if spec is not None:
                    feature_report = verify_enclosure_mesh(output, spec, part=part)
                    if not feature_report.valid:
                        raise ValueError("Compiled enclosure failed requested-feature verification")
                    report['enclosure_features'] = feature_report.to_dict()
                if output.stat().st_size > MAX_STL_BYTES:
                    raise ValueError("STL exceeds the 8 MiB browser download limit; use the CLI")
                raw = output.read_bytes()
                artifacts[part] = {'filename':f'{part}.stl', 'sha256':hashlib.sha256(raw).hexdigest(),
                                   'stl_base64':base64.b64encode(raw).decode('ascii'),
                                   'verification':report, 'preview_svg':_mesh_svg(output)}
        payload['mesh_artifacts'] = artifacts
        payload['preview_svg'] = next(iter(artifacts.values()))['preview_svg']
        payload['evaluation']['kernel_validity'] = True
        payload['evaluation']['evaluation_latency_ms'] += (time.perf_counter() - started) * 1000
        return payload
    finally:
        _COMPILER_SLOT.release()
