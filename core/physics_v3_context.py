"""Physics v3 provenance: temperature-aware materials and load combinations."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .physics_context import (
    LOAD_CASE_VERSION,
    PHYSICS_CONTEXT_VERSION,
    canonical_sha256,
    resolve_physics_context,
)

PHYSICS_CONTEXT_V2_VERSION = "neurocad-physics-context-v2"
MATERIAL_CARD_V2_VERSION = "neurocad-material-card-v2"
LOAD_COMBINATION_VERSION = "neurocad-load-combination-v1"
_PORTABLE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}")


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return value


def _only(value: dict[str, Any], *, allowed: set[str], required: set[str], name: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise ValueError(f"{name} has unsupported keys: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{name} is missing keys: {', '.join(missing)}")


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or _PORTABLE_ID.fullmatch(value.strip()) is None:
        raise ValueError(f"{name} must be a portable identifier")
    return value.strip()


def _text(value: Any, name: str, *, maximum: int = 2_048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1 to {maximum} characters")
    return value.strip()


def _revision(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _numeric_mapping(value: Any, name: str, *, allow_empty: bool = False) -> dict[str, float]:
    raw = _object(value, name)
    if len(raw) > 64 or (not raw and not allow_empty):
        raise ValueError(f"{name} must contain {'0 to' if allow_empty else '1 to'} 64 values")
    return {_identifier(key, f"{name} key"): _finite(item, f"{name}.{key}") for key, item in raw.items()}


def _interpolate_material(raw: Any) -> tuple[dict[str, Any], dict[str, float], list[str]]:
    value = _object(raw, "context.material")
    _only(
        value,
        allowed={
            "schema_version",
            "material_id",
            "revision",
            "source",
            "properties",
            "temperature_tables",
            "evaluation_temperature_k",
        },
        required={"schema_version", "material_id", "revision", "source"},
        name="context.material",
    )
    if value["schema_version"] != MATERIAL_CARD_V2_VERSION:
        raise ValueError(f"context.material.schema_version must be {MATERIAL_CARD_V2_VERSION}")
    material_id = _identifier(value["material_id"], "context.material.material_id")
    revision = _revision(value["revision"], "context.material.revision")
    source = _text(value["source"], "context.material.source")
    properties = _numeric_mapping(value.get("properties", {}), "context.material.properties", allow_empty=True)
    raw_tables = _object(value.get("temperature_tables", {}), "context.material.temperature_tables")
    if len(raw_tables) > 64:
        raise ValueError("context.material.temperature_tables supports at most 64 properties")
    if not properties and not raw_tables:
        raise ValueError("context.material requires at least one constant property or temperature table")
    evaluation = value.get("evaluation_temperature_k")
    if raw_tables and evaluation is None:
        raise ValueError("temperature_tables require evaluation_temperature_k")
    evaluation_temperature = None if evaluation is None else _finite(evaluation, "context.material.evaluation_temperature_k", positive=True)
    tables: dict[str, list[dict[str, float]]] = {}
    interpolated: list[str] = []
    resolved = dict(properties)
    for raw_name, raw_points in raw_tables.items():
        name = _identifier(raw_name, "context.material.temperature_tables key")
        if not isinstance(raw_points, list) or not 2 <= len(raw_points) <= 256:
            raise ValueError(f"context.material.temperature_tables.{name} must contain 2 to 256 points")
        points: list[dict[str, float]] = []
        last_temperature: float | None = None
        for index, raw_point in enumerate(raw_points):
            point = _object(raw_point, f"context.material.temperature_tables.{name}[{index}]")
            _only(point, allowed={"temperature_k", "value"}, required={"temperature_k", "value"}, name=f"temperature point {name}[{index}]")
            temperature = _finite(point["temperature_k"], f"{name}[{index}].temperature_k", positive=True)
            property_value = _finite(point["value"], f"{name}[{index}].value")
            if last_temperature is not None and temperature <= last_temperature:
                raise ValueError(f"temperature table {name!r} temperatures must be strictly increasing")
            points.append({"temperature_k": temperature, "value": property_value})
            last_temperature = temperature
        assert evaluation_temperature is not None
        if not points[0]["temperature_k"] <= evaluation_temperature <= points[-1]["temperature_k"]:
            raise ValueError(f"evaluation_temperature_k is outside table {name!r}; extrapolation is not allowed")
        for left, right in zip(points, points[1:], strict=False):
            if evaluation_temperature <= right["temperature_k"]:
                fraction = (evaluation_temperature - left["temperature_k"]) / (right["temperature_k"] - left["temperature_k"])
                resolved[name] = left["value"] + fraction * (right["value"] - left["value"])
                break
        tables[name] = points
        interpolated.append(name)
    if "density_kg_m3" in resolved and resolved["density_kg_m3"] <= 0:
        raise ValueError("resolved density_kg_m3 must be positive")
    card: dict[str, Any] = {
        "schema_version": MATERIAL_CARD_V2_VERSION,
        "material_id": material_id,
        "revision": revision,
        "source": source,
        "properties": properties,
        "temperature_tables": tables,
    }
    if evaluation_temperature is not None:
        card["evaluation_temperature_k"] = evaluation_temperature
    return card, resolved, sorted(interpolated)


def _resolve_combination(raw_cases: Any, raw_combination: Any) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float]]:
    if not isinstance(raw_cases, list) or not 1 <= len(raw_cases) <= 64:
        raise ValueError("context.load_cases must contain 1 to 64 load cases")
    cases: list[dict[str, Any]] = []
    case_by_id: dict[str, dict[str, Any]] = {}
    coordinate_system: str | None = None
    for index, raw in enumerate(raw_cases):
        case = _object(raw, f"context.load_cases[{index}]")
        _only(
            case,
            allowed={"schema_version", "case_id", "coordinate_system", "source", "values"},
            required={"schema_version", "case_id", "coordinate_system", "source", "values"},
            name=f"context.load_cases[{index}]",
        )
        if case["schema_version"] != LOAD_CASE_VERSION:
            raise ValueError(f"context.load_cases[{index}].schema_version must be {LOAD_CASE_VERSION}")
        case_id = _identifier(case["case_id"], f"context.load_cases[{index}].case_id")
        if case_id in case_by_id:
            raise ValueError(f"duplicate load case id {case_id!r}")
        system = _text(case["coordinate_system"], f"context.load_cases[{index}].coordinate_system", maximum=128)
        if coordinate_system is not None and system != coordinate_system:
            raise ValueError("all load cases in a combination must use the same coordinate_system")
        coordinate_system = system
        normalized = {
            "schema_version": LOAD_CASE_VERSION,
            "case_id": case_id,
            "coordinate_system": system,
            "source": _text(case["source"], f"context.load_cases[{index}].source"),
            "values": _numeric_mapping(case["values"], f"context.load_cases[{index}].values"),
        }
        normalized["load_case_sha256"] = canonical_sha256(normalized)
        cases.append(normalized)
        case_by_id[case_id] = normalized

    combination = _object(raw_combination, "context.load_combination")
    _only(
        combination,
        allowed={"schema_version", "combination_id", "source", "coefficients"},
        required={"schema_version", "combination_id", "source", "coefficients"},
        name="context.load_combination",
    )
    if combination["schema_version"] != LOAD_COMBINATION_VERSION:
        raise ValueError(f"context.load_combination.schema_version must be {LOAD_COMBINATION_VERSION}")
    coefficients = _numeric_mapping(combination["coefficients"], "context.load_combination.coefficients")
    unknown = sorted(set(coefficients) - set(case_by_id))
    if unknown:
        raise ValueError(f"load combination references unknown cases: {', '.join(unknown)}")
    combined_values: dict[str, float] = {}
    for case_id, coefficient in coefficients.items():
        for name, value in case_by_id[case_id]["values"].items():
            combined_values[name] = combined_values.get(name, 0.0) + coefficient * value
    resolved_combination = {
        "schema_version": LOAD_COMBINATION_VERSION,
        "combination_id": _identifier(combination["combination_id"], "context.load_combination.combination_id"),
        "coordinate_system": coordinate_system,
        "source": _text(combination["source"], "context.load_combination.source"),
        "coefficients": coefficients,
        "combined_values": combined_values,
    }
    resolved_combination["load_combination_sha256"] = canonical_sha256(resolved_combination)
    return cases, resolved_combination, combined_values


def _check_electro_thermal_geometry(bindings: dict[str, Any], inputs: dict[str, Any], *, model: str) -> None:
    if model != "electro_thermal_wire" or "geometry" not in bindings:
        return
    geometry = bindings["geometry"]
    metrics = geometry["metrics"]
    if metrics["operation"] != "add" or metrics["shape"] != "cylinder":
        raise ValueError("electro_thermal_wire geometry binding requires an additive cylinder component")
    section = metrics.get("section_properties")
    if not isinstance(section, dict) or "area_mm2" not in section:
        raise ValueError("bound cylinder does not expose an exact cross-sectional area")
    area = float(section["area_mm2"])
    length = float(metrics["volume_mm3"]) / area
    derived = {"area_mm2": area, "length_mm": length}
    checked = []
    for name, value in derived.items():
        if name in inputs:
            supplied = _finite(inputs[name], f"inputs.{name}")
            if not math.isclose(supplied, value, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"inputs.{name} contradicts bound component {geometry['component_id']!r}: {supplied!r} != {value!r}")
            checked.append(name)
    geometry["model_inputs_checked"] = sorted(set(geometry.get("model_inputs_checked", [])) | set(checked))


def resolve_physics_context_v3(raw: Any, *, model: str, inputs: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Resolve context v1 unchanged or the Physics v3 context-v2 contract."""

    value = _object(raw, "context")
    if value.get("schema_version") == PHYSICS_CONTEXT_VERSION:
        return resolve_physics_context(value, model=model, inputs=inputs, base_dir=base_dir)
    _only(
        value,
        allowed={"schema_version", "geometry", "material", "load_cases", "load_combination"},
        required={"schema_version"},
        name="context",
    )
    if value["schema_version"] != PHYSICS_CONTEXT_V2_VERSION:
        raise ValueError(f"context.schema_version must be {PHYSICS_CONTEXT_VERSION} or {PHYSICS_CONTEXT_V2_VERSION}")
    if set(value) == {"schema_version"}:
        raise ValueError("context requires geometry, material, or a load combination")
    if ("load_cases" in value) != ("load_combination" in value):
        raise ValueError("context.load_cases and context.load_combination must be provided together")

    v1_context: dict[str, Any] = {"schema_version": PHYSICS_CONTEXT_VERSION}
    material_card: dict[str, Any] | None = None
    resolved_properties: dict[str, float] | None = None
    interpolated: list[str] = []
    if "geometry" in value:
        v1_context["geometry"] = value["geometry"]
    if "material" in value:
        material_card, resolved_properties, interpolated = _interpolate_material(value["material"])
        v1_context["material"] = {
            "schema_version": "neurocad-material-card-v1",
            "material_id": material_card["material_id"],
            "revision": material_card["revision"],
            "source": material_card["source"],
            "properties": resolved_properties,
            **(
                {"temperature_k": material_card["evaluation_temperature_k"]}
                if "evaluation_temperature_k" in material_card
                else {}
            ),
        }
    cases: list[dict[str, Any]] | None = None
    combination: dict[str, Any] | None = None
    if "load_cases" in value:
        cases, combination, combined_values = _resolve_combination(value["load_cases"], value["load_combination"])
        v1_context["load_case"] = {
            "schema_version": LOAD_CASE_VERSION,
            "case_id": combination["combination_id"],
            "coordinate_system": combination["coordinate_system"],
            "source": combination["source"],
            "values": combined_values,
        }
    resolved_v1 = resolve_physics_context(v1_context, model=model, inputs=inputs, base_dir=base_dir)
    bindings: dict[str, Any] = {"schema_version": PHYSICS_CONTEXT_V2_VERSION}
    if "geometry" in resolved_v1:
        bindings["geometry"] = resolved_v1["geometry"]
    if material_card is not None and resolved_properties is not None:
        used = resolved_v1["material"]["properties_used"]
        bindings["material"] = {
            **material_card,
            "material_card_sha256": canonical_sha256(material_card),
            "resolved_properties": resolved_properties,
            "interpolated_properties": interpolated,
            "properties_used": used,
            "resolved_material_sha256": resolved_v1["material"]["material_card_sha256"],
        }
    if cases is not None and combination is not None:
        bindings["load_cases"] = cases
        bindings["load_combination"] = {
            **combination,
            "values_used": resolved_v1["load_case"]["values_used"],
            "resolved_load_case_sha256": resolved_v1["load_case"]["load_case_sha256"],
        }
    bindings["warnings"] = list(resolved_v1["warnings"])
    _check_electro_thermal_geometry(bindings, inputs, model=model)
    bindings["resolved_v1_binding_sha256"] = resolved_v1["binding_sha256"]
    bindings["binding_sha256"] = canonical_sha256({key: item for key, item in bindings.items() if key != "binding_sha256"})
    return bindings
