"""Source-bound semantic roles for planar faces on an axis-aligned envelope.

Selectors contain geometry predicates, never persisted kernel entity indices.
This deliberately small vocabulary does not infer loads or boundary conditions.
"""
from __future__ import annotations

import math
import re
from typing import Any

from .gmsh_integrity import GmshMeshingError

ROLE_TOLERANCE_MM = 1e-6
ROLE_RECEIPT_VERSION = "neurocad-mesh-roles-v1"


def validate_roles(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"source_step_sha256", "roles"}:
        raise ValueError("boundary roles require source_step_sha256 and roles")
    digest, roles = value["source_step_sha256"], value["roles"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("boundary roles require a lowercase SHA-256 source identity")
    if not isinstance(roles, dict) or not 1 <= len(roles) <= 16:
        raise ValueError("boundary roles must contain 1 through 16 named selectors")
    normalized = {}
    for name, selector in sorted(roles.items()):
        if (not isinstance(name, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,47}", name) is None
                or name in {"domain", "boundary"}):
            raise ValueError("role names must be distinct portable names other than domain/boundary")
        if not isinstance(selector, dict) or set(selector) != {"axis", "side", "expected_surfaces"}:
            raise ValueError("role selector requires axis, side and expected_surfaces; indices are forbidden")
        if selector["axis"] not in ("x", "y", "z") or selector["side"] not in ("min", "max"):
            raise ValueError("role selector requires axis x/y/z and side min/max")
        count = selector["expected_surfaces"]
        if type(count) is not int or not 1 <= count <= 64:
            raise ValueError("expected_surfaces must be an integer from 1 through 64")
        normalized[name] = dict(selector)
    return {"source_step_sha256": digest, "roles": normalized}


def bind_roles(gmsh: Any, surfaces: list[tuple[int, int]], request: dict[str, Any]) -> dict[str, list[int]]:
    bounds = {tag: tuple(float(x) for x in gmsh.model.getBoundingBox(2, tag)) for _, tag in surfaces}
    if not bounds or any(len(box) != 6 or not all(math.isfinite(x) for x in box) for box in bounds.values()):
        raise GmshMeshingError("semantic roles require finite surface bounds")
    bindings = {}
    for name, selector in request["roles"].items():
        axis = "xyz".index(selector["axis"])
        side = selector["side"]
        coordinate = (min(box[axis] for box in bounds.values()) if side == "min"
                      else max(box[axis + 3] for box in bounds.values()))
        selected = sorted(tag for tag, box in bounds.items()
                          if gmsh.model.getType(2, tag) == "Plane"
                          and abs(box[axis] - coordinate) <= ROLE_TOLERANCE_MM
                          and abs(box[axis + 3] - coordinate) <= ROLE_TOLERANCE_MM)
        if len(selected) != selector["expected_surfaces"]:
            raise GmshMeshingError(f"semantic role {name!r} matched {len(selected)} surfaces; "
                                   f"expected {selector['expected_surfaces']}")
        group = gmsh.model.addPhysicalGroup(2, selected)
        gmsh.model.setPhysicalName(2, group, name)
        bindings[name] = selected
    return bindings
