"""Declared isolated axis-aligned cylindrical bores on the final solid.

This is a bounded geometric contract, not arbitrary feature recognition. A bore
must open on a bounding plane. Intersecting bores, ambiguous outputs and absent
material clearance fail. The export route supplies reimported STEP evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

KIND = "output_cylindrical_hole"
KEYS = {"kind", "axis", "direction", "entry_mm", "radius_mm", "depth_mm",
        "termination", "clearance_mm", "tolerance_mm", "volume_tolerance_mm3"}


def number(value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("Geometry measurements must be finite numbers")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("Unrepresentable geometry measurement") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError("Geometry measurement outside its finite domain")
    return result


def validate_probe(probe: dict[str, Any]) -> None:
    if not isinstance(probe, dict) or set(probe) != KEYS or probe["kind"] != KIND:
        raise ValueError("Cylindrical-hole probe requires exactly the declared geometry fields")
    if probe["axis"] not in ("x", "y", "z") or type(probe["direction"]) is not int or probe["direction"] not in (-1, 1):
        raise ValueError("Bore needs one Cartesian axis and an integer direction of -1 or 1")
    if probe["termination"] not in ("through", "blind"):
        raise ValueError("Bore termination must be through or blind")
    if not isinstance(probe["entry_mm"], (list, tuple)) or len(probe["entry_mm"]) != 3:
        raise ValueError("Bore entry needs three finite coordinates")
    for value in probe["entry_mm"]:
        number(value)
    radius, depth, clearance, tolerance, volume_tolerance = (
        number(probe[key], positive=True) for key in
        ("radius_mm", "depth_mm", "clearance_mm", "tolerance_mm", "volume_tolerance_mm3"))
    if tolerance >= min(radius, depth, clearance) / 4:
        raise ValueError("Linear tolerance must be less than one quarter of every probe scale")
    bore_volume = math.pi * (radius - tolerance)**2 * (depth - 2*tolerance)
    shell_volume = math.pi * ((radius + clearance)**2 - (radius + tolerance)**2) * (depth - 2*tolerance)
    cap_volume = math.pi * (radius - tolerance)**2 * clearance
    if not all(math.isfinite(v) and v > 0 for v in (bore_volume, shell_volume, cap_volume)):
        raise ValueError("Probe volumes must be positive and representable")
    if volume_tolerance > min(bore_volume, shell_volume, cap_volume) * 0.001:
        raise ValueError("Volume tolerance cannot hide more than 0.1 percent of a probe")


def probe_hash(probe: dict[str, Any]) -> str:
    validate_probe(probe)
    return hashlib.sha256(json.dumps(probe, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def measure_bore(shape: Any, bd: Any, probe: dict[str, Any]) -> dict[str, Any]:
    """Measure final material in the void, surrounding sleeve and blind end cap."""
    validate_probe(probe)
    if not shape.is_valid or not shape.is_manifold or len(shape.solids()) != 1:
        raise ValueError("Bore verification requires exactly one valid manifold solid")
    axis = ("x", "y", "z").index(probe["axis"])
    direction = probe["direction"]
    entry = [float(v) for v in probe["entry_mm"]]
    r, depth, clearance, tol = (float(probe[k]) for k in ("radius_mm", "depth_mm", "clearance_mm", "tolerance_mm"))
    bounds = shape.bounding_box()
    lo, hi = ([float(getattr(point, a)) for a in ("X", "Y", "Z")] for point in (bounds.min, bounds.max))
    near, far = (lo[axis], hi[axis]) if direction == 1 else (hi[axis], lo[axis])
    end = entry[axis] + direction * depth
    angles = (0, 90, 0) if axis == 0 else (90, 0, 0) if axis == 1 else (0, 0, 0)

    def cylinder(radius: float, start: float, length: float) -> Any:
        center = list(entry)
        center[axis] += direction * (start + length / 2)
        return bd.Pos(*center) * bd.Rot(*angles) * bd.Cylinder(radius, length)

    def volume(value: Any) -> float:
        return abs(number(value.volume))

    cavity = cylinder(r - tol, tol, depth - 2 * tol)
    outer = cylinder(r + clearance, tol, depth - 2 * tol)
    inner = cylinder(r + tol, tol, depth - 2 * tol)
    sleeve = outer - inner
    cap = cylinder(r - tol, depth + tol, clearance)
    return {
        "probe_sha256": probe_hash(probe),
        "entry_error_mm": abs(entry[axis] - near),
        "terminal_error_mm": abs(end - far) if probe["termination"] == "through" else max(0.0, direction * (end - far)),
        "void_material_mm3": volume(shape & cavity),
        "sleeve_missing_mm3": volume(sleeve - shape),
        "cap_missing_mm3": volume(cap - shape) if probe["termination"] == "blind" else 0.0,
        "solid_count": len(shape.solids()),
        "valid_brep": bool(shape.is_valid), "manifold": bool(shape.is_manifold),
    }


def evaluate_measurement(probe: dict[str, Any], evidence: dict[str, Any]) -> bool:
    validate_probe(probe)
    expected_keys = {"probe_sha256", "entry_error_mm", "terminal_error_mm", "void_material_mm3",
                     "sleeve_missing_mm3", "cap_missing_mm3", "solid_count", "valid_brep", "manifold"}
    if not isinstance(evidence, dict) or set(evidence) != expected_keys:
        raise ValueError("Missing or invalid final-bore measurement evidence")
    if evidence["probe_sha256"] != probe_hash(probe):
        raise ValueError("Bore evidence was measured for a different probe")
    if (evidence["valid_brep"] is not True or evidence["manifold"] is not True
            or type(evidence["solid_count"]) is not int or evidence["solid_count"] != 1):
        raise ValueError("Final bore evidence must describe one valid manifold solid")
    passed = True
    for key in ("entry_error_mm", "terminal_error_mm", "void_material_mm3", "sleeve_missing_mm3", "cap_missing_mm3"):
        value = number(evidence[key])
        if value < 0:
            raise ValueError("Residual measurements cannot be negative")
        limit = probe["tolerance_mm"] if key.endswith("_mm") else probe["volume_tolerance_mm3"]
        passed = passed and value <= limit
    return passed
