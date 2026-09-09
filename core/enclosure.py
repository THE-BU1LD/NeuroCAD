"""Typed, deterministic electronics-enclosure design support.

This module deliberately starts from an explicit engineering specification.  A
natural-language model may propose such a specification, but it cannot bypass
the validation performed here or emit geometry directly.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, TypeGuard, cast

from .ir import MAX_NODES, CADProgram, Constraint, Node, Primitive, Transform, validate_program

SPEC_VERSION = "neurocad-enclosure-v1"
MIN_DIMENSION_MM = 0.1
MAX_DIMENSION_MM = 100_000.0
FACES = {"front", "rear", "left", "right", "bottom", "top"}
CUTOUT_KINDS = {"rectangular", "circular"}
LID_KINDS = {"none", "screw", "friction"}
FEATURE_ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")


@dataclass(frozen=True)
class ManufacturingProfile:
    """Named, disclosed fabrication assumptions rather than hidden defaults."""

    name: str
    minimum_wall_mm: float
    press_clearance_mm: float
    hole_compensation_mm: float
    minimum_ligament_mm: float


MANUFACTURING_PROFILES: dict[str, ManufacturingProfile] = {
    "fdm_draft": ManufacturingProfile("fdm_draft", 1.6, 0.15, 0.30, 1.2),
    "fdm_standard": ManufacturingProfile("fdm_standard", 1.2, 0.10, 0.20, 1.0),
    "fdm_precision": ManufacturingProfile("fdm_precision", 1.0, 0.05, 0.10, 0.8),
    "resin_standard": ManufacturingProfile("resin_standard", 0.8, 0.05, 0.08, 0.7),
}


@dataclass(frozen=True)
class HardwareProfile:
    name: str
    nominal_thread_mm: float
    clearance_hole_mm: float
    pilot_hole_mm: float
    boss_outer_mm: float
    heat_set_insert_diameter_mm: float
    heat_set_insert_depth_mm: float


HARDWARE_PROFILES: dict[str, HardwareProfile] = {
    "M2": HardwareProfile("M2", 2.0, 2.4, 1.6, 5.5, 3.2, 4.0),
    "M2.5": HardwareProfile("M2.5", 2.5, 2.9, 2.0, 6.5, 4.0, 5.0),
    "M3": HardwareProfile("M3", 3.0, 3.4, 2.5, 7.5, 4.6, 5.8),
    "M4": HardwareProfile("M4", 4.0, 4.5, 3.3, 9.5, 6.0, 7.0),
}


@dataclass(frozen=True)
class CutoutSpec:
    id: str
    kind: str
    face: str
    center_uv_mm: tuple[float, float]
    size_mm: tuple[float, float] | None = None
    diameter_mm: float | None = None
    corner_radius_mm: float = 0.0
    purpose: str = "generic"


@dataclass(frozen=True)
class StandoffSpec:
    id: str
    center_xy_mm: tuple[float, float]
    height_mm: float
    outer_diameter_mm: float
    hole_diameter_mm: float
    hardware: str | None = None


@dataclass(frozen=True)
class VentPatternSpec:
    id: str
    face: str
    center_uv_mm: tuple[float, float]
    rows: int
    columns: int
    diameter_mm: float
    pitch_mm: float


@dataclass(frozen=True)
class LidSpec:
    kind: str
    thickness_mm: float
    clearance_mm: float
    lip_height_mm: float = 0.0
    hardware: str | None = None
    fastener_positions_xy_mm: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class PCBSpec:
    size_mm: tuple[float, float, float]
    origin_xy_mm: tuple[float, float] = (0.0, 0.0)
    mounting_holes_xy_mm: tuple[tuple[float, float], ...] = ()
    component_height_mm: float = 0.0


@dataclass(frozen=True)
class EnclosureSpec:
    outer_size_mm: tuple[float, float, float]
    wall_mm: float
    profile: str
    lid: LidSpec
    corner_radius_mm: float = 0.0
    floor_mm: float | None = None
    cutouts: tuple[CutoutSpec, ...] = ()
    standoffs: tuple[StandoffSpec, ...] = ()
    vents: tuple[VentPatternSpec, ...] = ()
    pcb: PCBSpec | None = None
    title: str = "electronics enclosure"
    units: str = "mm"
    version: str = SPEC_VERSION


@dataclass(frozen=True)
class SpecIssue:
    severity: str
    path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class SpecValidationReport:
    issues: tuple[SpecIssue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[SpecIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[SpecIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "issues": [issue.to_dict() for issue in self.issues]}


@dataclass(frozen=True)
class EnclosureBuild:
    spec: EnclosureSpec
    body: CADProgram
    lid: CADProgram | None
    validation: SpecValidationReport

    @property
    def parts(self) -> dict[str, CADProgram]:
        result = {"body": self.body}
        if self.lid is not None:
            result["lid"] = self.lid
        return result


def _finite(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _length_issue(value: object, path: str, issues: list[SpecIssue], *, allow_zero: bool = False) -> float | None:
    if not _finite(value):
        issues.append(SpecIssue("error", path, "invalid_length", "must be a finite millimetre value"))
        return None
    result = float(value)
    minimum = 0.0 if allow_zero else MIN_DIMENSION_MM
    if result < minimum or result > MAX_DIMENSION_MM:
        issues.append(
            SpecIssue(
                "error",
                path,
                "length_out_of_range",
                f"must be between {minimum:g} and {MAX_DIMENSION_MM:g} mm",
            )
        )
        return None
    return result


def _inside_face(
    face: str,
    center: tuple[float, float],
    half_u: float,
    half_v: float,
    spec: EnclosureSpec,
    margin: float,
) -> bool:
    width, depth, height = spec.outer_size_mm
    face_u = width if face in {"front", "rear", "top", "bottom"} else depth
    face_v = height if face in {"front", "rear", "left", "right"} else depth
    return abs(center[0]) + half_u + margin < face_u / 2 and abs(center[1]) + half_v + margin < face_v / 2


def _rect_for_feature(
    feature: CutoutSpec | VentPatternSpec,
    *,
    hole_compensation_mm: float = 0.0,
) -> tuple[float, float, float, float]:
    if isinstance(feature, VentPatternSpec):
        diameter = feature.diameter_mm + hole_compensation_mm
        width = (feature.columns - 1) * feature.pitch_mm + diameter
        height = (feature.rows - 1) * feature.pitch_mm + diameter
        return feature.center_uv_mm[0], feature.center_uv_mm[1], width / 2, height / 2
    if feature.kind == "circular":
        radius = (float(feature.diameter_mm or 0.0) + hole_compensation_mm) / 2
        return feature.center_uv_mm[0], feature.center_uv_mm[1], radius, radius
    width, height = feature.size_mm or (0.0, 0.0)
    return feature.center_uv_mm[0], feature.center_uv_mm[1], width / 2, height / 2


def _valid_feature_id(identifier: object) -> bool:
    return isinstance(identifier, str) and FEATURE_ID_PATTERN.fullmatch(identifier) is not None


def _generated_ids_and_counts(spec: EnclosureSpec) -> tuple[list[str], int, int]:
    """Return every generated node id plus exact body/lid node counts."""

    body_ids = ["body_outer", "body_cavity", "body_shell"]
    lid_ids = ["lid_plate"] if spec.lid.kind != "none" else []
    if spec.lid.kind != "none" and spec.lid.lip_height_mm > 0:
        lid_ids.extend(("lid_lip", "lid_positive"))
    for cutout in spec.cutouts:
        (lid_ids if cutout.face == "top" else body_ids).append(cutout.id)
    for vent in spec.vents:
        target = lid_ids if vent.face == "top" else body_ids
        if (
            isinstance(vent.rows, int)
            and not isinstance(vent.rows, bool)
            and 1 <= vent.rows <= 64
            and isinstance(vent.columns, int)
            and not isinstance(vent.columns, bool)
            and 1 <= vent.columns <= 64
        ):
            for row in range(vent.rows):
                for column in range(vent.columns):
                    target.append(f"{vent.id}_{row + 1}_{column + 1}")
    body_mount_ids: list[str] = []
    for standoff in spec.standoffs:
        body_mount_ids.extend((f"{standoff.id}_outer", f"{standoff.id}_hole"))
    if spec.lid.kind == "screw" and isinstance(spec.lid.fastener_positions_xy_mm, tuple):
        for index, _ in enumerate(spec.lid.fastener_positions_xy_mm, start=1):
            body_mount_ids.extend((f"lid_boss_{index}_outer", f"lid_boss_{index}_hole"))
            lid_ids.append(f"lid_fastener_{index}")
            if spec.lid.lip_height_mm > 0:
                lid_ids.append(f"lid_boss_relief_{index}")
    body_ids.extend(body_mount_ids)
    if body_mount_ids:
        body_ids.extend(("body_positive", "body_complete"))
    if spec.lid.kind != "none" and any(
        (
            any(cutout.face == "top" for cutout in spec.cutouts),
            any(vent.face == "top" for vent in spec.vents),
            spec.lid.kind == "screw" and bool(spec.lid.fastener_positions_xy_mm),
        )
    ):
        lid_ids.append("lid_complete")
    return body_ids + lid_ids, len(body_ids), len(lid_ids)


def validate_enclosure_spec(spec: EnclosureSpec) -> SpecValidationReport:
    if not isinstance(spec, EnclosureSpec):
        raise TypeError("spec must be an EnclosureSpec")
    issues: list[SpecIssue] = []
    for name, collection in (("cutouts", spec.cutouts), ("standoffs", spec.standoffs), ("vents", spec.vents)):
        if not isinstance(collection, tuple):
            issues.append(SpecIssue("error", f"$.{name}", "invalid_collection", "must be an immutable tuple"))
        elif len(collection) > 256:
            issues.append(SpecIssue("error", f"$.{name}", "resource_limit", "at most 256 feature records are supported"))
    if any(issue.code == "invalid_collection" for issue in issues):
        return SpecValidationReport(tuple(issues))
    if spec.version != SPEC_VERSION:
        issues.append(SpecIssue("error", "$.version", "unsupported_version", f"expected {SPEC_VERSION}"))
    if spec.units != "mm":
        issues.append(SpecIssue("error", "$.units", "unsupported_units", "canonical specifications use mm"))
    if (
        not isinstance(spec.title, str)
        or not spec.title.strip()
        or len(spec.title) > 256
        or any(ord(character) < 32 for character in spec.title)
    ):
        issues.append(SpecIssue("error", "$.title", "invalid_title", "title must contain 1 to 256 characters"))
    if not isinstance(spec.profile, str) or spec.profile not in MANUFACTURING_PROFILES:
        issues.append(SpecIssue("error", "$.profile", "unknown_profile", "select a named manufacturing profile"))
        profile = None
    else:
        profile = MANUFACTURING_PROFILES[spec.profile]

    if not isinstance(spec.outer_size_mm, tuple) or len(spec.outer_size_mm) != 3:
        issues.append(SpecIssue("error", "$.outer_size_mm", "invalid_size", "must contain width, depth, and height"))
        dimensions = None
    else:
        parsed = [
            _length_issue(value, f"$.outer_size_mm[{index}]", issues)
            for index, value in enumerate(spec.outer_size_mm)
        ]
        dimensions = (
            cast(tuple[float, float, float], (parsed[0], parsed[1], parsed[2]))
            if all(value is not None for value in parsed)
            else None
        )
    wall = _length_issue(spec.wall_mm, "$.wall_mm", issues)
    floor = _length_issue(spec.floor_mm if spec.floor_mm is not None else spec.wall_mm, "$.floor_mm", issues)
    radius = _length_issue(spec.corner_radius_mm, "$.corner_radius_mm", issues, allow_zero=True)
    if profile is not None and wall is not None and wall < profile.minimum_wall_mm:
        issues.append(
            SpecIssue(
                "error",
                "$.wall_mm",
                "below_profile_minimum",
                f"{spec.profile} requires at least {profile.minimum_wall_mm:g} mm walls",
            )
        )
    if dimensions is not None and wall is not None and floor is not None:
        width, depth, height = dimensions
        if 2 * wall >= min(width, depth) or floor >= height:
            issues.append(SpecIssue("error", "$", "empty_cavity", "wall/floor dimensions leave no interior cavity"))
        if radius is not None and radius > min(width, depth) / 2:
            issues.append(SpecIssue("error", "$.corner_radius_mm", "invalid_radius", "exceeds half the planar size"))

    lid = spec.lid
    if not isinstance(lid, LidSpec):
        issues.append(SpecIssue("error", "$.lid", "invalid_lid", "must be a LidSpec"))
        return SpecValidationReport(tuple(issues))
    if lid.kind == "slide":
        issues.append(
            SpecIssue(
                "error",
                "$.lid.kind",
                "unimplemented_lid",
                "slide rails and capture geometry are not implemented; use none, screw, or friction",
            )
        )
    elif lid.kind not in LID_KINDS:
        issues.append(SpecIssue("error", "$.lid.kind", "unknown_lid", "unsupported lid kind"))
    _length_issue(lid.thickness_mm, "$.lid.thickness_mm", issues, allow_zero=lid.kind == "none")
    clearance = _length_issue(lid.clearance_mm, "$.lid.clearance_mm", issues, allow_zero=True)
    lip_height = _length_issue(lid.lip_height_mm, "$.lid.lip_height_mm", issues, allow_zero=True)
    if dimensions is not None and floor is not None and lip_height is not None and lid.kind != "none" and lip_height >= dimensions[2] - floor:
        issues.append(SpecIssue(
            "error", "$.lid.lip_height_mm", "lip_reaches_floor",
            f"insertion plug height {lip_height:g} mm must be below the {dimensions[2] - floor:g} mm cavity depth",
        ))
    if lid.kind == "none" and (
        lid.thickness_mm != 0
        or lid.clearance_mm != 0
        or lid.lip_height_mm != 0
        or lid.hardware is not None
        or lid.fastener_positions_xy_mm
    ):
        issues.append(SpecIssue("error", "$.lid", "inconsistent_lid", "a lid of kind none cannot have geometry"))
    if lid.kind == "none" and (any(item.face == "top" for item in spec.cutouts) or any(item.face == "top" for item in spec.vents)):
        issues.append(SpecIssue("error", "$.lid", "top_feature_without_lid", "top features require a generated lid part"))
    if lid.kind == "friction":
        if not clearance:
            issues.append(SpecIssue("error", "$.lid.clearance_mm", "missing_clearance", "friction lids require positive clearance"))
        if lid.lip_height_mm <= 0:
            issues.append(SpecIssue("error", "$.lid.lip_height_mm", "missing_lip", "friction lids require a positive insertion plug height"))
        if lid.hardware is not None or lid.fastener_positions_xy_mm:
            issues.append(SpecIssue("error", "$.lid", "inconsistent_lid", "friction lids cannot declare screw hardware"))
        if profile is not None and clearance is not None and clearance < profile.press_clearance_mm:
            issues.append(
                SpecIssue(
                    "error",
                    "$.lid.clearance_mm",
                    "below_profile_clearance",
                    f"{spec.profile} requires at least {profile.press_clearance_mm:g} mm friction-fit clearance",
                )
            )
    if dimensions is not None and clearance is not None and lid.kind != "none":
        plate_width = dimensions[0] - 2 * clearance
        plate_depth = dimensions[1] - 2 * clearance
        if plate_width < MIN_DIMENSION_MM or plate_depth < MIN_DIMENSION_MM:
            issues.append(SpecIssue("error", "$.lid.clearance_mm", "invalid_lid_size", "clearance leaves no lid plate"))
        if lid.lip_height_mm > 0 and (
            dimensions[0] - 2 * (spec.wall_mm + clearance) < MIN_DIMENSION_MM
            or dimensions[1] - 2 * (spec.wall_mm + clearance) < MIN_DIMENSION_MM
        ):
            issues.append(SpecIssue("error", "$.lid", "invalid_lip_size", "wall and clearance leave no insertion plug"))
    if lid.kind == "screw":
        if not isinstance(lid.hardware, str) or lid.hardware not in HARDWARE_PROFILES:
            issues.append(SpecIssue("error", "$.lid.hardware", "unknown_hardware", "screw lids require a known hardware profile"))
        if not isinstance(lid.fastener_positions_xy_mm, tuple):
            issues.append(SpecIssue("error", "$.lid.fastener_positions_xy_mm", "invalid_positions", "must be an immutable tuple"))
        elif not lid.fastener_positions_xy_mm:
            issues.append(SpecIssue("error", "$.lid.fastener_positions_xy_mm", "missing_fasteners", "screw lids require explicit fastener positions"))
        elif len(lid.fastener_positions_xy_mm) > 64:
            issues.append(SpecIssue("error", "$.lid.fastener_positions_xy_mm", "too_many_fasteners", "at most 64 fasteners are supported"))
        elif dimensions is not None and lid.hardware in HARDWARE_PROFILES:
            hardware = HARDWARE_PROFILES[lid.hardware]
            floor_value = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
            if dimensions[2] - floor_value - 0.5 < MIN_DIMENSION_MM:
                issues.append(SpecIssue("error", "$.lid", "insufficient_boss_height", "interior height is too small for lid bosses"))
            for index, position in enumerate(lid.fastener_positions_xy_mm):
                path = f"$.lid.fastener_positions_xy_mm[{index}]"
                if len(position) != 2 or not all(_finite(value) for value in position):
                    issues.append(SpecIssue("error", path, "invalid_position", "must contain two finite values"))
                    continue
                if (
                    abs(position[0]) + hardware.boss_outer_mm / 2 >= dimensions[0] / 2 - spec.wall_mm
                    or abs(position[1]) + hardware.boss_outer_mm / 2 >= dimensions[1] / 2 - spec.wall_mm
                ):
                    issues.append(SpecIssue("error", path, "fastener_outside", "fastener boss does not fit inside the cavity"))

    ids: set[str] = set()
    face_features: dict[str, list[CutoutSpec | VentPatternSpec]] = {face: [] for face in FACES}
    for index, cutout in enumerate(spec.cutouts):
        path = f"$.cutouts[{index}]"
        if not isinstance(cutout, CutoutSpec):
            issues.append(SpecIssue("error", path, "invalid_feature", "must be a CutoutSpec"))
            continue
        if not _valid_feature_id(cutout.id):
            issues.append(
                SpecIssue(
                    "error",
                    f"{path}.id",
                    "invalid_id",
                    "feature ids must start with a letter and contain at most 64 letters, digits, underscores, or hyphens",
                )
            )
        elif cutout.id in ids:
            issues.append(SpecIssue("error", f"{path}.id", "duplicate_id", "feature ids must be unique"))
        if isinstance(cutout.id, str):
            ids.add(cutout.id)
        if cutout.kind not in CUTOUT_KINDS:
            issues.append(SpecIssue("error", f"{path}.kind", "unknown_cutout", "unsupported cutout kind"))
        if cutout.face not in FACES:
            issues.append(SpecIssue("error", f"{path}.face", "unknown_face", "use a named enclosure face"))
            continue
        if not isinstance(cutout.center_uv_mm, tuple) or len(cutout.center_uv_mm) != 2 or not all(_finite(value) for value in cutout.center_uv_mm):
            issues.append(SpecIssue("error", f"{path}.center_uv_mm", "invalid_position", "must contain two finite values"))
            continue
        if cutout.kind == "rectangular":
            if cutout.size_mm is None or len(cutout.size_mm) != 2:
                issues.append(SpecIssue("error", f"{path}.size_mm", "missing_size", "rectangular cutouts require width and height"))
                continue
            values = [_length_issue(value, f"{path}.size_mm[{axis}]", issues) for axis, value in enumerate(cutout.size_mm)]
            if any(value is None for value in values):
                continue
            half_u, half_v = float(values[0]) / 2, float(values[1]) / 2  # type: ignore[arg-type]
            corner_radius = _length_issue(cutout.corner_radius_mm, f"{path}.corner_radius_mm", issues, allow_zero=True)
            if corner_radius is not None and corner_radius > min(half_u, half_v):
                issues.append(SpecIssue("error", f"{path}.corner_radius_mm", "invalid_radius", "exceeds half the cutout size"))
            if corner_radius and cutout.face in {"front", "rear", "left", "right"}:
                issues.append(
                    SpecIssue(
                        "error",
                        f"{path}.corner_radius_mm",
                        "unsupported_side_radius",
                        "rounded rectangular cutouts are currently supported only on top and bottom faces",
                    )
                )
            if cutout.diameter_mm is not None:
                issues.append(SpecIssue("error", f"{path}.diameter_mm", "conflicting_size", "rectangular cutouts do not accept diameter"))
        else:
            diameter = _length_issue(cutout.diameter_mm, f"{path}.diameter_mm", issues)
            if diameter is None:
                continue
            compensated_diameter = diameter + (profile.hole_compensation_mm if profile is not None else 0.0)
            half_u = half_v = compensated_diameter / 2
            if cutout.corner_radius_mm != 0:
                issues.append(SpecIssue("error", f"{path}.corner_radius_mm", "conflicting_radius", "circular cutouts do not accept corner radius"))
            if cutout.size_mm is not None:
                issues.append(SpecIssue("error", f"{path}.size_mm", "conflicting_size", "circular cutouts do not accept size"))
        edge_margin = profile.minimum_ligament_mm if profile is not None else 0.0
        if dimensions is not None and not _inside_face(
            cutout.face,
            cutout.center_uv_mm,
            half_u,
            half_v,
            spec,
            edge_margin,
        ):
            issues.append(SpecIssue("error", path, "edge_clearance", "cutout violates the profile edge margin"))
        face_features[cutout.face].append(cutout)

    for index, vent in enumerate(spec.vents):
        path = f"$.vents[{index}]"
        if not isinstance(vent, VentPatternSpec):
            issues.append(SpecIssue("error", path, "invalid_feature", "must be a VentPatternSpec"))
            continue
        if not _valid_feature_id(vent.id):
            issues.append(
                SpecIssue(
                    "error",
                    f"{path}.id",
                    "invalid_id",
                    "feature ids must start with a letter and contain at most 64 letters, digits, underscores, or hyphens",
                )
            )
        elif vent.id in ids:
            issues.append(SpecIssue("error", f"{path}.id", "duplicate_id", "feature ids must be unique"))
        if isinstance(vent.id, str):
            ids.add(vent.id)
        if vent.face not in FACES:
            issues.append(SpecIssue("error", f"{path}.face", "unknown_face", "use a named enclosure face"))
            continue
        if not isinstance(vent.center_uv_mm, tuple) or len(vent.center_uv_mm) != 2 or not all(_finite(value) for value in vent.center_uv_mm):
            issues.append(SpecIssue("error", f"{path}.center_uv_mm", "invalid_position", "must contain two finite values"))
            continue
        if isinstance(vent.rows, bool) or not isinstance(vent.rows, int) or not 1 <= vent.rows <= 64:
            issues.append(SpecIssue("error", f"{path}.rows", "invalid_count", "rows must be an integer from 1 to 64"))
        if isinstance(vent.columns, bool) or not isinstance(vent.columns, int) or not 1 <= vent.columns <= 64:
            issues.append(SpecIssue("error", f"{path}.columns", "invalid_count", "columns must be an integer from 1 to 64"))
        diameter = _length_issue(vent.diameter_mm, f"{path}.diameter_mm", issues)
        pitch = _length_issue(vent.pitch_mm, f"{path}.pitch_mm", issues)
        modeled_diameter = diameter + (profile.hole_compensation_mm if profile is not None and diameter is not None else 0.0) if diameter is not None else None
        if modeled_diameter is not None and pitch is not None and pitch <= modeled_diameter:
            issues.append(
                SpecIssue(
                    "error",
                    f"{path}.pitch_mm",
                    "overlapping_vents",
                    "pitch must exceed the manufacturing-compensated vent diameter",
                )
            )
        if (
            dimensions is not None
            and profile is not None
            and diameter is not None
            and pitch is not None
            and isinstance(vent.rows, int)
            and not isinstance(vent.rows, bool)
            and isinstance(vent.columns, int)
            and not isinstance(vent.columns, bool)
            and vent.rows > 0
            and vent.columns > 0
        ):
            compensated_diameter = diameter + profile.hole_compensation_mm
            half_u = ((vent.columns - 1) * pitch + compensated_diameter) / 2
            half_v = ((vent.rows - 1) * pitch + compensated_diameter) / 2
            if not _inside_face(
                vent.face,
                vent.center_uv_mm,
                half_u,
                half_v,
                spec,
                profile.minimum_ligament_mm,
            ):
                issues.append(SpecIssue("error", path, "edge_clearance", "vent grid violates the profile edge margin"))
        face_features[vent.face].append(vent)

    for face, features in face_features.items():
        for left_index, left in enumerate(features):
            lx, ly, lhw, lhh = _rect_for_feature(
                left,
                hole_compensation_mm=profile.hole_compensation_mm if profile is not None else 0.0,
            )
            for right in features[left_index + 1 :]:
                rx, ry, rhw, rhh = _rect_for_feature(
                    right,
                    hole_compensation_mm=profile.hole_compensation_mm if profile is not None else 0.0,
                )
                if abs(lx - rx) <= lhw + rhw and abs(ly - ry) <= lhh + rhh:
                    issues.append(
                        SpecIssue(
                            "error",
                            f"$.faces.{face}",
                            "feature_overlap",
                            f"features {left.id!r} and {right.id!r} overlap",
                        )
                    )

    if dimensions is not None and wall is not None and floor is not None:
        width, depth, height = dimensions
        cavity_width, cavity_depth = width - 2 * wall, depth - 2 * wall
        validated_standoffs: list[tuple[StandoffSpec, float]] = []
        for index, standoff in enumerate(spec.standoffs):
            path = f"$.standoffs[{index}]"
            if not isinstance(standoff, StandoffSpec):
                issues.append(SpecIssue("error", path, "invalid_feature", "must be a StandoffSpec"))
                continue
            if not _valid_feature_id(standoff.id):
                issues.append(
                    SpecIssue(
                        "error",
                        f"{path}.id",
                        "invalid_id",
                        "feature ids must start with a letter and contain at most 64 letters, digits, underscores, or hyphens",
                    )
                )
            elif standoff.id in ids:
                issues.append(SpecIssue("error", f"{path}.id", "duplicate_id", "feature ids must be unique"))
            if isinstance(standoff.id, str):
                ids.add(standoff.id)
            if not isinstance(standoff.center_xy_mm, tuple) or len(standoff.center_xy_mm) != 2 or not all(_finite(value) for value in standoff.center_xy_mm):
                issues.append(SpecIssue("error", f"{path}.center_xy_mm", "invalid_position", "must contain two finite values"))
                continue
            standoff_height = _length_issue(standoff.height_mm, f"{path}.height_mm", issues)
            outer = _length_issue(standoff.outer_diameter_mm, f"{path}.outer_diameter_mm", issues)
            hole = _length_issue(standoff.hole_diameter_mm, f"{path}.hole_diameter_mm", issues)
            compensated_hole = hole + (profile.hole_compensation_mm if profile is not None and hole is not None else 0.0) if hole is not None else None
            if outer is not None and compensated_hole is not None and compensated_hole >= outer:
                issues.append(SpecIssue("error", path, "invalid_standoff", "hole diameter must be smaller than outer diameter"))
            if standoff_height is not None and standoff_height + floor >= height:
                issues.append(SpecIssue("error", path, "standoff_too_tall", "standoff exceeds the enclosure interior"))
            elif standoff_height is not None and lip_height is not None and lip_height > 0 and standoff_height + floor >= height - lip_height:
                issues.append(SpecIssue(
                    "error", path, "standoff_lip_collision",
                    f"standoff top at {standoff_height + floor:g} mm reaches the insertion plug envelope starting at {height - lip_height:g} mm above the base",
                ))
            if outer is not None and (
                abs(standoff.center_xy_mm[0]) + outer / 2 >= cavity_width / 2
                or abs(standoff.center_xy_mm[1]) + outer / 2 >= cavity_depth / 2
            ):
                issues.append(SpecIssue("error", path, "standoff_outside", "standoff does not fit inside the cavity"))
            if standoff.hardware is not None and (
                not isinstance(standoff.hardware, str) or standoff.hardware not in HARDWARE_PROFILES
            ):
                issues.append(SpecIssue("error", f"{path}.hardware", "unknown_hardware", "unknown hardware profile"))
            if outer is not None:
                validated_standoffs.append((standoff, outer))

        required_spacing = profile.minimum_ligament_mm if profile is not None else 0.0
        for left_index, (left_standoff, left_outer) in enumerate(validated_standoffs):
            for right_standoff, right_outer in validated_standoffs[left_index + 1 :]:
                distance = math.dist(left_standoff.center_xy_mm, right_standoff.center_xy_mm)
                if distance < (left_outer + right_outer) / 2 + required_spacing:
                    issues.append(
                        SpecIssue(
                            "error",
                            "$.standoffs",
                            "standoff_overlap",
                            f"standoffs {left_standoff.id!r} and {right_standoff.id!r} overlap or violate the profile ligament",
                        )
                    )

        if spec.pcb is not None:
            pcb = spec.pcb
            if not isinstance(pcb, PCBSpec):
                issues.append(SpecIssue("error", "$.pcb", "invalid_pcb", "must be a PCBSpec"))
                return SpecValidationReport(tuple(issues))
            if not isinstance(pcb.size_mm, tuple) or len(pcb.size_mm) != 3:
                issues.append(SpecIssue("error", "$.pcb.size_mm", "invalid_pcb", "PCB size must contain three positive values"))
                pcb_size = None
            else:
                pcb_values = [_length_issue(value, f"$.pcb.size_mm[{index}]", issues) for index, value in enumerate(pcb.size_mm)]
                pcb_size = (
                    cast(
                        tuple[float, float, float],
                        tuple(float(cast(float, value)) for value in pcb_values),
                    )
                    if all(value is not None for value in pcb_values)
                    else None
                )
            if not isinstance(pcb.origin_xy_mm, tuple) or len(pcb.origin_xy_mm) != 2 or not all(_finite(value) for value in pcb.origin_xy_mm):
                issues.append(SpecIssue("error", "$.pcb.origin_xy_mm", "invalid_position", "must contain two finite values"))
                pcb_origin = None
            else:
                pcb_origin = (float(pcb.origin_xy_mm[0]), float(pcb.origin_xy_mm[1]))
            component_height = _length_issue(pcb.component_height_mm, "$.pcb.component_height_mm", issues, allow_zero=True)
            if pcb_size is not None and pcb_origin is not None:
                if (
                    abs(pcb_origin[0]) + pcb_size[0] / 2 > cavity_width / 2
                    or abs(pcb_origin[1]) + pcb_size[1] / 2 > cavity_depth / 2
                ):
                    issues.append(SpecIssue("error", "$.pcb", "pcb_does_not_fit", "translated PCB exceeds the enclosure cavity"))
                holes_seen: set[tuple[float, float]] = set()
                if not isinstance(pcb.mounting_holes_xy_mm, tuple) or len(pcb.mounting_holes_xy_mm) > 256:
                    issues.append(SpecIssue("error", "$.pcb.mounting_holes_xy_mm", "invalid_mounting_holes", "must be a tuple of at most 256 positions"))
                else:
                    for index, hole_position in enumerate(pcb.mounting_holes_xy_mm):
                        path = f"$.pcb.mounting_holes_xy_mm[{index}]"
                        if not isinstance(hole_position, tuple) or len(hole_position) != 2 or not all(_finite(value) for value in hole_position):
                            issues.append(SpecIssue("error", path, "invalid_position", "must contain two finite values"))
                            continue
                        local = (float(hole_position[0]), float(hole_position[1]))
                        if local in holes_seen:
                            issues.append(SpecIssue("error", path, "duplicate_mounting_hole", "mounting-hole positions must be unique"))
                        holes_seen.add(local)
                        if abs(local[0]) > pcb_size[0] / 2 or abs(local[1]) > pcb_size[1] / 2:
                            issues.append(SpecIssue("error", path, "mounting_hole_outside_pcb", "mounting hole lies outside the PCB"))
                            continue
                        absolute = (local[0] + pcb_origin[0], local[1] + pcb_origin[1])
                        if not any(math.dist(absolute, standoff.center_xy_mm) <= 0.05 for standoff in spec.standoffs):
                            issues.append(
                                SpecIssue(
                                    "warning",
                                    path,
                                    "unmatched_mounting_hole",
                                    "mounting hole has no aligned standoff; mounting support remains unresolved",
                                )
                            )
                if component_height is not None:
                    required_z = (
                        floor
                        + max((standoff.height_mm for standoff in spec.standoffs), default=0.0)
                        + pcb_size[2]
                        + component_height
                    )
                    available_height = height - (lip_height or 0.0)
                    if required_z >= available_height:
                        issues.append(SpecIssue(
                            "error", "$.pcb", "pcb_height_exceeded",
                            f"PCB and components need {required_z:g} mm above the base; only {available_height:g} mm remain below the lid plug envelope",
                        ))

    generated_ids, body_node_count, lid_node_count = (
        _generated_ids_and_counts(spec)
        if all(isinstance(item, CutoutSpec) for item in spec.cutouts)
        and all(isinstance(item, StandoffSpec) for item in spec.standoffs)
        and all(isinstance(item, VentPatternSpec) for item in spec.vents)
        else ([], 0, 0)
    )
    duplicate_generated = sorted(identifier for identifier, count in Counter(generated_ids).items() if count > 1)
    if duplicate_generated:
        issues.append(
            SpecIssue(
                "error",
                "$",
                "generated_id_collision",
                "feature ids collide with generated nodes: " + ", ".join(duplicate_generated[:8]),
            )
        )
    if body_node_count > MAX_NODES:
        issues.append(SpecIssue("error", "$", "body_node_budget", f"body would generate {body_node_count} nodes; limit is {MAX_NODES}"))
    if lid_node_count > MAX_NODES:
        issues.append(SpecIssue("error", "$", "lid_node_budget", f"lid would generate {lid_node_count} nodes; limit is {MAX_NODES}"))

    return SpecValidationReport(tuple(issues))


def _primitive_node(
    node_id: str,
    kind: str,
    parameters: dict[str, Any],
    *,
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    role: str = "feature",
) -> Node:
    return Node(node_id, primitive=Primitive(kind, parameters), transform=Transform(translate, rotate), role=role)


def _face_transform(
    face: str,
    center_uv: tuple[float, float],
    spec: EnclosureSpec,
    *,
    circular: bool,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    width, depth, height = spec.outer_size_mm
    u, v = center_uv
    if face == "front":
        return (u, -depth / 2, v), ((90.0, 0.0, 0.0) if circular else (0.0, 0.0, 0.0))
    if face == "rear":
        return (u, depth / 2, v), ((90.0, 0.0, 0.0) if circular else (0.0, 0.0, 0.0))
    if face == "left":
        return (-width / 2, u, v), ((0.0, 90.0, 0.0) if circular else (0.0, 0.0, 0.0))
    if face == "right":
        return (width / 2, u, v), ((0.0, 90.0, 0.0) if circular else (0.0, 0.0, 0.0))
    z = -height / 2 if face == "bottom" else height / 2
    return (u, v, z), (0.0, 0.0, 0.0)


def _cutout_node(cutout: CutoutSpec, spec: EnclosureSpec) -> Node:
    floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
    through = (floor if cutout.face == "bottom" else spec.wall_mm) + 2.0
    compensation = MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
    translate, rotate = _face_transform(cutout.face, cutout.center_uv_mm, spec, circular=cutout.kind == "circular")
    if cutout.kind == "circular":
        return _primitive_node(
            cutout.id,
            "cylinder",
            {"radius": (float(cutout.diameter_mm or 0.0) + compensation) / 2, "height": through},
            translate=translate,
            rotate=rotate,
            role="cutout",
        )
    u, v = cutout.size_mm or (0.0, 0.0)
    if cutout.face in {"front", "rear"}:
        size = [u, through, v]
    elif cutout.face in {"left", "right"}:
        size = [through, u, v]
    else:
        size = [u, v, through]
    kind = "rounded_box" if cutout.corner_radius_mm > 0 else "box"
    parameters: dict[str, Any] = {"size": size}
    if kind == "rounded_box":
        parameters["radius"] = cutout.corner_radius_mm
    return _primitive_node(cutout.id, kind, parameters, translate=translate, role="cutout")


def _vent_nodes(vent: VentPatternSpec, spec: EnclosureSpec) -> list[Node]:
    nodes: list[Node] = []
    start_u = vent.center_uv_mm[0] - (vent.columns - 1) * vent.pitch_mm / 2
    start_v = vent.center_uv_mm[1] - (vent.rows - 1) * vent.pitch_mm / 2
    for row in range(vent.rows):
        for column in range(vent.columns):
            cutout = CutoutSpec(
                id=f"{vent.id}_{row + 1}_{column + 1}",
                kind="circular",
                face=vent.face,
                center_uv_mm=(start_u + column * vent.pitch_mm, start_v + row * vent.pitch_mm),
                diameter_mm=vent.diameter_mm,
                purpose="vent",
            )
            nodes.append(_cutout_node(cutout, spec))
    return nodes


def _lid_cutout_node(cutout: CutoutSpec, spec: EnclosureSpec) -> Node:
    through = spec.lid.thickness_mm + spec.lid.lip_height_mm + 2.0
    u, v = cutout.center_uv_mm
    if cutout.kind == "circular":
        return _primitive_node(
            cutout.id,
            "cylinder",
            {
                "radius": (
                    float(cutout.diameter_mm or 0.0)
                    + MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
                )
                / 2,
                "height": through,
            },
            translate=(u, v, 0.0),
            role="lid_cutout",
        )
    width, depth = cutout.size_mm or (0.0, 0.0)
    kind = "rounded_box" if cutout.corner_radius_mm > 0 else "box"
    parameters: dict[str, Any] = {"size": [width, depth, through]}
    if kind == "rounded_box":
        parameters["radius"] = cutout.corner_radius_mm
    return _primitive_node(cutout.id, kind, parameters, translate=(u, v, 0.0), role="lid_cutout")


def _lid_vent_nodes(vent: VentPatternSpec, spec: EnclosureSpec) -> list[Node]:
    nodes: list[Node] = []
    start_u = vent.center_uv_mm[0] - (vent.columns - 1) * vent.pitch_mm / 2
    start_v = vent.center_uv_mm[1] - (vent.rows - 1) * vent.pitch_mm / 2
    for row in range(vent.rows):
        for column in range(vent.columns):
            cutout = CutoutSpec(
                id=f"{vent.id}_{row + 1}_{column + 1}",
                kind="circular",
                face="top",
                center_uv_mm=(start_u + column * vent.pitch_mm, start_v + row * vent.pitch_mm),
                diameter_mm=vent.diameter_mm,
                purpose="vent",
            )
            nodes.append(_lid_cutout_node(cutout, spec))
    return nodes


def _body_program(spec: EnclosureSpec) -> CADProgram:
    width, depth, height = spec.outer_size_mm
    floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
    outer_kind = "rounded_box" if spec.corner_radius_mm > 0 else "box"
    outer_parameters: dict[str, Any] = {"size": [width, depth, height]}
    if outer_kind == "rounded_box":
        outer_parameters["radius"] = spec.corner_radius_mm
    nodes: list[Node] = [_primitive_node("body_outer", outer_kind, outer_parameters, role="body")]
    cavity_height = height - floor + 0.2
    cavity_kind = "rounded_box" if spec.corner_radius_mm > spec.wall_mm else "box"
    cavity_parameters: dict[str, Any] = {
        "size": [width - 2 * spec.wall_mm, depth - 2 * spec.wall_mm, cavity_height]
    }
    if cavity_kind == "rounded_box":
        cavity_parameters["radius"] = spec.corner_radius_mm - spec.wall_mm
    cavity = _primitive_node(
        "body_cavity",
        cavity_kind,
        cavity_parameters,
        translate=(0.0, 0.0, (floor + 0.2) / 2),
        role="cavity",
    )
    nodes.append(cavity)
    negative_ids = [cavity.id]
    for cutout in (item for item in spec.cutouts if item.face != "top"):
        node = _cutout_node(cutout, spec)
        nodes.append(node)
        negative_ids.append(node.id)
    for vent in (item for item in spec.vents if item.face != "top"):
        for node in _vent_nodes(vent, spec):
            nodes.append(node)
            negative_ids.append(node.id)
    nodes.append(Node("body_shell", composition="difference", children=("body_outer", *negative_ids), role="composition"))

    mount_outer_ids: list[str] = []
    mount_hole_ids: list[str] = []
    body_mounts = list(spec.standoffs)
    if spec.lid.kind == "screw" and spec.lid.hardware in HARDWARE_PROFILES:
        lid_hardware = HARDWARE_PROFILES[spec.lid.hardware]
        boss_height = height - floor - 0.5
        body_mounts.extend(
            StandoffSpec(
                id=f"lid_boss_{index}",
                center_xy_mm=position,
                height_mm=boss_height,
                outer_diameter_mm=lid_hardware.boss_outer_mm,
                hole_diameter_mm=lid_hardware.pilot_hole_mm,
                hardware=lid_hardware.name,
            )
            for index, position in enumerate(spec.lid.fastener_positions_xy_mm, start=1)
        )
    for standoff in body_mounts:
        z = -height / 2 + floor + standoff.height_mm / 2
        # Embed the solid base slightly into the floor. Face-to-face contact is
        # not a robust Boolean union and can make CGAL extremely slow or leave
        # nominally separate mesh shells. The visible top height is unchanged.
        floor_overlap = min(0.2, floor / 2)
        outer_id = f"{standoff.id}_outer"
        hole_id = f"{standoff.id}_hole"
        nodes.extend(
            [
                _primitive_node(
                    outer_id,
                    "cylinder",
                    {
                        "radius": standoff.outer_diameter_mm / 2,
                        "height": standoff.height_mm + floor_overlap,
                    },
                    translate=(
                        standoff.center_xy_mm[0],
                        standoff.center_xy_mm[1],
                        z - floor_overlap / 2,
                    ),
                    role="standoff",
                ),
                _primitive_node(
                    hole_id,
                    "cylinder",
                    {
                        "radius": (
                            standoff.hole_diameter_mm
                            + MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
                        )
                        / 2,
                        "height": standoff.height_mm + 0.4,
                    },
                    translate=(standoff.center_xy_mm[0], standoff.center_xy_mm[1], z + 0.2),
                    role="fastener_hole",
                ),
            ]
        )
        mount_outer_ids.append(outer_id)
        mount_hole_ids.append(hole_id)
    root = "body_shell"
    if mount_outer_ids:
        nodes.append(
            Node(
                "body_positive",
                composition="union",
                children=("body_shell", *mount_outer_ids),
                role="composition",
            )
        )
        root = "body_complete"
        nodes.append(
            Node(
                root,
                composition="difference",
                children=("body_positive", *mount_hole_ids),
                role="composition",
            )
        )
    metadata = {
        "source": "typed_enclosure_spec",
        "spec_version": spec.version,
        "part": "body",
        "outer_size_mm": list(spec.outer_size_mm),
        "feature_ids": [feature.id for feature in spec.cutouts]
        + [feature.id for feature in spec.vents]
        + [feature.id for feature in spec.standoffs],
        "profile": spec.profile,
        "hole_compensation_applied_mm": MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm,
    }
    constraints = (
        Constraint("dimension", target="body_outer", parameters={"parameter": "size", "value": list(spec.outer_size_mm)}),
        Constraint("child_count", target="body_shell", parameters={"value": 1 + len(negative_ids)}),
    )
    return CADProgram(f"{spec.title} — body", tuple(nodes), (root,), constraints, metadata)


def _lid_program(spec: EnclosureSpec) -> CADProgram | None:
    lid = spec.lid
    if lid.kind == "none":
        return None
    width, depth, _ = spec.outer_size_mm
    plate_width = width - 2 * lid.clearance_mm
    plate_depth = depth - 2 * lid.clearance_mm
    plate_radius = max(0.0, spec.corner_radius_mm - lid.clearance_mm)
    plate_parameters: dict[str, Any] = {"size": [plate_width, plate_depth, lid.thickness_mm]}
    if plate_radius > 0:
        plate_parameters["radius"] = plate_radius
    nodes: list[Node] = [
        _primitive_node("lid_plate", "rounded_box" if plate_radius > 0 else "box", plate_parameters, role="lid")
    ]
    positive_ids = ["lid_plate"]
    if lid.lip_height_mm > 0:
        lip_width = width - 2 * (spec.wall_mm + lid.clearance_mm)
        lip_depth = depth - 2 * (spec.wall_mm + lid.clearance_mm)
        lip_radius = max(0.0, spec.corner_radius_mm - spec.wall_mm - lid.clearance_mm)
        lip_parameters: dict[str, Any] = {"size": [lip_width, lip_depth, lid.lip_height_mm]}
        if lip_radius > 0:
            lip_parameters["radius"] = lip_radius
        nodes.append(
            _primitive_node(
                "lid_lip",
                "rounded_box" if lip_radius > 0 else "box",
                lip_parameters,
                translate=(0.0, 0.0, -(lid.thickness_mm + lid.lip_height_mm) / 2),
                role="friction_plug" if lid.kind == "friction" else "alignment_lip",
            )
        )
        positive_ids.append("lid_lip")
    positive_root = positive_ids[0]
    if len(positive_ids) > 1:
        positive_root = "lid_positive"
        nodes.append(Node(positive_root, composition="union", children=tuple(positive_ids), role="composition"))
    negative_ids: list[str] = []
    for cutout in (item for item in spec.cutouts if item.face == "top"):
        node = _lid_cutout_node(cutout, spec)
        nodes.append(node)
        negative_ids.append(node.id)
    for vent in (item for item in spec.vents if item.face == "top"):
        for node in _lid_vent_nodes(vent, spec):
            nodes.append(node)
            negative_ids.append(node.id)
    if lid.kind == "screw" and lid.hardware in HARDWARE_PROFILES:
        hardware = HARDWARE_PROFILES[lid.hardware]
        for index, (x, y) in enumerate(lid.fastener_positions_xy_mm, start=1):
            node_id = f"lid_fastener_{index}"
            nodes.append(
                _primitive_node(
                    node_id,
                    "cylinder",
                    {
                        "radius": (
                            hardware.clearance_hole_mm
                            + MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm
                        )
                        / 2,
                        "height": lid.thickness_mm + lid.lip_height_mm + 2,
                    },
                    translate=(x, y, -lid.lip_height_mm / 2),
                    role="fastener_hole",
                )
            )
            negative_ids.append(node_id)
            if lid.lip_height_mm > 0:
                # Clear the boss's whole outer ring beneath the plate. A screw
                # bore only clears the screw and otherwise leaves intersecting
                # lid/boss solids when the lid is seated on the enclosure rim.
                relief_id = f"lid_boss_relief_{index}"
                nodes.append(_primitive_node(
                    relief_id, "cylinder",
                    {"radius": hardware.boss_outer_mm / 2 + lid.clearance_mm, "height": lid.lip_height_mm + 0.2},
                    translate=(x, y, -(lid.thickness_mm + lid.lip_height_mm) / 2 - 0.1),
                    role="boss_clearance",
                ))
                negative_ids.append(relief_id)
    root = positive_root
    if negative_ids:
        root = "lid_complete"
        nodes.append(Node(root, composition="difference", children=(positive_root, *negative_ids), role="composition"))
    metadata = {
        "source": "typed_enclosure_spec",
        "spec_version": spec.version,
        "part": "lid",
        "lid_kind": lid.kind,
        "closure_mechanism": "insertion_plug" if lid.kind == "friction" else "screw_fasteners",
        "profile": spec.profile,
        "hole_compensation_applied_mm": MANUFACTURING_PROFILES[spec.profile].hole_compensation_mm,
    }
    return CADProgram(f"{spec.title} — lid", tuple(nodes), (root,), metadata=metadata)


def build_enclosure(spec: EnclosureSpec) -> EnclosureBuild:
    report = validate_enclosure_spec(spec)
    if not report.valid:
        raise ValueError(
            "invalid enclosure specification: "
            + "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        )
    body = _body_program(spec)
    lid = _lid_program(spec)
    for part_name, program in (("body", body), ("lid", lid)):
        if program is None:
            continue
        ir_report = validate_program(program)
        if not ir_report.valid:
            raise ValueError(
                f"generated {part_name} IR is invalid: "
                + "; ".join(f"{issue.path}: {issue.message}" for issue in ir_report.errors)
            )
    return EnclosureBuild(spec, body, lid, report)
