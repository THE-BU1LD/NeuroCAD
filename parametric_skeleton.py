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
# HELPERS
# ======================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ======================================================
# BASELINE GENERATOR (IMPROVED)
# ======================================================

def generate_aircraft_skeleton(intent: DesignIntent) -> AircraftSkeleton:
    """
    Physically consistent mapping: intent → aircraft geometry
    """

    eff = intent.objectives.get("efficiency", 0.0)
    spd = intent.objectives.get("speed", 0.0)
    stab = intent.objectives.get("stability", 0.0)
    slender = intent.latent.get("slenderness", 0.0)

    # -----------------------------
    # Wing (primary driver)
    # -----------------------------
    aspect_ratio = clamp(8 + 6 * eff - 2.5 * spd, 6, 14)

    wing_area = clamp(20 + 25 * stab + 10 * eff, 15, 80)

    wing_span = (aspect_ratio * wing_area) ** 0.5  # enforced consistency

    # -----------------------------
    # Fuselage (linked to span)
    # -----------------------------
    fuselage_length = clamp(0.7 * wing_span, 5, 80)

    fineness_ratio = clamp(8 + 4 * slender, 6, 12)
    fuselage_diameter = fuselage_length / fineness_ratio

    # -----------------------------
    # Aerodynamics
    # -----------------------------
    sweep_angle = clamp(5 + 35 * spd, 0, 45)

    thickness_ratio = clamp(
        0.12 - 0.04 * spd + 0.025 * stab,
        0.08,
        0.18
    )

    # -----------------------------
    # Stability (still simplified but bounded)
    # -----------------------------
    tail_volume = clamp(0.5 + 0.15 * stab, 0.4, 0.8)

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
# MUTATION (STRUCTURE-AWARE)
# ======================================================

def mutate_skeleton(skel: AircraftSkeleton, strength=0.1) -> AircraftSkeleton:
    """
    Mutate in a physically consistent way.
    Keeps key relationships intact.
    """

    def jitter(x):
        return x * (1 + random.uniform(-strength, strength))

    # --- mutate core drivers ---
    aspect_ratio = clamp(jitter(skel.aspect_ratio), 6, 14)
    wing_area = clamp(jitter(skel.wing_area), 15, 80)

    # recompute span (DON'T mutate independently)
    wing_span = (aspect_ratio * wing_area) ** 0.5

    # fuselage scales with span
    fuselage_length = clamp(jitter(0.7 * wing_span), 5, 80)

    fineness_ratio = clamp(jitter(fuselage_length / skel.fuselage_diameter), 6, 12)
    fuselage_diameter = fuselage_length / fineness_ratio

    # aero params
    sweep_angle = clamp(jitter(skel.sweep_angle), 0, 45)
    thickness_ratio = clamp(jitter(skel.thickness_ratio), 0.08, 0.18)

    # stability
    tail_volume = clamp(jitter(skel.tail_volume), 0.4, 0.8)

    return AircraftSkeleton(
        wing_span=wing_span,
        aspect_ratio=aspect_ratio,
        wing_area=wing_area,
        fuselage_length=fuselage_length,
        fuselage_diameter=fuselage_diameter,
        sweep_angle=sweep_angle,
        thickness_ratio=thickness_ratio,
        tail_volume=tail_volume,
    )