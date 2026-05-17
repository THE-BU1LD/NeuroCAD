from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .design_graph import Component, DesignGraph

UNIT_SCALE = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
}

NUM_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

DOMAIN_KEYWORDS = {
    "aircraft": ["plane", "airplane", "aircraft", "jet", "wing", "uav", "drone", "glider"],
    "vehicle": ["car", "truck", "vehicle", "bus", "van", "automobile"],
    "mechanism": ["motor", "gear", "gearbox", "pump", "turbine", "engine"],
    "container": ["box", "case", "enclosure", "housing", "shell"],
    "furniture": ["desk", "chair", "shelf", "table", "organizer"],
}

FEATURE_KEYWORDS = {
    "holes": ["hole", "holes", "drill", "bore"],
    "hollow": ["hollow", "shell", "thin wall"],
    "rounded": ["rounded", "fillet", "radius corner"],
    "slots": ["slot", "slots"],
    "fins": ["fin", "fins", "tail"],
    "wings": ["wing", "wings"],
    "wheels": ["wheel", "wheels"],
    "shaft": ["shaft", "axle", "rod"],
}


def _normalize(text: str) -> str:
    text = text.lower().replace("×", "x")
    text = re.sub(r"[^a-z0-9\.\-\+\s/x()_,;:]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_number(token: str) -> Optional[int]:
    return NUM_WORDS.get(token)


def _extract_float(token: str) -> Optional[float]:
    try:
        return float(token)
    except Exception:
        return None


def _extract_measurement(text: str, name: str) -> Optional[float]:
    patterns = [
        rf"{name}\s*(?:is\s*)?([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?",
        rf"{name}\s*(?:of\s*)?([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            value = float(m.group(1))
            unit = m.group(2) or "m"
            return value * UNIT_SCALE[unit]
    return None


def _extract_sequence_dims(text: str) -> Optional[Tuple[float, float, float]]:
    m = re.search(
        r"([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?\s*(?:x|by)\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?\s*(?:x|by)\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?",
        text,
    )
    if not m:
        return None
    out = []
    for i in (1, 3, 5):
        val = float(m.group(i))
        unit = m.group(i + 1) or "m"
        out.append(val * UNIT_SCALE[unit])
    return tuple(out)


def _extract_radius(text: str, default: float = 0.05) -> float:
    m = re.search(r"radius\s*(?:of\s*)?([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?", text)
    if m:
        return float(m.group(1)) * UNIT_SCALE[m.group(2) or "m"]
    m = re.search(r"r\s*=\s*([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?", text)
    if m:
        return float(m.group(1)) * UNIT_SCALE[m.group(2) or "m"]
    return default


def _extract_height(text: str, default: float = 0.1) -> float:
    m = re.search(r"height\s*(?:of\s*)?([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)?", text)
    if m:
        return float(m.group(1)) * UNIT_SCALE[m.group(2) or "m"]
    return default


def _extract_count(text: str, keywords: Iterable[str], default: int = 1) -> int:
    for kw in keywords:
        m = re.search(rf"(?:\b(\w+)\b|\b(\d+)\b)\s+{re.escape(kw)}", text)
        if m:
            token = m.group(1) or m.group(2)
            if token.isdigit():
                return max(1, int(token))
            n = _word_number(token)
            if n is not None:
                return max(1, n)
    return default


def infer_domain(text: str) -> str:
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(k in text for k in keywords):
            return domain
    return "generic"


def infer_features(text: str) -> Dict[str, bool]:
    flags = {}
    for name, kws in FEATURE_KEYWORDS.items():
        flags[name] = any(k in text for k in kws)
    return flags


def _make_component(
    name: str,
    kind: str,
    params: Dict[str, float],
    *,
    translate=(0.0, 0.0, 0.0),
    rotate=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
    operation: str = "union",
    role: str = "body",
) -> Component:
    geom = {"kind": kind, **params}
    return Component(
        name=name,
        params={"geometry": geom, **{k: v for k, v in params.items() if k != "geometry"}},
        operation=operation,
        role=role,
        transform={
            "translate": tuple(float(v) for v in translate),
            "rotate": tuple(float(v) for v in rotate),
            "scale": tuple(float(v) for v in scale),
        },
    )


def _aircraft_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "aircraft design")

    span = _extract_measurement(text, "span") or _extract_measurement(text, "wingspan") or 0.8
    length = _extract_measurement(text, "length") or 0.9
    height = _extract_measurement(text, "height") or 0.16
    radius = max(0.02, min(length * 0.09, span * 0.08))

    fuselage = graph.add_component(
        _make_component(
            "fuselage",
            "cylinder",
            {"radius": radius, "height": length, "center": True},
            rotate=(0.0, 90.0, 0.0),
            role="body",
        )
    )

    nose = graph.add_component(
        _make_component(
            "nose",
            "cone",
            {"r1": radius, "r2": 0.0, "height": radius * 1.7, "center": False},
            translate=(length * 0.5 + radius * 0.85, 0.0, 0.0),
            rotate=(0.0, 90.0, 0.0),
            role="aerodynamic",
        )
    )
    graph.connect(fuselage, nose, "coaxial")

    wing_thickness = max(0.008, radius * 0.18)
    wing_chord = max(span * 0.28, length * 0.18)
    wing = graph.add_component(
        _make_component(
            "wing",
            "box",
            {"size": (span, wing_chord, wing_thickness), "center": True},
            translate=(0.0, 0.0, -height * 0.05),
            role="lifting_surface",
        )
    )
    graph.connect(fuselage, wing, "mounted")

    tail = graph.add_component(
        _make_component(
            "tailplane",
            "box",
            {"size": (span * 0.25, wing_chord * 0.45, wing_thickness * 0.75), "center": True},
            translate=(-length * 0.42, 0.0, height * 0.18),
            role="stabilizer",
        )
    )
    graph.connect(fuselage, tail, "mounted")

    if flags.get("fins"):
        fin = graph.add_component(
            _make_component(
                "fin",
                "box",
                {"size": (span * 0.08, wing_chord * 0.2, height * 0.9), "center": True},
                translate=(-length * 0.45, 0.0, height * 0.35),
                role="stabilizer",
            )
        )
        graph.connect(fuselage, fin, "mounted")

    if flags.get("holes"):
        for idx, offset in enumerate((-span * 0.2, span * 0.2), start=1):
            hole = graph.add_component(
                _make_component(
                    f"mount_hole_{idx}",
                    "cylinder",
                    {"radius": radius * 0.18, "height": wing_thickness * 4, "center": True},
                    translate=(0.0, offset, 0.0),
                    operation="difference",
                    role="fastener",
                )
            )
            graph.connect(wing, hole, "cutout")

    return graph


def _vehicle_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "vehicle design")

    length = _extract_measurement(text, "length") or 0.35
    width = _extract_measurement(text, "width") or 0.16
    height = _extract_measurement(text, "height") or 0.11
    wheel_radius = max(0.015, min(width * 0.18, length * 0.08))
    wheel_thickness = max(0.01, wheel_radius * 0.6)

    chassis = graph.add_component(
        _make_component(
            "chassis",
            "box",
            {"size": (length, width, height), "center": True},
            role="body",
        )
    )

    cabin = graph.add_component(
        _make_component(
            "cabin",
            "box",
            {"size": (length * 0.42, width * 0.78, height * 0.95), "center": True},
            translate=(length * 0.07, 0.0, height * 0.45),
            role="body",
        )
    )
    graph.connect(chassis, cabin, "stacked")

    wheel_positions = [
        (-length * 0.32, -width * 0.36, -height * 0.55),
        (-length * 0.32, width * 0.36, -height * 0.55),
        (length * 0.32, -width * 0.36, -height * 0.55),
        (length * 0.32, width * 0.36, -height * 0.55),
    ]
    wheels: List[Component] = []
    for i, pos in enumerate(wheel_positions, start=1):
        wheel = graph.add_component(
            _make_component(
                f"wheel_{i}",
                "cylinder",
                {"radius": wheel_radius, "height": wheel_thickness, "center": True},
                translate=pos,
                rotate=(90.0, 0.0, 0.0),
                role="mobility",
            )
        )
        graph.connect(chassis, wheel, "axled")
        wheels.append(wheel)

    if flags.get("slots"):
        slot = graph.add_component(
            _make_component(
                "cargo_slot",
                "box",
                {"size": (length * 0.2, width * 0.45, height * 1.1), "center": True},
                translate=(length * 0.18, 0.0, height * 0.1),
                operation="difference",
                role="feature",
            )
        )
        graph.connect(chassis, slot, "cutout")

    return graph


def _motor_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "motor design")

    radius = _extract_radius(text, default=0.045)
    height = _extract_height(text, default=0.08)
    shaft_r = max(radius * 0.18, 0.004)
    shaft_h = height * 1.4

    housing = graph.add_component(
        _make_component(
            "housing",
            "cylinder",
            {"radius": radius, "height": height, "center": True},
            role="body",
        )
    )
    shaft = graph.add_component(
        _make_component(
            "shaft",
            "cylinder",
            {"radius": shaft_r, "height": shaft_h, "center": True},
            translate=(0.0, 0.0, height * 0.65),
            rotate=(90.0, 0.0, 0.0),
            role="mechanical",
        )
    )
    graph.connect(housing, shaft, "coaxial")

    rotor = graph.add_component(
        _make_component(
            "rotor",
            "cylinder",
            {"radius": radius * 0.65, "height": height * 0.72, "center": True},
            role="internal",
        )
    )
    graph.connect(housing, rotor, "internal")

    stator = graph.add_component(
        _make_component(
            "stator",
            "torus",
            {"R": radius * 0.82, "r": max(radius * 0.12, 0.003)},
            role="internal",
        )
    )
    graph.connect(housing, stator, "internal")

    if flags.get("holes"):
        bolt_circle = radius * 0.88
        for i in range(4):
            ang = math.tau * i / 4.0
            hole = graph.add_component(
                _make_component(
                    f"mount_hole_{i+1}",
                    "cylinder",
                    {"radius": max(radius * 0.07, 0.0025), "height": height * 1.2, "center": True},
                    translate=(bolt_circle * math.cos(ang), bolt_circle * math.sin(ang), 0.0),
                    operation="difference",
                    role="fastener",
                )
            )
            graph.connect(housing, hole, "cutout")

    return graph


def _container_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "container design")

    dims = _extract_sequence_dims(text)
    if dims is None:
        width = _extract_measurement(text, "width") or 0.12
        depth = _extract_measurement(text, "depth") or 0.08
        height = _extract_measurement(text, "height") or 0.06
        dims = (width, depth, height)

    w, d, h = dims
    body = graph.add_component(
        _make_component(
            "body",
            "box",
            {"size": (w, d, h), "center": True},
            role="body",
        )
    )

    if flags.get("hollow"):
        inner = graph.add_component(
            _make_component(
                "cavity",
                "box",
                {"size": (max(0.001, w * 0.86), max(0.001, d * 0.86), max(0.001, h * 0.86)), "center": True},
                operation="difference",
                role="feature",
            )
        )
        graph.connect(body, inner, "shell")

    if flags.get("rounded"):
        lid = graph.add_component(
            _make_component(
                "lid",
                "sphere",
                {"radius": min(w, d, h) * 0.24},
                translate=(0.0, 0.0, h * 0.54),
                role="feature",
            )
        )
        graph.connect(body, lid, "accent")

    hole_count = _extract_count(text, ["hole", "holes", "slot", "slots"], default=0)
    if hole_count:
        for idx in range(hole_count):
            off = -w * 0.35 + (w * 0.7) * (idx / max(1, hole_count - 1)) if hole_count > 1 else 0.0
            hole = graph.add_component(
                _make_component(
                    f"hole_{idx+1}",
                    "cylinder",
                    {"radius": min(w, d) * 0.05, "height": h * 1.5, "center": True},
                    translate=(off, 0.0, 0.0),
                    operation="difference",
                    role="fastener",
                )
            )
            graph.connect(body, hole, "cutout")

    return graph


def _furniture_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "furniture design")

    w = _extract_measurement(text, "width") or 0.4
    d = _extract_measurement(text, "depth") or 0.25
    h = _extract_measurement(text, "height") or 0.12

    base = graph.add_component(
        _make_component(
            "base",
            "box",
            {"size": (w, d, h), "center": True},
            role="body",
        )
    )
    tray = graph.add_component(
        _make_component(
            "tray",
            "box",
            {"size": (w * 0.88, d * 0.82, h * 0.55), "center": True},
            translate=(0.0, 0.0, h * 0.42),
            role="body",
        )
    )
    graph.connect(base, tray, "stacked")

    slot_count = _extract_count(text, ["slot", "slots", "compartment", "compartments"], default=0)
    for i in range(slot_count):
        slot = graph.add_component(
            _make_component(
                f"slot_{i+1}",
                "box",
                {"size": (w * 0.12, d * 0.72, h * 0.8), "center": True},
                translate=(-w * 0.28 + i * (w * 0.56 / max(1, slot_count - 1)) if slot_count > 1 else 0.0, 0.0, 0.0),
                operation="difference",
                role="feature",
            )
        )
        graph.connect(tray, slot, "cutout")

    return graph


def _generic_design(prompt: str, text: str, flags: Dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "generic design")

    dims = _extract_sequence_dims(text)
    if dims is not None:
        main = graph.add_component(
            _make_component("body", "box", {"size": dims, "center": True}, role="body")
        )
    elif "sphere" in text or "ball" in text:
        main = graph.add_component(
            _make_component("body", "sphere", {"radius": _extract_radius(text, 0.05)}, role="body")
        )
    elif "cylinder" in text or "tube" in text:
        main = graph.add_component(
            _make_component(
                "body",
                "cylinder",
                {"radius": _extract_radius(text, 0.04), "height": _extract_height(text, 0.08), "center": True},
                role="body",
            )
        )
    else:
        main = graph.add_component(
            _make_component("body", "box", {"size": (0.08, 0.08, 0.08), "center": True}, role="body")
        )

    if flags.get("holes"):
        hole = graph.add_component(
            _make_component(
                "hole",
                "cylinder",
                {"radius": 0.01, "height": 0.12, "center": True},
                operation="difference",
                role="feature",
            )
        )
        graph.connect(main, hole, "cutout")

    if flags.get("rounded"):
        cap = graph.add_component(
            _make_component(
                "cap",
                "sphere",
                {"radius": 0.02},
                translate=(0.0, 0.0, 0.05),
                role="feature",
            )
        )
        graph.connect(main, cap, "accent")

    return graph


def generate_design(prompt: str) -> DesignGraph:
    """Parse a natural-language prompt into a structured CAD design graph."""

    text = _normalize(prompt)
    flags = infer_features(text)
    domain = infer_domain(text)

    if domain == "aircraft":
        design = _aircraft_design(prompt, text, flags)
    elif domain == "vehicle":
        design = _vehicle_design(prompt, text, flags)
    elif domain == "mechanism":
        design = _motor_design(prompt, text, flags)
    elif domain in {"container", "furniture"}:
        design = _container_design(prompt, text, flags) if domain == "container" else _furniture_design(prompt, text, flags)
    else:
        design = _generic_design(prompt, text, flags)

    design.metadata.update(
        {
            "prompt": prompt,
            "normalized_prompt": text,
            "domain": domain,
            "flags": flags,
            "confidence": 0.9 if len(design.components) >= 2 else 0.6,
        }
    )
    return design
