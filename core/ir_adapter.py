from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any

from .design_graph import Component, DesignGraph
from .ir import CADProgram, Constraint, Node, Primitive, Transform, validate_program
from .validation import validate_design


def _safe_id(value: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "node"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _primitive(component: Component) -> Primitive:
    geometry = deepcopy(component.geometry())
    kind = str(geometry.pop("kind"))
    geometry.pop("center", None)
    parameters: dict[str, Any]
    if kind == "box":
        parameters = {"size": list(deepcopy(geometry["size"]))}
    elif kind == "rounded_box":
        parameters = {"size": list(deepcopy(geometry["size"])), "radius": geometry["radius"]}
    elif kind == "sphere":
        parameters = {"radius": geometry.get("radius", geometry.get("r"))}
    elif kind == "cylinder":
        parameters = {"radius": geometry.get("radius", geometry.get("r")), "height": geometry.get("height", geometry.get("h"))}
    elif kind == "cone":
        parameters = {"r1": geometry["r1"], "r2": geometry["r2"], "height": geometry.get("height", geometry.get("h"))}
    elif kind == "torus":
        parameters = {"major_radius": geometry["R"], "minor_radius": geometry["r"]}
    else:
        raise ValueError(f"cannot adapt unsupported geometry kind {kind!r} to canonical IR")
    return Primitive(kind, deepcopy(parameters))


def _local_center_offset(component: Component) -> tuple[float, float, float]:
    geometry = component.geometry()
    center = geometry.get("center", True)
    if center is not False:
        return 0.0, 0.0, 0.0
    kind = str(geometry.get("kind", ""))
    if kind in {"box", "rounded_box"}:
        size = geometry.get("size")
        if not isinstance(size, (list, tuple)) or len(size) != 3:
            raise ValueError(f"component {component.name!r} size must contain three values")
        return float(size[0]) / 2.0, float(size[1]) / 2.0, float(size[2]) / 2.0
    if kind in {"cylinder", "cone"}:
        height = geometry.get("height", geometry.get("h"))
        if isinstance(height, bool) or not isinstance(height, (int, float)):
            raise ValueError(f"component {component.name!r} height must be numeric")
        return 0.0, 0.0, float(height) / 2.0
    return 0.0, 0.0, 0.0


def _rotate_xyz(vector: tuple[float, float, float], angles: tuple[float, float, float]) -> tuple[float, float, float]:
    """Apply OpenSCAD's x, then y, then z Euler rotations to a vector."""

    x, y, z = vector
    ax, ay, az = (math.radians(angle) for angle in angles)
    cos_x, sin_x = math.cos(ax), math.sin(ax)
    y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
    cos_y, sin_y = math.cos(ay), math.sin(ay)
    x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    cos_z, sin_z = math.cos(az), math.sin(az)
    x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
    return x, y, z


def _transform(component: Component) -> Transform:
    def vector(name: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
        raw = component.transform.get(name, default)
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            raise ValueError(f"component {component.name!r} transform {name} must contain three values")
        return float(raw[0]), float(raw[1]), float(raw[2])

    translate = vector("translate", (0.0, 0.0, 0.0))
    rotate = vector("rotate", (0.0, 0.0, 0.0))
    scale = vector("scale", (1.0, 1.0, 1.0))
    offset = _local_center_offset(component)
    scaled_offset = (
        offset[0] * scale[0],
        offset[1] * scale[1],
        offset[2] * scale[2],
    )
    rotated_offset = _rotate_xyz(scaled_offset, rotate)
    return Transform(
        translate=(
            translate[0] + rotated_offset[0],
            translate[1] + rotated_offset[1],
            translate[2] + rotated_offset[2],
        ),
        rotate=rotate,
        scale=scale,
    )


def design_graph_to_ir(design: DesignGraph) -> CADProgram:
    design_validation = validate_design(design)
    if not design_validation.valid:
        raise ValueError("cannot adapt invalid design: " + "; ".join(design_validation.errors))

    used: set[str] = set()
    nodes: list[Node] = []
    constraints: list[Constraint] = []
    positives: list[str] = []
    negatives: list[str] = []
    intersections: list[str] = []
    component_ids: dict[int, str] = {}

    for component in design.components:
        node_id = _safe_id(component.name, used)
        component_ids[id(component)] = node_id
        primitive = _primitive(component)
        nodes.append(Node(node_id, primitive=primitive, transform=_transform(component), role=component.role))
        for parameter, value in primitive.parameters.items():
            constraints.append(
                Constraint(
                    "dimension",
                    target=node_id,
                    parameters={"parameter": parameter, "value": deepcopy(value)},
                )
            )
        if component.operation == "difference":
            negatives.append(node_id)
        elif component.operation == "intersection":
            intersections.append(node_id)
        elif component.operation == "union":
            positives.append(node_id)
        else:
            raise ValueError(f"component {component.name!r} has unsupported operation {component.operation!r}")

    if intersections:
        raise ValueError("flat DesignGraph intersection semantics cannot be adapted unambiguously; use canonical IR directly")
    if not positives:
        raise ValueError("design must contain at least one positive component")

    if len(positives) == 1:
        positive_root = positives[0]
    else:
        positive_root = _safe_id("positive_union", used)
        nodes.append(Node(positive_root, composition="union", children=tuple(positives), role="composition"))
        constraints.append(Constraint("child_count", target=positive_root, parameters={"value": len(positives)}))
    if negatives:
        root = _safe_id("design_difference", used)
        nodes.append(Node(root, composition="difference", children=(positive_root, *negatives), role="composition"))
        constraints.append(Constraint("child_count", target=root, parameters={"value": 1 + len(negatives)}))
    else:
        root = positive_root

    connections = [
        {"a": component_ids[id(connection.a)], "b": component_ids[id(connection.b)], "relation": connection.relation}
        for connection in design.connections
    ]
    metadata: dict[str, Any] = deepcopy(design.metadata)
    metadata.update({"source": "natural_language_design_graph", "connections": connections})
    program = CADProgram(design.title, tuple(nodes), (root,), tuple(constraints), metadata)
    report = validate_program(program)
    if not report.valid:
        raise ValueError("adapted canonical IR is invalid: " + "; ".join(error.message for error in report.errors))
    return program
