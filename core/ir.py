from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, cast

IR_VERSION = "neurocad-ir-v1"
PRIMITIVES = {"box", "rounded_box", "sphere", "cylinder", "cone", "torus"}
COMPOSITIONS = {"union", "difference", "intersection"}
CONSTRAINT_KINDS = {"dimension", "coincident", "offset", "child_count", "bounds"}
MAX_NODES = 1024
MAX_CONSTRAINTS = 1024
MAX_HIERARCHY_DEPTH = 128
MAX_ROLE_LENGTH = 256
Vec3 = tuple[float, float, float]


def _vec3(values: Iterable[float]) -> Vec3:
    items = tuple(values)
    if len(items) != 3:
        raise ValueError("expected exactly three values")
    return float(items[0]), float(items[1]), float(items[2])


def _strict_json_error(value: Any, path: str) -> str | None:
    """Return the first reason a value is not deterministic, finite JSON data."""

    if value is None or isinstance(value, (bool, str)):
        return None
    if isinstance(value, (int, float)):
        return None if _finite_number(value) else f"{path} contains a non-finite or out-of-range number"
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            error = _strict_json_error(item, f"{path}[{index}]")
            if error:
                return error
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"{path} contains a non-string object key"
            error = _strict_json_error(item, f"{path}.{key}")
            if error:
                return error
        return None
    return f"{path} contains unsupported value type {type(value).__name__}"


@dataclass(frozen=True)
class Transform:
    translate: Vec3 = (0.0, 0.0, 0.0)
    rotate: Vec3 = (0.0, 0.0, 0.0)
    scale: Vec3 = (1.0, 1.0, 1.0)

    def to_dict(self) -> dict[str, list[float]]:
        return {
            "translate": list(self.translate),
            "rotate": list(self.rotate),
            "scale": list(self.scale),
        }


@dataclass(frozen=True)
class Primitive:
    kind: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "parameters": _json_value(self.parameters)}


@dataclass(frozen=True)
class Node:
    id: str
    primitive: Primitive | None = None
    composition: str | None = None
    children: tuple[str, ...] = ()
    transform: Transform = field(default_factory=Transform)
    role: str = "body"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "transform": self.transform.to_dict(),
            "role": self.role,
        }
        if self.primitive is not None:
            result["primitive"] = self.primitive.to_dict()
        if self.composition is not None:
            result["composition"] = self.composition
            result["children"] = list(self.children)
        return result


@dataclass(frozen=True)
class Constraint:
    kind: str
    target: str | None = None
    reference: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    tolerance: float = 1e-6

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "parameters": _json_value(self.parameters),
            "tolerance": self.tolerance,
        }
        if self.target is not None:
            result["target"] = self.target
        if self.reference is not None:
            result["reference"] = self.reference
        return result


@dataclass(frozen=True)
class CADProgram:
    title: str
    nodes: tuple[Node, ...]
    roots: tuple[str, ...]
    constraints: tuple[Constraint, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = IR_VERSION
    units: str = "mm"

    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "units": self.units,
            "title": self.title,
            "nodes": [node.to_dict() for node in self.nodes],
            "roots": list(self.roots),
            "constraints": [constraint.to_dict() for constraint in self.constraints],
            "metadata": _json_value(self.metadata),
        }


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class IRValidationReport:
    valid: bool
    errors: tuple[ValidationIssue, ...]
    constraint_results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
            "constraint_results": [_json_value(result) for result in self.constraint_results],
        }


def _json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _finite_vector(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(_finite_number(item) for item in value)


def _primitive_errors(node: Node, path: str) -> list[ValidationIssue]:
    if node.primitive is None:
        return [ValidationIssue("invalid_node_kind", path, "primitive is missing")]
    if not isinstance(node.primitive, Primitive):
        return [ValidationIssue("invalid_node_kind", f"{path}.primitive", "must be a Primitive")]
    primitive = node.primitive
    parameters = primitive.parameters
    errors: list[ValidationIssue] = []
    if not isinstance(primitive.kind, str) or primitive.kind not in PRIMITIVES:
        return [ValidationIssue("unsupported_primitive", f"{path}.primitive.kind", str(primitive.kind))]
    if not isinstance(parameters, dict):
        return [ValidationIssue("invalid_parameter", f"{path}.primitive.parameters", "must be an object")]

    expected_parameters = {
        "box": {"size"},
        "rounded_box": {"size", "radius"},
        "sphere": {"radius"},
        "cylinder": {"radius", "height"},
        "cone": {"r1", "r2", "height"},
        "torus": {"major_radius", "minor_radius"},
    }[primitive.kind]
    actual_parameters = set(parameters)
    if actual_parameters != expected_parameters:
        missing = sorted(expected_parameters - actual_parameters)
        unexpected = sorted(str(key) for key in actual_parameters - expected_parameters)
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        errors.append(
            ValidationIssue(
                "invalid_parameter",
                f"{path}.primitive.parameters",
                "; ".join(details),
            )
        )
    json_error = _strict_json_error(parameters, f"{path}.primitive.parameters")
    if json_error:
        errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters", json_error))

    def positive(name: str, *, allow_zero: bool = False) -> float | None:
        raw = parameters.get(name)
        if not _finite_number(raw):
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.{name}", "must be finite"))
            return None
        value = float(cast(int | float, raw))
        invalid = value < 0 if allow_zero else value <= 0
        if invalid:
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.{name}", "must be positive"))
            return None
        return value

    if primitive.kind in {"box", "rounded_box"}:
        size = parameters.get("size")
        valid_size = True
        size_values: tuple[float, float, float] | None = None
        if not isinstance(size, (list, tuple)) or len(size) != 3:
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.size", "must contain three lengths"))
            valid_size = False
        elif any(not _finite_number(item) or float(item) <= 0 for item in size):
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.size", "all lengths must be positive"))
            valid_size = False
        else:
            size_values = float(size[0]), float(size[1]), float(size[2])
        if primitive.kind == "rounded_box":
            radius = positive("radius", allow_zero=True)
            if radius is not None and valid_size and size_values is not None and radius > min(size_values[0], size_values[1]) / 2:
                errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.radius", "exceeds half the planar size"))
    elif primitive.kind == "sphere":
        positive("radius")
    elif primitive.kind == "cylinder":
        positive("radius")
        positive("height")
    elif primitive.kind == "cone":
        r1 = positive("r1", allow_zero=True)
        r2 = positive("r2", allow_zero=True)
        positive("height")
        if r1 == 0 and r2 == 0:
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters", "cone cannot have two zero radii"))
    elif primitive.kind == "torus":
        major = positive("major_radius")
        minor = positive("minor_radius")
        if major is not None and minor is not None and minor >= major:
            errors.append(ValidationIssue("invalid_parameter", f"{path}.primitive.parameters.minor_radius", "must be smaller than major_radius"))
    return errors


def validate_program(program: CADProgram) -> IRValidationReport:
    errors: list[ValidationIssue] = []
    results: list[dict[str, Any]] = []
    if program.version != IR_VERSION:
        errors.append(ValidationIssue("unsupported_version", "$.version", f"expected {IR_VERSION}"))
    if program.units != "mm":
        errors.append(ValidationIssue("unsupported_units", "$.units", "canonical programs use mm"))
    if not isinstance(program.title, str) or not program.title.strip():
        errors.append(ValidationIssue("missing_title", "$.title", "title must be non-empty"))
    elif len(program.title) > 4096:
        errors.append(ValidationIssue("title_too_long", "$.title", "title is limited to 4096 characters"))
    nodes = program.nodes if isinstance(program.nodes, (list, tuple)) else ()
    constraints = program.constraints if isinstance(program.constraints, (list, tuple)) else ()
    if not isinstance(program.nodes, (list, tuple)):
        errors.append(ValidationIssue("invalid_nodes", "$.nodes", "nodes must be an array"))
    if not isinstance(program.constraints, (list, tuple)):
        errors.append(ValidationIssue("invalid_constraints", "$.constraints", "constraints must be an array"))
    if len(nodes) > MAX_NODES:
        errors.append(ValidationIssue("resource_limit", "$.nodes", f"at most {MAX_NODES} nodes are supported"))
    if len(constraints) > MAX_CONSTRAINTS:
        errors.append(ValidationIssue("resource_limit", "$.constraints", f"at most {MAX_CONSTRAINTS} constraints are supported"))
    if not isinstance(program.metadata, dict):
        errors.append(ValidationIssue("invalid_metadata", "$.metadata", "metadata must be an object"))
    else:
        json_error = _strict_json_error(program.metadata, "$.metadata")
        if json_error:
            errors.append(ValidationIssue("invalid_metadata", "$.metadata", json_error))

    node_map: dict[str, Node] = {}
    children_by_id: dict[str, tuple[str, ...]] = {}
    for index, node in enumerate(nodes):
        path = f"$.nodes[{index}]"
        if not isinstance(node, Node):
            errors.append(ValidationIssue("invalid_node", path, "must be a Node"))
            continue
        valid_id = isinstance(node.id, str) and bool(node.id) and len(node.id) <= 128
        if not valid_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in str(node.id)):
            errors.append(ValidationIssue("invalid_id", f"{path}.id", "use letters, digits, underscore, or hyphen"))
            continue
        if node.id in node_map:
            errors.append(ValidationIssue("duplicate_id", f"{path}.id", node.id))
            continue
        node_map[node.id] = node
        if not isinstance(node.children, (list, tuple)) or any(not isinstance(child, str) for child in node.children):
            errors.append(ValidationIssue("invalid_children", f"{path}.children", "children must be node ids"))
            children_by_id[node.id] = ()
        else:
            children_by_id[node.id] = tuple(node.children)
        is_leaf = node.primitive is not None
        is_group = node.composition is not None
        if is_leaf == is_group:
            errors.append(ValidationIssue("invalid_node_kind", path, "node must be exactly one of primitive or composition"))
        if is_leaf:
            if children_by_id[node.id]:
                errors.append(ValidationIssue("leaf_has_children", f"{path}.children", "primitive nodes cannot have children"))
            errors.extend(_primitive_errors(node, path))
        if is_group:
            if not isinstance(node.composition, str) or node.composition not in COMPOSITIONS:
                errors.append(ValidationIssue("invalid_composition", f"{path}.composition", str(node.composition)))
            if not children_by_id[node.id]:
                errors.append(ValidationIssue("empty_group", f"{path}.children", "composition requires children"))
            if node.composition == "difference" and len(children_by_id[node.id]) < 2:
                errors.append(ValidationIssue("invalid_difference", f"{path}.children", "difference requires at least two children"))
        if not isinstance(node.role, str) or not node.role.strip():
            errors.append(ValidationIssue("invalid_role", f"{path}.role", "role must be a non-empty string"))
        elif len(node.role) > MAX_ROLE_LENGTH:
            errors.append(ValidationIssue("invalid_role", f"{path}.role", f"role is limited to {MAX_ROLE_LENGTH} characters"))
        valid_transform = isinstance(node.transform, Transform) and all(
            _finite_vector(vector) for vector in (node.transform.translate, node.transform.rotate, node.transform.scale)
        )
        if not valid_transform:
            errors.append(ValidationIssue("invalid_transform", f"{path}.transform", "vectors must have three finite values"))
        elif any(float(value) == 0 for value in node.transform.scale):
            errors.append(ValidationIssue("invalid_transform", f"{path}.transform.scale", "scale cannot contain zero"))

    parents: dict[str, str] = {}
    for node_id, children in children_by_id.items():
        for child in children:
            if child not in node_map:
                errors.append(ValidationIssue("missing_reference", f"$.nodes[{node_id}].children", child))
            elif child in parents:
                errors.append(ValidationIssue("multiple_parents", f"$.nodes[{node_id}].children", child))
            else:
                parents[child] = node_id
    roots = tuple(program.roots) if isinstance(program.roots, (list, tuple)) else ()
    if not isinstance(program.roots, (list, tuple)) or any(not isinstance(root, str) for root in roots):
        errors.append(ValidationIssue("invalid_roots", "$.roots", "roots must be node ids"))
        roots = tuple(root for root in roots if isinstance(root, str))
    for index, root in enumerate(roots):
        if root not in node_map:
            errors.append(ValidationIssue("missing_reference", f"$.roots[{index}]", root))
        if root in parents:
            errors.append(ValidationIssue("root_has_parent", f"$.roots[{index}]", root))
    if len(set(roots)) != len(roots):
        errors.append(ValidationIssue("duplicate_root", "$.roots", "roots must be unique"))
    if not roots:
        errors.append(ValidationIssue("missing_root", "$.roots", "at least one root is required"))

    visiting: set[str] = set()
    visited: set[str] = set()
    depth_exceeded: set[str] = set()
    cycle_nodes: set[str] = set()
    for root in roots:
        stack: list[tuple[str, bool, int]] = [(root, False, 1)]
        while stack:
            node_id, exiting, depth = stack.pop()
            if node_id not in node_map:
                continue
            if exiting:
                visiting.discard(node_id)
                visited.add(node_id)
                continue
            if node_id in visited:
                continue
            if node_id in visiting:
                if node_id not in cycle_nodes:
                    errors.append(ValidationIssue("cycle", "$.nodes", f"cycle includes {node_id}"))
                    cycle_nodes.add(node_id)
                continue
            if depth > MAX_HIERARCHY_DEPTH:
                if node_id not in depth_exceeded:
                    errors.append(
                        ValidationIssue(
                            "hierarchy_too_deep",
                            "$.nodes",
                            f"hierarchy exceeds the supported depth of {MAX_HIERARCHY_DEPTH}",
                        )
                    )
                    depth_exceeded.add(node_id)
                continue
            visiting.add(node_id)
            stack.append((node_id, True, depth))
            stack.extend((child, False, depth + 1) for child in reversed(children_by_id.get(node_id, ())))
    unreachable = sorted(set(node_map) - visited)
    for node_id in unreachable:
        errors.append(ValidationIssue("unreachable_node", "$.nodes", node_id))

    hierarchy_is_safe = not any(
        issue.code
        in {
            "cycle",
            "duplicate_id",
            "hierarchy_too_deep",
            "invalid_children",
            "missing_reference",
            "multiple_parents",
            "unreachable_node",
        }
        for issue in errors
    )
    geometry_is_safe = hierarchy_is_safe and not any(
        issue.code
        in {
            "empty_group",
            "invalid_composition",
            "invalid_difference",
            "invalid_node_kind",
            "invalid_parameter",
            "invalid_transform",
            "unsupported_primitive",
        }
        for issue in errors
    )
    if geometry_is_safe:
        for node_id, node in node_map.items():
            if node.composition == "intersection":
                lower, upper = program_node_bounds(node, node_map)
                if any(lower[axis] >= upper[axis] for axis in range(3)):
                    errors.append(
                        ValidationIssue(
                            "empty_intersection",
                            f"$.nodes[{node_id}]",
                            "intersection bounds have no positive-volume overlap",
                        )
                    )
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, Constraint):
            result = {"kind": "invalid", "satisfied": False, "message": "constraint must be a Constraint"}
        elif constraint.kind == "bounds" and not geometry_is_safe:
            result = {
                "kind": constraint.kind,
                "satisfied": False,
                "message": "bounds cannot be evaluated for an invalid hierarchy",
            }
        else:
            result = _evaluate_constraint(constraint, node_map)
        result["index"] = index
        results.append(result)
        if not result["satisfied"]:
            errors.append(ValidationIssue("constraint_unsatisfied", f"$.constraints[{index}]", str(result["message"])))
    return IRValidationReport(not errors, tuple(errors), tuple(results))


def _evaluate_constraint(constraint: Constraint, node_map: dict[str, Node]) -> dict[str, Any]:
    if not isinstance(constraint.kind, str) or constraint.kind not in CONSTRAINT_KINDS:
        return {"kind": str(constraint.kind), "satisfied": False, "message": "unsupported constraint kind"}
    if constraint.target is not None and (not isinstance(constraint.target, str) or constraint.target not in node_map):
        return {"kind": constraint.kind, "satisfied": False, "message": f"missing target {constraint.target}"}
    if constraint.reference is not None and (not isinstance(constraint.reference, str) or constraint.reference not in node_map):
        return {"kind": constraint.kind, "satisfied": False, "message": f"missing reference {constraint.reference}"}
    if constraint.kind in {"dimension", "child_count", "bounds"} and constraint.target is None:
        return {"kind": constraint.kind, "satisfied": False, "message": "constraint requires target"}
    if constraint.kind in {"coincident", "offset"} and (constraint.target is None or constraint.reference is None):
        return {"kind": constraint.kind, "satisfied": False, "message": "constraint requires target and reference"}
    if not _finite_number(constraint.tolerance) or float(constraint.tolerance) < 0:
        return {"kind": constraint.kind, "satisfied": False, "message": "tolerance must be a finite non-negative number"}
    if not isinstance(constraint.parameters, dict):
        return {"kind": constraint.kind, "satisfied": False, "message": "parameters must be an object"}
    json_error = _strict_json_error(constraint.parameters, "parameters")
    if json_error:
        return {"kind": constraint.kind, "satisfied": False, "message": json_error}
    expected_parameter_keys = {
        "dimension": {"parameter", "value"},
        "coincident": set(),
        "offset": {"vector"},
        "child_count": {"value"},
        "bounds": {"min", "max"},
    }[constraint.kind]
    actual_parameter_keys = set(constraint.parameters)
    if actual_parameter_keys != expected_parameter_keys:
        missing = sorted(expected_parameter_keys - actual_parameter_keys)
        unexpected = sorted(str(key) for key in actual_parameter_keys - expected_parameter_keys)
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        return {
            "kind": constraint.kind,
            "satisfied": False,
            "message": "constraint parameters are invalid: " + "; ".join(details),
        }
    if constraint.kind in {"dimension", "child_count", "bounds"} and constraint.reference is not None:
        return {"kind": constraint.kind, "satisfied": False, "message": "constraint does not accept a reference"}
    tolerance = float(constraint.tolerance)
    if constraint.kind == "dimension":
        node = node_map[constraint.target or ""]
        name = constraint.parameters.get("parameter")
        expected = constraint.parameters.get("value")
        actual = node.primitive.parameters.get(name) if node.primitive and isinstance(name, str) else None
        if (
            isinstance(actual, (list, tuple))
            and isinstance(expected, (list, tuple))
            and len(actual) == len(expected)
            and all(_finite_number(item) for item in (*actual, *expected))
        ):
            satisfied = all(abs(float(left) - float(right)) <= tolerance for left, right in zip(actual, expected, strict=True))
        elif _finite_number(actual) and _finite_number(expected):
            satisfied = abs(float(cast(int | float, actual)) - float(cast(int | float, expected))) <= tolerance
        else:
            satisfied = False
        return {"kind": constraint.kind, "satisfied": satisfied, "actual": _json_value(actual), "expected": _json_value(expected), "message": "dimension matched" if satisfied else "dimension mismatch"}
    if constraint.kind == "coincident":
        target = node_map[constraint.target or ""].transform.translate
        reference = node_map[constraint.reference or ""].transform.translate
        satisfied = _finite_vector(target) and _finite_vector(reference) and all(
            abs(float(left) - float(right)) <= tolerance for left, right in zip(target, reference, strict=True)
        )
        return {"kind": constraint.kind, "satisfied": satisfied, "message": "coincident" if satisfied else "translations differ"}
    if constraint.kind == "offset":
        target = node_map[constraint.target or ""].transform.translate
        reference = node_map[constraint.reference or ""].transform.translate
        expected = constraint.parameters.get("vector")
        if (
            not isinstance(expected, (list, tuple))
            or not _finite_vector(expected)
            or not _finite_vector(target)
            or not _finite_vector(reference)
        ):
            return {"kind": constraint.kind, "satisfied": False, "message": "offset requires a three-value vector"}
        actual = [float(target[index]) - float(reference[index]) for index in range(3)]
        satisfied = all(abs(actual[index] - float(expected[index])) <= tolerance for index in range(3))
        return {"kind": constraint.kind, "satisfied": satisfied, "actual": actual, "expected": list(expected), "message": "offset matched" if satisfied else "offset mismatch"}
    if constraint.kind == "child_count":
        node = node_map[constraint.target or ""]
        expected = constraint.parameters.get("value")
        satisfied = isinstance(expected, int) and not isinstance(expected, bool) and len(node.children) == expected
        return {"kind": constraint.kind, "satisfied": satisfied, "actual": len(node.children), "expected": expected, "message": "child count matched" if satisfied else "child count mismatch"}
    if constraint.kind == "bounds":
        expected_min = constraint.parameters.get("min")
        expected_max = constraint.parameters.get("max")
        if (
            not isinstance(expected_min, (list, tuple))
            or not isinstance(expected_max, (list, tuple))
            or not _finite_vector(expected_min)
            or not _finite_vector(expected_max)
        ):
            return {
                "kind": constraint.kind,
                "satisfied": False,
                "message": "bounds requires finite three-value min and max vectors",
            }
        if any(float(expected_min[index]) > float(expected_max[index]) for index in range(3)):
            return {
                "kind": constraint.kind,
                "satisfied": False,
                "message": "bounds min cannot exceed max",
            }
        try:
            actual_min, actual_max = program_node_bounds(node_map[constraint.target or ""], node_map)
            satisfied = all(actual_min[index] >= float(expected_min[index]) - tolerance and actual_max[index] <= float(expected_max[index]) + tolerance for index in range(3))
            actual_bounds = [list(actual_min), list(actual_max)]
        except (KeyError, TypeError, ValueError, IndexError):
            satisfied = False
            actual_bounds = [[], []]
        return {"kind": constraint.kind, "satisfied": satisfied, "actual": actual_bounds, "message": "bounds satisfied" if satisfied else "bounds exceeded or malformed"}
    raise AssertionError("unreachable")


def program_node_bounds(node: Node, node_map: dict[str, Node]) -> tuple[Vec3, Vec3]:
    if node.primitive is not None:
        local_min, local_max = _primitive_bounds(node.primitive)
    else:
        child_bounds = [program_node_bounds(node_map[child], node_map) for child in node.children]
        if node.composition == "difference":
            local_min, local_max = child_bounds[0]
        elif node.composition == "intersection":
            local_min = _vec3(max(bounds[0][axis] for bounds in child_bounds) for axis in range(3))
            local_max = _vec3(min(bounds[1][axis] for bounds in child_bounds) for axis in range(3))
        else:
            local_min = _vec3(min(bounds[0][axis] for bounds in child_bounds) for axis in range(3))
            local_max = _vec3(max(bounds[1][axis] for bounds in child_bounds) for axis in range(3))
    return _transform_bounds(local_min, local_max, node.transform)


def program_bounds(program: CADProgram) -> tuple[Vec3, Vec3]:
    """Return conservative axis-aligned bounds for a program.

    Boolean difference and intersection nodes can make these bounds wider than
    the resulting solid.  Call :func:`program_bounds_are_exact` before using
    them as an exact output-mesh contract.
    """

    node_map = program.node_map()
    bounds = [program_node_bounds(node_map[root], node_map) for root in program.roots]
    return (
        _vec3(min(item[0][axis] for item in bounds) for axis in range(3)),
        _vec3(max(item[1][axis] for item in bounds) for axis in range(3)),
    )


def program_bounds_are_exact(program: CADProgram) -> bool:
    """Return whether ``program_bounds`` is guaranteed to be an exact AABB."""

    node_map = program.node_map()
    memo: dict[str, bool] = {}

    def axes_preserved(transform: Transform) -> bool:
        return all(abs(angle / 90.0 - round(angle / 90.0)) <= 1e-9 for angle in transform.rotate)

    def exact(node_id: str) -> bool:
        if node_id in memo:
            return memo[node_id]
        node = node_map[node_id]
        # An oriented box fills its local bounding box, so the support-function
        # calculation in _transform_bounds is exact at every rotation.  Other
        # primitives and arbitrary groups are only exact under axis-preserving
        # rotations.
        transform_exact = bool(node.primitive and node.primitive.kind == "box") or axes_preserved(node.transform)
        if node.primitive is not None:
            result = transform_exact
        elif node.composition == "union":
            result = transform_exact and all(exact(child) for child in node.children)
        else:
            # Difference returns the first child's conservative bounds, while
            # intersection returns the overlap of child AABBs.  Neither is an
            # exact result-solid bound in the general case.
            result = False
        memo[node_id] = result
        return result

    try:
        return bool(program.roots) and all(exact(root) for root in program.roots)
    except (KeyError, RecursionError, TypeError, ValueError):
        return False


def _primitive_bounds(primitive: Primitive) -> tuple[Vec3, Vec3]:
    parameters = primitive.parameters
    if primitive.kind in {"box", "rounded_box"}:
        size = _vec3(float(value) for value in parameters["size"])
        half = _vec3(value / 2 for value in size)
    elif primitive.kind == "sphere":
        radius = float(parameters["radius"])
        half = (radius, radius, radius)
    elif primitive.kind == "cylinder":
        radius, height = float(parameters["radius"]), float(parameters["height"])
        half = (radius, radius, height / 2)
    elif primitive.kind == "cone":
        radius, height = max(float(parameters["r1"]), float(parameters["r2"])), float(parameters["height"])
        half = (radius, radius, height / 2)
    elif primitive.kind == "torus":
        major, minor = float(parameters["major_radius"]), float(parameters["minor_radius"])
        half = (major + minor, major + minor, minor)
    else:
        raise ValueError(f"unsupported primitive {primitive.kind}")
    return _vec3(-value for value in half), half


def _transform_bounds(local_min: Vec3, local_max: Vec3, transform: Transform) -> tuple[Vec3, Vec3]:
    center = _vec3((local_min[index] + local_max[index]) / 2 for index in range(3))
    half = _vec3((local_max[index] - local_min[index]) / 2 * abs(transform.scale[index]) for index in range(3))
    rx, ry, rz = (math.radians(value) for value in transform.rotate)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    matrix = (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )
    rotated_center = _vec3(sum(matrix[row][column] * center[column] * transform.scale[column] for column in range(3)) + transform.translate[row] for row in range(3))
    rotated_half = _vec3(sum(abs(matrix[row][column]) * half[column] for column in range(3)) for row in range(3))
    return (
        _vec3(rotated_center[index] - rotated_half[index] for index in range(3)),
        _vec3(rotated_center[index] + rotated_half[index] for index in range(3)),
    )
