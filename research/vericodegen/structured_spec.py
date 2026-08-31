"""Strict structured-output boundary for the VeriCodeGen successor study.

This is a NEW research-only specification format. It is not the historical
NeuroCAD typed parser and must not be used to reinterpret the falsified legacy
mechanism claim. Stage 2 may use it as the treatment-defining deterministic
compiler path after a model emits JSON matching ``vericodegen-structured-v1``.
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence

from core.design_graph import Component, DesignGraph
from core.scad_export import design_to_scad


SPEC_VERSION = "vericodegen-structured-v1"
ALLOWED_TOP_LEVEL = {"spec_version", "title", "components", "connections"}
ALLOWED_COMPONENT_KEYS = {"name", "role", "operation", "geometry", "transform"}
ALLOWED_OPERATIONS = {"union", "difference"}
ALLOWED_GEOMETRY = {"box", "sphere", "cylinder", "cone", "torus"}
ALLOWED_TRANSFORM_KEYS = {"translate", "rotate", "scale"}
ALLOWED_CONNECTION_KEYS = {"a", "b", "relation"}


class StructuredSpecError(ValueError):
    """Raised when a successor structured output is invalid or unsafe to compile."""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _positive(name: str, value: Any, errors: list[str]) -> float | None:
    if not _is_number(value) or float(value) <= 0:
        errors.append(f"{name} must be a finite number > 0")
        return None
    return float(value)


def _vector3(name: str, value: Any, errors: list[str], *, positive: bool = False) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        errors.append(f"{name} must be a 3-element array")
        return None
    if any(not _is_number(item) for item in value):
        errors.append(f"{name} must contain only finite numbers")
        return None
    vector = tuple(float(item) for item in value)
    if positive and any(item <= 0 for item in vector):
        errors.append(f"{name} must contain values > 0")
        return None
    return vector


def _validate_geometry(value: Any, prefix: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        errors.append(f"{prefix} must be an object")
        return None

    kind = value.get("kind")
    if kind not in ALLOWED_GEOMETRY:
        errors.append(f"{prefix}.kind must be one of {', '.join(sorted(ALLOWED_GEOMETRY))}")
        return None

    center = value.get("center", True)
    if not isinstance(center, bool):
        errors.append(f"{prefix}.center must be boolean when present")

    if kind == "box":
        allowed = {"kind", "size", "center"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            errors.append(f"{prefix} has unsupported box keys: {', '.join(unknown)}")
        size = _vector3(f"{prefix}.size", value.get("size"), errors, positive=True)
        if size is None:
            return None
        return {"kind": "box", "size": list(size), "center": bool(center)}

    if kind == "sphere":
        allowed = {"kind", "radius"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            errors.append(f"{prefix} has unsupported sphere keys: {', '.join(unknown)}")
        radius = _positive(f"{prefix}.radius", value.get("radius"), errors)
        if radius is None:
            return None
        return {"kind": "sphere", "radius": radius}

    if kind == "cylinder":
        allowed = {"kind", "radius", "height", "center"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            errors.append(f"{prefix} has unsupported cylinder keys: {', '.join(unknown)}")
        radius = _positive(f"{prefix}.radius", value.get("radius"), errors)
        height = _positive(f"{prefix}.height", value.get("height"), errors)
        if radius is None or height is None:
            return None
        return {"kind": "cylinder", "radius": radius, "height": height, "center": bool(center)}

    if kind == "cone":
        allowed = {"kind", "r1", "r2", "height", "center"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            errors.append(f"{prefix} has unsupported cone keys: {', '.join(unknown)}")
        r1 = _positive(f"{prefix}.r1", value.get("r1"), errors)
        r2_value = value.get("r2")
        if not _is_number(r2_value) or float(r2_value) < 0:
            errors.append(f"{prefix}.r2 must be a finite number >= 0")
            r2 = None
        else:
            r2 = float(r2_value)
        height = _positive(f"{prefix}.height", value.get("height"), errors)
        if r1 is None or r2 is None or height is None:
            return None
        if r1 == 0 and r2 == 0:
            errors.append(f"{prefix} cone cannot have both radii equal to zero")
            return None
        return {"kind": "cone", "r1": r1, "r2": r2, "height": height, "center": bool(center)}

    allowed = {"kind", "R", "r"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        errors.append(f"{prefix} has unsupported torus keys: {', '.join(unknown)}")
    major = _positive(f"{prefix}.R", value.get("R"), errors)
    minor = _positive(f"{prefix}.r", value.get("r"), errors)
    if major is None or minor is None:
        return None
    if major <= minor:
        errors.append(f"{prefix}.R must be greater than {prefix}.r for a non-self-intersecting torus")
        return None
    return {"kind": "torus", "R": major, "r": minor}


def _validate_transform(value: Any, prefix: str, errors: list[str]) -> dict[str, Sequence[float]] | None:
    if value is None:
        return {
            "translate": (0.0, 0.0, 0.0),
            "rotate": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0),
        }
    if not isinstance(value, Mapping):
        errors.append(f"{prefix} must be an object")
        return None
    unknown = sorted(set(value) - ALLOWED_TRANSFORM_KEYS)
    if unknown:
        errors.append(f"{prefix} has unsupported keys: {', '.join(unknown)}")

    translate = _vector3(f"{prefix}.translate", value.get("translate", [0, 0, 0]), errors)
    rotate = _vector3(f"{prefix}.rotate", value.get("rotate", [0, 0, 0]), errors)
    scale = _vector3(f"{prefix}.scale", value.get("scale", [1, 1, 1]), errors, positive=True)
    if translate is None or rotate is None or scale is None:
        return None
    return {"translate": translate, "rotate": rotate, "scale": scale}


def validate_structured_spec(spec: Mapping[str, Any]) -> list[str]:
    """Return all structural violations rather than failing on the first one."""

    errors: list[str] = []
    unknown_top = sorted(set(spec) - ALLOWED_TOP_LEVEL)
    if unknown_top:
        errors.append(f"unsupported top-level keys: {', '.join(unknown_top)}")
    if spec.get("spec_version") != SPEC_VERSION:
        errors.append(f"spec_version must equal {SPEC_VERSION}")

    title = spec.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title must be a non-empty string")

    components = spec.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        components = []

    names: list[str] = []
    positive_count = 0
    for index, raw_component in enumerate(components):
        prefix = f"components[{index}]"
        if not isinstance(raw_component, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(raw_component) - ALLOWED_COMPONENT_KEYS)
        if unknown:
            errors.append(f"{prefix} has unsupported keys: {', '.join(unknown)}")

        name = raw_component.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}.name must be a non-empty string")
        elif not re_safe_name(name):
            errors.append(f"{prefix}.name must use only letters, digits, underscore, or hyphen")
        else:
            names.append(name)

        role = raw_component.get("role", "body")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"{prefix}.role must be a non-empty string")

        operation = raw_component.get("operation", "union")
        if operation not in ALLOWED_OPERATIONS:
            errors.append(f"{prefix}.operation must be union or difference")
        elif operation == "union":
            positive_count += 1

        _validate_geometry(raw_component.get("geometry"), f"{prefix}.geometry", errors)
        _validate_transform(raw_component.get("transform"), f"{prefix}.transform", errors)

    if len(names) != len(set(names)):
        errors.append("component names must be unique")
    if components and positive_count == 0:
        errors.append("at least one union component is required before subtraction")

    connections = spec.get("connections", [])
    if not isinstance(connections, list):
        errors.append("connections must be a list")
        connections = []
    known_names = set(names)
    seen_connections: set[tuple[str, str, str]] = set()
    for index, raw_connection in enumerate(connections):
        prefix = f"connections[{index}]"
        if not isinstance(raw_connection, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(raw_connection) - ALLOWED_CONNECTION_KEYS)
        if unknown:
            errors.append(f"{prefix} has unsupported keys: {', '.join(unknown)}")
        a = raw_connection.get("a")
        b = raw_connection.get("b")
        relation = raw_connection.get("relation")
        if not isinstance(a, str) or a not in known_names:
            errors.append(f"{prefix}.a must reference an existing component")
        if not isinstance(b, str) or b not in known_names:
            errors.append(f"{prefix}.b must reference an existing component")
        if a == b and isinstance(a, str):
            errors.append(f"{prefix} cannot connect a component to itself")
        if not isinstance(relation, str) or not relation.strip():
            errors.append(f"{prefix}.relation must be a non-empty string")
        if isinstance(a, str) and isinstance(b, str) and isinstance(relation, str):
            key = (a, b, relation)
            reverse = (b, a, relation)
            if key in seen_connections or reverse in seen_connections:
                errors.append(f"{prefix} duplicates an existing connection")
            seen_connections.add(key)

    return errors


def re_safe_name(value: str) -> bool:
    return bool(value) and all(character.isalnum() or character in "_-" for character in value)


def parse_structured_json(text: str) -> dict[str, Any]:
    """Parse exactly one JSON object; markdown fences or prose fail closed."""

    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredSpecError(f"structured output is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise StructuredSpecError("structured output root must be a JSON object")
    errors = validate_structured_spec(value)
    if errors:
        raise StructuredSpecError("structured output rejected:\n- " + "\n- ".join(errors))
    return value


def spec_to_design(spec: Mapping[str, Any]) -> DesignGraph:
    errors = validate_structured_spec(spec)
    if errors:
        raise StructuredSpecError("structured output rejected:\n- " + "\n- ".join(errors))

    design = DesignGraph(title=str(spec["title"]))
    by_name: dict[str, Component] = {}
    for index, raw in enumerate(spec["components"]):
        component_errors: list[str] = []
        geometry = _validate_geometry(raw["geometry"], f"components[{index}].geometry", component_errors)
        transform = _validate_transform(raw.get("transform"), f"components[{index}].transform", component_errors)
        if component_errors or geometry is None or transform is None:
            raise StructuredSpecError("structured output rejected:\n- " + "\n- ".join(component_errors))
        component = Component(
            name=raw["name"],
            params={"geometry": geometry},
            operation=raw.get("operation", "union"),
            transform=transform,
            role=raw.get("role", "body"),
        )
        design.add_component(component)
        by_name[component.name] = component

    for raw in spec.get("connections", []):
        design.connect(by_name[raw["a"]], by_name[raw["b"]], relation=raw["relation"])

    design.metadata.update(
        {
            "research_spec_version": SPEC_VERSION,
            "structured_successor": True,
            "historical_parser_claim": "not_applicable_falsified",
        }
    )
    return design


def compile_structured_json(text: str, *, fn: int = 96) -> str:
    """Strict JSON -> validated DesignGraph -> deterministic OpenSCAD."""

    if not isinstance(fn, int) or isinstance(fn, bool) or not 12 <= fn <= 360:
        raise StructuredSpecError("fn must be an integer in [12, 360]")
    return design_to_scad(spec_to_design(parse_structured_json(text)), fn=fn)
