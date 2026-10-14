"""Deterministic composite-shape generation with bounded exact analysis.

The shape builders intentionally use the existing canonical IR primitives and
Boolean compositions.  Analysis is exact for the declared idealized geometry;
it is not a substitute for meshing, FEA, fatigue, joints, or physical tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .ir import CADProgram, Node, Primitive, Transform, validate_program
from .physics_context import canonical_sha256

COMPLEX_SHAPE_REQUEST_VERSION = "neurocad-complex-shape-request-v1"
COMPLEX_SHAPE_ANALYSIS_VERSION = "neurocad-complex-shape-analysis-v1"
SUPPORTED_COMPLEX_SHAPES = ("hollow_shaft", "i_beam", "l_bracket", "perforated_plate")

_ANALYSIS_KEYS = {
    "source",
    "density_kg_m3",
    "elastic_modulus_mpa",
    "shear_modulus_mpa",
    "yield_strength_mpa",
    "safety_factor",
    "axial_force_n",
    "tip_force_x_n",
    "tip_force_y_n",
    "bending_moment_x_n_mm",
    "bending_moment_y_n_mm",
    "torque_n_mm",
    "effective_length_factor",
}


@dataclass(frozen=True)
class ComplexShapeBundle:
    program: CADProgram
    analysis: dict[str, Any]
    request: dict[str, Any]


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return value


def _only(value: dict[str, Any], *, allowed: set[str], required: set[str], name: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if extra:
        raise ValueError(f"{name} has unsupported keys: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{name} is missing keys: {', '.join(missing)}")


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _positive(value: Any, name: str, *, allow_zero: bool = False) -> float:
    result = _finite(value, name)
    if result < 0 if allow_zero else result <= 0:
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return result


def _integer(value: Any, name: str, *, minimum: int = 1, maximum: int = 20) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def _analysis_inputs(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    value = _object(raw, "analysis")
    _only(value, allowed=_ANALYSIS_KEYS, required={"source"}, name="analysis")
    source = value["source"]
    if not isinstance(source, str) or not source.strip() or len(source) > 2_048:
        raise ValueError("analysis.source must contain 1 to 2048 characters")
    result: dict[str, Any] = {"source": source.strip()}
    positive = {
        "density_kg_m3",
        "elastic_modulus_mpa",
        "shear_modulus_mpa",
        "yield_strength_mpa",
        "safety_factor",
        "effective_length_factor",
    }
    for name in sorted(set(value) - {"source"}):
        result[name] = _positive(value[name], f"analysis.{name}") if name in positive else _finite(value[name], f"analysis.{name}")
    result.setdefault("safety_factor", 1.0)
    result.setdefault("effective_length_factor", 1.0)
    for name in (
        "axial_force_n",
        "tip_force_x_n",
        "tip_force_y_n",
        "bending_moment_x_n_mm",
        "bending_moment_y_n_mm",
        "torque_n_mm",
    ):
        result.setdefault(name, 0.0)
    return result


def _box(node_id: str, size: tuple[float, float, float], *, translate: tuple[float, float, float] = (0, 0, 0)) -> Node:
    return Node(node_id, primitive=Primitive("box", {"size": list(size)}), transform=Transform(translate=translate))


def _validate_program(program: CADProgram) -> CADProgram:
    report = validate_program(program)
    if not report.valid:
        raise ValueError("generated complex shape is invalid: " + "; ".join(f"{item.path}: {item.message}" for item in report.errors))
    return program


def _mass_properties(
    *,
    density: float | None,
    volume_mm3: float,
    area_mm2: float,
    length_mm: float,
    centroid_xy_mm: tuple[float, float],
    ix_mm4: float,
    iy_mm4: float,
    ixy_mm4: float,
) -> dict[str, Any] | None:
    if density is None:
        return None
    mass = density * volume_mm3 * 1e-9
    return {
        "mass_kg": mass,
        "center_of_mass_mm": [centroid_xy_mm[0], centroid_xy_mm[1], 0.0],
        "centroidal_mass_moments_kg_m2": {
            "about_x": mass * (ix_mm4 / area_mm2 + length_mm**2 / 12.0) * 1e-6,
            "about_y": mass * (iy_mm4 / area_mm2 + length_mm**2 / 12.0) * 1e-6,
            "about_z": mass * (ix_mm4 + iy_mm4) / area_mm2 * 1e-6,
            "product_xy": mass * ixy_mm4 / area_mm2 * 1e-6,
        },
        "density_source": "explicit analysis.density_kg_m3",
    }


def _principal_moments(ix: float, iy: float, ixy: float) -> tuple[float, float, float]:
    average = (ix + iy) / 2.0
    radius = math.hypot((ix - iy) / 2.0, ixy)
    minimum = average - radius
    maximum = average + radius
    angle = 0.5 * math.atan2(-2.0 * ixy, iy - ix)
    return minimum, maximum, angle


def _structural_analysis(
    *,
    shape: str,
    analysis: dict[str, Any],
    area_mm2: float,
    length_mm: float,
    centroid_xy_mm: tuple[float, float],
    ix_mm4: float,
    iy_mm4: float,
    ixy_mm4: float,
    material_points_xy_mm: list[tuple[float, float]],
    polar_mm4: float | None = None,
    torsion_radius_mm: float | None = None,
) -> dict[str, Any] | None:
    if not analysis:
        return None
    torque = float(analysis["torque_n_mm"])
    if torque and (polar_mm4 is None or torsion_radius_mm is None):
        raise ValueError(f"analysis.torque_n_mm is not supported for {shape}; only hollow_shaft has an exact torsion mapping")
    axial = float(analysis["axial_force_n"])
    tip_x = float(analysis["tip_force_x_n"])
    tip_y = float(analysis["tip_force_y_n"])
    moment_x = float(analysis["bending_moment_x_n_mm"]) + tip_y * length_mm
    moment_y = float(analysis["bending_moment_y_n_mm"]) + tip_x * length_mm
    determinant = ix_mm4 * iy_mm4 - ixy_mm4**2
    if determinant <= 0:
        raise ValueError("cross-section inertia matrix is not positive definite")
    axial_stress = axial / area_mm2
    stresses = []
    for x, y in material_points_xy_mm:
        local_x = x - centroid_xy_mm[0]
        local_y = y - centroid_xy_mm[1]
        bending = (
            (ix_mm4 * moment_y + ixy_mm4 * moment_x) * local_x
            - (iy_mm4 * moment_x + ixy_mm4 * moment_y) * local_y
        ) / determinant
        stresses.append(axial_stress + bending)
    maximum_normal = max(stresses)
    minimum_normal = min(stresses)
    if shape == "hollow_shaft" and torsion_radius_mm is not None:
        # On the entire circular boundary, a*x+b*y has extrema +/-r*hypot(a,b).
        # Four cardinal samples miss the extrema under simultaneous biaxial bending.
        bending_amplitude = torsion_radius_mm * math.hypot(moment_x / ix_mm4, moment_y / iy_mm4)
        maximum_normal = axial_stress + bending_amplitude
        minimum_normal = axial_stress - bending_amplitude
    maximum_absolute_normal = max(abs(maximum_normal), abs(minimum_normal))
    torsional_shear = 0.0 if polar_mm4 is None or torsion_radius_mm is None else abs(torque) * torsion_radius_mm / polar_mm4
    von_mises = math.sqrt(maximum_absolute_normal**2 + 3.0 * torsional_shear**2)
    modulus = analysis.get("elastic_modulus_mpa")
    shear_modulus = analysis.get("shear_modulus_mpa")
    yield_strength = analysis.get("yield_strength_mpa")
    safety = float(analysis["safety_factor"])
    result: dict[str, Any] = {
        "load_sign_convention": "axial positive in tension; tip and moment components use centroidal +x/+y axes and a +z member axis",
        "root_resultants": {
            "axial_force_n": axial,
            "bending_moment_x_n_mm": moment_x,
            "bending_moment_y_n_mm": moment_y,
            "torque_n_mm": torque,
        },
        "normal_stress_mpa": {
            "minimum": minimum_normal,
            "maximum": maximum_normal,
            "maximum_absolute": maximum_absolute_normal,
        },
        "maximum_torsional_shear_mpa": torsional_shear if polar_mm4 is not None else None,
        "maximum_von_mises_screen_mpa": von_mises,
        "yield_utilization": None,
        "buckling_utilization": None,
        "constraint_satisfied": None,
        "checks": [],
    }
    checks: list[bool] = []
    if yield_strength is not None:
        allowable = float(yield_strength) / safety
        result["yield_utilization"] = von_mises / allowable
        result["checks"].append("maximum normal plus exact shaft torsion compared with supplied yield strength and safety factor")
        checks.append(von_mises <= allowable)
    if modulus is not None:
        modulus_value = float(modulus)
        result["cantilever_tip_displacement_mm"] = {
            "x": length_mm**3 * (ix_mm4 * tip_x + ixy_mm4 * tip_y) / (3.0 * modulus_value * determinant),
            "y": length_mm**3 * (iy_mm4 * tip_y + ixy_mm4 * tip_x) / (3.0 * modulus_value * determinant),
        }
        effective_length = float(analysis["effective_length_factor"]) * length_mm
        principal_min, principal_max, _ = _principal_moments(ix_mm4, iy_mm4, ixy_mm4)
        critical = math.pi**2 * modulus_value * principal_min / effective_length**2
        result["euler_buckling"] = {
            "minimum_axis_critical_compressive_load_n": critical,
            "effective_length_mm": effective_length,
            "utilization": max(0.0, -axial) / (critical / safety),
        }
        if axial < 0:
            result["buckling_utilization"] = max(0.0, -axial) / (critical / safety)
            result["checks"].append("ideal Euler buckling about the minimum principal axis")
            checks.append(-axial <= critical / safety)
        density = analysis.get("density_kg_m3")
        if density is not None:
            length_m = length_mm * 1e-3
            area_m2 = area_mm2 * 1e-6
            mass_per_length = float(density) * area_m2
            beta = 1.875104068711961
            frequencies = [
                beta**2 / (2.0 * math.pi * length_m**2) * math.sqrt(modulus_value * 1e6 * moment * 1e-12 / mass_per_length)
                for moment in (principal_min, principal_max)
            ]
            result["ideal_cantilever_bending_frequencies_hz"] = frequencies
    if torque and polar_mm4 is not None:
        if shear_modulus is None:
            result["torsion_warning"] = "twist not calculated because analysis.shear_modulus_mpa was not supplied"
        else:
            result["twist_radians"] = torque * length_mm / (float(shear_modulus) * polar_mm4)
    if checks:
        result["constraint_satisfied"] = all(checks)
    return result


def _final_analysis(
    *,
    shape: str,
    parameters: dict[str, Any],
    analysis_inputs: dict[str, Any],
    volume_mm3: float,
    surface_area_mm2: float,
    bounds_mm: tuple[float, float, float],
    area_mm2: float,
    length_mm: float,
    centroid_xy_mm: tuple[float, float],
    ix_mm4: float,
    iy_mm4: float,
    ixy_mm4: float,
    material_points_xy_mm: list[tuple[float, float]],
    minimum_feature_mm: float,
    extra_geometry: dict[str, Any],
    polar_mm4: float | None = None,
    torsion_radius_mm: float | None = None,
) -> dict[str, Any]:
    principal_min, principal_max, principal_angle = _principal_moments(ix_mm4, iy_mm4, ixy_mm4)
    density = analysis_inputs.get("density_kg_m3") if analysis_inputs else None
    mass = _mass_properties(
        density=None if density is None else float(density),
        volume_mm3=volume_mm3,
        area_mm2=area_mm2,
        length_mm=length_mm,
        centroid_xy_mm=centroid_xy_mm,
        ix_mm4=ix_mm4,
        iy_mm4=iy_mm4,
        ixy_mm4=ixy_mm4,
    )
    structural = _structural_analysis(
        shape=shape,
        analysis=analysis_inputs,
        area_mm2=area_mm2,
        length_mm=length_mm,
        centroid_xy_mm=centroid_xy_mm,
        ix_mm4=ix_mm4,
        iy_mm4=iy_mm4,
        ixy_mm4=ixy_mm4,
        material_points_xy_mm=material_points_xy_mm,
        polar_mm4=polar_mm4,
        torsion_radius_mm=torsion_radius_mm,
    )
    report: dict[str, Any] = {
        "schema_version": COMPLEX_SHAPE_ANALYSIS_VERSION,
        "shape": shape,
        "parameters": parameters,
        "geometry": {
            "calculation_status": "exact for the generated idealized composite geometry",
            "volume_mm3": volume_mm3,
            "surface_area_mm2": surface_area_mm2,
            "centroid_mm": [centroid_xy_mm[0], centroid_xy_mm[1], 0.0],
            "bounding_dimensions_mm": list(bounds_mm),
            "minimum_geometric_feature_mm": minimum_feature_mm,
            **extra_geometry,
        },
        "cross_section": {
            "reference_plane": "x-y centroidal section; member extrusion is along +z",
            "area_mm2": area_mm2,
            "centroid_xy_mm": list(centroid_xy_mm),
            "second_moment_x_mm4": ix_mm4,
            "second_moment_y_mm4": iy_mm4,
            "product_moment_xy_mm4": ixy_mm4,
            "principal_second_moments_mm4": [principal_min, principal_max],
            "principal_axis_angle_radians": principal_angle,
            **({"polar_second_moment_mm4": polar_mm4} if polar_mm4 is not None else {}),
        },
        "mass_properties": mass,
        "structural_screen": structural,
        "input_provenance": {
            "geometry": "explicit request parameters",
            "analysis": analysis_inputs.get("source") if analysis_inputs else None,
        },
        "assumptions": [
            "ideal sharp-edged or analytic primitives with the exact dimensions in the request",
            "homogeneous material only when an explicit density or modulus is supplied",
            "linear elastic small-deflection screening; no joints, local stress concentrations, fatigue, creep, plasticity, contact, or residual stress",
            "modal and buckling outputs use ideal uniform cantilever/Euler boundary models, not FEA or experimental calibration",
        ],
        "claim_boundary": "generated geometry and bounded analytical screening; not FEA, CFD, certification, safety approval, or physical validation",
    }
    report["analysis_sha256"] = canonical_sha256(report)
    return report


def _hollow_shaft(parameters: dict[str, Any], analysis: dict[str, Any]) -> tuple[CADProgram, dict[str, Any]]:
    required = {"outer_diameter_mm", "inner_diameter_mm", "length_mm"}
    _only(parameters, allowed=required, required=required, name="parameters")
    outer = _positive(parameters["outer_diameter_mm"], "parameters.outer_diameter_mm")
    inner = _positive(parameters["inner_diameter_mm"], "parameters.inner_diameter_mm", allow_zero=True)
    length = _positive(parameters["length_mm"], "parameters.length_mm")
    if inner >= outer:
        raise ValueError("parameters.inner_diameter_mm must be smaller than outer_diameter_mm")
    ro, ri = outer / 2.0, inner / 2.0
    nodes = [Node("outer", primitive=Primitive("cylinder", {"radius": ro, "height": length}))]
    root = "outer"
    if inner > 0:
        nodes.extend(
            [
                Node("bore", primitive=Primitive("cylinder", {"radius": ri, "height": length + 2.0}), role="void"),
                Node("hollow_shaft", composition="difference", children=("outer", "bore"), role="composition"),
            ]
        )
        root = "hollow_shaft"
    program = _validate_program(
        CADProgram(
            "Parametric hollow shaft",
            tuple(nodes),
            (root,),
            metadata={"source": "complex_shape", "shape": "hollow_shaft", "request_version": COMPLEX_SHAPE_REQUEST_VERSION},
        )
    )
    area = math.pi * (ro**2 - ri**2)
    ix = math.pi * (ro**4 - ri**4) / 4.0
    polar = 2.0 * ix
    volume = area * length
    surface = 2.0 * math.pi * (ro + ri) * length + 2.0 * area
    report = _final_analysis(
        shape="hollow_shaft",
        parameters=parameters,
        analysis_inputs=analysis,
        volume_mm3=volume,
        surface_area_mm2=surface,
        bounds_mm=(outer, outer, length),
        area_mm2=area,
        length_mm=length,
        centroid_xy_mm=(0.0, 0.0),
        ix_mm4=ix,
        iy_mm4=ix,
        ixy_mm4=0.0,
        material_points_xy_mm=[(ro, 0.0), (-ro, 0.0), (0.0, ro), (0.0, -ro)],
        minimum_feature_mm=(outer - inner) / 2.0,
        extra_geometry={"wall_thickness_mm": (outer - inner) / 2.0},
        polar_mm4=polar,
        torsion_radius_mm=ro,
    )
    return program, report


def _i_beam(parameters: dict[str, Any], analysis: dict[str, Any]) -> tuple[CADProgram, dict[str, Any]]:
    required = {"width_mm", "height_mm", "flange_thickness_mm", "web_thickness_mm", "length_mm"}
    _only(parameters, allowed=required, required=required, name="parameters")
    width = _positive(parameters["width_mm"], "parameters.width_mm")
    height = _positive(parameters["height_mm"], "parameters.height_mm")
    flange = _positive(parameters["flange_thickness_mm"], "parameters.flange_thickness_mm")
    web = _positive(parameters["web_thickness_mm"], "parameters.web_thickness_mm")
    length = _positive(parameters["length_mm"], "parameters.length_mm")
    if 2.0 * flange >= height:
        raise ValueError("twice flange_thickness_mm must be smaller than height_mm")
    if web >= width:
        raise ValueError("web_thickness_mm must be smaller than width_mm")
    flange_y = (height - flange) / 2.0
    nodes = (
        _box("top_flange", (width, flange, length), translate=(0.0, flange_y, 0.0)),
        _box("bottom_flange", (width, flange, length), translate=(0.0, -flange_y, 0.0)),
        _box("web", (web, height - 2.0 * flange, length)),
        Node("i_beam", composition="union", children=("top_flange", "bottom_flange", "web"), role="composition"),
    )
    program = _validate_program(
        CADProgram(
            "Parametric I-beam",
            nodes,
            ("i_beam",),
            metadata={"source": "complex_shape", "shape": "i_beam", "request_version": COMPLEX_SHAPE_REQUEST_VERSION},
        )
    )
    web_height = height - 2.0 * flange
    area = 2.0 * width * flange + web * web_height
    ix = width * height**3 / 12.0 - (width - web) * web_height**3 / 12.0
    iy = 2.0 * flange * width**3 / 12.0 + web_height * web**3 / 12.0
    perimeter = 4.0 * width + 2.0 * height - 2.0 * web
    points = [
        (x, y)
        for x in (-width / 2.0, width / 2.0)
        for y in (-height / 2.0, -height / 2.0 + flange, height / 2.0 - flange, height / 2.0)
    ] + [(x, y) for x in (-web / 2.0, web / 2.0) for y in (-web_height / 2.0, web_height / 2.0)]
    report = _final_analysis(
        shape="i_beam",
        parameters=parameters,
        analysis_inputs=analysis,
        volume_mm3=area * length,
        surface_area_mm2=2.0 * area + perimeter * length,
        bounds_mm=(width, height, length),
        area_mm2=area,
        length_mm=length,
        centroid_xy_mm=(0.0, 0.0),
        ix_mm4=ix,
        iy_mm4=iy,
        ixy_mm4=0.0,
        material_points_xy_mm=points,
        minimum_feature_mm=min(flange, web),
        extra_geometry={
            "section_modulus_x_mm3": ix / (height / 2.0),
            "section_modulus_y_mm3": iy / (width / 2.0),
            "web_slenderness": web_height / web,
            "flange_outstand_slenderness": ((width - web) / 2.0) / flange,
        },
    )
    return program, report


def _l_bracket(parameters: dict[str, Any], analysis: dict[str, Any]) -> tuple[CADProgram, dict[str, Any]]:
    required = {"width_mm", "height_mm", "thickness_mm", "length_mm"}
    _only(parameters, allowed=required, required=required, name="parameters")
    width = _positive(parameters["width_mm"], "parameters.width_mm")
    height = _positive(parameters["height_mm"], "parameters.height_mm")
    thickness = _positive(parameters["thickness_mm"], "parameters.thickness_mm")
    length = _positive(parameters["length_mm"], "parameters.length_mm")
    if thickness >= min(width, height):
        raise ValueError("thickness_mm must be smaller than width_mm and height_mm")
    horizontal_center = (0.0, -height / 2.0 + thickness / 2.0)
    vertical_center = (-width / 2.0 + thickness / 2.0, thickness / 2.0)
    nodes = (
        _box("horizontal_leg", (width, thickness, length), translate=(*horizontal_center, 0.0)),
        _box("vertical_leg", (thickness, height - thickness, length), translate=(*vertical_center, 0.0)),
        Node("l_bracket", composition="union", children=("horizontal_leg", "vertical_leg"), role="composition"),
    )
    program = _validate_program(
        CADProgram(
            "Parametric L-bracket",
            nodes,
            ("l_bracket",),
            metadata={"source": "complex_shape", "shape": "l_bracket", "request_version": COMPLEX_SHAPE_REQUEST_VERSION},
        )
    )
    rectangles = [
        (width, thickness, horizontal_center[0], horizontal_center[1]),
        (thickness, height - thickness, vertical_center[0], vertical_center[1]),
    ]
    area = sum(box_width * box_height for box_width, box_height, _, _ in rectangles)
    cx = sum(box_width * box_height * x for box_width, box_height, x, _ in rectangles) / area
    cy = sum(box_width * box_height * y for box_width, box_height, _, y in rectangles) / area
    ix = sum(
        box_width * box_height**3 / 12.0 + box_width * box_height * (y - cy) ** 2
        for box_width, box_height, _, y in rectangles
    )
    iy = sum(
        box_height * box_width**3 / 12.0 + box_width * box_height * (x - cx) ** 2
        for box_width, box_height, x, _ in rectangles
    )
    ixy = sum(box_width * box_height * (x - cx) * (y - cy) for box_width, box_height, x, y in rectangles)
    points: list[tuple[float, float]] = []
    for box_width, box_height, x, y in rectangles:
        points.extend(
            (x + sign_x * box_width / 2.0, y + sign_y * box_height / 2.0)
            for sign_x in (-1.0, 1.0)
            for sign_y in (-1.0, 1.0)
        )
    report = _final_analysis(
        shape="l_bracket",
        parameters=parameters,
        analysis_inputs=analysis,
        volume_mm3=area * length,
        surface_area_mm2=2.0 * area + 2.0 * (width + height) * length,
        bounds_mm=(width, height, length),
        area_mm2=area,
        length_mm=length,
        centroid_xy_mm=(cx, cy),
        ix_mm4=ix,
        iy_mm4=iy,
        ixy_mm4=ixy,
        material_points_xy_mm=points,
        minimum_feature_mm=thickness,
        extra_geometry={"centroid_offset_from_bounding_box_center_mm": [cx, cy]},
    )
    return program, report


def _grid_positions(span: float, count: int, margin: float) -> list[float]:
    if count == 1:
        return [0.0]
    first, last = -span / 2.0 + margin, span / 2.0 - margin
    pitch = (last - first) / (count - 1)
    return [first + index * pitch for index in range(count)]


def _perforated_plate(parameters: dict[str, Any], analysis: dict[str, Any]) -> tuple[CADProgram, dict[str, Any]]:
    required = {"width_mm", "height_mm", "thickness_mm", "hole_diameter_mm", "columns", "rows", "edge_margin_mm"}
    _only(parameters, allowed=required, required=required, name="parameters")
    width = _positive(parameters["width_mm"], "parameters.width_mm")
    height = _positive(parameters["height_mm"], "parameters.height_mm")
    thickness = _positive(parameters["thickness_mm"], "parameters.thickness_mm")
    diameter = _positive(parameters["hole_diameter_mm"], "parameters.hole_diameter_mm")
    columns = _integer(parameters["columns"], "parameters.columns")
    rows = _integer(parameters["rows"], "parameters.rows")
    margin = _positive(parameters["edge_margin_mm"], "parameters.edge_margin_mm")
    radius = diameter / 2.0
    if margin < radius:
        raise ValueError("edge_margin_mm must be at least half hole_diameter_mm")
    if 2.0 * margin >= width or 2.0 * margin >= height:
        raise ValueError("edge_margin_mm leaves no interior grid span")
    x_positions = _grid_positions(width, columns, margin)
    y_positions = _grid_positions(height, rows, margin)
    x_pitch = math.inf if columns == 1 else x_positions[1] - x_positions[0]
    y_pitch = math.inf if rows == 1 else y_positions[1] - y_positions[0]
    if min(x_pitch, y_pitch) <= diameter:
        raise ValueError("hole grid overlaps; increase plate size or edge margin, reduce counts, or reduce hole diameter")
    nodes: list[Node] = [_box("plate", (width, height, thickness))]
    holes: list[str] = []
    for row, y in enumerate(y_positions):
        for column, x in enumerate(x_positions):
            node_id = f"hole_{row + 1}_{column + 1}"
            holes.append(node_id)
            nodes.append(
                Node(
                    node_id,
                    primitive=Primitive("cylinder", {"radius": radius, "height": thickness + 2.0}),
                    transform=Transform(translate=(x, y, 0.0)),
                    role="void",
                )
            )
    nodes.append(Node("perforated_plate", composition="difference", children=("plate", *holes), role="composition"))
    program = _validate_program(
        CADProgram(
            "Parametric perforated plate",
            tuple(nodes),
            ("perforated_plate",),
            metadata={"source": "complex_shape", "shape": "perforated_plate", "request_version": COMPLEX_SHAPE_REQUEST_VERSION},
        )
    )
    gross_area = width * height
    hole_area = math.pi * radius**2
    count = rows * columns
    area = gross_area - count * hole_area
    ix = width * height**3 / 12.0 - sum(math.pi * radius**4 / 4.0 + hole_area * y**2 for y in y_positions for _ in x_positions)
    iy = height * width**3 / 12.0 - sum(math.pi * radius**4 / 4.0 + hole_area * x**2 for _ in y_positions for x in x_positions)
    if ix <= 0 or iy <= 0:
        raise ValueError("perforation layout leaves a non-positive section moment")
    volume = area * thickness
    surface = 2.0 * area + 2.0 * (width + height) * thickness + count * math.pi * diameter * thickness
    x_ligament = min(margin - radius, x_pitch - diameter if math.isfinite(x_pitch) else width - diameter)
    y_ligament = min(margin - radius, y_pitch - diameter if math.isfinite(y_pitch) else height - diameter)
    if any(float(analysis.get(name, 0.0)) != 0 for name in _ANALYSIS_KEYS - {"source", "density_kg_m3", "safety_factor", "effective_length_factor"}):
        raise ValueError("perforated_plate supports geometric and mass analysis only; its load path requires a declared plate model and boundary conditions")
    mass = None
    if analysis and "density_kg_m3" in analysis:
        density = float(analysis["density_kg_m3"])
        mass_value = density * volume * 1e-9
        mass = {
            "mass_kg": mass_value,
            "center_of_mass_mm": [0.0, 0.0, 0.0],
            "centroidal_mass_moments_kg_m2": {
                "about_x": mass_value * (ix / area + thickness**2 / 12.0) * 1e-6,
                "about_y": mass_value * (iy / area + thickness**2 / 12.0) * 1e-6,
                "about_z": mass_value * (ix + iy) / area * 1e-6,
                "product_xy": 0.0,
            },
            "density_source": "explicit analysis.density_kg_m3",
        }
    principal_min, principal_max, _ = _principal_moments(ix, iy, 0.0)
    report: dict[str, Any] = {
        "schema_version": COMPLEX_SHAPE_ANALYSIS_VERSION,
        "shape": "perforated_plate",
        "parameters": parameters,
        "geometry": {
            "calculation_status": "exact for the generated through-hole grid",
            "volume_mm3": volume,
            "surface_area_mm2": surface,
            "centroid_mm": [0.0, 0.0, 0.0],
            "bounding_dimensions_mm": [width, height, thickness],
            "hole_count": count,
            "open_area_fraction": count * hole_area / gross_area,
            "minimum_x_ligament_mm": x_ligament,
            "minimum_y_ligament_mm": y_ligament,
            "minimum_geometric_feature_mm": min(thickness, x_ligament, y_ligament),
        },
        "face_section": {
            "net_area_mm2": area,
            "second_moment_x_mm4": ix,
            "second_moment_y_mm4": iy,
            "principal_second_moments_mm4": [principal_min, principal_max],
        },
        "mass_properties": mass,
        "structural_screen": None,
        "input_provenance": {"geometry": "explicit request parameters", "analysis": analysis.get("source") if analysis else None},
        "assumptions": [
            "holes are circular, through-thickness, non-overlapping, and centered on the declared rectangular grid",
            "face section properties subtract each exact circular void by the parallel-axis theorem",
            "no pressure, plate-bending, buckling, stress-concentration, fatigue, or boundary-condition model is inferred",
        ],
        "claim_boundary": "generated geometry and exact idealized mass/section analysis; not plate FEA, certification, or physical validation",
    }
    report["analysis_sha256"] = canonical_sha256(report)
    return program, report


_BUILDERS = {
    "hollow_shaft": _hollow_shaft,
    "i_beam": _i_beam,
    "l_bracket": _l_bracket,
    "perforated_plate": _perforated_plate,
}


def build_complex_shape(raw: Any) -> ComplexShapeBundle:
    """Validate a strict request and return canonical geometry plus analysis."""

    request = _object(raw, "complex shape request")
    _only(
        request,
        allowed={"schema_version", "shape", "parameters", "analysis"},
        required={"schema_version", "shape", "parameters"},
        name="complex shape request",
    )
    if request["schema_version"] != COMPLEX_SHAPE_REQUEST_VERSION:
        raise ValueError(f"schema_version must be {COMPLEX_SHAPE_REQUEST_VERSION}")
    shape = request["shape"]
    if not isinstance(shape, str) or shape not in _BUILDERS:
        raise ValueError("shape must be one of " + ", ".join(SUPPORTED_COMPLEX_SHAPES))
    parameters = _object(request["parameters"], "parameters")
    analysis = _analysis_inputs(request.get("analysis"))
    program, report = _BUILDERS[shape](parameters, analysis)
    normalized_request = {
        "schema_version": COMPLEX_SHAPE_REQUEST_VERSION,
        "shape": shape,
        "parameters": parameters,
        **({"analysis": analysis} if analysis else {}),
    }
    program_payload = program.to_dict()
    report["request_sha256"] = canonical_sha256(normalized_request)
    report["program_sha256"] = canonical_sha256(program_payload)
    report["receipt_sha256"] = canonical_sha256({key: value for key, value in report.items() if key != "receipt_sha256"})
    return ComplexShapeBundle(program, report, normalized_request)


def complex_shape_catalog() -> dict[str, Any]:
    return {
        "schema_version": "neurocad-complex-shape-catalog-v1",
        "request_schema_version": COMPLEX_SHAPE_REQUEST_VERSION,
        "shapes": [
            {
                "name": "hollow_shaft",
                "parameters": ["outer_diameter_mm", "inner_diameter_mm", "length_mm"],
                "analysis": "exact annulus geometry, mass/inertia, combined axial/biaxial bending, torsion/twist, buckling, and ideal modes",
            },
            {
                "name": "i_beam",
                "parameters": ["width_mm", "height_mm", "flange_thickness_mm", "web_thickness_mm", "length_mm"],
                "analysis": "exact I-section geometry, mass/inertia, biaxial bending, deflection, Euler screening, and ideal modes",
            },
            {
                "name": "l_bracket",
                "parameters": ["width_mm", "height_mm", "thickness_mm", "length_mm"],
                "analysis": "exact unsymmetric centroid, product/principal inertia, coupled biaxial bending/deflection, buckling, and ideal modes",
            },
            {
                "name": "perforated_plate",
                "parameters": ["width_mm", "height_mm", "thickness_mm", "hole_diameter_mm", "columns", "rows", "edge_margin_mm"],
                "analysis": "exact through-hole volume, surface area, ligaments, face-section inertia, and optional mass properties",
            },
        ],
        "analysis_inputs": sorted(_ANALYSIS_KEYS),
        "claim_boundary": "composite canonical geometry and bounded closed-form analysis; not FEA, CFD, certification, or physical validation",
    }
