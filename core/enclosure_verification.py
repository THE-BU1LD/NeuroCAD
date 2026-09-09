"""Independent request-level probes for compiled enclosure meshes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import verify_stl
from .enclosure import HARDWARE_PROFILES, MANUFACTURING_PROFILES, CutoutSpec, EnclosureSpec, VentPatternSpec


@dataclass(frozen=True)
class FeatureProbe:
    feature_id: str
    check: str
    passed: bool
    point_mm: tuple[float, float, float]
    expected: str
    observed: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "check": self.check,
            "passed": self.passed,
            "point_mm": list(self.point_mm),
            "expected": self.expected,
            "observed": self.observed,
        }


@dataclass(frozen=True)
class EnclosureMeshVerification:
    valid: bool
    part: str
    topology: dict[str, Any]
    probes: tuple[FeatureProbe, ...]
    method: str = "independent-ray-parity-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "part": self.part,
            "topology": dict(self.topology),
            "probes": [probe.to_dict() for probe in self.probes],
            "method": self.method,
        }


class _MeshOccupancy:
    def __init__(self, mesh: Any):
        triangles = np.asarray(mesh.triangles, dtype=float)
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
            raise ValueError("mesh triangles have an unexpected shape")
        self.v0 = triangles[:, 0]
        self.e1 = triangles[:, 1] - triangles[:, 0]
        self.e2 = triangles[:, 2] - triangles[:, 0]
        direction = np.asarray([1.0, 0.3713906763541037, 0.1732050807568877])
        self.direction = direction / np.linalg.norm(direction)
        self.h = np.cross(np.broadcast_to(self.direction, self.e2.shape), self.e2)
        self.a = np.einsum("ij,ij->i", self.e1, self.h)

    def contains(self, point: tuple[float, float, float]) -> bool:
        epsilon = 1e-9
        valid = np.abs(self.a) > epsilon
        if not np.any(valid):
            return False
        f = np.zeros_like(self.a)
        f[valid] = 1.0 / self.a[valid]
        s = np.asarray(point, dtype=float) - self.v0
        u = f * np.einsum("ij,ij->i", s, self.h)
        q = np.cross(s, self.e1)
        v = f * np.einsum("j,ij->i", self.direction, q)
        t = f * np.einsum("ij,ij->i", self.e2, q)
        hits = np.sort(t[valid & (u >= -epsilon) & (u <= 1 + epsilon) & (v >= -epsilon) & (u + v <= 1 + epsilon) & (t > epsilon)])
        if not hits.size:
            return False
        unique_hits = 1 + int(np.count_nonzero(np.diff(hits) > 1e-7))
        return bool(unique_hits % 2)


def _wall_point(face: str, uv: tuple[float, float], spec: EnclosureSpec) -> tuple[float, float, float]:
    width, depth, height = spec.outer_size_mm
    u, v = uv
    if face == "front":
        return u, -depth / 2 + spec.wall_mm / 2, v
    if face == "rear":
        return u, depth / 2 - spec.wall_mm / 2, v
    if face == "left":
        return -width / 2 + spec.wall_mm / 2, u, v
    if face == "right":
        return width / 2 - spec.wall_mm / 2, u, v
    if face == "bottom":
        floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
        return u, v, -height / 2 + floor / 2
    return u, v, 0.0


def _top_point(uv: tuple[float, float]) -> tuple[float, float, float]:
    return uv[0], uv[1], 0.0


def _probe(
    occupancy: _MeshOccupancy,
    feature_id: str,
    check: str,
    point: tuple[float, float, float],
    expected_inside: bool,
) -> FeatureProbe:
    observed_inside = occupancy.contains(point)
    return FeatureProbe(
        feature_id,
        check,
        observed_inside is expected_inside,
        point,
        "solid" if expected_inside else "void",
        "solid" if observed_inside else "void",
    )


def _cutout_boundary_probe(cutout: CutoutSpec, spec: EnclosureSpec, *, lid: bool) -> tuple[float, float, float]:
    if cutout.kind == "circular":
        offset = float(cutout.diameter_mm or 0.0) / 2 + max(0.35, spec.wall_mm / 3)
        uv = (cutout.center_uv_mm[0] + offset, cutout.center_uv_mm[1])
    else:
        width, _ = cutout.size_mm or (0.0, 0.0)
        uv = (cutout.center_uv_mm[0] + width / 2 + max(0.35, spec.wall_mm / 3), cutout.center_uv_mm[1])
    return _top_point(uv) if lid else _wall_point(cutout.face, uv, spec)


def _vent_centers(vent: VentPatternSpec) -> tuple[tuple[float, float], ...]:
    start_u = vent.center_uv_mm[0] - (vent.columns - 1) * vent.pitch_mm / 2
    start_v = vent.center_uv_mm[1] - (vent.rows - 1) * vent.pitch_mm / 2
    return tuple(
        (start_u + column * vent.pitch_mm, start_v + row * vent.pitch_mm)
        for row in range(vent.rows)
        for column in range(vent.columns)
    )


def _point_in_planar_feature(
    point: tuple[float, float],
    feature: CutoutSpec | VentPatternSpec,
    spec: EnclosureSpec,
    *,
    padding: float = 0.2,
) -> bool:
    compensation = MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
    if isinstance(feature, VentPatternSpec):
        radius = (feature.diameter_mm + compensation) / 2 + padding
        return any((point[0] - u) ** 2 + (point[1] - v) ** 2 <= radius**2 for u, v in _vent_centers(feature))
    if feature.kind == "circular":
        radius = (float(feature.diameter_mm or 0.0) + compensation) / 2 + padding
        return (point[0] - feature.center_uv_mm[0]) ** 2 + (point[1] - feature.center_uv_mm[1]) ** 2 <= radius**2
    width, depth = feature.size_mm or (0.0, 0.0)
    return (
        abs(point[0] - feature.center_uv_mm[0]) <= width / 2 + padding
        and abs(point[1] - feature.center_uv_mm[1]) <= depth / 2 + padding
    )


def _planar_candidates(half_x: float, half_y: float) -> tuple[tuple[float, float], ...]:
    fractions = (0.0, -0.4, 0.4, -0.7, 0.7, -0.9, 0.9)
    return tuple((x_fraction * half_x, y_fraction * half_y) for x_fraction in fractions for y_fraction in fractions)


def _free_body_point(spec: EnclosureSpec, *, floor: bool) -> tuple[float, float, float] | None:
    width, depth, height = spec.outer_size_mm
    floor_height = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
    half_x = width / 2 - spec.wall_mm - 0.25
    half_y = depth / 2 - spec.wall_mm - 0.25
    mounts = [(item.center_xy_mm, item.outer_diameter_mm / 2 + 0.25) for item in spec.standoffs]
    if spec.lid.kind == "screw" and spec.lid.hardware in HARDWARE_PROFILES:
        radius = HARDWARE_PROFILES[spec.lid.hardware].boss_outer_mm / 2 + 0.25
        mounts.extend((position, radius) for position in spec.lid.fastener_positions_xy_mm)
    bottom_features: tuple[CutoutSpec | VentPatternSpec, ...] = (
        tuple(item for item in spec.cutouts if item.face == "bottom")
        + tuple(item for item in spec.vents if item.face == "bottom")
    )
    for candidate in _planar_candidates(half_x, half_y):
        if any(math.dist(candidate, center) <= radius for center, radius in mounts):
            continue
        if floor and any(_point_in_planar_feature(candidate, feature, spec) for feature in bottom_features):
            continue
        z = -height / 2 + floor_height / 2 if floor else (-height / 2 + floor_height + height / 2) / 2
        return candidate[0], candidate[1], z
    return None


def _free_lid_material_point(spec: EnclosureSpec, *, plug: bool = False) -> tuple[float, float, float] | None:
    inset = spec.wall_mm if plug else 0.0
    half_x = spec.outer_size_mm[0] / 2 - spec.lid.clearance_mm - inset - 0.25
    half_y = spec.outer_size_mm[1] / 2 - spec.lid.clearance_mm - inset - 0.25
    features: tuple[CutoutSpec | VentPatternSpec, ...] = (
        tuple(item for item in spec.cutouts if item.face == "top")
        + tuple(item for item in spec.vents if item.face == "top")
    )
    fastener_radius = 0.0
    if spec.lid.kind == "screw" and spec.lid.hardware in HARDWARE_PROFILES:
        hardware = HARDWARE_PROFILES[spec.lid.hardware]
        fastener_radius = (
            hardware.clearance_hole_mm + MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
        ) / 2 + 0.25
        if plug:
            fastener_radius = hardware.boss_outer_mm / 2 + spec.lid.clearance_mm + 0.25
    for candidate in _planar_candidates(half_x, half_y):
        if any(_point_in_planar_feature(candidate, feature, spec) for feature in features):
            continue
        if fastener_radius and any(
            math.dist(candidate, position) <= fastener_radius for position in spec.lid.fastener_positions_xy_mm
        ):
            continue
        z = -(spec.lid.thickness_mm + spec.lid.lip_height_mm) / 2 if plug else 0.0
        return candidate[0], candidate[1], z
    return None


def verify_enclosure_mesh(path: Path, spec: EnclosureSpec, *, part: str) -> EnclosureMeshVerification:
    """Verify final mesh topology and every explicitly requested feature.

    Ray-parity probes are independent of the generating IR.  They verify the
    material/void state at feature centers and adjacent material.  They are a
    bounded feature oracle, not a proof of arbitrary surface equivalence.
    """

    if part not in {"body", "lid"}:
        raise ValueError("part must be body or lid")
    if part == "lid" and spec.lid.kind == "none":
        raise ValueError("specification does not contain a lid")
    if part == "body":
        expected_extents = list(spec.outer_size_mm)
    else:
        expected_extents = [
            spec.outer_size_mm[0] - 2 * spec.lid.clearance_mm,
            spec.outer_size_mm[1] - 2 * spec.lid.clearance_mm,
            spec.lid.thickness_mm + spec.lid.lip_height_mm,
        ]
    topology = verify_stl(path, expected_extents_mm=expected_extents)
    import trimesh

    mesh = trimesh.load_mesh(path, force="mesh", process=True)
    occupancy = _MeshOccupancy(mesh)
    probes: list[FeatureProbe] = []
    if part == "body":
        floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
        floor_point = _free_body_point(spec, floor=True)
        cavity_point = _free_body_point(spec, floor=False)
        if floor_point is not None:
            probes.append(_probe(occupancy, "body", "floor material", floor_point, True))
        if cavity_point is not None:
            probes.append(_probe(occupancy, "body", "interior cavity", cavity_point, False))
            probes.append(
                _probe(
                    occupancy,
                    "body",
                    "open top",
                    (cavity_point[0], cavity_point[1], spec.outer_size_mm[2] / 2 - 0.1),
                    False,
                )
            )
        for cutout in (item for item in spec.cutouts if item.face != "top"):
            center = _wall_point(cutout.face, cutout.center_uv_mm, spec)
            probes.append(_probe(occupancy, cutout.id, "cutout center", center, False))
            probes.append(_probe(occupancy, cutout.id, "adjacent wall", _cutout_boundary_probe(cutout, spec, lid=False), True))
        for vent in (item for item in spec.vents if item.face != "top"):
            for index, center_uv in enumerate(_vent_centers(vent), start=1):
                probes.append(
                    _probe(occupancy, vent.id, f"vent center {index}", _wall_point(vent.face, center_uv, spec), False)
                )
        for standoff in spec.standoffs:
            z = -spec.outer_size_mm[2] / 2 + floor + standoff.height_mm / 2
            hole = (standoff.center_xy_mm[0], standoff.center_xy_mm[1], z)
            ring = (standoff.center_xy_mm[0] + (standoff.hole_diameter_mm + standoff.outer_diameter_mm) / 4, standoff.center_xy_mm[1], z)
            probes.append(_probe(occupancy, standoff.id, "standoff bore", hole, False))
            probes.append(_probe(occupancy, standoff.id, "standoff ligament", ring, True))
    else:
        for cutout in (item for item in spec.cutouts if item.face == "top"):
            probes.append(_probe(occupancy, cutout.id, "lid cutout center", _top_point(cutout.center_uv_mm), False))
            probes.append(_probe(occupancy, cutout.id, "adjacent lid", _cutout_boundary_probe(cutout, spec, lid=True), True))
        for vent in (item for item in spec.vents if item.face == "top"):
            for index, center_uv in enumerate(_vent_centers(vent), start=1):
                probes.append(_probe(occupancy, vent.id, f"lid vent center {index}", _top_point(center_uv), False))
        if spec.lid.kind == "screw":
            for index, position in enumerate(spec.lid.fastener_positions_xy_mm, start=1):
                probes.append(_probe(occupancy, f"lid_fastener_{index}", "lid fastener bore", _top_point(position), False))
                if spec.lid.lip_height_mm > 0:
                    if spec.lid.hardware is None:
                        raise ValueError("screw lid verification requires a hardware profile")
                    hardware = HARDWARE_PROFILES[spec.lid.hardware]
                    hole_diameter = hardware.clearance_hole_mm + MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
                    ring_radius = (hole_diameter + hardware.boss_outer_mm) / 4
                    z = -(spec.lid.thickness_mm + spec.lid.lip_height_mm) / 2
                    for side, (dx, dy) in enumerate(((ring_radius, 0), (-ring_radius, 0), (0, ring_radius), (0, -ring_radius))):
                        probes.append(_probe(
                            occupancy, f"lid_boss_relief_{index}", f"boss ring clearance {side + 1}",
                            (position[0] + dx, position[1] + dy, z), False,
                        ))
        material_point = _free_lid_material_point(spec)
        if material_point is not None:
            probes.append(_probe(occupancy, "lid", "lid material", material_point, True))
        if spec.lid.lip_height_mm > 0:
            plug_point = _free_lid_material_point(spec, plug=True)
            if plug_point is not None:
                probes.append(_probe(occupancy, "lid", "insertion plug material", plug_point, True))
            z = -(spec.lid.thickness_mm + spec.lid.lip_height_mm) / 2
            shoulder_x = spec.outer_size_mm[0] / 2 - spec.lid.clearance_mm - spec.wall_mm / 2
            shoulder_y = spec.outer_size_mm[1] / 2 - spec.lid.clearance_mm - spec.wall_mm / 2
            for index, point in enumerate(((shoulder_x, 0, z), (-shoulder_x, 0, z), (0, shoulder_y, z), (0, -shoulder_y, z))):
                probes.append(_probe(occupancy, "lid", f"insertion shoulder clearance {index + 1}", point, False))
        # Off-axis corner probes distinguish a rounded lid/plug from the former
        # rectangular solids with identical extents and manifold topology.
        for plug in (False, True):
            if plug and spec.lid.lip_height_mm <= 0:
                continue
            inset = spec.lid.clearance_mm + (spec.wall_mm if plug else 0.0)
            radius = max(0.0, spec.corner_radius_mm - inset)
            if radius <= 0:
                continue
            x = spec.outer_size_mm[0] / 2 - spec.corner_radius_mm + 0.9 * radius
            y = spec.outer_size_mm[1] / 2 - spec.corner_radius_mm + 0.9 * radius
            z = -(spec.lid.thickness_mm + spec.lid.lip_height_mm) / 2 if plug else 0.0
            for index, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)), start=1):
                probes.append(_probe(
                    occupancy, "lid_lip" if plug else "lid_plate", f"rounded corner clearance {index}",
                    (sx * x, sy * y, z), False,
                ))
    return EnclosureMeshVerification(all(probe.passed for probe in probes), part, topology, tuple(probes))
