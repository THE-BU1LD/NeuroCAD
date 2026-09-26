"""Bounded mesh round-trip checks and no-replace publication; not a sandbox."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import math
import os
import struct
import sys
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COORD_ABS_TOL_MM = 1e-12
COORD_REL_TOL = 1e-13
MAX_VERIFY_NODES = 1_000_000
MAX_VERIFY_ELEMENTS = 3_000_000


class GmshMeshingError(ValueError):
    pass


@dataclass(frozen=True)
class MeshSnapshot:
    node_tags: array
    coordinates: array
    topology_sha256: str
    physical_groups: tuple[tuple[int, int, str, tuple[int, ...]], ...]


def capture_mesh(gmsh: Any) -> MeshSnapshot:
    """Snapshot nodes and exported 2-D/3-D elements, independent of API order.

    Only 2-D/3-D elements are exported by the adapter's physical groups.
    0-D/1-D elements are therefore intentionally outside this comparison.
    These are post-generation verification limits, NOT native allocation limits.
    """
    tags, raw_coords, _ = gmsh.model.mesh.getNodes()
    if not 0 < len(tags) <= MAX_VERIFY_NODES:
        raise GmshMeshingError("mesh node count exceeds bounded verification contract")
    if len(raw_coords) != 3 * len(tags):
        raise GmshMeshingError("mesh node coordinate array has incorrect length")
    order = sorted(range(len(tags)), key=lambda i: int(tags[i]))
    node_tags = array("Q", (int(tags[i]) for i in order))
    if node_tags[0] == 0 or any(a == b for a, b in zip(node_tags, node_tags[1:])):
        raise GmshMeshingError("mesh node tags must be positive and unique")
    coordinates = array("d", (float(raw_coords[3 * i + j]) for i in order for j in range(3)))
    if any(not math.isfinite(value) for value in coordinates):
        raise GmshMeshingError("mesh node coordinates must be finite")

    digest = hashlib.sha256(b"neurocad-mesh-topology-v1\0")
    total = 0
    for dim in (2, 3):
        for _, entity in sorted(gmsh.model.getEntities(dim)):
            types, blocks, connectivity = gmsh.model.mesh.getElements(dim, int(entity))
            if not len(types) == len(blocks) == len(connectivity):
                raise GmshMeshingError("mesh element block arrays have inconsistent lengths")
            for index in sorted(range(len(types)), key=lambda i: int(types[i])):
                element_type = int(types[index])
                properties = gmsh.model.mesh.getElementProperties(element_type)
                width = int(properties[3])
                element_tags, nodes = blocks[index], connectivity[index]
                total += len(element_tags)
                if total > MAX_VERIFY_ELEMENTS:
                    raise GmshMeshingError("mesh element count exceeds bounded verification contract")
                if int(properties[1]) != dim or width <= 0 or len(nodes) != width * len(element_tags):
                    raise GmshMeshingError("mesh element connectivity has incorrect shape")
                digest.update(struct.pack(
                    ">5Q", dim, int(entity), element_type, width, len(element_tags)
                ))
                previous = 0
                for i in sorted(range(len(element_tags)), key=lambda j: int(element_tags[j])):
                    tag = int(element_tags[i])
                    if tag <= previous:
                        raise GmshMeshingError("mesh element tags must be positive and unique per block")
                    previous = tag
                    digest.update(struct.pack(
                        f">{width + 1}Q", tag,
                        *(int(nodes[width * i + j]) for j in range(width)),
                    ))

    groups = tuple(sorted(
        (
            int(dim), int(tag), str(gmsh.model.getPhysicalName(dim, tag)),
            tuple(sorted(int(entity) for entity in gmsh.model.getEntitiesForPhysicalGroup(dim, tag))),
        )
        for dim, tag in gmsh.model.getPhysicalGroups()
    ))
    return MeshSnapshot(node_tags, coordinates, digest.hexdigest(), groups)


def verify_mesh_roundtrip(before: MeshSnapshot, after: MeshSnapshot) -> None:
    """Reject count-preserving damage; allow only documented ASCII float drift."""
    if before.node_tags != after.node_tags:
        raise GmshMeshingError("serialized MSH roundtrip changed node identities")
    if before.topology_sha256 != after.topology_sha256:
        raise GmshMeshingError("serialized MSH roundtrip changed element topology or entity membership")
    if before.physical_groups != after.physical_groups:
        raise GmshMeshingError("serialized MSH roundtrip changed physical-group membership")
    if len(before.coordinates) != len(after.coordinates) or any(
        not math.isclose(a, b, rel_tol=COORD_REL_TOL, abs_tol=COORD_ABS_TOL_MM)
        for a, b in zip(before.coordinates, after.coordinates)
    ):
        raise GmshMeshingError("serialized MSH roundtrip changed node coordinates")


def publish_directory_noreplace(staging: Path, destination: Path) -> None:
    """Atomically publish sibling directories without replacing any destination.

    The caller owns staging and must clean it on failure. Parent directories are
    trusted. Unsupported platforms/filesystems fail closed, without an unsafe
    check-then-rename fallback. Atomic visibility is not power-loss durability.
    """
    if staging.parent != destination.parent:
        raise ValueError("staging and destination must share a parent directory")
    if staging.is_symlink() or not staging.is_dir():
        raise ValueError("staging must be a regular directory")
    if sys.platform == "win32":
        # Unlike POSIX rename(), Windows rename refuses an existing destination.
        os.rename(staging, destination)
        return
    if sys.platform.startswith("linux"):
        function_name, flags = "renameat2", 1  # RENAME_NOREPLACE
    elif sys.platform == "darwin":
        function_name, flags = "renameatx_np", 0x4  # RENAME_EXCL, XNU sys/stdio.h
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace directory publication unavailable")
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, function_name, None)
    if function is None:
        raise OSError(errno.ENOTSUP, f"{function_name} unavailable; refusing overwrite fallback")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    parent_fd = os.open(staging.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = function(
            parent_fd, os.fsencode(staging.name), parent_fd, os.fsencode(destination.name), flags
        )
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination))
    finally:
        os.close(parent_fd)
