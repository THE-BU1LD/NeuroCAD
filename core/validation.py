from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .design_graph import DesignGraph

SUPPORTED_FABRICATION_DOMAINS = {"plate", "enclosure", "primitive"}
MIN_PRIMITIVE_LENGTH_MM = 0.1
MAX_PRIMITIVE_LENGTH_MM = 100000.0
UNSUPPORTED_REQUESTS = {
    "lid": "lids are not implemented",
    "snap fit": "snap fits require calibrated clearances and are not implemented",
    "thread": "threads are not implemented",
    "hinge": "hinges are not implemented",
    "tolerance": "manufacturing tolerances are not implemented",
    "fillet": "true edge fillets are not implemented; use a rounded planar profile",
}


@dataclass
class ValidationReport:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": list(self.errors), "warnings": list(self.warnings)}


def _numbers(value: Any) -> Iterable[float]:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        try:
            yield float(value)
        except (OverflowError, ValueError):
            yield math.nan
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _numbers(item)


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _finite_vector(value: Any, *, size: int = 3) -> tuple[float, ...] | None:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        return None
    converted = tuple(_finite_float(item) for item in value)
    if any(item is None for item in converted):
        return None
    return tuple(item for item in converted if item is not None)


def validate_design(design: DesignGraph, *, require_prompt_contract: bool | None = None) -> ValidationReport:
    report = ValidationReport()
    metadata = design.metadata
    if require_prompt_contract is None:
        require_prompt_contract = metadata.get("source_kind") == "prompt" or "normalized_prompt" in metadata
    fabrication_domain = metadata.get("fabrication_domain")
    prompt = str(metadata.get("normalized_prompt", ""))

    if require_prompt_contract:
        if fabrication_domain not in SUPPORTED_FABRICATION_DOMAINS:
            report.error(
                "unsupported domain: production generation currently supports plates, "
                "rectangular boxes/enclosures, and fully dimensioned box/cylinder/sphere primitives"
            )
        if not metadata.get("recognized"):
            report.error("the prompt was not recognized as a fully supported design")
        if not metadata.get("explicit_dimensions"):
            report.error("all overall dimensions must be stated explicitly")
        if metadata.get("prompt_fully_consumed") is not True:
            report.error("prompt contains unconsumed or unsupported text; rewrite it using only the documented grammar")

    flags = metadata.get("flags") or {}
    if not isinstance(flags, dict):
        report.error("feature flags must be an object")
        flags = {}
    if fabrication_domain == "primitive" and any(flags.get(name) for name in ("holes", "slots", "rounded", "hollow")):
        report.error("features on generic primitives are unsupported; describe the object as a plate, box, or enclosure")

    for phrase, reason in UNSUPPORTED_REQUESTS.items():
        phrase_pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
        if re.search(phrase_pattern, prompt):
            report.error(f"unsupported request '{phrase}': {reason}")

    if not design.components:
        report.error("the design has no components")
        return report

    allowed_operations = {"union", "difference", "intersection"}
    allowed_geometry = {"box", "cube", "rounded_box", "sphere", "cylinder", "cone", "torus"}
    for component in design.components:
        geometry = component.geometry()
        kind = str(geometry.get("kind", "")).lower()
        if component.operation not in allowed_operations:
            report.error(f"component {component.name!r} has unsupported operation {component.operation!r}")
        if kind not in allowed_geometry:
            report.error(f"component {component.name!r} has unsupported geometry {kind!r}")
        if "center" in geometry and not isinstance(geometry["center"], bool):
            report.error(f"component {component.name!r} center must be a boolean")
        for number in _numbers(geometry):
            if not math.isfinite(number):
                report.error(f"component {component.name!r} contains a non-finite dimension")
        if kind in {"box", "cube", "rounded_box"}:
            size = geometry.get("size")
            dimensions = _finite_vector(size)
            if dimensions is None:
                report.error(f"component {component.name!r} must have exactly three size dimensions")
            elif any(value <= 0 for value in dimensions):
                report.error(f"component {component.name!r} has a non-positive size")
            elif any(value < MIN_PRIMITIVE_LENGTH_MM for value in dimensions):
                report.error(f"component {component.name!r} has a size below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
            elif any(value > MAX_PRIMITIVE_LENGTH_MM for value in dimensions):
                report.error(f"component {component.name!r} has a size above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
            if kind == "rounded_box":
                radius = _finite_float(geometry.get("radius"))
                if radius is None or radius < 0:
                    report.error(f"component {component.name!r} has an invalid corner radius")
                elif radius < MIN_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a corner radius below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
                elif radius > MAX_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a corner radius above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
                elif dimensions is not None and radius > min(dimensions[0], dimensions[1]) / 2:
                    report.error(f"component {component.name!r} corner radius exceeds half the planar size")
        elif kind in {"cylinder", "cone"}:
            height = _finite_float(geometry.get("height", geometry.get("h")))
            radii = [geometry[key] for key in ("radius", "r", "r1", "r2") if key in geometry]
            finite_radii = [_finite_float(radius) for radius in radii]
            if (
                height is None
                or height <= 0
                or not radii
                or any(radius is None or radius < 0 for radius in finite_radii)
                or (kind == "cylinder" and any(radius == 0 for radius in finite_radii))
                or (kind == "cone" and all(radius == 0 for radius in finite_radii))
            ):
                report.error(f"component {component.name!r} has invalid cylinder/cone dimensions")
            else:
                validated_height = float(height)
                validated_radii = [float(radius) for radius in finite_radii if radius is not None]
                if validated_height < MIN_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a height below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
                elif validated_height > MAX_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a height above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
                for radius in validated_radii:
                    if radius == 0 and kind == "cone":
                        continue
                    if radius < MIN_PRIMITIVE_LENGTH_MM:
                        report.error(f"component {component.name!r} has a radius below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
                    elif radius > MAX_PRIMITIVE_LENGTH_MM:
                        report.error(f"component {component.name!r} has a radius above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
        elif kind == "sphere":
            radius = _finite_float(geometry.get("radius", geometry.get("r")))
            if radius is None or radius <= 0:
                report.error(f"component {component.name!r} has a non-positive radius")
            elif radius < MIN_PRIMITIVE_LENGTH_MM:
                report.error(f"component {component.name!r} has a radius below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
            elif radius > MAX_PRIMITIVE_LENGTH_MM:
                report.error(f"component {component.name!r} has a radius above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
        elif kind == "torus":
            major = _finite_float(geometry.get("R"))
            minor = _finite_float(geometry.get("r"))
            if major is None or minor is None or major <= 0 or minor <= 0 or minor >= major:
                report.error(f"component {component.name!r} has invalid torus radii")
            else:
                if min(major, minor) < MIN_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a torus radius below {MIN_PRIMITIVE_LENGTH_MM:g} mm")
                if max(major, minor) > MAX_PRIMITIVE_LENGTH_MM:
                    report.error(f"component {component.name!r} has a torus radius above {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")

        transform = component.transform
        if not isinstance(transform, dict):
            report.error(f"component {component.name!r} transform must be an object")
        else:
            translate = _finite_vector(transform.get("translate"))
            rotate = _finite_vector(transform.get("rotate"))
            scale = _finite_vector(transform.get("scale"))
            if translate is None or rotate is None or scale is None:
                report.error(f"component {component.name!r} transform requires three finite translate, rotate, and scale values")
            elif any(value == 0 for value in scale):
                report.error(f"component {component.name!r} transform scale cannot contain zero")

    overall = metadata.get("dimensions_mm")
    overall_dimensions = _finite_vector(overall) if isinstance(overall, (list, tuple)) else None
    if isinstance(overall, (list, tuple)):
        if overall_dimensions is None:
            report.error("overall dimensions must contain three finite values")
        elif any(value < 0.1 for value in overall_dimensions):
            report.error("overall dimensions below 0.1 mm are outside the supported range")
        elif any(value > 100000 for value in overall_dimensions):
            report.error("overall dimensions above 100,000 mm are outside the supported range")

    if metadata.get("rounded_requested"):
        corner_radius = _finite_float(metadata.get("corner_radius_mm"))
        if not metadata.get("corner_radius_explicit"):
            report.error("corner radius must be stated explicitly for a rounded profile")
        if corner_radius is None or corner_radius <= 0:
            report.error("corner radius must be a positive finite dimension")

    requested_holes_raw = metadata.get("hole_count_requested") or 0
    requested_holes = requested_holes_raw if isinstance(requested_holes_raw, int) and not isinstance(requested_holes_raw, bool) else -1
    if requested_holes < 0 or requested_holes > 256:
        report.error("requested hole count must be an integer from 0 to 256")
    if flags.get("holes") and metadata.get("hole_count_explicit") is not True:
        report.error("hole count must be stated explicitly; plural holes cannot default to one")
    actual_holes = sum(1 for component in design.components if component.name.startswith("hole_"))
    if requested_holes != actual_holes:
        report.error(f"requested {requested_holes} holes but generated {actual_holes}")
    if requested_holes and not metadata.get("hole_diameter_explicit"):
        report.error("hole diameter must be stated explicitly")
    if requested_holes and fabrication_domain != "plate":
        report.error("holes are supported only on dimensioned plates")
    if requested_holes:
        diameter = _finite_float(metadata.get("hole_diameter_mm"))
        if diameter is None or diameter <= 0:
            report.error("hole diameter must be a positive finite dimension")
        elif overall_dimensions is not None and diameter >= min(overall_dimensions[0], overall_dimensions[1]):
            report.error("hole diameter must be smaller than the plate width and depth")

    requested_slots_raw = metadata.get("slot_count_requested") or 0
    requested_slots = requested_slots_raw if isinstance(requested_slots_raw, int) and not isinstance(requested_slots_raw, bool) else -1
    if requested_slots < 0 or requested_slots > 256:
        report.error("requested slot count must be an integer from 0 to 256")
    if flags.get("slots") and metadata.get("slot_count_explicit") is not True:
        report.error("slot count must be stated explicitly; plural slots cannot default to one")
    actual_slots = sum(1 for component in design.components if component.name.startswith("slot_"))
    if requested_slots != actual_slots:
        report.error(f"requested {requested_slots} slots but generated {actual_slots}")
    if requested_slots and not metadata.get("slot_dimensions_explicit"):
        report.error("slot width and length must be stated explicitly")
    if requested_slots and fabrication_domain != "plate":
        report.error("slots are supported only on dimensioned plates")
    if requested_slots:
        slot_dimensions = _finite_vector(metadata.get("slot_dimensions_mm"), size=2)
        if slot_dimensions is None or any(value <= 0 for value in slot_dimensions):
            report.error("slot dimensions must contain two positive finite values")
        elif overall_dimensions is not None and (
            slot_dimensions[0] >= overall_dimensions[0] or slot_dimensions[1] >= overall_dimensions[1]
        ):
            report.error("slot dimensions must be smaller than the corresponding plate dimensions")

    if fabrication_domain == "plate" and overall_dimensions is not None:
        half_width, half_depth = overall_dimensions[0] / 2, overall_dimensions[1] / 2
        hole_specs: list[tuple[float, float, float]] = []
        slot_specs: list[tuple[float, float, float, float]] = []
        for component in design.components:
            center = _finite_vector(component.transform.get("translate")) if isinstance(component.transform, dict) else None
            if center is None:
                continue
            geometry = component.geometry()
            if component.name.startswith("hole_"):
                radius = _finite_float(geometry.get("radius", geometry.get("r")))
                if radius is not None and radius > 0:
                    hole_specs.append((center[0], center[1], radius))
                    if abs(center[0]) + radius >= half_width or abs(center[1]) + radius >= half_depth:
                        report.error(f"component {component.name!r} does not remain fully inside the plate boundary")
            elif component.name.startswith("slot_"):
                size = _finite_vector(geometry.get("size"))
                if size is not None and size[0] > 0 and size[1] > 0:
                    half_x, half_y = size[0] / 2, size[1] / 2
                    slot_specs.append((center[0], center[1], half_x, half_y))
                    if abs(center[0]) + half_x >= half_width or abs(center[1]) + half_y >= half_depth:
                        report.error(f"component {component.name!r} does not remain fully inside the plate boundary")

        if any(
            math.hypot(left[0] - right[0], left[1] - right[1]) <= left[2] + right[2]
            for index, left in enumerate(hole_specs)
            for right in hole_specs[index + 1 :]
        ):
            report.error("generated hole features overlap; reduce the count or diameter")
        if any(
            abs(left[0] - right[0]) <= left[2] + right[2] and abs(left[1] - right[1]) <= left[3] + right[3]
            for index, left in enumerate(slot_specs)
            for right in slot_specs[index + 1 :]
        ):
            report.error("generated slot features overlap; reduce the count or dimensions")
        for hole_x, hole_y, radius in hole_specs:
            for slot_x, slot_y, half_x, half_y in slot_specs:
                closest_x = max(abs(hole_x - slot_x) - half_x, 0.0)
                closest_y = max(abs(hole_y - slot_y) - half_y, 0.0)
                if closest_x * closest_x + closest_y * closest_y <= radius * radius:
                    report.error("generated hole and slot features overlap; request one non-overlapping feature family")
                    hole_specs = []
                    break
            if not hole_specs:
                break

    wall = metadata.get("wall_thickness_mm")
    if fabrication_domain == "enclosure" and wall is not None:
        wall_value = _finite_float(wall)
        if not metadata.get("wall_thickness_explicit"):
            report.error("wall thickness must be stated explicitly for a hollow enclosure")
        if wall_value is None:
            report.error("wall thickness must be a finite number")
        elif wall_value < 0.8:
            report.error("wall thickness below 0.8 mm is outside the supported range")
        if wall_value is not None and overall_dimensions is not None:
            if 2 * wall_value >= min(overall_dimensions[0], overall_dimensions[1]):
                report.error("wall thickness leaves no interior cavity")
            if wall_value >= overall_dimensions[2]:
                report.error("wall thickness must be smaller than enclosure height")

    if "material" in prompt:
        report.warn("material is recorded only in the prompt; NeuroCAD does not model material behaviour")
    return report
