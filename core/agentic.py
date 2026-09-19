"""Persistent conversational planning over NeuroCAD's validated CAD IR.

Planning may be probabilistic and provider-driven. Every accepted plan is still
converted into the bounded canonical IR and validated before an artifact is
published into the project workspace.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from .artifacts import write_text_atomic
from .ir import CADProgram, Constraint, Node, Primitive, Transform, program_node_bounds, validate_program
from .ir_export import program_to_scad
from .ir_parser import serialize_ir_json
from .json_io import read_bounded_utf8, strict_json_loads

AGENT_PLAN_VERSION = "neurocad-agent-plan-v1"
AGENT_PROJECT_VERSION = "neurocad-agent-project-v1"
MAX_PROVIDER_RESPONSE_BYTES = 1_048_576
MAX_PROJECT_BYTES = 4 * 1_048_576
MAX_COMPONENTS = 256
MAX_ASSUMPTIONS = 128
MAX_HISTORY = 256
SUPPORTED_SHAPES = frozenset({"box", "rounded_box", "sphere", "cylinder", "cone", "torus"})
WEAPON_TERMS = re.compile(r"\b(?:missile|weapon|firearm|gun|bomb|explosive|warhead|grenade|mine)\b", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _text(value: Any, name: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1 to {maximum} characters")
    return value.strip()


def _vector(value: Any, name: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if value is None:
        return default
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must contain exactly three finite numbers")
    return tuple(_finite(item, f"{name}[{index}]") for index, item in enumerate(value))  # type: ignore[return-value]


@dataclass(frozen=True)
class AgentAssumption:
    name: str
    value: str
    reason: str
    source: str = "inferred"

    def __post_init__(self) -> None:
        _text(self.name, "assumption name", maximum=128)
        _text(self.value, "assumption value", maximum=256)
        _text(self.reason, "assumption reason", maximum=512)
        if self.source not in {"user", "inferred", "provider", "calculated"}:
            raise ValueError("assumption source must be user, inferred, provider, or calculated")


@dataclass(frozen=True)
class AgentComponent:
    id: str
    label: str
    part: str
    operation: str
    shape: str
    parameters: dict[str, Any]
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        _text(self.id, "component id", maximum=128)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", self.id) is None:
            raise ValueError(f"component id {self.id!r} is not a portable identifier")
        _text(self.label, "component label", maximum=128)
        _text(self.part, "component part", maximum=128)
        if self.operation not in {"add", "subtract"}:
            raise ValueError("component operation must be add or subtract")
        if self.shape not in SUPPORTED_SHAPES:
            raise ValueError(f"unsupported component shape {self.shape!r}")
        if not isinstance(self.parameters, dict):
            raise TypeError("component parameters must be an object")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["translate"] = list(self.translate)
        value["rotate"] = list(self.rotate)
        return value


@dataclass(frozen=True)
class AgentPlan:
    title: str
    summary: str
    assumptions: tuple[AgentAssumption, ...]
    components: tuple[AgentComponent, ...]
    version: str = AGENT_PLAN_VERSION

    def __post_init__(self) -> None:
        _text(self.title, "plan title", maximum=256)
        _text(self.summary, "plan summary", maximum=1_024)
        if self.version != AGENT_PLAN_VERSION:
            raise ValueError(f"plan version must be {AGENT_PLAN_VERSION!r}")
        if not 1 <= len(self.components) <= MAX_COMPONENTS:
            raise ValueError(f"plans require 1 to {MAX_COMPONENTS} components")
        if len(self.assumptions) > MAX_ASSUMPTIONS:
            raise ValueError(f"plans support at most {MAX_ASSUMPTIONS} assumptions")
        identifiers = [component.id for component in self.components]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("component ids must be unique")
        seen_parts: set[str] = set()
        for component in self.components:
            if component.part not in seen_parts:
                seen_parts.add(component.part)
                if component.operation != "add":
                    raise ValueError(f"part {component.part!r} must begin with an additive component")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "title": self.title,
            "summary": self.summary,
            "assumptions": [asdict(item) for item in self.assumptions],
            "components": [item.to_dict() for item in self.components],
        }


def parse_agent_plan(raw: Any) -> AgentPlan:
    if not isinstance(raw, dict):
        raise TypeError("agent plan must be an object")
    if set(raw) != {"version", "title", "summary", "assumptions", "components"}:
        raise ValueError("agent plan requires exactly version, title, summary, assumptions, and components")
    assumptions_raw, components_raw = raw["assumptions"], raw["components"]
    if not isinstance(assumptions_raw, list) or not isinstance(components_raw, list):
        raise TypeError("agent plan assumptions and components must be arrays")
    assumptions: list[AgentAssumption] = []
    for index, item in enumerate(assumptions_raw):
        if not isinstance(item, dict) or set(item) != {"name", "value", "reason", "source"}:
            raise ValueError(f"assumptions[{index}] has an invalid schema")
        assumptions.append(AgentAssumption(**item))
    components: list[AgentComponent] = []
    expected = {"id", "label", "part", "operation", "shape", "parameters", "translate", "rotate"}
    for index, item in enumerate(components_raw):
        if not isinstance(item, dict) or set(item) != expected:
            raise ValueError(f"components[{index}] has an invalid schema")
        components.append(
            AgentComponent(
                id=item["id"],
                label=item["label"],
                part=item["part"],
                operation=item["operation"],
                shape=item["shape"],
                parameters=item["parameters"],
                translate=_vector(item["translate"], f"components[{index}].translate", (0.0, 0.0, 0.0)),
                rotate=_vector(item["rotate"], f"components[{index}].rotate", (0.0, 0.0, 0.0)),
            )
        )
    plan = AgentPlan(raw["title"], raw["summary"], tuple(assumptions), tuple(components), raw["version"])
    plan_to_program(plan)
    return plan


def _primitive(component: AgentComponent) -> Primitive:
    return Primitive(component.shape, component.parameters)


def plan_to_program(plan: AgentPlan, *, component_count: int | None = None) -> CADProgram:
    """Convert a complete or progressive plan prefix into validated CAD IR."""

    count = len(plan.components) if component_count is None else component_count
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= len(plan.components):
        raise ValueError("component_count must select a non-empty plan prefix")
    selected = plan.components[:count]
    nodes: list[Node] = []
    constraints: list[Constraint] = []
    used = {component.id for component in selected}

    def unique(base: str) -> str:
        candidate, suffix = base, 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        return candidate

    part_order = tuple(dict.fromkeys(component.part for component in selected))
    roots: list[str] = []
    for component in selected:
        role = "void" if component.operation == "subtract" else "body"
        nodes.append(
            Node(
                component.id,
                primitive=_primitive(component),
                transform=Transform(translate=component.translate, rotate=component.rotate),
                role=role,
            )
        )
    for part in part_order:
        positives = [item.id for item in selected if item.part == part and item.operation == "add"]
        negatives = [item.id for item in selected if item.part == part and item.operation == "subtract"]
        if not positives:
            continue
        positive_root = positives[0]
        if len(positives) > 1:
            positive_root = unique(re.sub(r"[^A-Za-z0-9_-]", "_", part) + "_union")
            nodes.append(Node(positive_root, composition="union", children=tuple(positives), role="composition"))
        root = positive_root
        if negatives:
            root = unique(re.sub(r"[^A-Za-z0-9_-]", "_", part) + "_difference")
            nodes.append(Node(root, composition="difference", children=(positive_root, *negatives), role="composition"))
        roots.append(root)
    if not roots:
        raise ValueError("the selected plan prefix contains no additive component")
    program = CADProgram(
        plan.title,
        tuple(nodes),
        tuple(roots),
        tuple(constraints),
        {
            "source": "agent_plan",
            "plan_version": plan.version,
            "summary": plan.summary,
            "assumptions": [asdict(item) for item in plan.assumptions],
            "progress": {"components_complete": count, "components_total": len(plan.components)},
        },
    )
    report = validate_program(program)
    if not report.valid:
        details = "; ".join(f"{item.path}: {item.message}" for item in report.errors)
        raise ValueError("agent plan does not produce valid CAD IR: " + details)
    return program


def program_preview_svg(program: CADProgram) -> str:
    """Render a fast schematic preview for progressive agent feedback."""

    node_map = program.node_map()
    leaves = [node for node in program.nodes if node.primitive is not None]
    bounds = [program_node_bounds(node, node_map) for node in leaves]
    min_x = min(item[0][0] for item in bounds)
    max_x = max(item[1][0] for item in bounds)
    min_z = min(item[0][2] for item in bounds)
    max_z = max(item[1][2] for item in bounds)
    span_x, span_z = max(max_x - min_x, 1.0), max(max_z - min_z, 1.0)
    scale = min(720.0 / span_x, 440.0 / span_z)

    def point(x: float, z: float) -> tuple[float, float]:
        return 40.0 + (x - min_x) * scale, 40.0 + (max_z - z) * scale

    shapes: list[str] = []
    for node, (lower, upper) in zip(leaves, bounds, strict=True):
        x, y = point(lower[0], upper[2])
        width = max((upper[0] - lower[0]) * scale, 2.0)
        height = max((upper[2] - lower[2]) * scale, 2.0)
        subtractive = node.role == "void"
        fill = "#101820" if subtractive else "#2dd4bf"
        stroke = "#fb7185" if subtractive else "#ccfbf1"
        opacity = "0.72" if subtractive else "0.88"
        if node.primitive and node.primitive.kind == "sphere":
            shapes.append(
                f'<ellipse cx="{x + width / 2:.2f}" cy="{y + height / 2:.2f}" rx="{width / 2:.2f}" '
                f'ry="{height / 2:.2f}" fill="{fill}" stroke="{stroke}" opacity="{opacity}" stroke-width="2" />'
            )
        else:
            shapes.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
                f'rx="3" fill="{fill}" stroke="{stroke}" opacity="{opacity}" stroke-width="2" />'
            )
    title = html.escape(program.title)
    progress = program.metadata["progress"]
    return (
        '<svg viewBox="0 0 800 520" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Progressive schematic preview of {title}">'
        '<rect width="800" height="520" fill="#081018" />'
        '<g opacity=".18" stroke="#8aa4b2"><path d="M0 480H800M40 0V520" /></g>'
        + "".join(shapes)
        + f'<text x="24" y="28" fill="#d7f9f4" font-family="system-ui" font-size="14">{title}</text>'
        + f'<text x="776" y="28" text-anchor="end" fill="#8aa4b2" font-family="system-ui" font-size="12">'
        f'{progress["components_complete"]}/{progress["components_total"]} components</text></svg>'
    )


class PlanningProvider(Protocol):
    name: str

    def plan(self, prompt: str, previous: AgentPlan | None = None) -> AgentPlan: ...


def _capacity_ml(prompt: str, previous: AgentPlan | None = None) -> tuple[float, bool]:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(ml|millilit(?:er|re)s?|l|lit(?:er|re)s?)\b", prompt, re.IGNORECASE)
    if match is None:
        if previous is not None:
            for assumption in previous.assumptions:
                if assumption.name == "capacity":
                    prior = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*mL\s*", assumption.value, re.IGNORECASE)
                    if prior is not None:
                        return float(prior.group(1)), False
        return 750.0, False
    value = float(match.group(1))
    if match.group(2).lower() in {"l", "liter", "litre", "liters", "litres"}:
        value *= 1_000.0
    if not 100 <= value <= 5_000:
        raise ValueError("bottle capacity must be between 100 mL and 5 L")
    return value, True


def _water_bottle_plan(prompt: str, previous: AgentPlan | None) -> AgentPlan:
    capacity_ml, capacity_is_explicit = _capacity_ml(prompt, previous)
    prior_radius = 38.0
    prior_internal_height: float | None = None
    had_carry_loop = False
    if previous is not None:
        for component in previous.components:
            if component.id == "body_outer":
                prior_radius = float(component.parameters["radius"])
            elif component.id == "body_cavity":
                prior_internal_height = float(component.parameters["height"]) - 0.2
            elif component.id == "carry_loop":
                had_carry_loop = True
    outer_radius = prior_radius + (5.0 if re.search(r"\bwiden(?:ed)?\s+(?:the\s+)?base\b", prompt, re.IGNORECASE) else 0.0)
    wall = 3.0
    bottom = 3.5
    proportion_assumption: AgentAssumption | None = None
    if re.search(r"\btaller\b", prompt, re.IGNORECASE):
        baseline_height = prior_internal_height or capacity_ml * 1_000.0 / (math.pi * (outer_radius - wall) ** 2)
        target_height = baseline_height * 1.15
        outer_radius = math.sqrt(capacity_ml * 1_000.0 / (math.pi * target_height)) + wall
        proportion_assumption = AgentAssumption(
            "proportion change", "15% taller at constant capacity",
            "Interpreted taller as a slimmer profile while retaining the liquid capacity", "inferred",
        )
    elif re.search(r"\bshorter\b", prompt, re.IGNORECASE):
        baseline_height = prior_internal_height or capacity_ml * 1_000.0 / (math.pi * (outer_radius - wall) ** 2)
        target_height = baseline_height * 0.85
        outer_radius = math.sqrt(capacity_ml * 1_000.0 / (math.pi * target_height)) + wall
        proportion_assumption = AgentAssumption(
            "proportion change", "15% shorter at constant capacity",
            "Interpreted shorter as a wider profile while retaining the liquid capacity", "inferred",
        )
    inner_radius = outer_radius - wall
    internal_height = capacity_ml * 1_000.0 / (math.pi * inner_radius**2)
    if not 80 <= internal_height <= 400:
        raise ValueError("the inferred bottle proportions are outside the supported concept range")
    body_height = internal_height + bottom
    shoulder_height, neck_height = 26.0, 28.0
    neck_outer, neck_inner = 18.0, 14.5
    components = [
        AgentComponent("body_outer", "Main bottle body", "bottle", "add", "cylinder", {"radius": outer_radius, "height": body_height}, (0, 0, body_height / 2)),
        AgentComponent("shoulder_outer", "Tapered shoulder", "bottle", "add", "cone", {"r1": outer_radius, "r2": neck_outer, "height": shoulder_height}, (0, 0, body_height + shoulder_height / 2)),
        AgentComponent("neck_outer", "Bottle neck", "bottle", "add", "cylinder", {"radius": neck_outer, "height": neck_height}, (0, 0, body_height + shoulder_height + neck_height / 2)),
        AgentComponent("body_cavity", "Main liquid cavity", "bottle", "subtract", "cylinder", {"radius": inner_radius, "height": internal_height + 0.2}, (0, 0, bottom + internal_height / 2)),
        AgentComponent("shoulder_cavity", "Shoulder liquid cavity", "bottle", "subtract", "cone", {"r1": inner_radius, "r2": neck_inner, "height": shoulder_height + 0.4}, (0, 0, body_height + shoulder_height / 2)),
        AgentComponent("neck_bore", "Open neck", "bottle", "subtract", "cylinder", {"radius": neck_inner, "height": neck_height + 1.0}, (0, 0, body_height + shoulder_height + neck_height / 2)),
        AgentComponent("cap_outer", "Removable cap concept", "cap", "add", "cylinder", {"radius": neck_outer + 2.5, "height": 18.0}, (0, 0, body_height + shoulder_height + neck_height - 9.0)),
        AgentComponent("cap_cavity", "Cap clearance", "cap", "subtract", "cylinder", {"radius": neck_outer + 0.6, "height": 15.0}, (0, 0, body_height + shoulder_height + neck_height - 7.5)),
    ]
    remove_loop = re.search(r"\b(?:remove|delete|without)\b.{0,24}\b(?:loop|handle)\b", prompt, re.IGNORECASE)
    add_loop = re.search(r"\b(?:carrying|carry)\s+(?:loop|handle)\b", prompt, re.IGNORECASE)
    if (had_carry_loop or add_loop) and not remove_loop:
        components.append(
            AgentComponent(
                "carry_loop",
                "Carrying loop concept",
                "cap",
                "add",
                "torus",
                {"major_radius": 13.0, "minor_radius": 3.0},
                (neck_outer + 11.0, 0, body_height + shoulder_height + neck_height - 4.0),
                (90.0, 0.0, 0.0),
            )
        )
    assumptions = [
        AgentAssumption("capacity", f"{capacity_ml:g} mL", "Used the requested capacity, retained the prior capacity, or used the common personal-bottle default", "user" if capacity_is_explicit else "inferred"),
        AgentAssumption("wall thickness", f"{wall:g} mm", "Concept-stage printable wall; material and process remain unspecified"),
        AgentAssumption("cap", "slip-fit concept", "Thread standard requires a manufacturing-specific follow-up"),
        AgentAssumption("use boundary", "concept model", "Food-contact safety, sealing, and pressure performance are not inferred"),
    ]
    if proportion_assumption is not None:
        assumptions.append(proportion_assumption)
    return AgentPlan(
        "Water bottle concept",
        "A hollow capacity-driven bottle body with tapered shoulder, open neck, and separate cap concept.",
        tuple(assumptions),
        tuple(components),
    )


def _wheel_plan(prompt: str = "", previous: AgentPlan | None = None) -> AgentPlan:
    prior_diameter = 106.0
    if previous is not None:
        for component in previous.components:
            if component.id == "tire":
                prior_diameter = 2.0 * (
                    float(component.parameters["major_radius"]) + float(component.parameters["minor_radius"])
                )
                break
    dimension = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(mm|millimeters?|millimetres?|cm|centimeters?|centimetres?|inches?|inch|in)\b",
        prompt,
        re.IGNORECASE,
    )
    requested_mm: float | None = None
    if dimension is not None:
        requested_mm = float(dimension.group(1))
        unit = dimension.group(2).lower()
        if unit.startswith(("cm", "centim")):
            requested_mm *= 10.0
        elif unit in {"in", "inch", "inches"}:
            requested_mm *= 25.4
    relative = bool(re.search(r"\b(?:bigger|larger|wider|increase|grow)\b", prompt, re.IGNORECASE))
    smaller = bool(re.search(r"\b(?:smaller|narrower|decrease|shrink)\b", prompt, re.IGNORECASE))
    if requested_mm is None:
        diameter = prior_diameter
    elif relative:
        diameter = prior_diameter + requested_mm
    elif smaller:
        diameter = prior_diameter - requested_mm
    else:
        diameter = requested_mm
    if not 20.0 <= diameter <= 3_000.0:
        raise ValueError("wheel diameter must be between 20 mm and 3 m")
    scale = diameter / 106.0
    components = [
        AgentComponent("tire", "Wheel rim", "wheel", "add", "torus", {"major_radius": 45.0 * scale, "minor_radius": 8.0 * scale}),
        AgentComponent("hub", "Central hub", "wheel", "add", "cylinder", {"radius": 13.0 * scale, "height": 16.0 * scale}),
    ]
    for index, angle in enumerate((0.0, 60.0, 120.0)):
        components.append(AgentComponent(
            f"spoke_{index + 1}", f"Spoke pair {index + 1}", "wheel", "add", "rounded_box",
            {"size": [74.0 * scale, 6.0 * scale, 8.0 * scale], "radius": 2.0 * scale},
            (0.0, 0.0, 8.0 * scale), (0.0, 0.0, angle),
        ))
    components.append(AgentComponent(
        "axle_bore", "Axle bore", "wheel", "subtract", "cylinder", {"radius": 5.0 * scale, "height": 18.0 * scale}
    ))
    return AgentPlan(
        "Wheel concept", "An editable wheel concept with rim, hub, radial spokes, and an axle bore.",
        (
            AgentAssumption(
                "overall diameter", f"{diameter:g} mm",
                "Applied the requested dimensional edit" if requested_mm is not None else "Used a compact general-purpose concept size",
                "user" if requested_mm is not None else "inferred",
            ),
            AgentAssumption("axle bore", f"{10.0 * scale:g} mm", "Scaled with the wheel because no axle standard was specified"),
            *(
                (AgentAssumption("unit conversion", f"{float(dimension.group(1)):g} in = {requested_mm:g} mm", "Converted inches exactly at 25.4 mm per inch", "calculated"),)
                if dimension is not None and dimension.group(2).lower() in {"in", "inch", "inches"}
                else ()
            ),
            AgentAssumption("use boundary", "concept model", "Loads, material, bearings, and manufacturing process remain unspecified"),
        ), tuple(components),
    )


def _primitive_concept_plan(prompt: str) -> AgentPlan | None:
    lowered = prompt.lower()
    if re.search(r"\bcylinder\b", lowered):
        component = AgentComponent(
            "cylinder",
            "Cylinder concept",
            "main",
            "add",
            "cylinder",
            {"radius": 20.0, "height": 50.0},
            (0.0, 0.0, 25.0),
        )
        dimensions = "20 mm radius and 50 mm height"
    elif re.search(r"\b(?:sphere|ball)\b", lowered):
        component = AgentComponent("sphere", "Sphere concept", "main", "add", "sphere", {"radius": 20.0})
        dimensions = "20 mm radius"
    elif re.search(r"\b(?:box|block|cube)\b", lowered):
        component = AgentComponent(
            "box",
            "Box concept",
            "main",
            "add",
            "rounded_box",
            {"size": [60.0, 40.0, 30.0], "radius": 3.0},
            (0.0, 0.0, 15.0),
        )
        dimensions = "60 x 40 x 30 mm"
    else:
        return None
    return AgentPlan(
        component.label,
        "An immediately editable concept created from conventional dimensions.",
        (
            AgentAssumption("overall dimensions", dimensions, "The request omitted dimensions, so a compact concept default was used"),
            AgentAssumption("use boundary", "concept model", "No material, manufacturing process, or load case was specified"),
        ),
        (component,),
    )


def _mark_three_cosplay_plan(prompt: str) -> AgentPlan:
    height_match = re.search(r"\b(1[4-9]\d|2[0-1]\d)\s*cm\b", prompt, re.IGNORECASE)
    height_mm = float(height_match.group(1)) * 10.0 if height_match else 1_780.0
    scale = height_mm / 1_780.0

    def vec(values: tuple[float, float, float]) -> tuple[float, float, float]:
        return tuple(value * scale for value in values)  # type: ignore[return-value]

    def size(values: tuple[float, float, float]) -> list[float]:
        return [value * scale for value in values]

    components = (
        AgentComponent("helmet_outer", "Helmet shell", "helmet", "add", "sphere", {"radius": 135.0 * scale}, vec((0, 0, 1_655))),
        AgentComponent("helmet_inner", "Helmet head clearance", "helmet", "subtract", "sphere", {"radius": 124.0 * scale}, vec((0, 0, 1_655))),
        AgentComponent("helmet_opening", "Helmet lower opening", "helmet", "subtract", "box", {"size": size((190, 230, 130))}, vec((0, -20, 1_545))),
        AgentComponent("chest_outer", "Chest plate", "torso", "add", "rounded_box", {"size": size((440, 220, 480)), "radius": 42.0 * scale}, vec((0, 0, 1_285))),
        AgentComponent("chest_inner", "Chest clearance", "torso", "subtract", "rounded_box", {"size": size((414, 194, 458)), "radius": 34.0 * scale}, vec((0, -6, 1_282))),
        AgentComponent("abdomen", "Abdominal shell", "abdomen", "add", "rounded_box", {"size": size((330, 190, 280)), "radius": 32.0 * scale}, vec((0, 0, 910))),
        AgentComponent("abdomen_inner", "Abdominal clearance", "abdomen", "subtract", "rounded_box", {"size": size((306, 166, 260)), "radius": 26.0 * scale}, vec((0, -5, 910))),
        AgentComponent("left_upper_arm", "Left upper-arm panel", "left_arm", "add", "cylinder", {"radius": 74.0 * scale, "height": 300.0 * scale}, vec((-292, 0, 1_270)), (0, 10, 0)),
        AgentComponent("left_arm_clearance", "Left arm clearance", "left_arm", "subtract", "cylinder", {"radius": 62.0 * scale, "height": 282.0 * scale}, vec((-292, 0, 1_270)), (0, 10, 0)),
        AgentComponent("right_upper_arm", "Right upper-arm panel", "right_arm", "add", "cylinder", {"radius": 74.0 * scale, "height": 300.0 * scale}, vec((292, 0, 1_270)), (0, -10, 0)),
        AgentComponent("right_arm_clearance", "Right arm clearance", "right_arm", "subtract", "cylinder", {"radius": 62.0 * scale, "height": 282.0 * scale}, vec((292, 0, 1_270)), (0, -10, 0)),
        AgentComponent("left_forearm", "Left forearm panel", "left_forearm", "add", "cone", {"r1": 68.0 * scale, "r2": 52.0 * scale, "height": 300.0 * scale}, vec((-335, 0, 930)), (0, 6, 0)),
        AgentComponent("right_forearm", "Right forearm panel", "right_forearm", "add", "cone", {"r1": 68.0 * scale, "r2": 52.0 * scale, "height": 300.0 * scale}, vec((335, 0, 930)), (0, -6, 0)),
        AgentComponent("pelvis", "Pelvis shell", "pelvis", "add", "rounded_box", {"size": size((350, 210, 190)), "radius": 34.0 * scale}, vec((0, 0, 675))),
        AgentComponent("pelvis_inner", "Pelvis clearance", "pelvis", "subtract", "rounded_box", {"size": size((326, 186, 170)), "radius": 28.0 * scale}, vec((0, -5, 675))),
        AgentComponent("left_thigh", "Left thigh panel", "left_leg", "add", "cone", {"r1": 91.0 * scale, "r2": 72.0 * scale, "height": 410.0 * scale}, vec((-112, 0, 430))),
        AgentComponent("right_thigh", "Right thigh panel", "right_leg", "add", "cone", {"r1": 91.0 * scale, "r2": 72.0 * scale, "height": 410.0 * scale}, vec((112, 0, 430))),
        AgentComponent("left_boot", "Left boot shell", "left_boot", "add", "rounded_box", {"size": size((150, 285, 180)), "radius": 28.0 * scale}, vec((-105, -36, 105))),
        AgentComponent("right_boot", "Right boot shell", "right_boot", "add", "rounded_box", {"size": size((150, 285, 180)), "radius": 28.0 * scale}, vec((105, -36, 105))),
        AgentComponent("arc_reactor", "Chest light recess", "torso", "subtract", "cylinder", {"radius": 58.0 * scale, "height": 30.0 * scale}, vec((0, -106, 1_330)), (90, 0, 0)),
    )
    return AgentPlan(
        "Mark III inspired cosplay shell",
        "A staged decorative wearable-shell concept split into helmet, torso, arm, pelvis, leg, and boot regions.",
        (
            AgentAssumption("wearer height", f"{height_mm:g} mm", "Used the stated height or an adult display-fit reference", "user" if height_match else "inferred"),
            AgentAssumption("intended use", "cosplay and display only", "No protective, powered, flight, pressure, or weapon function is modeled"),
            AgentAssumption("fit allowance", "conceptual clearances", "Body scan, joints, closures, padding, and range-of-motion measurements are still required"),
            AgentAssumption("manufacturing", "unresolved", "Panels must be split and reviewed for the chosen printer and material before fabrication"),
        ),
        components,
    )


class BuiltinPlanningProvider:
    """Small offline planner used when no language-model provider is configured."""

    name = "builtin"

    def plan(self, prompt: str, previous: AgentPlan | None = None) -> AgentPlan:
        source = _text(prompt, "agent prompt", maximum=8_192)
        if WEAPON_TERMS.search(source):
            raise ValueError("weapon design requests are outside the NeuroCAD agent boundary")
        if re.search(r"\b(?:iron\s+man|mark\s*(?:iii|3)|cosplay\s+(?:armor|suit))\b", source, re.IGNORECASE):
            return _mark_three_cosplay_plan(source)
        if re.search(r"\bwheel\b", source, re.IGNORECASE):
            prior = previous if previous is not None and "wheel" in previous.title.lower() else None
            return _wheel_plan(source, prior)
        if re.search(r"\b(?:water\s+)?bottle\b", source, re.IGNORECASE):
            prior = previous if previous is not None and "bottle" in previous.title.lower() else None
            return _water_bottle_plan(source, prior)
        primitive = _primitive_concept_plan(source)
        if primitive is not None:
            return primitive
        context_is_bottle = previous is not None and "bottle" in previous.title.lower()
        bottle_revision = re.search(
            r"\b(?:it|make|add|remove|delete|widen|narrow|taller|shorter|capacity|cap|neck|base|loop|handle)\b",
            source, re.IGNORECASE,
        )
        if context_is_bottle and bottle_revision:
            return _water_bottle_plan(source, previous)
        context_is_wheel = previous is not None and "wheel" in previous.title.lower()
        wheel_revision = re.search(
            r"\b(?:it|make|diameter|bigger|larger|wider|smaller|narrower|increase|decrease|grow|shrink|hub|spoke|bore)\b",
            source, re.IGNORECASE,
        )
        if context_is_wheel and wheel_revision:
            return _wheel_plan(source, previous)
        raise ValueError(
            "the offline planner currently knows bottles, wheels, basic primitives, and cosplay shells; configure an OpenAI-compatible provider "
            "with NEUROCAD_LLM_ENDPOINT and NEUROCAD_LLM_MODEL for open-ended benign objects"
        )


_SYSTEM_PROMPT = """You are NeuroCAD's concept planner. Convert the user's benign object request into one JSON object.
Use only the supplied schema and millimetres. Make reasonable concept-stage assumptions instead of asking questions.
Build useful assemblies from box, rounded_box, sphere, cylinder, cone, and torus primitives. Each part must begin with
an additive component; subtractive components form cavities. Do not design weapons, life-critical equipment, or claim
manufacturing safety. Keep components under 64 unless the request truly requires more. Output JSON only.

Schema:
{"version":"neurocad-agent-plan-v1","title":"...","summary":"...","assumptions":[{"name":"...","value":"...","reason":"...","source":"user|inferred|provider|calculated"}],"components":[{"id":"portable_id","label":"...","part":"part_name","operation":"add|subtract","shape":"box|rounded_box|sphere|cylinder|cone|torus","parameters":{},"translate":[0,0,0],"rotate":[0,0,0]}]}
Parameter schemas: box {"size":[x,y,z]}; rounded_box {"size":[x,y,z],"radius":r}; sphere {"radius":r};
cylinder {"radius":r,"height":h}; cone {"r1":r1,"r2":r2,"height":h}; torus {"major_radius":R,"minor_radius":r}.
"""


class OpenAICompatiblePlanningProvider:
    """Bounded JSON planning client for OpenAI-compatible chat endpoints."""

    name = "openai-compatible"

    def __init__(self, endpoint: str, model: str, *, api_key: str | None = None, timeout_seconds: int = 120):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("provider endpoint must be an http(s) URL without embedded credentials")
        self.endpoint = endpoint.rstrip("/")
        self.model = _text(model, "provider model", maximum=256)
        self.api_key = api_key
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 600:
            raise ValueError("provider timeout must be an integer from 1 through 600 seconds")
        self.timeout_seconds = timeout_seconds

    def plan(self, prompt: str, previous: AgentPlan | None = None) -> AgentPlan:
        source = _text(prompt, "agent prompt", maximum=8_192)
        if WEAPON_TERMS.search(source):
            raise ValueError("weapon design requests are outside the NeuroCAD agent boundary")
        context = "No prior plan." if previous is None else "Current validated plan:\n" + json.dumps(previous.to_dict(), separators=(",", ":"))
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": context + "\n\nUser request:\n" + source},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")  # nosec B310
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                payload = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            detail = exc.read(4_096).decode("utf-8", errors="replace")
            raise RuntimeError(f"planning provider returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"planning provider is unavailable: {exc.reason}") from exc
        if len(payload) > MAX_PROVIDER_RESPONSE_BYTES:
            raise ValueError("planning provider response exceeds 1 MiB")
        decoded = strict_json_loads(payload.decode("utf-8"))
        try:
            content = decoded["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("planning provider response has no chat message content") from exc
        if not isinstance(content, str):
            raise TypeError("planning provider content must be a JSON string")
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        return parse_agent_plan(strict_json_loads(cleaned))


def planning_provider(selection: str = "auto", environment: Mapping[str, str] | None = None) -> PlanningProvider:
    env = os.environ if environment is None else environment
    choice = selection.strip().lower()
    if choice not in {"auto", "builtin", "openai", "ollama", "compatible"}:
        raise ValueError("provider must be auto, builtin, openai, ollama, or compatible")
    endpoint = env.get("NEUROCAD_LLM_ENDPOINT")
    model = env.get("NEUROCAD_LLM_MODEL")
    if choice == "builtin":
        return BuiltinPlanningProvider()
    if choice == "ollama":
        return OpenAICompatiblePlanningProvider(
            endpoint or env.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/v1/chat/completions",
            model or env.get("NEUROCAD_OLLAMA_MODEL", "qwen3-coder"),
        )
    if choice == "openai":
        key = env.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is required for provider openai")
        return OpenAICompatiblePlanningProvider(
            endpoint or "https://api.openai.com/v1/chat/completions",
            model or "gpt-5",
            api_key=key,
        )
    if choice == "compatible":
        if not endpoint or not model:
            raise ValueError("compatible provider requires NEUROCAD_LLM_ENDPOINT and NEUROCAD_LLM_MODEL")
        return OpenAICompatiblePlanningProvider(endpoint, model, api_key=env.get("NEUROCAD_LLM_API_KEY"))
    if endpoint and model:
        return OpenAICompatiblePlanningProvider(endpoint, model, api_key=env.get("NEUROCAD_LLM_API_KEY"))
    if env.get("OPENAI_API_KEY"):
        return OpenAICompatiblePlanningProvider(
            "https://api.openai.com/v1/chat/completions",
            model or "gpt-5",
            api_key=env["OPENAI_API_KEY"],
        )
    if env.get("NEUROCAD_OLLAMA_MODEL"):
        return planning_provider("ollama", env)
    return BuiltinPlanningProvider()


@dataclass(frozen=True)
class AgentRunResult:
    project_dir: str
    revision: int
    provider: str
    plan: AgentPlan
    current_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AGENT_PROJECT_VERSION,
            "project_dir": self.project_dir,
            "revision": self.revision,
            "provider": self.provider,
            "plan": self.plan.to_dict(),
            "current_snapshot": self.current_snapshot,
        }


class AgentWorkspace:
    """Filesystem-backed, checkpointed agent project."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.project_path = self.root / "project.json"
        self.events_path = self.root / "events.jsonl"
        self.snapshots = self.root / "snapshots"

    def initialize(self) -> None:
        if self.root.exists() and not self.root.is_dir():
            raise ValueError("agent project path exists and is not a directory")
        self.snapshots.mkdir(parents=True, exist_ok=True)

    def read_state(self) -> dict[str, Any] | None:
        if not self.project_path.exists():
            return None
        raw = strict_json_loads(read_bounded_utf8(self.project_path, max_bytes=MAX_PROJECT_BYTES, label="agent project"))
        if not isinstance(raw, dict) or raw.get("schema_version") != AGENT_PROJECT_VERSION:
            raise ValueError("agent project has an unsupported schema")
        return raw

    def read_plan(self) -> AgentPlan | None:
        state = self.read_state()
        return None if state is None else parse_agent_plan(state["plan"])

    def _event(self, kind: str, message: str, *, revision: int, stage: int, status: str, callback: Callable[[dict[str, Any]], None] | None) -> dict[str, Any]:
        event = {
            "at": _utc_now(),
            "kind": kind,
            "message": message,
            "revision": revision,
            "stage": stage,
            "status": status,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n")
        if callback is not None:
            callback(event)
        return event

    def _write_state(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
        if len(payload.encode("utf-8")) > MAX_PROJECT_BYTES:
            raise ValueError("agent project exceeds 4 MiB")
        write_text_atomic(self.project_path, payload)

    def run(
        self,
        prompt: str,
        provider: PlanningProvider,
        *,
        fn: int = 64,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> AgentRunResult:
        self.initialize()
        previous_state = self.read_state()
        previous_plan = None if previous_state is None else parse_agent_plan(previous_state["plan"])
        revision = 1 if previous_state is None else int(previous_state["revision"]) + 1
        self._event("understanding", "Understanding request", revision=revision, stage=0, status="running", callback=callback)
        plan = provider.plan(prompt, previous_plan)
        plan_to_program(plan)
        self._event("planned", f"Planned {len(plan.components)} components", revision=revision, stage=0, status="running", callback=callback)
        history = [] if previous_state is None else list(previous_state.get("history", []))[-(MAX_HISTORY - 1) :]
        current_snapshot: dict[str, Any] = {}
        for stage, component in enumerate(plan.components, start=1):
            program = plan_to_program(plan, component_count=stage)
            prefix = f"r{revision:04d}-s{stage:04d}"
            ir_path = self.snapshots / f"{prefix}.ncad.json"
            scad_path = self.snapshots / f"{prefix}.scad"
            preview_path = self.snapshots / f"{prefix}.svg"
            ir_text = serialize_ir_json(program)
            scad_text = program_to_scad(program, fn=fn)
            preview_text = program_preview_svg(program)
            write_text_atomic(ir_path, ir_text)
            write_text_atomic(scad_path, scad_text)
            write_text_atomic(preview_path, preview_text)
            current_snapshot = {
                "stage": stage,
                "stages_total": len(plan.components),
                "component_id": component.id,
                "component_label": component.label,
                "ir": str(ir_path.relative_to(self.root)),
                "scad": str(scad_path.relative_to(self.root)),
                "preview": str(preview_path.relative_to(self.root)),
                "sha256": {
                    "ir": hashlib.sha256(ir_text.encode()).hexdigest(),
                    "scad": hashlib.sha256(scad_text.encode()).hexdigest(),
                    "preview": hashlib.sha256(preview_text.encode()).hexdigest(),
                },
            }
            state = {
                "schema_version": AGENT_PROJECT_VERSION,
                "project_id": self.root.name,
                "title": plan.title,
                "revision": revision,
                "status": "building",
                "validation_level": "canonical_ir",
                "claim_boundary": "Concept geometry only; manufacturing and physics validation remain required before export.",
                "provider": provider.name,
                "prompt": prompt,
                "plan": plan.to_dict(),
                "current_snapshot": current_snapshot,
                "history": history,
                "updated_at": _utc_now(),
            }
            self._write_state(state)
            write_text_atomic(self.root / "design.ncad.json", ir_text)
            write_text_atomic(self.root / "design.scad", scad_text)
            write_text_atomic(self.root / "preview.svg", preview_text)
            self._event("component", component.label, revision=revision, stage=stage, status="running", callback=callback)
        history.append(
            {
                "revision": revision,
                "prompt": prompt,
                "provider": provider.name,
                "components": len(plan.components),
                "completed_at": _utc_now(),
            }
        )
        final_state = {
            "schema_version": AGENT_PROJECT_VERSION,
            "project_id": self.root.name,
            "title": plan.title,
            "revision": revision,
            "status": "draft_complete",
            "validation_level": "canonical_ir",
            "claim_boundary": "Concept geometry only; manufacturing and physics validation remain required before export.",
            "provider": provider.name,
            "prompt": prompt,
            "plan": plan.to_dict(),
            "current_snapshot": current_snapshot,
            "history": history,
            "updated_at": _utc_now(),
        }
        self._write_state(final_state)
        self._event("complete", "Draft revision complete", revision=revision, stage=len(plan.components), status="complete", callback=callback)
        return AgentRunResult(str(self.root), revision, provider.name, plan, current_snapshot)
