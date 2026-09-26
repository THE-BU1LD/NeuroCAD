"""Optional Gmsh CAD-to-volume-mesh backend with fail-closed receipts."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import shutil
import tempfile
import threading
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from core.gmsh_integrity import (
    COORD_ABS_TOL_MM,
    COORD_REL_TOL,
    GmshMeshingError as GmshMeshingError,
    capture_mesh,
    publish_directory_noreplace,
    verify_mesh_roundtrip,
)

GMSH_RECEIPT_VERSION = "neurocad-gmsh-mesh-receipt-v1"
MAX_STEP_BYTES = 256 * 1024 * 1024
MAX_MESH_ELEMENTS = 2_000_000
MAX_QUALITY_ELEMENTS = 200_000
_GMSH_LOCK = threading.Lock()


class GmshUnavailable(RuntimeError):
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
    roundtrip_verification: str = "nodes-connectivity-physical-membership-v1"
    roundtrip_coordinate_abs_tol_mm: float = COORD_ABS_TOL_MM
    roundtrip_coordinate_rel_tol: float = COORD_REL_TOL
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


def _snapshot_step(source: Path, snapshot: Path) -> tuple[int, str]:
    """Hash exactly the bounded private copy passed to Gmsh, not a mutable source."""
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as reader, snapshot.open("xb") as writer:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_STEP_BYTES:
                raise GmshMeshingError(
                    f"STEP source size must be from 1 through {MAX_STEP_BYTES} bytes"
                )
            writer.write(chunk)
            digest.update(chunk)
    if size == 0:
        raise GmshMeshingError(
            f"STEP source size must be from 1 through {MAX_STEP_BYTES} bytes"
        )
    return size, digest.hexdigest()


def _finite_positive(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a positive finite number")
    try:
        parsed = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a positive finite number") from exc
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
        source_input = source_step.expanduser()
        if source_input.is_symlink():
            raise FileNotFoundError(f"STEP source is missing or not a regular file: {source_input}")
        source = source_input.resolve()
        destination_input = output_dir.expanduser()
        if destination_input.exists() or destination_input.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination_input}")
        destination = destination_input.resolve()
        if not source.is_file():
            raise FileNotFoundError(f"STEP source is missing or not a regular file: {source}")
        source_bytes = source.stat().st_size
        if source_bytes <= 0 or source_bytes > MAX_STEP_BYTES:
            raise GmshMeshingError(
                f"STEP source size must be from 1 through {MAX_STEP_BYTES} bytes"
            )
        maximum = _finite_positive(max_size_mm, name="max_size_mm")
        minimum = _finite_positive(
            max(0.01, maximum / 5.0) if min_size_mm is None else min_size_mm,
            name="min_size_mm",
        )
        if minimum > maximum:
            raise ValueError("min_size_mm cannot exceed max_size_mm")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
        try:
            mesh_path = staging / "design.msh"
            receipt_path = staging / "meshing-receipt.json"
            source_snapshot = staging / "source.step"
            source_bytes, source_hash = _snapshot_step(source, source_snapshot)
            gmsh = self.gmsh

            with _GMSH_LOCK:
                if gmsh.isInitialized():
                    raise GmshMeshingError("refusing to use an already initialized Gmsh session")
                initialized = False
                try:
                    gmsh.initialize(readConfigFiles=False)
                    initialized = True
                    gmsh.option.setNumber("General.Terminal", 0)
                    gmsh.option.setNumber("Mesh.MeshSizeMin", minimum)
                    gmsh.option.setNumber("Mesh.MeshSizeMax", maximum)
                    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
                    gmsh.option.setNumber("Mesh.Binary", 0)
                    gmsh.open(str(source_snapshot))
                    source_snapshot.unlink()

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
                        if len(qualities) != element_count:
                            raise GmshMeshingError(
                                "Gmsh element quality count does not match volume-element count"
                            )
                        if any(not math.isfinite(item) for item in qualities):
                            raise GmshMeshingError("Gmsh returned non-finite element quality")
                        if any(item <= 0.0 for item in qualities):
                            raise GmshMeshingError("Gmsh returned non-positive element quality")
                        min_sicn = min(qualities)
                        mean_sicn = sum(qualities) / len(qualities)

                    original_mesh = capture_mesh(gmsh)
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

                    verify_mesh_roundtrip(original_mesh, capture_mesh(gmsh))

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
                finally:
                    if initialized:
                        gmsh.finalize()

            publish_directory_noreplace(staging, destination)
            return receipt
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
