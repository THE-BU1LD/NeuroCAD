from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from .design_graph import Component, DesignGraph

# OpenSCAD is unitless, but its fabrication ecosystem conventionally uses
# millimetres.  NeuroCAD therefore keeps every internal and exported length in
# millimetres.  Do not convert these values to SI metres before SCAD export.
UNIT_SCALE = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
}

UNIT_PATTERN = r"mm|millimeters?|cm|centimeters?|m|meters?|in|inch(?:es)?"
SIGNED_NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)"
UNSIGNED_INTEGER_PATTERN = r"\d+"

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
    "plate": ["plate", "panel", "bracket", "mounting board"],
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


def _normalization_is_lossless(text: str) -> bool:
    """Reject characters that normalization would otherwise silently erase."""

    prepared = text.lower().replace("×", "x")
    return re.fullmatch(r"[a-z0-9\.\-\+\s/x()_,;:]*", prepared) is not None


def _word_number(token: str) -> int | None:
    return NUM_WORDS.get(token)


def _to_mm(value: str, unit: str | None, default_unit: str = "mm") -> float:
    converted = float(value) * UNIT_SCALE[unit or default_unit]
    if not math.isfinite(converted):
        raise ValueError("dimension is outside the supported finite numeric range")
    return converted


def _extract_measurement(text: str, name: str) -> float | None:
    adjective = {
        "width": "wide",
        "depth": "deep",
        "height": "high|tall",
        "length": "long",
        "thickness": "thick",
        "diameter": "diameter",
        "radius": "radius",
        "wall": "walls?",
    }.get(name, name)
    patterns = [
        rf"\b{name}\s*(?:(?:is|of|=)\s*)?({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\b",
        rf"(?<![\w.])({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s*(?:{adjective})\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            value = float(m.group(1))
            return _to_mm(str(value), m.group(2))
    return None


def _extract_sequence_dims(text: str) -> tuple[float, float, float] | None:
    pattern = (
        rf"({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s*(?:x|by)\s*"
        rf"({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s*(?:x|by)\s*"
        rf"({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?"
    )
    matches = list(re.finditer(pattern, text))
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError("multiple overall dimension sequences are ambiguous")
    m = matches[0]
    units = [m.group(i) for i in (2, 4, 6)]
    shared_unit = next((unit for unit in reversed(units) if unit), "mm")
    out = []
    for value_index, unit in zip((1, 3, 5), units):
        out.append(_to_mm(m.group(value_index), unit, shared_unit))
    return out[0], out[1], out[2]


def _extract_radius(text: str, default: float = 50.0) -> float:
    value = _extract_measurement(text, "radius")
    if value is not None:
        return value
    m = re.search(rf"\br\s*=\s*({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\b", text)
    return _to_mm(m.group(1), m.group(2)) if m else default


def _extract_height(text: str, default: float = 100.0) -> float:
    value = _extract_measurement(text, "height")
    return value if value is not None else default


def _extract_count(text: str, keywords: Iterable[str], default: int = 0) -> tuple[int, bool]:
    """Return a feature count and whether it was stated unambiguously.

    Only the first token in the feature's ``with``/``and`` clause can be a
    count.  This prevents ``-4`` being re-read as ``4`` and ``2.5`` being
    re-read as ``5`` by a later regex match.  A singular ``a/an ... hole`` or
    ``slot`` is an explicit grammatical count of one; plurals always need an
    integer or supported number word.
    """

    keyword_matches = [match for keyword in keywords for match in re.finditer(rf"\b{re.escape(keyword)}\b", text)]
    for feature_match in sorted(keyword_matches, key=lambda match: match.start()):
        prefix = text[: feature_match.start()]
        clauses = re.split(r"\b(?:with|and)\b", prefix)
        if len(clauses) < 2:
            continue
        words = clauses[-1].strip().split()
        if not words:
            continue
        token = words[0]
        feature_word = feature_match.group(0)
        if token in {"a", "an"}:
            if feature_word.endswith("s"):
                return default, False
            return 1, True
        number_word = _word_number(token)
        if number_word is not None:
            if not 1 <= number_word <= 256:
                raise ValueError("feature counts must be integers from 1 to 256")
            return number_word, True
        if re.fullmatch(SIGNED_NUMBER_PATTERN, token):
            if len(words) > 1 and (re.fullmatch(UNIT_PATTERN, words[1]) or words[1] in {"x", "by"}):
                # ``4 mm holes`` and ``12 x 5 mm slots`` state dimensions but
                # no plural count.
                return default, False
            if token.startswith(("-", "+")) or "." in token:
                raise ValueError("feature counts must be unsigned whole integers from 1 to 256")
            count = int(token)
            if count > 256:
                raise ValueError("feature counts above 256 are not supported")
            if count < 1:
                raise ValueError("feature counts must be integers from 1 to 256")
            return count, True
    return default, False


def _extract_feature_diameter(text: str, feature: str) -> float | None:
    plural = feature + "s"
    patterns = [
        rf"\b(?:{feature}|{plural})\s+(?:of\s+)?(?:diameter\s+)?({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})\b",
        rf"\b(?:diameter|dia)\s+({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s+(?:{feature}|{plural})\b",
        rf"(?<![\w.])({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})\s+(?:diameter\s+)?(?:{feature}|{plural})\b",
        rf"\b(?:{feature}|{plural}).{{0,24}}?({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})\s+diameter\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _to_mm(match.group(1), match.group(2))
    return None


def _extract_two_dims(text: str, noun: str) -> tuple[float, float] | None:
    match = re.search(
        rf"(?<![\w.])({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s*(?:x|by)\s*"
        rf"({SIGNED_NUMBER_PATTERN})\s*({UNIT_PATTERN})?\s+(?:{noun}|{noun}s)\b",
        text,
    )
    if not match:
        return None
    first_unit, second_unit = match.group(2), match.group(4)
    shared = second_unit or first_unit or "mm"
    return (
        _to_mm(match.group(1), first_unit, shared),
        _to_mm(match.group(3), second_unit, shared),
    )


def _matches_prompt_contract(text: str, domain: str) -> bool:
    """Whether the complete normalized prompt belongs to the supported grammar.

    This deliberately uses anchored patterns.  Parsing individual dimensions
    is not evidence that trailing or interleaved prose was understood.
    """

    number = SIGNED_NUMBER_PATTERN
    unit = rf"(?:{UNIT_PATTERN})"
    measure = rf"{number}\s*{unit}?"
    dimensions = rf"{measure}\s*(?:x|by)\s*{measure}\s*(?:x|by)\s*{measure}"
    count_word = "|".join(word for word, value in NUM_WORDS.items() if value > 0)
    count = rf"(?:{UNSIGNED_INTEGER_PATTERN}|{count_word})"
    one_count = r"(?:1|one|a|an)"
    hole = rf"(?:{count}\s+{measure}\s+(?:diameter\s+)?holes?|{one_count}\s+{measure}\s+(?:diameter\s+)?hole)"
    slot = rf"(?:{count}\s+{measure}\s*(?:x|by)\s*{measure}\s+slots?|{one_count}\s+{measure}\s*(?:x|by)\s*{measure}\s+slot)"
    corner = rf"corner\s+radius\s+{measure}"
    wall = rf"{measure}\s+(?:wall\s+thickness|walls?)"
    plate_modifier = rf"(?:{hole}|{slot}|{corner})"
    plate_suffix = rf"(?:\s+with\s+{plate_modifier}(?:\s+and\s+{plate_modifier})?)?"
    article = r"(?:a|an)"

    patterns: list[str]
    if domain == "plate":
        plate_noun = r"(?:plate|panel|bracket|mounting\s+board)"
        patterns = [
            rf"{article}\s+(?:solid\s+)?{dimensions}\s+(?:rounded\s+)?{plate_noun}{plate_suffix}",
            rf"{article}\s+(?:rounded\s+)?{plate_noun}\s+{measure}\s+wide\s+{measure}\s+deep\s+(?:and\s+)?{measure}\s+thick{plate_suffix}",
        ]
    elif domain == "container":
        hollow_noun = r"(?:case|enclosure|housing|shell)"
        solid_noun = r"(?:box|rectangular\s+box)"
        patterns = [
            rf"{article}\s+{dimensions}\s+{hollow_noun}(?:\s+with\s+{wall})?",
            rf"{article}\s+(?:solid\s+)?{dimensions}\s+{solid_noun}",
        ]
    elif domain == "generic":
        block_noun = r"(?:block|cube|cuboid|rectangular\s+block|rectangular\s+prism)"
        radius = rf"radius\s+{measure}"
        diameter = rf"diameter\s+{measure}"
        height = rf"height\s+{measure}"
        patterns = [
            rf"{article}\s+(?:solid\s+)?{dimensions}\s+{block_noun}",
            rf"{article}\s+(?:sphere|ball)\s+with\s+{radius}",
            rf"{article}\s+{measure}\s+radius\s+(?:sphere|ball)",
            rf"{article}\s+(?:cylinder|tube)\s+with\s+(?:{radius}|{diameter})\s+and\s+{height}",
            rf"{article}\s+{measure}\s+(?:radius|diameter)\s+(?:cylinder|tube)\s+(?:with\s+)?{height}",
        ]
    else:
        return False

    if len(re.findall(r"\bholes?\b", text)) > 1:
        return False
    if len(re.findall(r"\bslots?\b", text)) > 1:
        return False
    return any(re.fullmatch(pattern, text) is not None for pattern in patterns)


def _feature_positions(count: int, width: float, depth: float, margin: float) -> list[tuple[float, float, float]]:
    usable_x = max(0.0, width / 2.0 - margin)
    usable_y = max(0.0, depth / 2.0 - margin)
    if count <= 0:
        return []
    if count == 1:
        return [(0.0, 0.0, 0.0)]
    if count == 2:
        return [(-usable_x, 0.0, 0.0), (usable_x, 0.0, 0.0)]
    if count == 4:
        return [
            (-usable_x, -usable_y, 0.0),
            (-usable_x, usable_y, 0.0),
            (usable_x, -usable_y, 0.0),
            (usable_x, usable_y, 0.0),
        ]
    # A regular elliptical ring has its centroid exactly at the origin for any
    # count >= 3.  The previous truncated row-major grid shifted odd feature
    # counts away from the requested center.
    return [
        (
            usable_x * math.cos(math.tau * index / count),
            usable_y * math.sin(math.tau * index / count),
            0.0,
        )
        for index in range(count)
    ]


def infer_domain(text: str) -> str:
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(k)}\b", text) for k in keywords):
            return domain
    return "generic"


def infer_features(text: str) -> dict[str, bool]:
    flags = {}
    for name, kws in FEATURE_KEYWORDS.items():
        flags[name] = any(re.search(rf"\b{re.escape(k)}\b", text) for k in kws)
    return flags


def _make_component(
    name: str,
    kind: str,
    params: dict[str, Any],
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


def _aircraft_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "aircraft design")

    span = _extract_measurement(text, "span") or _extract_measurement(text, "wingspan") or 800.0
    length = _extract_measurement(text, "length") or 900.0
    height = _extract_measurement(text, "height") or 160.0
    radius = max(20.0, min(length * 0.09, span * 0.08))

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

    wing_thickness = max(8.0, radius * 0.18)
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


def _vehicle_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "vehicle design")

    length = _extract_measurement(text, "length") or 350.0
    width = _extract_measurement(text, "width") or 160.0
    height = _extract_measurement(text, "height") or 110.0
    wheel_radius = max(15.0, min(width * 0.18, length * 0.08))
    wheel_thickness = max(10.0, wheel_radius * 0.6)

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
    wheels: list[Component] = []
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


def _motor_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "motor design")

    radius = _extract_radius(text, default=45.0)
    height = _extract_height(text, default=80.0)
    shaft_r = max(radius * 0.18, 4.0)
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
            {"R": radius * 0.82, "r": max(radius * 0.12, 3.0)},
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
                    f"mount_hole_{i + 1}",
                    "cylinder",
                    {"radius": max(radius * 0.07, 2.5), "height": height * 1.2, "center": True},
                    translate=(bolt_circle * math.cos(ang), bolt_circle * math.sin(ang), 0.0),
                    operation="difference",
                    role="fastener",
                )
            )
            graph.connect(housing, hole, "cutout")

    return graph


def _fabrication_design(prompt: str, text: str, flags: dict[str, bool], *, plate: bool) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or ("plate design" if plate else "enclosure design"))

    dims = _extract_sequence_dims(text)
    explicit_dims = dims is not None
    if dims is None:
        width = _extract_measurement(text, "width")
        depth = _extract_measurement(text, "depth")
        height = _extract_measurement(text, "thickness" if plate else "height")
        explicit_dims = all(value is not None for value in (width, depth, height))
        dims = (
            width if width is not None else 120.0,
            depth if depth is not None else 80.0,
            height if height is not None else (3.0 if plate else 60.0),
        )

    w, d, h = dims
    explicit_corner_radius = _extract_measurement(text, "corner radius")
    corner_radius = explicit_corner_radius if explicit_corner_radius is not None else 0.0
    rounded = flags.get("rounded", False) or corner_radius > 0
    if rounded and explicit_corner_radius is None:
        corner_radius = min(w, d) * 0.06
    body_geometry: dict[str, object] = {"size": (w, d, h), "center": True}
    if rounded:
        body_geometry["radius"] = corner_radius
    body = graph.add_component(
        _make_component(
            "body",
            "rounded_box" if rounded else "box",
            body_geometry,
            role="body",
        )
    )

    explicit_wall = _extract_measurement(text, "wall thickness")
    if explicit_wall is None:
        explicit_wall = _extract_measurement(text, "wall")
    wall = explicit_wall
    hollow = flags.get("hollow", False) or bool(re.search(r"\b(enclosure|case|housing)\b", text))
    if hollow:
        wall = wall if wall is not None else max(2.0, min(w, d, h) * 0.06)
        cavity_height = max(0.1, h - wall + 0.2)
        inner = graph.add_component(
            _make_component(
                "cavity",
                "box",
                {
                    "size": (max(0.1, w - 2 * wall), max(0.1, d - 2 * wall), cavity_height),
                    "center": True,
                },
                translate=(0.0, 0.0, (wall + 0.2) / 2.0),
                operation="difference",
                role="feature",
            )
        )
        graph.connect(body, inner, "shell")

    hole_count, hole_count_explicit = _extract_count(text, ["hole", "holes"])
    explicit_hole_diameter = _extract_feature_diameter(text, "hole")
    hole_diameter = explicit_hole_diameter if explicit_hole_diameter is not None else min(w, d) * 0.1
    if hole_count:
        margin = max(hole_diameter, (wall or 0.0) * 1.5, min(w, d) * 0.1)
        for idx, position in enumerate(_feature_positions(hole_count, w, d, margin)):
            hole = graph.add_component(
                _make_component(
                    f"hole_{idx + 1}",
                    "cylinder",
                    {"radius": hole_diameter / 2.0, "height": h + 2.0, "center": True},
                    translate=position,
                    operation="difference",
                    role="fastener",
                )
            )
            graph.connect(body, hole, "cutout")

    slot_count, slot_count_explicit = _extract_count(text, ["slot", "slots"])
    explicit_slot_dims = _extract_two_dims(text, "slot")
    slot_dims = explicit_slot_dims if explicit_slot_dims is not None else (max(8.0, w * 0.2), max(3.0, d * 0.08))
    for idx, position in enumerate(_feature_positions(slot_count, w, d, max(slot_dims))):
        slot = graph.add_component(
            _make_component(
                f"slot_{idx + 1}",
                "box",
                {"size": (slot_dims[0], slot_dims[1], h + 2.0), "center": True},
                translate=position,
                operation="difference",
                role="feature",
            )
        )
        graph.connect(body, slot, "cutout")

    graph.metadata.update(
        {
            "recognized": True,
            "fabrication_domain": "plate" if plate else "enclosure",
            "explicit_dimensions": explicit_dims,
            "dimensions_mm": [w, d, h],
            "wall_thickness_mm": wall,
            "wall_thickness_explicit": explicit_wall is not None,
            "corner_radius_mm": corner_radius if rounded else None,
            "corner_radius_explicit": explicit_corner_radius is not None,
            "rounded_requested": rounded,
            "hole_count_requested": hole_count,
            "hole_count_explicit": hole_count_explicit,
            "hole_diameter_mm": hole_diameter if hole_count else None,
            "hole_diameter_explicit": explicit_hole_diameter is not None,
            "slot_count_requested": slot_count,
            "slot_count_explicit": slot_count_explicit,
            "slot_dimensions_mm": list(slot_dims) if slot_count else None,
            "slot_dimensions_explicit": explicit_slot_dims is not None,
            "units": "mm",
        }
    )

    return graph


def _container_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    return _fabrication_design(prompt, text, flags, plate=False)


def _plate_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    return _fabrication_design(prompt, text, flags, plate=True)


def _furniture_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "furniture design")

    w = _extract_measurement(text, "width") or 400.0
    d = _extract_measurement(text, "depth") or 250.0
    h = _extract_measurement(text, "height") or 120.0

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

    slot_count, _ = _extract_count(text, ["slot", "slots", "compartment", "compartments"])
    for i in range(slot_count):
        slot = graph.add_component(
            _make_component(
                f"slot_{i + 1}",
                "box",
                {"size": (w * 0.12, d * 0.72, h * 0.8), "center": True},
                translate=(-w * 0.28 + i * (w * 0.56 / max(1, slot_count - 1)) if slot_count > 1 else 0.0, 0.0, 0.0),
                operation="difference",
                role="feature",
            )
        )
        graph.connect(tray, slot, "cutout")

    return graph


def _generic_design(prompt: str, text: str, flags: dict[str, bool]) -> DesignGraph:
    graph = DesignGraph(title=prompt.strip() or "generic design")

    dims = _extract_sequence_dims(text)
    recognized = False
    if dims is not None and re.search(r"\b(?:block|cube|cuboid|rectangular prism)\b", text):
        main = graph.add_component(_make_component("body", "box", {"size": dims, "center": True}, role="body"))
        recognized = True
    elif re.search(r"\b(?:sphere|ball)\b", text):
        explicit_radius = _extract_measurement(text, "radius")
        main = graph.add_component(
            _make_component("body", "sphere", {"radius": explicit_radius if explicit_radius is not None else 50.0}, role="body")
        )
        recognized = explicit_radius is not None
    elif re.search(r"\b(?:cylinder|tube)\b", text):
        explicit_radius = _extract_measurement(text, "radius")
        diameter = _extract_measurement(text, "diameter")
        explicit_height = _extract_measurement(text, "height")
        main = graph.add_component(
            _make_component(
                "body",
                "cylinder",
                {
                    "radius": explicit_radius if explicit_radius is not None else (diameter / 2.0 if diameter is not None else 40.0),
                    "height": explicit_height if explicit_height is not None else 80.0,
                    "center": True,
                },
                role="body",
            )
        )
        recognized = (explicit_radius is not None or diameter is not None) and explicit_height is not None
    else:
        main = graph.add_component(_make_component("body", "box", {"size": (80.0, 80.0, 80.0), "center": True}, role="body"))

    if flags.get("holes"):
        hole = graph.add_component(
            _make_component(
                "hole",
                "cylinder",
                {"radius": 10.0, "height": 120.0, "center": True},
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
                {"radius": 20.0},
                translate=(0.0, 0.0, 50.0),
                role="feature",
            )
        )
        graph.connect(main, cap, "accent")

    graph.metadata.update(
        {
            "recognized": recognized,
            "explicit_dimensions": recognized,
            "fabrication_domain": "primitive" if recognized else None,
            "units": "mm",
        }
    )

    return graph


def generate_design(prompt: str) -> DesignGraph:
    """Parse a prompt into a graph that public exporters will validate."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("engineering prompt must be a non-empty string")
    if len(prompt) > 4096:
        raise ValueError("engineering prompts are limited to 4096 characters")
    text = _normalize(prompt)
    normalization_is_lossless = _normalization_is_lossless(prompt)
    flags = infer_features(text)
    domain = infer_domain(text)

    # Legacy aircraft, vehicle, mechanism, and furniture generators produced
    # plausible-looking default geometry for unsupported requests.  They are
    # intentionally quarantined from the production parser.
    if domain == "container":
        design = _container_design(prompt, text, flags)
    elif domain == "plate":
        design = _plate_design(prompt, text, flags)
    elif domain == "generic":
        design = _generic_design(prompt, text, flags)
    else:
        design = DesignGraph(title=prompt.strip() or "unsupported design")

    design.metadata.update(
        {
            "prompt": prompt,
            "source_kind": "prompt",
            "normalized_prompt": text,
            "domain": domain,
            "flags": flags,
            "prompt_fully_consumed": normalization_is_lossless and _matches_prompt_contract(text, domain),
            "confidence": 0.9 if len(design.components) >= 2 else 0.6,
            "units": "mm",
        }
    )
    design.metadata.setdefault("recognized", False)
    design.metadata.setdefault("explicit_dimensions", False)
    return design
