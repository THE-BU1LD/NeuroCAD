"""Shared geometry verifier for the frozen VeriCodeGen successor study.

This module deliberately operates on final mesh artifacts rather than NeuroCAD
internal state so the direct-generation and structured-generation arms can be
judged by the same measurements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import trimesh


AXES = ("x", "y", "z")


@dataclass(frozen=True)
class VerificationReport:
    passed: bool
    failures: tuple[str, ...]
    measurements: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_mesh(value: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
    if isinstance(value, trimesh.Trimesh):
        mesh = value.copy()
    elif isinstance(value, trimesh.Scene):
        geometries = [geometry.copy() for geometry in value.geometry.values()]
        if not geometries:
            raise ValueError("mesh artifact contains no geometry")
        mesh = trimesh.util.concatenate(geometries)
    else:
        raise TypeError(f"unsupported mesh type: {type(value)!r}")

    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise ValueError("mesh artifact is empty")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("mesh artifact contains non-finite vertices")
    return mesh


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    """Load a final geometry artifact for shared verification."""

    loaded = trimesh.load(Path(path), force=None, process=False)
    return _coerce_mesh(loaded)


def _component_count(mesh: trimesh.Trimesh) -> int:
    """Count face-connected components without optional scipy/networkx deps.

    Trimesh's high-level ``split`` helper delegates to optional graph engines.
    The verifier must remain reproducible with the repository's declared base
    dependencies, so Stage 0 uses a small union-find over vertex indices instead.
    """

    faces = np.asarray(mesh.faces, dtype=np.int64)
    parent = np.arange(len(mesh.vertices), dtype=np.int64)
    rank = np.zeros(len(mesh.vertices), dtype=np.int8)
    used = np.zeros(len(mesh.vertices), dtype=bool)

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = int(parent[node])
        return node

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        if rank[root_left] < rank[root_right]:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left
        if rank[root_left] == rank[root_right]:
            rank[root_left] += 1

    for face in faces:
        if len(face) == 0:
            continue
        used[face] = True
        anchor = int(face[0])
        for vertex in face[1:]:
            union(anchor, int(vertex))

    vertices = np.flatnonzero(used)
    return len({find(int(vertex)) for vertex in vertices})


def _check_range(
    name: str,
    value: float,
    rule: Mapping[str, Any],
    failures: list[str],
) -> None:
    if "min" in rule and value < float(rule["min"]):
        failures.append(f"{name}={value:.9g} below minimum {float(rule['min']):.9g}")
    if "max" in rule and value > float(rule["max"]):
        failures.append(f"{name}={value:.9g} above maximum {float(rule['max']):.9g}")


def verify_mesh(
    artifact: trimesh.Trimesh | trimesh.Scene,
    constraints: Mapping[str, Any],
) -> VerificationReport:
    """Evaluate predeclared hard constraints against a final mesh artifact.

    Supported constraints are intentionally small and objective for Stage 0:

    - ``watertight``: required boolean mesh watertightness;
    - ``max_components``: maximum connected mesh components;
    - ``volume``: mapping with optional ``min``/``max``;
    - ``extents``: per-axis ``x``/``y``/``z`` mappings with optional min/max;
    - ``bounds``: optional ``min`` and/or ``max`` 3-vectors bounding the artifact.

    Unknown constraints fail closed so a benchmark task cannot silently request a
    measurement that the shared verifier ignores.
    """

    allowed = {"watertight", "max_components", "volume", "extents", "bounds"}
    unknown = sorted(set(constraints) - allowed)
    if unknown:
        raise ValueError(f"unsupported hard constraints: {', '.join(unknown)}")

    mesh = _coerce_mesh(artifact)
    failures: list[str] = []

    extents = np.asarray(mesh.extents, dtype=float)
    bounds = np.asarray(mesh.bounds, dtype=float)
    volume = float(abs(mesh.volume))
    component_count = _component_count(mesh)

    measurements: dict[str, Any] = {
        "watertight": bool(mesh.is_watertight),
        "component_count": int(component_count),
        "volume": volume,
        "extents": {axis: float(extents[index]) for index, axis in enumerate(AXES)},
        "bounds": {
            "min": [float(value) for value in bounds[0]],
            "max": [float(value) for value in bounds[1]],
        },
    }

    if "watertight" in constraints:
        expected = bool(constraints["watertight"])
        if bool(mesh.is_watertight) is not expected:
            failures.append(
                f"watertight={bool(mesh.is_watertight)} but expected {expected}"
            )

    if "max_components" in constraints:
        maximum = int(constraints["max_components"])
        if maximum < 1:
            raise ValueError("max_components must be at least 1")
        if component_count > maximum:
            failures.append(
                f"component_count={component_count} above maximum {maximum}"
            )

    if "volume" in constraints:
        rule = constraints["volume"]
        if not isinstance(rule, Mapping):
            raise ValueError("volume constraint must be an object")
        _check_range("volume", volume, rule, failures)

    if "extents" in constraints:
        rules = constraints["extents"]
        if not isinstance(rules, Mapping):
            raise ValueError("extents constraint must be an object")
        unknown_axes = sorted(set(rules) - set(AXES))
        if unknown_axes:
            raise ValueError(f"unsupported extent axes: {', '.join(unknown_axes)}")
        for index, axis in enumerate(AXES):
            if axis not in rules:
                continue
            rule = rules[axis]
            if not isinstance(rule, Mapping):
                raise ValueError(f"extent constraint for {axis} must be an object")
            _check_range(f"extent.{axis}", float(extents[index]), rule, failures)

    if "bounds" in constraints:
        rule = constraints["bounds"]
        if not isinstance(rule, Mapping):
            raise ValueError("bounds constraint must be an object")
        unknown_bound_keys = sorted(set(rule) - {"min", "max"})
        if unknown_bound_keys:
            raise ValueError(
                f"unsupported bounds keys: {', '.join(unknown_bound_keys)}"
            )
        for side, row in (("min", bounds[0]), ("max", bounds[1])):
            if side not in rule:
                continue
            expected = np.asarray(rule[side], dtype=float)
            if expected.shape != (3,):
                raise ValueError(f"bounds.{side} must contain exactly three values")
            if side == "min":
                violated = row < expected
                comparator = "below"
            else:
                violated = row > expected
                comparator = "above"
            for index in np.flatnonzero(violated):
                failures.append(
                    f"bounds.{side}.{AXES[index]}={row[index]:.9g} {comparator} "
                    f"allowed {expected[index]:.9g}"
                )

    return VerificationReport(
        passed=not failures,
        failures=tuple(failures),
        measurements=measurements,
    )
