"""Deterministic CadQuery source export for the canonical NeuroCAD IR.

The exporter is intentionally bounded.  It translates the same primitive/CSG
program accepted by :mod:`core.ir`; it does not infer missing geometry or add a
language model.  Unsupported scale transforms fail closed instead of silently
changing the represented solid.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .ir import CADProgram, Node, validate_program

CADQUERY_EXPORT_VERSION = "neurocad-cadquery-source-v1"


def _number(value: Any) -> str:
    return repr(float(value))


def _vector(values: object) -> str:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError("expected a three-element vector")
    return "(" + ", ".join(_number(value) for value in values) + ")"


def _primitive_expression(node: Node) -> str:
    if node.primitive is None:
        raise ValueError(f"node {node.id!r} is not a primitive")
    kind = node.primitive.kind
    parameters = node.primitive.parameters
    if kind == "box":
        x, y, z = parameters["size"]
        return (
            'cq.Workplane("XY").box('
            f"{_number(x)}, {_number(y)}, {_number(z)}, centered=(True, True, True))"
        )
    if kind == "rounded_box":
        x, y, z = parameters["size"]
        radius = parameters["radius"]
        return (
            'cq.Workplane("XY").box('
            f"{_number(x)}, {_number(y)}, {_number(z)}, centered=(True, True, True))"
            f".edges().fillet({_number(radius)})"
        )
    if kind == "sphere":
        return f'cq.Workplane("XY").sphere({_number(parameters["radius"])})'
    if kind == "cylinder":
        radius = _number(parameters["radius"])
        half_height = _number(float(parameters["height"]) / 2.0)
        return f'cq.Workplane("XY").circle({radius}).extrude({half_height}, both=True)'
    if kind == "cone":
        r1 = _number(parameters["r1"])
        r2 = _number(parameters["r2"])
        height = float(parameters["height"])
        return (
            'cq.Workplane("XY").newObject(['
            f"cq.Solid.makeCone({r1}, {r2}, {_number(height)}, "
            f"cq.Vector(0.0, 0.0, {_number(-height / 2.0)}))])"
        )
    if kind == "torus":
        major = _number(parameters["major_radius"])
        minor = _number(parameters["minor_radius"])
        return f'cq.Workplane("XY").newObject([cq.Solid.makeTorus({major}, {minor})])'
    raise ValueError(f"unsupported canonical primitive {kind!r}")


def _apply_transform(expression: str, node: Node) -> str:
    transform = node.transform
    if tuple(float(value) for value in transform.scale) != (1.0, 1.0, 1.0):
        raise ValueError(
            f"node {node.id!r} uses a scale transform; the CadQuery v1 exporter refuses "
            "non-rigid transforms"
        )
    result = expression
    axes = (
        ((1.0, 0.0, 0.0), float(transform.rotate[0])),
        ((0.0, 1.0, 0.0), float(transform.rotate[1])),
        ((0.0, 0.0, 1.0), float(transform.rotate[2])),
    )
    for axis, angle in axes:
        if angle != 0.0:
            result = f"({result}).rotate((0.0, 0.0, 0.0), {_vector(axis)}, {_number(angle)})"
    translate = tuple(float(value) for value in transform.translate)
    if translate != (0.0, 0.0, 0.0):
        result = f"({result}).translate({_vector(translate)})"
    return result


def _program_sha256(program: CADProgram) -> str:
    payload = json.dumps(
        program.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def program_to_cadquery_python(program: CADProgram) -> str:
    """Render a validated canonical program as deterministic CadQuery source."""

    report = validate_program(program)
    if not report.valid:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        raise ValueError(f"cannot export invalid canonical IR: {details}")

    lines = [
        f"# {CADQUERY_EXPORT_VERSION}",
        f"# canonical_ir_sha256={_program_sha256(program)}",
        "import cadquery as cq",
        "",
        "def create_cad():",
    ]
    variables: dict[str, str] = {}
    for index, node in enumerate(program.nodes):
        variable = f"node_{index:04d}"
        variables[node.id] = variable
        if node.primitive is not None:
            expression = _primitive_expression(node)
        else:
            children = [variables[child] for child in node.children]
            expression = children[0]
            operation = {
                "union": "union",
                "difference": "cut",
                "intersection": "intersect",
            }[str(node.composition)]
            for child in children[1:]:
                expression = f"({expression}).{operation}({child})"
        lines.append(f"    {variable} = {_apply_transform(expression, node)}")

    roots = [variables[root] for root in program.roots]
    result = roots[0]
    for root in roots[1:]:
        result = f"({result}).union({root})"
    lines.extend(
        [
            f"    return {result}",
            "",
            "final_result = create_cad()",
            "",
        ]
    )
    return "\n".join(lines)


def export_cadquery_python(
    program: CADProgram,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Atomically write one generated CadQuery program."""

    write_text_atomic(path, program_to_cadquery_python(program), overwrite=overwrite)
    return path
