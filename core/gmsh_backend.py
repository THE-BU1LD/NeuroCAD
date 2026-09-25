"""Optional Gmsh CAD-to-volume-mesh backend with fail-closed receipts."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import shutil
import tempfile
import threading
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

GMSH_RECEIPT_VERSION = "neurocad-gmsh-mesh-receipt-v1"
MAX_STEP_BYTES = 256 * 1024 * 1024
MAX_MESH_ELEMENTS = 2_000_000
MAX_QUALITY_ELEMENTS = 200_000
_GMSH_LOCK = threading.Lock()


class GmshUnavailable(RuntimeError):
    pass


class GmshMeshingError(ValueError):
    pass


@dataclass(frozen=True)
class GmshMeshReceipt:
    backend: str
    backend_version: str
    source_step_sha256: str
    source_step_bytes: int
    mesh_path: str
    mesh_sha256: str
    mesh_bytes: int
    volume_entity_count: int
    boundary_surface_count: int
    node_count: int
    volume_element_count: int
    physical_groups: tuple[str, ...]
    mesh_size_min_mm: float
    mesh_size_max_mm: float
    min_sicn: float | None
    mean_sicn: float | None
    roundtrip_node_count: int
    roundtrip_volume_element_count: int
    roundtrip_physical_groups: tuple[str, ...]
    claim_boundary: str = (
        "verified mesh generation and serialization only; not solver convergence, "
        "structural safety, manufacturability, or experimental validation"
    )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["physical_groups"] = list(self.physical_groups)
        value["roundtrip_physical_groups"] = list(self.roundtrip_physical_groups)
        value["receipt_version"] = GMSH_RECEIPT_VERSION
        return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_positive(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    if parsed < 0.01 or parsed > 1_000_000:
        raise ValueError(f"{name} must be between 0.01 and 1,000,000 mm")
    return parsed


def _physical_group_names(gmsh: Any) -> tuple[str, ...]:
    names: list[str] = []
    for dim, tag in gmsh.model.getPhysicalGroups():
        name = gmsh.model.getPhysicalName(dim, tag)
        names.append(name or f"{dim}:{tag}")
    return tuple(sorted(names))


def _mesh_counts(gmsh: Any) -> tuple[int, int, list[int]]:
    node_tags, _, _ = gmsh.model.mesh.getNodes()
    _, element_blocks, _ = gmsh.model.mesh.getElements(3)
    element_tags = [int(tag) for block in element_blocks for tag in block]
    return len(node_tags), len(element_tags), element_tags


class GmshBackend:
    def __init__(self) -> None:
        try:
            self.gmsh = importlib.import_module("gmsh")
        except (ImportError, OSError) as exc:
            raise GmshUnavailable(
                "Gmsh Python bindings are unavailable; install the mesh-gmsh optional dependency"
            ) from exc
        try:
            self.version = metadata.version("gmsh")
        except metadata.PackageNotFoundError:
            self.version = "unknown"

    def mesh_step(
        self,
        source_step: Path,
        output_dir: Path,
        *,
        max_size_mm: float,
        min_size_mm: float | None = None,
    ) -> GmshMeshReceipt:
        source = source_step.expanduser().resolve()
        destination = output_dir.expanduser().resolve()
        if source.is_symlink() or not source.is_file():
            raise FileNotFoundError(f"STEP source is missing or not a regular file: {source}")
        source_bytes = source.stat().st_size
        if source_bytes <= 0 or source_bytes > MAX_STEP_BYTES:
            raise GmshMeshingError(
                f"STEP source size must be from 1 through {MAX_STEP_BYTES} bytes"
            )
        maximum = _finite_positive(max_size_mm, name="max_size_mm")
        minimum = _finite_positive(
            maximum / 5.0 if min_size_mm is None else min_size_mm,
            name="min_size_mm",
        )
        if minimum > maximum:
            raise ValueError("min_size_mm cannot exceed max_size_mm")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
        mesh_path = staging / "design.msh"
        receipt_path = staging / "meshing-receipt.json"
        source_hash = _sha256(source)
        gmsh = self.gmsh

        with _GMSH_LOCK:
            initialized = False
            try:
                gmsh.initialize(readConfigFiles=False)
                initialized = True
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.option.setNumber("Mesh.MeshSizeMin", minimum)
                gmsh.option.setNumber("Mesh.MeshSizeMax", maximum)
                gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
                gmsh.option.setNumber("Mesh.Binary", 0)
                gmsh.open(str(source))

                volumes = gmsh.model.getEntities(3)
                surfaces = gmsh.model.getEntities(2)
                if not volumes:
                    raise GmshMeshingError("STEP input contains no 3-D volume entities")
                if not surfaces:
                    raise GmshMeshingError("STEP input contains no boundary surfaces")

                domain_tag = gmsh.model.addPhysicalGroup(3, [tag for _, tag in volumes])
                gmsh.model.setPhysicalName(3, domain_tag, "domain")
                boundary_tag = gmsh.model.addPhysicalGroup(2, [tag for _, tag in surfaces])
                gmsh.model.setPhysicalName(2, boundary_tag, "boundary")

                gmsh.model.mesh.generate(3)
                node_count, element_count, element_tags = _mesh_counts(gmsh)
                if node_count == 0 or element_count == 0:
                    raise GmshMeshingError("Gmsh generated an empty volume mesh")
                if element_count > MAX_MESH_ELEMENTS:
                    raise GmshMeshingError(
                        f"generated mesh has {element_count} volume elements; "
                        f"limit is {MAX_MESH_ELEMENTS}"
                    )
                groups = _physical_group_names(gmsh)
                if "domain" not in groups or "boundary" not in groups:
                    raise GmshMeshingError("required domain/boundary physical groups were not created")

                min_sicn: float | None = None
                mean_sicn: float | None = None
                if element_count <= MAX_QUALITY_ELEMENTS:
                    qualities = [
                        float(item)
                        for item in gmsh.model.mesh.getElementQualities(
                            element_tags,
                            "minSICN",
                        )
                    ]
                    if qualities:
                        if any(not math.isfinite(item) for item in qualities):
                            raise GmshMeshingError("Gmsh returned non-finite element quality")
                        min_sicn = min(qualities)
                        mean_sicn = sum(qualities) / len(qualities)

                gmsh.write(str(mesh_path))
                if not mesh_path.is_file() or mesh_path.stat().st_size == 0:
                    raise GmshMeshingError("Gmsh did not write a non-empty mesh artifact")

                gmsh.clear()
                gmsh.open(str(mesh_path))
                roundtrip_nodes, roundtrip_elements, _ = _mesh_counts(gmsh)
                roundtrip_groups = _physical_group_names(gmsh)
                if roundtrip_nodes != node_count or roundtrip_elements != element_count:
                    raise GmshMeshingError(
                        "serialized MSH roundtrip changed mesh node or volume-element count"
                    )
                if roundtrip_groups != groups:
                    raise GmshMeshingError(
                        "serialized MSH roundtrip changed physical-group names"
                    )

                receipt = GmshMeshReceipt(
                    backend="gmsh",
                    backend_version=self.version,
                    source_step_sha256=source_hash,
                    source_step_bytes=source_bytes,
                    mesh_path=mesh_path.name,
                    mesh_sha256=_sha256(mesh_path),
                    mesh_bytes=mesh_path.stat().st_size,
                    volume_entity_count=len(volumes),
                    boundary_surface_count=len(surfaces),
                    node_count=node_count,
                    volume_element_count=element_count,
                    physical_groups=groups,
                    mesh_size_min_mm=minimum,
                    mesh_size_max_mm=maximum,
                    min_sicn=min_sicn,
                    mean_sicn=mean_sicn,
                    roundtrip_node_count=roundtrip_nodes,
                    roundtrip_volume_element_count=roundtrip_elements,
                    roundtrip_physical_groups=roundtrip_groups,
                )
                receipt_path.write_text(
                    json.dumps(receipt.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8",
                )
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
            finally:
                if initialized:
                    try:
                        gmsh.finalize()
                    except Exception:  # noqa: BLE001 - cleanup must not mask the primary result
                        pass

        os.replace(staging, destination)
        return receipt
