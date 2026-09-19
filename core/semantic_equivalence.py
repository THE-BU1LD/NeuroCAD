"""Full-graph semantic comparison for validated canonical CAD programs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from typing import Any

from .ir import CADProgram, Constraint, Node, validate_program

SEMANTIC_FORM_VERSION = "neurocad-program-semantics-v1"


def _json_value(value: Any) -> Any:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return 0.0 if number == 0.0 else number
    if isinstance(value, dict):
        return {key: _json_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def program_semantic_form(program: CADProgram) -> dict[str, Any]:
    """Return an identifier-independent representation of complete CSG semantics."""

    report = validate_program(program)
    if not report.valid:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        raise ValueError(f"cannot compare an invalid CAD program: {details}")
    nodes = program.node_map()
    memo: dict[str, dict[str, Any]] = {}

    def visit(identifier: str) -> dict[str, Any]:
        if identifier in memo:
            return memo[identifier]
        node = nodes[identifier]
        form: dict[str, Any] = {
            "role": node.role,
            "transform": _json_value(node.transform.to_dict()),
        }
        if node.primitive is not None:
            form["primitive"] = _json_value(node.primitive.to_dict())
        else:
            children = [visit(child) for child in node.children]
            if node.composition in {"union", "intersection"}:
                children.sort(key=_canonical_json)
            elif node.composition == "difference" and len(children) > 2:
                children = [children[0], *sorted(children[1:], key=_canonical_json)]
            form["composition"] = node.composition
            form["children"] = children
        memo[identifier] = form
        return form

    roots = sorted((visit(root) for root in program.roots), key=_canonical_json)
    constraints = sorted((_constraint_form(item, nodes, visit) for item in program.constraints), key=_canonical_json)
    return {
        "schema_version": SEMANTIC_FORM_VERSION,
        "units": program.units,
        "roots": roots,
        "constraints": constraints,
    }


def _constraint_form(
    constraint: Constraint,
    nodes: dict[str, Node],
    visit: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": constraint.kind,
        "parameters": _json_value(constraint.parameters),
        "tolerance": _json_value(constraint.tolerance),
    }
    if constraint.target is not None:
        result["target"] = visit(constraint.target) if constraint.target in nodes else constraint.target
    if constraint.reference is not None:
        result["reference"] = visit(constraint.reference) if constraint.reference in nodes else constraint.reference
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def program_semantic_sha256(program: CADProgram) -> str:
    return hashlib.sha256(_canonical_json(program_semantic_form(program)).encode("utf-8")).hexdigest()


def _equivalent(left: Any, right: Any, tolerance: float) -> bool:
    if isinstance(left, dict):
        return isinstance(right, dict) and set(left) == set(right) and all(_equivalent(left[key], right[key], tolerance) for key in left)
    if isinstance(left, list):
        return (
            isinstance(right, list)
            and len(left) == len(right)
            and all(_equivalent(a, b, tolerance) for a, b in zip(left, right, strict=True))
        )
    if isinstance(left, (int, float)) and not isinstance(left, bool):
        return (
            isinstance(right, (int, float))
            and not isinstance(right, bool)
            and math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
        )
    return left == right


def programs_semantically_equivalent(
    expected: CADProgram,
    actual: CADProgram,
    *,
    tolerance: float = 1e-9,
) -> bool:
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a finite non-negative number")
    return _equivalent(program_semantic_form(expected), program_semantic_form(actual), float(tolerance))
