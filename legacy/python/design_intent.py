"""
design_intent.py

NeuroCAD Design Intent Compiler (v2)
-----------------------------------
Natural language → mathematical design intent
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List


# ======================================================
# DESIGN INTENT
# ======================================================

@dataclass
class DesignIntent:
    domain: str
    subtype: str

    # Continuous objective weights (sum to 1)
    objectives: Dict[str, float]

    # Hard constraints (symbolic)
    constraints: Dict[str, str]

    # Physics domains required
    physics_domains: List[str]

    # Continuous latent intent vector (for ML / mutation)
    latent: Dict[str, float]

    confidence: float = 1.0


# ======================================================
# LINGUISTIC ONTOLOGY
# ======================================================

DOMAIN_MAP = {
    "aircraft": ["plane", "aircraft", "airplane", "jet", "wing", "uav", "drone"],
}

SUBTYPE_MAP = {
    "fixed_wing": ["airliner", "glider", "fixed wing"],
    "uav": ["uav", "drone"],
    "fighter": ["fighter", "supersonic"],
}

OBJECTIVE_AXES = {
    "efficiency": ["efficient", "range", "endurance"],
    "speed": ["fast", "speed", "supersonic"],
    "stability": ["stable", "smooth"],
    "maneuverability": ["agile", "maneuverable"],
    "payload": ["payload", "cargo", "weight"],
}

LATENT_AXES = {
    "slenderness": ["sleek", "thin", "slender"],
    "robustness": ["strong", "robust", "durable"],
    "complexity": ["advanced", "complex"],
}

PHYSICS_BY_DOMAIN = {
    "aircraft": ["aerodynamics", "structures", "dynamics"],
}


# ======================================================
# PARSER
# ======================================================

def parse_prompt(prompt: str) -> DesignIntent:
    text = prompt.lower()

    # -----------------------------
    # DOMAIN
    # -----------------------------
    domain = "unknown"
    for d, keys in DOMAIN_MAP.items():
        if any(k in text for k in keys):
            domain = d
            break

    # -----------------------------
    # SUBTYPE
    # -----------------------------
    subtype = "generic"
    for s, keys in SUBTYPE_MAP.items():
        if any(k in text for k in keys):
            subtype = s
            break

    # -----------------------------
    # OBJECTIVES
    # -----------------------------
    raw_obj = {}
    for obj, keys in OBJECTIVE_AXES.items():
        count = sum(k in text for k in keys)
        if count > 0:
            raw_obj[obj] = count

    if not raw_obj:
        raw_obj["efficiency"] = 1

    total = sum(raw_obj.values())
    objectives = {k: v / total for k, v in raw_obj.items()}

    # -----------------------------
    # LATENT VECTOR
    # -----------------------------
    latent = {}
    for axis, keys in LATENT_AXES.items():
        latent[axis] = min(1.0, 0.3 * sum(k in text for k in keys))

    # -----------------------------
    # CONSTRAINTS
    # -----------------------------
    constraints = {}
    if "subsonic" in text:
        constraints["mach"] = "<0.85"
    if "supersonic" in text:
        constraints["mach"] = ">1.0"
    if "short runway" in text:
        constraints["takeoff_distance"] = "<500m"

    physics = PHYSICS_BY_DOMAIN.get(domain, [])

    confidence = min(1.0, 0.6 + 0.1 * len(objectives))

    return DesignIntent(
        domain=domain,
        subtype=subtype,
        objectives=objectives,
        constraints=constraints,
        physics_domains=physics,
        latent=latent,
        confidence=confidence,
    )
