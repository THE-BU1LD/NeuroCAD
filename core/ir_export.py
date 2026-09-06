from __future__ import annotations

import re

from .ir import CADProgram, Node, validate_program
from .scad_export import apply_transform, primitive_to_scad


def _indent(text: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def _geometry(node: Node) -> dict[str, object]:
    if node.primitive is None:
        raise ValueError(f"node {node.id} is not a primitive")
    parameters = node.primitive.parameters
    kind = node.primitive.kind
    if kind in {"box", "rounded_box"}:
        geometry: dict[str, object] = {"kind": kind, "size": parameters["size"], "center": True}
        if kind == "rounded_box":
            geometry["radius"] = parameters["radius"]
        return geometry
    if kind == "sphere":
        return {"kind": kind, "radius": parameters["radius"]}
    if kind == "cylinder":
        return {"kind": kind, "radius": parameters["radius"], "height": parameters["height"], "center": True}
    if kind == "cone":
        return {"kind": kind, "r1": parameters["r1"], "r2": parameters["r2"], "height": parameters["height"], "center": True}
    if kind == "torus":
        return {"kind": kind, "R": parameters["major_radius"], "r": parameters["minor_radius"]}
    raise ValueError(f"unsupported primitive {kind}")


def _render_node(node_id: str, node_map: dict[str, Node], active: set[str]) -> str:
    if node_id in active:
        raise ValueError(f"cycle encountered while rendering {node_id}")
    active.add(node_id)
    node = node_map[node_id]
    if node.primitive is not None:
        body = primitive_to_scad(_geometry(node))
    else:
        children = [_render_node(child, node_map, active) for child in node.children]
        body = f"{node.composition}() {{\n" + "\n".join(_indent(child) for child in children) + "\n}"
    active.remove(node_id)
    return apply_transform(body, node.transform.to_dict())


def program_to_scad(program: CADProgram, *, fn: int = 96) -> str:
    if not 3 <= int(fn) <= 1000:
        raise ValueError("fn must be between 3 and 1000")
    report = validate_program(program)
    if not report.valid:
        raise ValueError("cannot export invalid canonical IR: " + "; ".join(error.message for error in report.errors))
    node_map = program.node_map()
    roots = [_render_node(root, node_map, set()) for root in program.roots]
    body = roots[0] if len(roots) == 1 else "union() {\n" + "\n".join(_indent(root) for root in roots) + "\n}"
    safe_title = re.sub(r"[\r\n]+", " ", program.title).replace("//", "/ /").strip()
    return "\n".join(
        [
            "// ========================================",
            f"// {safe_title}",
            "// NeuroCAD canonical IR; dimensions are millimetres",
            "// ========================================",
            f"$fn = {int(fn)};",
            "",
            body,
            "",
        ]
    )
