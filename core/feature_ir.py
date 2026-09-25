"""Experimental editable feature-history IR for NeuroCAD.

This module is intentionally isolated from the verified v1 CSG compiler.
It defines an additive representation for future exact-CAD backends.

Persisted selectors are semantic queries, never raw kernel face or edge indices.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .json_io import strict_json_loads

FEATURE_IR_VERSION = "neurocad-feature-ir-v0alpha1"
MAX_PARAMETERS = 1024
MAX_FEATURES = 1024
MAX_SELECTORS = 4096
MAX_JSON_BYTES = 4 * 1024 * 1024

FEATURE_KINDS = frozenset(
    {
        "datum_plane",
        "datum_axis",
        "primitive_box",
        "primitive_cylinder",
        "sketch",
        "extrude",
        "revolve",
        "boolean_union",
        "boolean_cut",
        "boolean_intersect",
        "fillet",
        "chamfer",
        "linear_pattern",
        "circular_pattern",
        "mirror",
    }
)
SELECTOR_ENTITIES = frozenset({"body", "solid", "face", "edge", "vertex", "wire"})
PARAMETER_UNITS = frozenset({"mm", "deg", "unitless"})
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


@dataclass(frozen=True)
class DesignParameter:
    id: str
    value: float
    unit: str = "mm"
    lower: float | None = None
    upper: float | None = None
    role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntitySelector:
    entity: str
    generated_by: str
    predicates: tuple[dict[str, Any], ...] = ()
    role: str | None = None
    unique: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "generated_by": self.generated_by,
            "predicates": [dict(item) for item in self.predicates],
            "role": self.role,
            "unique": self.unique,
        }


@dataclass(frozen=True)
class Feature:
    id: str
    kind: str
    inputs: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    selectors: tuple[EntitySelector, ...] = ()
    role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "inputs": list(self.inputs),
            "parameters": _json_value(self.parameters),
            "selectors": [selector.to_dict() for selector in self.selectors],
            "role": self.role,
        }


@dataclass(frozen=True)
class FeatureProgram:
    title: str
    parameters: tuple[DesignParameter, ...]
    features: tuple[Feature, ...]
    outputs: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = FEATURE_IR_VERSION
    units: str = "mm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "units": self.units,
            "title": self.title,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "features": [feature.to_dict() for feature in self.features],
            "outputs": list(self.outputs),
            "metadata": _json_value(self.metadata),
        }


@dataclass(frozen=True)
class FeatureIRIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class FeatureIRValidationReport:
    valid: bool
    errors: tuple[FeatureIRIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": [error.to_dict() for error in self.errors]}


class FeatureIRParseError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("invalid NeuroCAD feature IR:\n- " + "\n- ".join(errors))


def _json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _strict_json_error(value: Any, path: str) -> str | None:
    if value is None or isinstance(value, (bool, str)):
        return None
    if isinstance(value, (int, float)):
        return None if _finite(value) else f"{path} contains a non-finite number"
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            error = _strict_json_error(item, f"{path}[{index}]")
            if error:
                return error
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"{path} contains a non-string key"
            error = _strict_json_error(item, f"{path}.{key}")
            if error:
                return error
        return None
    return f"{path} contains unsupported type {type(value).__name__}"


def _vec3(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(_finite(item) for item in value)


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _positive_int(value: Any, minimum: int = 1) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _contract_errors(feature: Feature, index: int) -> list[FeatureIRIssue]:
    path = f"$.features[{index}]"
    parameters = feature.parameters
    errors: list[FeatureIRIssue] = []

    def require(name: str) -> Any:
        if name not in parameters:
            errors.append(FeatureIRIssue("missing_parameter", f"{path}.parameters.{name}", "required"))
            return None
        return parameters[name]

    if feature.kind == "datum_plane":
        for name in ("origin", "normal", "x_axis"):
            value = require(name)
            if value is not None and not _vec3(value):
                errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.{name}", "must be a finite 3-vector"))
    elif feature.kind == "datum_axis":
        for name in ("origin", "direction"):
            value = require(name)
            if value is not None and not _vec3(value):
                errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.{name}", "must be a finite 3-vector"))
    elif feature.kind == "primitive_box":
        size = require("size")
        if size is not None and (not _vec3(size) or any(float(item) <= 0 for item in size)):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.size", "must contain three positive lengths"))
    elif feature.kind == "primitive_cylinder":
        for name in ("radius", "height"):
            value = require(name)
            if value is not None and not _positive(value):
                errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.{name}", "must be positive"))
    elif feature.kind == "sketch":
        plane = require("plane")
        entities = require("entities")
        constraints = require("constraints")
        if plane is not None and not isinstance(plane, str):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.plane", "must be a plane id or XY/XZ/YZ"))
        if entities is not None and not isinstance(entities, list):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.entities", "must be an array"))
        if constraints is not None and not isinstance(constraints, list):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.constraints", "must be an array"))
    elif feature.kind in {"extrude", "revolve"}:
        amount_name = "distance" if feature.kind == "extrude" else "angle_deg"
        amount = require(amount_name)
        operation = require("operation")
        if amount is not None and (
            not _positive(amount) or (feature.kind == "revolve" and float(amount) > 360)
        ):
            message = "must be positive" if feature.kind == "extrude" else "must be in (0, 360]"
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.{amount_name}", message))
        if operation is not None and operation not in {"new", "add", "cut", "intersect"}:
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.operation", "must be new/add/cut/intersect"))
        if not feature.inputs:
            errors.append(FeatureIRIssue("missing_input", f"{path}.inputs", f"{feature.kind} requires a sketch input"))
    elif feature.kind in {"fillet", "chamfer"}:
        amount_name = "radius" if feature.kind == "fillet" else "distance"
        amount = require(amount_name)
        if amount is not None and not _positive(amount):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.{amount_name}", "must be positive"))
        if len(feature.inputs) != 1:
            errors.append(FeatureIRIssue("invalid_input_count", f"{path}.inputs", f"{feature.kind} requires exactly one body input"))
        if not feature.selectors:
            errors.append(FeatureIRIssue("missing_selector", f"{path}.selectors", f"{feature.kind} requires edge selectors"))
        elif any(selector.entity != "edge" for selector in feature.selectors):
            errors.append(FeatureIRIssue("invalid_selector", f"{path}.selectors", f"{feature.kind} selectors must target edges"))
    elif feature.kind == "linear_pattern":
        count, spacing, direction = require("count"), require("spacing"), require("direction")
        if count is not None and not _positive_int(count, 2):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.count", "must be an integer >= 2"))
        if spacing is not None and not _positive(spacing):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.spacing", "must be positive"))
        if direction is not None and not _vec3(direction):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.direction", "must be a finite 3-vector"))
        if len(feature.inputs) != 1:
            errors.append(FeatureIRIssue("invalid_input_count", f"{path}.inputs", "linear_pattern requires exactly one feature input"))
    elif feature.kind == "circular_pattern":
        count, angle, axis = require("count"), require("angle_deg"), require("axis")
        if count is not None and not _positive_int(count, 2):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.count", "must be an integer >= 2"))
        if angle is not None and (not _positive(angle) or float(angle) > 360):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.angle_deg", "must be in (0, 360]"))
        if axis is not None and not _vec3(axis):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.axis", "must be a finite 3-vector"))
        if len(feature.inputs) != 1:
            errors.append(FeatureIRIssue("invalid_input_count", f"{path}.inputs", "circular_pattern requires exactly one feature input"))
    elif feature.kind == "mirror":
        plane = require("plane")
        if plane is not None and not isinstance(plane, str):
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters.plane", "must be a plane id or XY/XZ/YZ"))
        if len(feature.inputs) != 1:
            errors.append(FeatureIRIssue("invalid_input_count", f"{path}.inputs", "mirror requires exactly one feature input"))
    elif feature.kind in {"boolean_union", "boolean_cut", "boolean_intersect"} and len(feature.inputs) < 2:
        errors.append(FeatureIRIssue("invalid_input_count", f"{path}.inputs", f"{feature.kind} requires at least two inputs"))
    return errors


def validate_feature_program(program: FeatureProgram) -> FeatureIRValidationReport:
    errors: list[FeatureIRIssue] = []
    if program.version != FEATURE_IR_VERSION:
        errors.append(FeatureIRIssue("unsupported_version", "$.version", f"expected {FEATURE_IR_VERSION}"))
    if program.units != "mm":
        errors.append(FeatureIRIssue("unsupported_units", "$.units", "canonical feature programs use mm"))
    if not isinstance(program.title, str) or not program.title.strip() or len(program.title) > 4096:
        errors.append(FeatureIRIssue("invalid_title", "$.title", "title must contain 1 to 4096 characters"))
    if len(program.parameters) > MAX_PARAMETERS:
        errors.append(FeatureIRIssue("resource_limit", "$.parameters", f"at most {MAX_PARAMETERS} parameters are supported"))
    if len(program.features) > MAX_FEATURES:
        errors.append(FeatureIRIssue("resource_limit", "$.features", f"at most {MAX_FEATURES} features are supported"))
    if sum(len(feature.selectors) for feature in program.features) > MAX_SELECTORS:
        errors.append(FeatureIRIssue("resource_limit", "$.features[*].selectors", f"at most {MAX_SELECTORS} selectors are supported"))

    parameter_ids: set[str] = set()
    for index, parameter in enumerate(program.parameters):
        path = f"$.parameters[{index}]"
        if not isinstance(parameter.id, str) or ID_RE.fullmatch(parameter.id) is None:
            errors.append(FeatureIRIssue("invalid_id", f"{path}.id", "use letters, digits, underscore or hyphen"))
        elif parameter.id in parameter_ids:
            errors.append(FeatureIRIssue("duplicate_id", f"{path}.id", parameter.id))
        parameter_ids.add(parameter.id)
        if parameter.unit not in PARAMETER_UNITS:
            errors.append(FeatureIRIssue("unsupported_unit", f"{path}.unit", str(parameter.unit)))
        if not _finite(parameter.value):
            errors.append(FeatureIRIssue("invalid_value", f"{path}.value", "must be finite"))
        for name, value in (("lower", parameter.lower), ("upper", parameter.upper)):
            if value is not None and not _finite(value):
                errors.append(FeatureIRIssue("invalid_value", f"{path}.{name}", "must be finite"))
        if parameter.lower is not None and parameter.upper is not None and _finite(parameter.lower) and _finite(parameter.upper):
            if float(parameter.lower) > float(parameter.upper):
                errors.append(FeatureIRIssue("invalid_bounds", path, "lower bound exceeds upper bound"))
        if _finite(parameter.value) and parameter.lower is not None and _finite(parameter.lower):
            if float(parameter.value) < float(parameter.lower):
                errors.append(FeatureIRIssue("out_of_bounds", f"{path}.value", "below lower bound"))
        if _finite(parameter.value) and parameter.upper is not None and _finite(parameter.upper):
            if float(parameter.value) > float(parameter.upper):
                errors.append(FeatureIRIssue("out_of_bounds", f"{path}.value", "above upper bound"))

    seen: set[str] = set()
    feature_map: dict[str, Feature] = {}
    for index, feature in enumerate(program.features):
        path = f"$.features[{index}]"
        if not isinstance(feature.id, str) or ID_RE.fullmatch(feature.id) is None:
            errors.append(FeatureIRIssue("invalid_id", f"{path}.id", "use letters, digits, underscore or hyphen"))
        elif feature.id in seen:
            errors.append(FeatureIRIssue("duplicate_id", f"{path}.id", feature.id))
        if feature.kind not in FEATURE_KINDS:
            errors.append(FeatureIRIssue("unsupported_feature", f"{path}.kind", str(feature.kind)))
        if not isinstance(feature.role, str) or len(feature.role) > 256:
            errors.append(FeatureIRIssue("invalid_role", f"{path}.role", "role must be a string no longer than 256 characters"))
        json_error = _strict_json_error(feature.parameters, f"{path}.parameters")
        if json_error:
            errors.append(FeatureIRIssue("invalid_parameter", f"{path}.parameters", json_error))
        for input_index, input_id in enumerate(feature.inputs):
            if input_id not in seen:
                errors.append(
                    FeatureIRIssue(
                        "forward_or_missing_reference",
                        f"{path}.inputs[{input_index}]",
                        "feature inputs must reference an earlier feature",
                    )
                )
        for selector_index, selector in enumerate(feature.selectors):
            selector_path = f"{path}.selectors[{selector_index}]"
            if selector.entity not in SELECTOR_ENTITIES:
                errors.append(FeatureIRIssue("unsupported_entity", f"{selector_path}.entity", str(selector.entity)))
            if selector.generated_by not in seen:
                errors.append(
                    FeatureIRIssue(
                        "forward_or_missing_reference",
                        f"{selector_path}.generated_by",
                        "selector provenance must reference an earlier feature",
                    )
                )
            if selector.role is not None and (not isinstance(selector.role, str) or len(selector.role) > 256):
                errors.append(FeatureIRIssue("invalid_role", f"{selector_path}.role", "role must be null or a string <= 256 characters"))
            if not isinstance(selector.unique, bool):
                errors.append(FeatureIRIssue("invalid_selector", f"{selector_path}.unique", "must be boolean"))
            for predicate_index, predicate in enumerate(selector.predicates):
                predicate_path = f"{selector_path}.predicates[{predicate_index}]"
                if not isinstance(predicate, dict) or not isinstance(predicate.get("kind"), str):
                    errors.append(FeatureIRIssue("invalid_predicate", predicate_path, "must be an object with a string kind"))
                    continue
                if "index" in predicate or predicate.get("kind") in {"kernel_index", "face_index", "edge_index"}:
                    errors.append(
                        FeatureIRIssue(
                            "unstable_selector",
                            predicate_path,
                            "raw kernel face or edge indices cannot be persisted",
                        )
                    )
                predicate_error = _strict_json_error(predicate, predicate_path)
                if predicate_error:
                    errors.append(FeatureIRIssue("invalid_predicate", predicate_path, predicate_error))
        if feature.kind in FEATURE_KINDS:
            errors.extend(_contract_errors(feature, index))
        seen.add(feature.id)
        feature_map[feature.id] = feature

    if not program.features:
        errors.append(FeatureIRIssue("missing_feature", "$.features", "at least one feature is required"))
    if not program.outputs:
        errors.append(FeatureIRIssue("missing_output", "$.outputs", "at least one output feature is required"))
    elif len(set(program.outputs)) != len(program.outputs):
        errors.append(FeatureIRIssue("duplicate_output", "$.outputs", "output ids must be unique"))
    for index, output in enumerate(program.outputs):
        if output not in feature_map:
            errors.append(FeatureIRIssue("missing_reference", f"$.outputs[{index}]", str(output)))

    metadata_error = _strict_json_error(program.metadata, "$.metadata")
    if metadata_error:
        errors.append(FeatureIRIssue("invalid_metadata", "$.metadata", metadata_error))
    return FeatureIRValidationReport(not errors, tuple(errors))


def serialize_feature_ir_json(program: FeatureProgram, *, pretty: bool = True) -> str:
    report = validate_feature_program(program)
    if not report.valid:
        raise FeatureIRParseError([f"{item.path}: {item.code}: {item.message}" for item in report.errors])
    kwargs: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    if pretty:
        return json.dumps(program.to_dict(), indent=2, **kwargs) + "\n"
    return json.dumps(program.to_dict(), separators=(",", ":"), **kwargs)


def _only_keys(value: dict[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise FeatureIRParseError([f"{path}: unsupported keys: {', '.join(extra)}"])
    if missing:
        raise FeatureIRParseError([f"{path}: missing keys: {', '.join(missing)}"])


def feature_program_from_dict(raw: dict[str, Any]) -> FeatureProgram:
    _only_keys(
        raw,
        {"version", "units", "title", "parameters", "features", "outputs", "metadata"},
        {"version", "units", "title", "parameters", "features", "outputs", "metadata"},
        "$",
    )
    if not isinstance(raw["parameters"], list) or not isinstance(raw["features"], list) or not isinstance(raw["outputs"], list):
        raise FeatureIRParseError(["$: parameters, features and outputs must be arrays"])
    if not isinstance(raw["metadata"], dict):
        raise FeatureIRParseError(["$.metadata: must be an object"])

    parameters: list[DesignParameter] = []
    for index, item in enumerate(raw["parameters"]):
        path = f"$.parameters[{index}]"
        if not isinstance(item, dict):
            raise FeatureIRParseError([f"{path}: must be an object"])
        _only_keys(item, {"id", "value", "unit", "lower", "upper", "role"}, {"id", "value", "unit", "lower", "upper", "role"}, path)
        parameters.append(
            DesignParameter(
                id=item["id"],
                value=item["value"],
                unit=item["unit"],
                lower=item["lower"],
                upper=item["upper"],
                role=item["role"],
            )
        )

    features: list[Feature] = []
    for index, item in enumerate(raw["features"]):
        path = f"$.features[{index}]"
        if not isinstance(item, dict):
            raise FeatureIRParseError([f"{path}: must be an object"])
        _only_keys(item, {"id", "kind", "inputs", "parameters", "selectors", "role"}, {"id", "kind", "inputs", "parameters", "selectors", "role"}, path)
        if not isinstance(item["inputs"], list) or not isinstance(item["parameters"], dict) or not isinstance(item["selectors"], list):
            raise FeatureIRParseError([f"{path}: inputs/selectors must be arrays and parameters must be an object"])
        selectors: list[EntitySelector] = []
        for selector_index, selector_raw in enumerate(item["selectors"]):
            selector_path = f"{path}.selectors[{selector_index}]"
            if not isinstance(selector_raw, dict):
                raise FeatureIRParseError([f"{selector_path}: must be an object"])
            _only_keys(
                selector_raw,
                {"entity", "generated_by", "predicates", "role", "unique"},
                {"entity", "generated_by", "predicates", "role", "unique"},
                selector_path,
            )
            if not isinstance(selector_raw["predicates"], list):
                raise FeatureIRParseError([f"{selector_path}.predicates: must be an array"])
            selectors.append(
                EntitySelector(
                    entity=selector_raw["entity"],
                    generated_by=selector_raw["generated_by"],
                    predicates=tuple(selector_raw["predicates"]),
                    role=selector_raw["role"],
                    unique=selector_raw["unique"],
                )
            )
        features.append(
            Feature(
                id=item["id"],
                kind=item["kind"],
                inputs=tuple(item["inputs"]),
                parameters=dict(item["parameters"]),
                selectors=tuple(selectors),
                role=item["role"],
            )
        )

    program = FeatureProgram(
        title=raw["title"],
        parameters=tuple(parameters),
        features=tuple(features),
        outputs=tuple(raw["outputs"]),
        metadata=dict(raw["metadata"]),
        version=raw["version"],
        units=raw["units"],
    )
    report = validate_feature_program(program)
    if not report.valid:
        raise FeatureIRParseError([f"{item.path}: {item.code}: {item.message}" for item in report.errors])
    return program


def parse_feature_ir_json(text: str) -> FeatureProgram:
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise FeatureIRParseError([f"$: input exceeds {MAX_JSON_BYTES} bytes"])
    try:
        raw = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise FeatureIRParseError([f"line {exc.lineno}, column {exc.colno}: {exc.msg}"]) from exc
    if not isinstance(raw, dict):
        raise FeatureIRParseError(["$: root must be an object"])
    return feature_program_from_dict(raw)
