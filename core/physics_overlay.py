"""Component-bound result summaries for CAD viewers.

This is deliberately not a spatial contour field.  A closed-form scalar model
cannot justify per-vertex stress, temperature, velocity, or displacement data.
"""

from __future__ import annotations

import math
from typing import Any

from .physics_context import canonical_sha256

OVERLAY_VERSION = "neurocad-component-overlay-v1"

_UNIT_SUFFIXES = (
    ("_n_per_mm", "N/mm"),
    ("_n_s_m", "N*s/m"),
    ("_a_per_mm2", "A/mm^2"),
    ("_k_per_w", "K/W"),
    ("_w_per_k", "W/K"),
    ("_w_m2", "W/m^2"),
    ("_m3_s", "m^3/s"),
    ("_kg_m3", "kg/m^3"),
    ("_pa_s", "Pa*s"),
    ("_rad_s", "rad/s"),
    ("_n_mm", "N*mm"),
    ("_mm4", "mm^4"),
    ("_mm3", "mm^3"),
    ("_mm2", "mm^2"),
    ("_mpa", "MPa"),
    ("_pa", "Pa"),
    ("_hz", "Hz"),
    ("_ohm", "ohm"),
    ("_a", "A"),
    ("_v", "V"),
    ("_w", "W"),
    ("_n", "N"),
    ("_kg", "kg"),
    ("_m_s", "m/s"),
    ("_mm", "mm"),
    ("_m", "m"),
    ("_k", "K"),
    ("_s", "s"),
    ("_radians", "rad"),
)


def _unit(name: str) -> str:
    for suffix, unit in _UNIT_SUFFIXES:
        if name.endswith(suffix):
            return unit
    return "1"


def build_component_overlay(report: dict[str, Any]) -> dict[str, Any] | None:
    """Build one honest uniform component annotation from a bound report."""

    bindings = report.get("bindings")
    if not isinstance(bindings, dict):
        return None
    geometry = bindings.get("geometry")
    if not isinstance(geometry, dict):
        return None
    results = report.get("results")
    if not isinstance(results, dict):
        raise TypeError("physics report results must be an object")
    constraint = results.get("constraint_satisfied")
    status = "pass" if constraint is True else ("fail" if constraint is False else "not_evaluated")
    metrics = [
        {"name": name, "value": float(value), "unit": _unit(name)}
        for name, value in sorted(results.items())
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    ][:32]
    overlay: dict[str, Any] = {
        "schema_version": OVERLAY_VERSION,
        "component_id": geometry.get("component_id"),
        "geometry_sha256": geometry.get("geometry_sha256"),
        "model": report.get("model"),
        "status": status,
        "spatial_field": False,
        "scope": "uniform annotation on the exact bound primitive; values are model-level scalars, not nodal or per-vertex fields",
        "metrics": metrics,
        "legend": {
            "pass": "the model's explicitly supplied constraint evaluated true",
            "fail": "the model's explicitly supplied constraint evaluated false",
            "not_evaluated": "the request did not provide enough information for a pass/fail constraint",
        },
    }
    overlay["overlay_sha256"] = canonical_sha256(overlay)
    return overlay
