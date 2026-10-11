"""Traceable bindings for NeuroCAD analytical-physics reports.

The analytical models in :mod:`core.physics` deliberately accept explicit
numbers.  This module adds the missing provenance layer: a result can be bound
to one exact agent-project component, a versioned material card, and a named
load case.  Bindings are hashed, checked for contradictory inputs, and can be
re-verified after the CAD project changes.

The geometry metrics below describe the selected primitive in isolation.  They
are not a Boolean evaluation of its complete part or assembly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .agentic import AGENT_PROJECT_VERSION, MAX_PROJECT_BYTES, AgentComponent, parse_agent_plan
from .ir import Node, Primitive, Transform, program_node_bounds
from .json_io import read_bounded_utf8, strict_json_loads

PHYSICS_CONTEXT_VERSION = "neurocad-physics-context-v1"
MATERIAL_CARD_VERSION = "neurocad-material-card-v1"
LOAD_CASE_VERSION = "neurocad-load-case-v1"
PHYSICS_VERIFICATION_VERSION = "neurocad-physics-verification-v1"
_PORTABLE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}")


class StalePhysicsBindingError(ValueError):
    """Raised when a request names a geometry hash that is no longer current."""


def canonical_sha256(value: Any) -> str:
    """Hash strict canonical JSON without accepting NaN or infinity."""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return value


def _only_keys(value: dict[str, Any], *, allowed: set[str], required: set[str], name: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise ValueError(f"{name} has unsupported keys: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{name} is missing keys: {', '.join(missing)}")


def _text(value: Any, name: str, *, maximum: int = 2_048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1 to {maximum} characters")
    return value.strip()


def _identifier(value: Any, name: str) -> str:
    result = _text(value, name, maximum=128)
    if _PORTABLE_ID.fullmatch(result) is None:
        raise ValueError(f"{name} must be a portable identifier")
    return result


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _revision(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _canonical_component(component: AgentComponent) -> dict[str, Any]:
    """Return only fields whose change can alter geometry or assembly meaning."""

    return {
        "component_id": component.id,
        "part": component.part,
        "operation": component.operation,
        "shape": component.shape,
        "parameters": component.parameters,
        "translate_mm": list(component.translate),
        "rotate_degrees": list(component.rotate),
    }


def component_geometry_sha256(component: AgentComponent) -> str:
    return canonical_sha256(_canonical_component(component))


def _rotation_matrix(degrees: tuple[float, float, float]) -> tuple[tuple[float, float, float], ...]:
    rx, ry, rz = (math.radians(value) for value in degrees)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def _world_point(local: tuple[float, float, float], component: AgentComponent) -> list[float]:
    matrix = _rotation_matrix(component.rotate)
    return [sum(matrix[row][column] * local[column] for column in range(3)) + component.translate[row] for row in range(3)]


def component_geometry_metrics(component: AgentComponent) -> dict[str, Any]:
    """Calculate exact primitive-level metrics for supported agent geometry."""

    parameters = component.parameters
    shape = component.shape
    volume: float
    surface_area: float
    local_centroid = (0.0, 0.0, 0.0)
    section: dict[str, Any] | None = None

    if shape in {"box", "rounded_box"}:
        width, depth, height = (_finite(item, f"{shape}.size", positive=True) for item in parameters["size"])
        if shape == "box":
            profile_area = width * depth
            profile_perimeter = 2.0 * (width + depth)
            section = {
                "reference_plane": "local x-y centroidal section",
                "area_mm2": profile_area,
                "second_moment_x_mm4": width * depth**3 / 12.0,
                "second_moment_y_mm4": depth * width**3 / 12.0,
                "polar_second_moment_mm4": width * depth * (width**2 + depth**2) / 12.0,
            }
        else:
            radius = _finite(parameters["radius"], "rounded_box.radius")
            if radius < 0 or radius > min(width, depth) / 2.0:
                raise ValueError("rounded_box.radius is outside the supported profile")
            profile_area = width * depth - (4.0 - math.pi) * radius**2
            profile_perimeter = 2.0 * (width + depth) + 2.0 * (math.pi - 4.0) * radius
        volume = profile_area * height
        surface_area = 2.0 * profile_area + profile_perimeter * height
    elif shape == "sphere":
        radius = _finite(parameters["radius"], "sphere.radius", positive=True)
        volume = 4.0 * math.pi * radius**3 / 3.0
        surface_area = 4.0 * math.pi * radius**2
        section = {
            "reference_plane": "great-circle centroidal section",
            "area_mm2": math.pi * radius**2,
            "second_moment_x_mm4": math.pi * radius**4 / 4.0,
            "second_moment_y_mm4": math.pi * radius**4 / 4.0,
            "polar_second_moment_mm4": math.pi * radius**4 / 2.0,
        }
    elif shape == "cylinder":
        radius = _finite(parameters["radius"], "cylinder.radius", positive=True)
        height = _finite(parameters["height"], "cylinder.height", positive=True)
        volume = math.pi * radius**2 * height
        surface_area = 2.0 * math.pi * radius * (radius + height)
        section = {
            "reference_plane": "local x-y centroidal section",
            "area_mm2": math.pi * radius**2,
            "second_moment_x_mm4": math.pi * radius**4 / 4.0,
            "second_moment_y_mm4": math.pi * radius**4 / 4.0,
            "polar_second_moment_mm4": math.pi * radius**4 / 2.0,
        }
    elif shape == "cone":
        radius_1 = _finite(parameters["r1"], "cone.r1")
        radius_2 = _finite(parameters["r2"], "cone.r2")
        height = _finite(parameters["height"], "cone.height", positive=True)
        if radius_1 < 0 or radius_2 < 0 or radius_1 + radius_2 == 0:
            raise ValueError("cone radii must be non-negative and not both zero")
        radius_sum = radius_1**2 + radius_1 * radius_2 + radius_2**2
        volume = math.pi * height * radius_sum / 3.0
        slant = math.hypot(radius_1 - radius_2, height)
        surface_area = math.pi * (radius_1 + radius_2) * slant + math.pi * (radius_1**2 + radius_2**2)
        centroid_from_lower = height * (radius_1**2 + 2.0 * radius_1 * radius_2 + 3.0 * radius_2**2) / (4.0 * radius_sum)
        local_centroid = (0.0, 0.0, centroid_from_lower - height / 2.0)
        reference_radius = max(radius_1, radius_2)
        section = {
            "reference_plane": "larger end-face section",
            "area_mm2": math.pi * reference_radius**2,
            "second_moment_x_mm4": math.pi * reference_radius**4 / 4.0,
            "second_moment_y_mm4": math.pi * reference_radius**4 / 4.0,
            "polar_second_moment_mm4": math.pi * reference_radius**4 / 2.0,
        }
    elif shape == "torus":
        major = _finite(parameters["major_radius"], "torus.major_radius", positive=True)
        minor = _finite(parameters["minor_radius"], "torus.minor_radius", positive=True)
        if minor >= major:
            raise ValueError("torus.minor_radius must be smaller than major_radius")
        volume = 2.0 * math.pi**2 * major * minor**2
        surface_area = 4.0 * math.pi**2 * major * minor
    else:  # pragma: no cover - AgentComponent rejects unsupported shapes
        raise ValueError(f"unsupported component shape {shape!r}")

    node = Node(
        component.id,
        primitive=Primitive(component.shape, component.parameters),
        transform=Transform(translate=component.translate, rotate=component.rotate),
        role="void" if component.operation == "subtract" else "body",
    )
    lower, upper = program_node_bounds(node, {component.id: node})
    result: dict[str, Any] = {
        "scope": "isolated primitive before Boolean assembly evaluation",
        "shape": shape,
        "operation": component.operation,
        "volume_mm3": volume,
        "surface_area_mm2": surface_area,
        "centroid_mm": _world_point(local_centroid, component),
        "bounding_box_mm": {
            "minimum": list(lower),
            "maximum": list(upper),
            "dimensions": [upper[index] - lower[index] for index in range(3)],
        },
    }
    if section is not None:
        result["section_properties"] = section
    return result


def _read_agent_component(project_file: Path, component_id: str) -> tuple[dict[str, Any], AgentComponent]:
    raw = strict_json_loads(read_bounded_utf8(project_file, max_bytes=MAX_PROJECT_BYTES, label="agent project"))
    state = _object(raw, "agent project")
    if state.get("schema_version") != AGENT_PROJECT_VERSION:
        raise ValueError(f"geometry.agent_project must use {AGENT_PROJECT_VERSION}")
    plan = parse_agent_plan(state.get("plan"))
    component = next((item for item in plan.components if item.id == component_id), None)
    if component is None:
        raise ValueError(f"component {component_id!r} does not exist in the bound agent project")
    return state, component


def _resolve_geometry(raw: Any, base_dir: Path) -> tuple[dict[str, Any], AgentComponent]:
    value = _object(raw, "context.geometry")
    _only_keys(
        value,
        allowed={"agent_project", "component_id", "expected_geometry_sha256"},
        required={"agent_project", "component_id"},
        name="context.geometry",
    )
    requested_path = _text(value["agent_project"], "context.geometry.agent_project", maximum=4_096)
    project_file = Path(requested_path).expanduser()
    if not project_file.is_absolute():
        project_file = base_dir / project_file
    project_file = project_file.resolve()
    component_id = _identifier(value["component_id"], "context.geometry.component_id")
    state, component = _read_agent_component(project_file, component_id)
    observed_hash = component_geometry_sha256(component)
    expected_hash = value.get("expected_geometry_sha256")
    if expected_hash is not None:
        expected_hash = _text(expected_hash, "context.geometry.expected_geometry_sha256", maximum=64).lower()
        if re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
            raise ValueError("context.geometry.expected_geometry_sha256 must be a SHA-256 hex digest")
        if expected_hash != observed_hash:
            raise StalePhysicsBindingError(
                f"geometry binding is stale for component {component_id!r}: expected {expected_hash}, observed {observed_hash}"
            )
    return (
        {
            "source_type": "neurocad-agent-component-v1",
            "agent_project": str(project_file),
            "project_id": _text(state.get("project_id"), "agent project project_id", maximum=256),
            "project_revision": _revision(state.get("revision"), "agent project revision"),
            "component_id": component_id,
            "geometry_sha256": observed_hash,
            "geometry_status": "current",
            "metrics": component_geometry_metrics(component),
        },
        component,
    )


def _numeric_mapping(value: Any, name: str) -> dict[str, float]:
    raw = _object(value, name)
    if not 1 <= len(raw) <= 64:
        raise ValueError(f"{name} must contain 1 to 64 explicit numeric values")
    result: dict[str, float] = {}
    for key, item in raw.items():
        result[_identifier(key, f"{name} key")] = _finite(item, f"{name}.{key}")
    return result


def _resolve_material(raw: Any, inputs: dict[str, Any]) -> dict[str, Any]:
    value = _object(raw, "context.material")
    _only_keys(
        value,
        allowed={"schema_version", "material_id", "revision", "source", "properties", "temperature_k"},
        required={"schema_version", "material_id", "revision", "source", "properties"},
        name="context.material",
    )
    if value["schema_version"] != MATERIAL_CARD_VERSION:
        raise ValueError(f"context.material.schema_version must be {MATERIAL_CARD_VERSION}")
    material_id = _identifier(value["material_id"], "context.material.material_id")
    revision = _revision(value["revision"], "context.material.revision")
    source = _text(value["source"], "context.material.source")
    properties = _numeric_mapping(value["properties"], "context.material.properties")
    if "density_kg_m3" in properties and properties["density_kg_m3"] <= 0:
        raise ValueError("context.material.properties.density_kg_m3 must be positive")
    temperature = None if "temperature_k" not in value else _finite(value["temperature_k"], "context.material.temperature_k", positive=True)
    used = sorted(set(properties) & set(inputs))
    for name in used:
        input_value = _finite(inputs[name], f"inputs.{name}")
        if not math.isclose(input_value, properties[name], rel_tol=1e-12, abs_tol=0.0):
            raise ValueError(f"inputs.{name} contradicts material card {material_id!r}: {input_value!r} != {properties[name]!r}")
    card = {
        "schema_version": MATERIAL_CARD_VERSION,
        "material_id": material_id,
        "revision": revision,
        "source": source,
        "properties": properties,
        **({"temperature_k": temperature} if temperature is not None else {}),
    }
    return {**card, "material_card_sha256": canonical_sha256(card), "properties_used": used}


def _resolve_load_case(raw: Any, inputs: dict[str, Any]) -> dict[str, Any]:
    value = _object(raw, "context.load_case")
    _only_keys(
        value,
        allowed={"schema_version", "case_id", "coordinate_system", "source", "values"},
        required={"schema_version", "case_id", "coordinate_system", "source", "values"},
        name="context.load_case",
    )
    if value["schema_version"] != LOAD_CASE_VERSION:
        raise ValueError(f"context.load_case.schema_version must be {LOAD_CASE_VERSION}")
    case_id = _identifier(value["case_id"], "context.load_case.case_id")
    coordinate_system = _text(value["coordinate_system"], "context.load_case.coordinate_system", maximum=128)
    source = _text(value["source"], "context.load_case.source")
    loads = _numeric_mapping(value["values"], "context.load_case.values")
    used = sorted(set(loads) & set(inputs))
    for name in used:
        input_value = _finite(inputs[name], f"inputs.{name}")
        if not math.isclose(input_value, loads[name], rel_tol=1e-12, abs_tol=0.0):
            raise ValueError(f"inputs.{name} contradicts load case {case_id!r}: {input_value!r} != {loads[name]!r}")
    load_case = {
        "schema_version": LOAD_CASE_VERSION,
        "case_id": case_id,
        "coordinate_system": coordinate_system,
        "source": source,
        "values": loads,
    }
    return {**load_case, "load_case_sha256": canonical_sha256(load_case), "values_used": used}


def _check_geometry_model_inputs(
    component: AgentComponent,
    metrics: dict[str, Any],
    *,
    model: str,
    inputs: dict[str, Any],
) -> list[str]:
    """Reject exact geometry/model contradictions for supported mappings."""

    if component.operation != "add":
        return []
    derived: dict[str, float] = {}
    if model == "circular_shaft_torsion":
        if component.shape != "cylinder":
            raise ValueError("circular_shaft_torsion geometry binding requires an additive cylinder component")
        derived = {
            "outer_diameter_mm": 2.0 * float(component.parameters["radius"]),
            "length_mm": float(component.parameters["height"]),
        }
    elif model == "hydrostatic_buoyancy":
        derived = {"displaced_volume_mm3": float(metrics["volume_mm3"])}
    elif model == "lumped_thermal_transient":
        derived = {
            "volume_mm3": float(metrics["volume_mm3"]),
            "surface_area_mm2": float(metrics["surface_area_mm2"]),
        }

    checked = sorted(set(derived) & set(inputs))
    for name in checked:
        input_value = _finite(inputs[name], f"inputs.{name}")
        if not math.isclose(input_value, derived[name], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"inputs.{name} contradicts bound component {component.id!r}: {input_value!r} != {derived[name]!r}")
    return checked


def resolve_physics_context(raw: Any, *, model: str, inputs: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Validate and resolve a context object into immutable report bindings."""

    value = _object(raw, "context")
    _only_keys(
        value,
        allowed={"schema_version", "geometry", "material", "load_case"},
        required={"schema_version"},
        name="context",
    )
    if value["schema_version"] != PHYSICS_CONTEXT_VERSION:
        raise ValueError(f"context.schema_version must be {PHYSICS_CONTEXT_VERSION}")
    if not set(value) - {"schema_version"}:
        raise ValueError("context requires at least one geometry, material, or load_case binding")

    bindings: dict[str, Any] = {"schema_version": PHYSICS_CONTEXT_VERSION}
    component: AgentComponent | None = None
    if "geometry" in value:
        bindings["geometry"], component = _resolve_geometry(value["geometry"], base_dir)
        bindings["geometry"]["model_inputs_checked"] = _check_geometry_model_inputs(
            component,
            bindings["geometry"]["metrics"],
            model=model,
            inputs=inputs,
        )
    if "material" in value:
        bindings["material"] = _resolve_material(value["material"], inputs)
    if "load_case" in value:
        bindings["load_case"] = _resolve_load_case(value["load_case"], inputs)

    warnings: list[str] = []
    material = bindings.get("material")
    if material is not None:
        if not material["properties_used"]:
            warnings.append("material card is provenance-only for this model; no card property name matched a model input")
        if component is not None and component.operation == "add" and "density_kg_m3" in material["properties"]:
            volume_mm3 = bindings["geometry"]["metrics"]["volume_mm3"]
            bindings["geometry"]["metrics"]["material_mass_kg"] = material["properties"]["density_kg_m3"] * volume_mm3 * 1e-9
    load_case = bindings.get("load_case")
    if load_case is not None and not load_case["values_used"]:
        warnings.append("load case is provenance-only for this model; no load value name matched a model input")
    if component is not None and component.operation == "subtract":
        warnings.append("bound component is subtractive; primitive metrics describe the isolated void, not material mass")
    bindings["warnings"] = warnings
    bindings["binding_sha256"] = canonical_sha256({key: value for key, value in bindings.items() if key != "binding_sha256"})
    return bindings


def verify_physics_report(raw: Any) -> dict[str, Any]:
    """Compare a saved bound result with the component currently on disk."""

    report = _object(raw, "physics report")
    bindings = _object(report.get("bindings"), "physics report bindings")
    geometry = _object(bindings.get("geometry"), "physics report geometry binding")
    if geometry.get("source_type") != "neurocad-agent-component-v1":
        raise ValueError("physics report does not contain a verifiable agent-component binding")
    project_file = Path(_text(geometry.get("agent_project"), "physics report agent_project", maximum=4_096))
    component_id = _identifier(geometry.get("component_id"), "physics report component_id")
    expected_hash = _text(geometry.get("geometry_sha256"), "physics report geometry_sha256", maximum=64).lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
        raise ValueError("physics report geometry_sha256 must be a SHA-256 hex digest")

    result: dict[str, Any] = {
        "schema_version": PHYSICS_VERIFICATION_VERSION,
        "report_schema_version": report.get("schema_version"),
        "agent_project": str(project_file),
        "component_id": component_id,
        "expected_geometry_sha256": expected_hash,
    }
    try:
        state, component = _read_agent_component(project_file, component_id)
    except (OSError, TypeError, ValueError) as exc:
        return {**result, "status": "unavailable", "current": False, "reason": str(exc)}
    observed_hash = component_geometry_sha256(component)
    current = observed_hash == expected_hash
    return {
        **result,
        "status": "current" if current else "stale",
        "current": current,
        "observed_geometry_sha256": observed_hash,
        "observed_project_revision": state.get("revision"),
        "reason": None if current else "bound component geometry changed after the physics result was recorded",
    }
