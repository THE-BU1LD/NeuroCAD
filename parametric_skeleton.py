"""
parametric_skeleton.py

High-level parametric design skeletons.
This file bridges intent → geometry.
"""

import random
from dataclasses import dataclass
from typing import Dict
from design_intent import DesignIntent


# ======================================================
# AIRCRAFT SKELETON
# ======================================================

@dataclass
class AircraftSkeleton:
    wing_span: float
    aspect_ratio: float
    wing_area: float

    fuselage_length: float
    fuselage_diameter: float

    sweep_angle: float
    thickness_ratio: float

    tail_volume: float

    def as_dict(self) -> Dict[str, float]:
        return self.__dict__


# ======================================================
# BASELINE GENERATOR
# ======================================================

def generate_aircraft_skeleton(intent: DesignIntent) -> AircraftSkeleton:
    """
    Maps design intent → physically consistent baseline skeleton
    """

    # -----------------------------
    # Objective weights
    # -----------------------------
    eff = intent.objectives.get("efficiency", 0.0)
    spd = intent.objectives.get("speed", 0.0)
    stab = intent.objectives.get("stability", 0.0)

    # -----------------------------
    # Wing
    # -----------------------------
    aspect_ratio = 8 + 8 * eff - 3 * spd
    aspect_ratio = max(6, min(14, aspect_ratio))

    wing_area = 25 + 20 * stab + 15 * eff
    wing_span = (aspect_ratio * wing_area) ** 0.5

    # -----------------------------
    # Fuselage
    # -----------------------------
    fuselage_length = 0.75 * wing_span
    fuselage_diameter = fuselage_length / (8 + 4 * intent.latent.get("slenderness", 0))

    # -----------------------------
    # Aero shaping
    # -----------------------------
    sweep_angle = 5 + 30 * spd
    thickness_ratio = 0.14 - 0.05 * spd + 0.03 * stab

    # -----------------------------
    # Stability
    # -----------------------------
    tail_volume = 0.45 + 0.2 * stab

    return AircraftSkeleton(
        wing_span=round(wing_span, 3),
        aspect_ratio=round(aspect_ratio, 3),
        wing_area=round(wing_area, 3),
        fuselage_length=round(fuselage_length, 3),
        fuselage_diameter=round(fuselage_diameter, 3),
        sweep_angle=round(sweep_angle, 3),
        thickness_ratio=round(thickness_ratio, 3),
        tail_volume=round(tail_volume, 3),
    )


# ======================================================
# MUTATION (FOR AUTONOMOUS IMPROVEMENT)
# ======================================================

def mutate_skeleton(skel: AircraftSkeleton, strength=0.1) -> AircraftSkeleton:
    def jitter(x, s):
        return max(0.01, x * (1 + random.uniform(-s, s)))

    return AircraftSkeleton(
        wing_span=jitter(skel.wing_span, strength),
        aspect_ratio=jitter(skel.aspect_ratio, strength),
        wing_area=jitter(skel.wing_area, strength),
        fuselage_length=jitter(skel.fuselage_length, strength),
        fuselage_diameter=jitter(skel.fuselage_diameter, strength),
        sweep_angle=jitter(skel.sweep_angle, strength),
        thickness_ratio=jitter(skel.thickness_ratio, strength),
        tail_volume=jitter(skel.tail_volume, strength),
    )
