"""Structural-only report retained from canonical main PR #48; not mesh or physical verification."""
from __future__ import annotations

import hashlib
import math
from typing import Any

from text_to_cad import TextToCAD

_VERIFICATION_SCOPE = "structural_generation_only"
_CLAIM_BOUNDARY = (
    "Checks generation integrity and design-graph structure only; it does not establish "
    "manufacturability, simulation accuracy, safety, or physical feasibility."
)
_SUPPORTED_OPERATIONS = {"union", "difference", "intersection"}


def _finite_sequence(values: Any) -> bool:
    try:
        return all(math.isfinite(float(value)) for value in values)
    except (TypeError, ValueError):
        return False


def _component_record(component: Any) -> dict[str, Any]:
    geometry = component.geometry() if callable(getattr(component, "geometry", None)) else {}
    transform = dict(getattr(component, "transform", {}) or {})
    return {
        "name": str(getattr(component, "name", "")),
        "role": str(getattr(component, "role", "")),
        "operation": str(getattr(component, "operation", "")),
        "geometry": dict(geometry or {}),
        "transform": transform,
    }


def _build_verification_bundle(prompt: str, fn: int = 96) -> tuple[dict[str, Any], str]:
    doc = TextToCAD(fn=fn).build(prompt)
    design = getattr(doc, "design", None)
    components = list(getattr(design, "components", []) or []) if design is not None else []
    connections = list(getattr(design, "connections", []) or []) if design is not None else []
    scad = str(getattr(doc, "scad", "") or "")

    names = [str(getattr(component, "name", "")) for component in components]
    component_ids = {id(component) for component in components}

    checks = [
        {"name": "supported_validated_program", "passed": doc.validation.valid and doc.program is not None,
         "detail": "; ".join(doc.validation.errors) or "strict prompt and IR validation passed"},
        {
            "name": "scad_nonempty",
            "passed": bool(scad.strip()),
            "detail": f"{len(scad)} characters generated",
        },
        {
            "name": "design_graph_nonempty",
            "passed": bool(components),
            "detail": f"{len(components)} components",
        },
        {
            "name": "unique_component_names",
            "passed": bool(names) and all(names) and len(names) == len(set(names)),
            "detail": f"{len(set(names))}/{len(names)} unique names",
        },
        {
            "name": "supported_boolean_operations",
            "passed": all(
                str(getattr(component, "operation", "")) in _SUPPORTED_OPERATIONS
                for component in components
            ),
            "detail": "operations are limited to union/difference/intersection",
        },
        {
            "name": "geometry_kind_present",
            "passed": all(
                bool(
                    (component.geometry() if callable(getattr(component, "geometry", None)) else {}).get(
                        "kind"
                    )
                )
                for component in components
            ),
            "detail": "every component declares a geometry kind",
        },
        {
            "name": "finite_transforms",
            "passed": all(
                all(
                    _finite_sequence((getattr(component, "transform", {}) or {}).get(key, ()))
                    for key in ("translate", "rotate", "scale")
                )
                for component in components
            ),
            "detail": "all translate/rotate/scale entries are finite numbers",
        },
        {
            "name": "connections_resolve",
            "passed": all(
                id(getattr(connection, "a", None)) in component_ids
                and id(getattr(connection, "b", None)) in component_ids
                for connection in connections
            ),
            "detail": f"{len(connections)} graph connections resolve to emitted components",
        },
    ]

    passed = all(check["passed"] for check in checks)
    report = {
        "schema_version": 1,
        "status": "valid" if passed else "invalid",
        "verification_scope": _VERIFICATION_SCOPE,
        "claim_boundary": _CLAIM_BOUNDARY,
        "prompt": prompt,
        "fn": int(fn),
        "checks": checks,
        "design": {
            "title": str(getattr(design, "title", "")) if design is not None else "",
            "component_count": len(components),
            "connection_count": len(connections),
            "metadata": dict(getattr(design, "metadata", {}) or {}) if design is not None else {},
            "components": [_component_record(component) for component in components],
            "connections": [
                {
                    "a": str(getattr(getattr(connection, "a", None), "name", "")),
                    "b": str(getattr(getattr(connection, "b", None), "name", "")),
                    "relation": str(getattr(connection, "relation", "")),
                }
                for connection in connections
            ],
        },
        "artifact": {
            "format": "scad",
            "sha256": hashlib.sha256(scad.encode("utf-8")).hexdigest(),
            "character_count": len(scad),
            "line_count": len(scad.splitlines()),
        },
    }
    return report, scad


def build_verification_report(prompt: str, fn: int = 96) -> dict[str, Any]:
    """Build a deterministic, structural-only public-alpha verification report."""

    report, _ = _build_verification_bundle(prompt, fn=fn)
    return report


