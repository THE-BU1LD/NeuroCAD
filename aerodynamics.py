"""
aerodynamics.py
----------------
Agent-oriented aerodynamic reasoning engine.

GOALS
-----
• Fast (no CFD, no meshes)
• Deterministic & explainable
• Shape-aware
• Optimization-friendly
• Assembly-capable

This module enables:
- Drag & lift estimation
- Flow regime detection
- Stability heuristics
- Aero efficiency scoring
- Actionable design diagnostics
"""

from typing import Dict, List, Any, Tuple
import math

# ==========================================================
# ENVIRONMENT CONSTANTS
# ==========================================================

AIR_DENSITY = 1.225               # kg/m^3
KINEMATIC_VISCOSITY = 1.5e-5      # m^2/s
DEFAULT_SPEED = 10.0              # m/s
GRAVITY = 9.81                    # m/s^2

# ==========================================================
# SHAPE AERODYNAMIC PRIORS
# ==========================================================

CD_TABLE = {
    "sphere": 0.47,
    "cube": 1.05,
    "cylinder": 0.82,
    "flat_plate": 1.28,
    "streamlined": 0.12,
    "airfoil": 0.04,
    "unknown": 1.0,
}

CL_TABLE = {
    "airfoil": 0.9,
    "streamlined": 0.3,
    "flat_plate": 0.1,
    "cube": 0.0,
    "cylinder": 0.1,
    "sphere": 0.05,
    "unknown": 0.0,
}

# ==========================================================
# CORE PHYSICS
# ==========================================================

def reynolds_number(v: float, L: float) -> float:
    if L <= 0:
        return 0.0
    return (v * L) / KINEMATIC_VISCOSITY


def drag_force(cd: float, area: float, v: float) -> float:
    return 0.5 * AIR_DENSITY * v**2 * cd * area


def lift_force(cl: float, area: float, v: float) -> float:
    return 0.5 * AIR_DENSITY * v**2 * cl * area


def dynamic_pressure(v: float) -> float:
    return 0.5 * AIR_DENSITY * v**2


# ==========================================================
# GEOMETRY INTERPRETATION
# ==========================================================

def infer_shape(obj: Any) -> str:
    name = obj.__class__.__name__.lower()
    prim = getattr(obj, "primitive", "").lower()

    for k in CD_TABLE:
        if k in name or k in prim:
            return k

    if prim in {"cube", "cylinder"}:
        return prim

    return "unknown"


def characteristic_length(obj: Any) -> float:
    if hasattr(obj, "length"):
        return obj.length
    if hasattr(obj, "radius"):
        return 2 * obj.radius
    if hasattr(obj, "height"):
        return obj.height
    if hasattr(obj, "bounding_box"):
        return max(obj.bounding_box)
    return 0.1


def frontal_area(obj: Any) -> float:
    if hasattr(obj, "bounding_box"):
        _, y, z = obj.bounding_box
        return y * z

    if hasattr(obj, "radius"):
        return math.pi * obj.radius**2

    if hasattr(obj, "width") and hasattr(obj, "height"):
        return obj.width * obj.height

    return 1.0


def aspect_ratio(obj: Any) -> float:
    if hasattr(obj, "height") and hasattr(obj, "radius"):
        return obj.height / max(2 * obj.radius, 1e-3)
    return 1.0


# ==========================================================
# FLOW REGIME CLASSIFICATION
# ==========================================================

def flow_regime(Re: float) -> str:
    if Re < 2e3:
        return "creeping"
    if Re < 5e4:
        return "laminar"
    if Re < 1e6:
        return "transitional"
    return "turbulent"


def separation_risk(shape: str, Re: float) -> float:
    risk = 0.0
    if shape in {"cube", "flat_plate"}:
        risk += 0.6
    if Re > 1e5:
        risk += 0.2
    if shape == "streamlined":
        risk -= 0.3
    return max(0.0, min(1.0, risk))


# ==========================================================
# AERODYNAMIC EFFICIENCY
# ==========================================================

def lift_to_drag(cl: float, cd: float) -> float:
    if cd <= 0:
        return 0.0
    return cl / cd


def aero_efficiency_score(cl: float, cd: float) -> float:
    ld = lift_to_drag(cl, cd)
    return max(0.0, min(100.0, ld * 20))


# ==========================================================
# SINGLE OBJECT ANALYSIS
# ==========================================================

def analyze(obj: Any, velocity: float = DEFAULT_SPEED) -> Dict[str, Any]:
    shape = infer_shape(obj)

    cd = CD_TABLE.get(shape, CD_TABLE["unknown"])
    cl = CL_TABLE.get(shape, 0.0)

    area = frontal_area(obj)
    L = characteristic_length(obj)

    Re = reynolds_number(velocity, L)
    regime = flow_regime(Re)

    drag = drag_force(cd, area, velocity)
    lift = lift_force(cl, area, velocity)

    sep = separation_risk(shape, Re)
    efficiency = aero_efficiency_score(cl, cd)

    diagnostics: List[str] = []
    suggestions: List[str] = []

    # ---- Diagnostics ----
    if cd > 0.8:
        diagnostics.append("High drag coefficient detected")

    if shape in {"cube", "flat_plate"}:
        diagnostics.append("Bluff body → severe flow separation")

    if sep > 0.5:
        diagnostics.append("High flow separation risk")

    if regime == "laminar":
        diagnostics.append("Low Reynolds number → weak aerodynamic authority")

    if efficiency < 20:
        diagnostics.append("Poor aerodynamic efficiency")

    # ---- Suggestions ----
    if shape == "cube":
        suggestions.append("Replace cube with cylinder or teardrop profile")

    if area > 0.3:
        suggestions.append("Reduce frontal area")

    if hasattr(obj, "fillet") and obj.fillet is None:
        suggestions.append("Add fillets to reduce separation")

    if aspect_ratio(obj) < 1.5:
        suggestions.append("Increase aspect ratio for better streamlining")

    return {
        "shape": shape,
        "cd": cd,
        "cl": cl,
        "area": area,
        "characteristic_length": L,
        "reynolds_number": Re,
        "flow_regime": regime,
        "drag_force": drag,
        "lift_force": lift,
        "separation_risk": sep,
        "efficiency_score": efficiency,
        "diagnostics": diagnostics,
        "suggestions": suggestions,
    }


# ==========================================================
# ASSEMBLY ANALYSIS
# ==========================================================

def analyze_assembly(parts: List[Any], velocity: float = DEFAULT_SPEED) -> Dict[str, Any]:
    total_drag = 0.0
    total_lift = 0.0
    diagnostics: List[str] = []
    suggestions: List[str] = []
    shape_counts: Dict[str, int] = {}

    for p in parts:
        r = analyze(p, velocity)
        total_drag += r["drag_force"]
        total_lift += r["lift_force"]

        diagnostics.extend(r["diagnostics"])
        suggestions.extend(r["suggestions"])

        shape = r["shape"]
        shape_counts[shape] = shape_counts.get(shape, 0) + 1

    if shape_counts.get("cube", 0) > 0:
        diagnostics.append("Multiple bluff bodies causing wake interaction")

    if len(shape_counts) > 4:
        diagnostics.append("Highly heterogeneous geometry → turbulent interference")

    return {
        "total_drag": total_drag,
        "total_lift": total_lift,
        "shape_distribution": shape_counts,
        "diagnostics": list(set(diagnostics)),
        "suggestions": list(set(suggestions)),
    }