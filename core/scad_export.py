from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .design_graph import Component, DesignGraph
from .validation import MAX_PRIMITIVE_LENGTH_MM, MIN_PRIMITIVE_LENGTH_MM, validate_design


def _fmt_num(value: float) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("OpenSCAD numbers must be finite integers or floats")
    if isinstance(value, int):
        return str(value)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("OpenSCAD numbers must be finite")
    if math.isfinite(value) and abs(value - round(value)) < 1e-9:
        return str(round(value))
    # Fifteen significant digits preserve normal Python float dimensions and,
    # unlike fixed six-place formatting, cannot silently turn a non-zero
    # primitive into zero.
    return format(value, ".15g")


def _fmt_vec(vec: Sequence[float]) -> str:
    return "[" + ", ".join(_fmt_num(v) for v in vec) + "]"


def _length(value: Any, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite numeric length")
    try:
        converted = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be between {MIN_PRIMITIVE_LENGTH_MM:g} and {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite numeric length")
    if allow_zero and converted == 0:
        return 0.0
    if converted < MIN_PRIMITIVE_LENGTH_MM or converted > MAX_PRIMITIVE_LENGTH_MM:
        raise ValueError(f"{name} must be between {MIN_PRIMITIVE_LENGTH_MM:g} and {MAX_PRIMITIVE_LENGTH_MM:,.0f} mm")
    return converted


def _length_vector(value: Any, name: str, *, size: int) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{name} must contain exactly {size} lengths")
    return tuple(_length(item, f"{name}[{index}]") for index, item in enumerate(value))


def _center(geometry: Mapping[str, Any]) -> bool:
    value = geometry.get("center", True)
    if not isinstance(value, bool):
        raise TypeError("primitive center must be a boolean")
    return value


def _primitive_scad(geometry: dict[str, Any]) -> str:
    raw_kind = geometry.get("kind")
    if not isinstance(raw_kind, str) or not raw_kind:
        raise ValueError("geometry kind must be stated explicitly")
    kind = raw_kind.lower()

    if kind in {"box", "cube"}:
        size = _length_vector(geometry.get("size"), "box size", size=3)
        center = _center(geometry)
        return f"cube(size={_fmt_vec(size)}, center={'true' if center else 'false'});"

    if kind == "rounded_box":
        size = _length_vector(geometry.get("size"), "rounded box size", size=3)
        width, depth, height = size
        radius = _length(geometry.get("radius"), "rounded box radius")
        if radius > min(width, depth) / 2.0:
            raise ValueError("rounded box radius cannot exceed half its planar size")
        inner = (width - 2 * radius, depth - 2 * radius)
        body = (
            f"linear_extrude(height={_fmt_num(height)}, center=true, convexity=10) "
            f"offset(r={_fmt_num(radius)}) square({_fmt_vec(inner)}, center=true);"
        )
        if not _center(geometry):
            body = f"translate({_fmt_vec((width / 2, depth / 2, height / 2))}) {{\n{_indent(body)}\n}}"
        return body

    if kind == "sphere":
        r = _length(geometry.get("radius", geometry.get("r")), "sphere radius")
        return f"sphere(r={_fmt_num(r)});"

    if kind in {"cylinder", "tube"}:
        h = _length(geometry.get("height", geometry.get("h")), "cylinder height")
        center = _center(geometry)
        if "radius" in geometry or "r" in geometry:
            r = _length(geometry.get("radius", geometry.get("r")), "cylinder radius")
            return f"cylinder(r={_fmt_num(r)}, h={_fmt_num(h)}, center={'true' if center else 'false'});"
        if "diameter" in geometry or "d" in geometry:
            d = _length(geometry.get("diameter", geometry.get("d")), "cylinder diameter")
            return f"cylinder(d={_fmt_num(d)}, h={_fmt_num(h)}, center={'true' if center else 'false'});"
        raise ValueError("cylinder radius or diameter must be stated explicitly")

    if kind == "cone":
        r1 = _length(geometry.get("r1", geometry.get("radius1")), "cone r1", allow_zero=True)
        r2 = _length(geometry.get("r2", geometry.get("radius2")), "cone r2", allow_zero=True)
        if r1 == 0 and r2 == 0:
            raise ValueError("cone cannot have two zero radii")
        h = _length(geometry.get("height", geometry.get("h")), "cone height")
        center = _center(geometry)
        return f"cylinder(r1={_fmt_num(r1)}, r2={_fmt_num(r2)}, h={_fmt_num(h)}, center={'true' if center else 'false'});"

    if kind == "torus":
        R = _length(geometry.get("R"), "torus major radius")
        r = _length(geometry.get("r"), "torus minor radius")
        if r >= R:
            raise ValueError("torus minor radius must be smaller than its major radius")
        return f"rotate_extrude(convexity=10) translate([{_fmt_num(R)}, 0, 0]) circle(r={_fmt_num(r)});"

    raise ValueError(f"Unsupported geometry kind: {kind}")


def primitive_to_scad(geometry: dict[str, Any]) -> str:
    """Render one validated primitive dictionary to deterministic OpenSCAD."""

    return _primitive_scad(geometry)


def _apply_transform(scad: str, transform: Mapping[str, Sequence[float]]) -> str:
    result = scad
    scale = tuple(transform.get("scale", (1.0, 1.0, 1.0)))
    rotate = tuple(transform.get("rotate", (0.0, 0.0, 0.0)))
    translate = tuple(transform.get("translate", (0.0, 0.0, 0.0)))

    if any(abs(v - 1.0) > 1e-12 for v in scale):
        result = f"scale({_fmt_vec(scale)}) {{\n{_indent(result)}\n}}"

    if any(abs(v) > 1e-12 for v in rotate):
        result = f"rotate({_fmt_vec(rotate)}) {{\n{_indent(result)}\n}}"

    if any(abs(v) > 1e-12 for v in translate):
        result = f"translate({_fmt_vec(translate)}) {{\n{_indent(result)}\n}}"

    return result


def apply_transform(scad: str, transform: Mapping[str, Sequence[float]]) -> str:
    """Apply scale, rotation, and translation to an OpenSCAD expression."""

    return _apply_transform(scad, transform)


def _indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join((pad + line) if line else line for line in text.splitlines())


def _safe_comment(value: object) -> str:
    return re.sub(r"[\r\n]+", " ", str(value)).replace("//", "/ /").strip()


def render_component(component: Component) -> str:
    geometry = component.params.get("geometry")
    if not geometry:
        raise ValueError(f"Component {component.name!r} does not include geometry")
    body = _primitive_scad(geometry)
    body = _apply_transform(body, component.transform)
    return f"// component: {_safe_comment(component.name)} ({_safe_comment(component.role)})\n{body}\n"


def design_to_scad(design: DesignGraph, *, fn: int = 96) -> str:
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("fn must be an integer between 3 and 1000")
    validation = validate_design(design)
    if not validation.valid:
        raise ValueError("cannot export invalid design: " + "; ".join(validation.errors))
    positives: list[str] = []
    negatives: list[str] = []
    intersections: list[str] = []

    for component in design.components:
        rendered = render_component(component)
        if component.operation == "difference":
            negatives.append(rendered)
        elif component.operation == "intersection":
            intersections.append(rendered)
        elif component.operation == "union":
            positives.append(rendered)
        else:
            raise ValueError(f"unsupported component operation {component.operation!r}")

    if intersections and (positives or negatives):
        raise ValueError("flat DesignGraph cannot mix intersection with union or difference components; use canonical IR hierarchy")
    if negatives and not positives:
        raise ValueError("difference export requires at least one positive component")

    safe_title = re.sub(r"[\r\n]+", " ", str(design.title)).replace("//", "/ /").strip()
    lines = [
        "// ========================================",
        f"// {safe_title}",
        "// Generated by NeuroCAD; dimensions are millimetres",
        "// ========================================",
        f"$fn = {int(fn)};",
        "",
    ]

    if intersections:
        lines.append("intersection() {")
        for block in intersections:
            lines.append(_indent(block.rstrip()))
        lines.append("}")
    elif negatives:
        lines.append("difference() {")
        lines.append(_indent("union() {"))
        for block in positives:
            lines.append(_indent(_indent(block.rstrip())))
        lines.append(_indent("}"))
        for block in negatives:
            lines.append(_indent(block.rstrip()))
        lines.append("}")
    else:
        lines.append("union() {")
        for block in positives:
            lines.append(_indent(block.rstrip()))
        lines.append("}")

    return "\n".join(lines).rstrip() + "\n"
