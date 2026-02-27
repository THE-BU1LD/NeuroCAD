# fatigue.py
import math
from typing import Dict, Any, List

# ==========================================================
# MATERIAL FATIGUE PROPERTIES (heuristic, normalized)
# ==========================================================
# Values are relative endurance factors (higher = better)
# Tuned for early-stage design screening, not certification

FATIGUE_FACTOR = {
    "PLA": 0.35,
    "ABS": 0.55,
    "PETG": 0.45,
    "NYLON": 0.70,
    "ALUMINUM": 0.85,
    "STEEL": 1.00,
}

DEFAULT_FATIGUE = 0.5


# ==========================================================
# FATIGUE DIAGNOSTICS
# ==========================================================

def fatigue_diagnostics(
    part,
    cycles: int = 1_000,
    load_factor: float = 1.0,
) -> Dict[str, Any]:
    """
    Estimates fatigue vulnerability under cyclic loading.

    Parameters
    ----------
    cycles : int
        Expected load cycles (order of magnitude)
    load_factor : float
        Relative cyclic stress multiplier (1.0 = nominal)

    Returns
    -------
    Dict[str, Any]
        fatigue_risk_score : int (0–3)
        notes : List[str]
    """

    risk = 0
    notes: List[str] = []

    # -----------------------
    # Material fatigue strength
    # -----------------------
    material = (part.material or "").upper()
    endurance = FATIGUE_FACTOR.get(material, DEFAULT_FATIGUE)

    if endurance < 0.4:
        risk += 2
        notes.append("Low fatigue endurance material")
    elif endurance < 0.6:
        risk += 1
        notes.append("Moderate fatigue endurance material")

    # -----------------------
    # Stress concentration (geometry-driven)
    # -----------------------
    fillet = getattr(part, "fillet", 0)

    if fillet < 0.25:
        risk += 1
        notes.append("Sharp geometry increases fatigue crack initiation")

    # -----------------------
    # Slenderness amplification
    # -----------------------
    if getattr(part, "height", None) and getattr(part, "radius", None):
        slenderness = part.height / max(part.radius, 1e-6)

        if slenderness > 15:
            risk += 1
            notes.append("Slender geometry amplifies cyclic bending")

    # -----------------------
    # Hollow shell penalty
    # -----------------------
    if getattr(part, "hollow", False):
        risk += 1
        notes.append("Hollow sections accelerate fatigue damage")

    # -----------------------
    # Cycle scaling (logarithmic)
    # -----------------------
    cycle_factor = math.log10(max(cycles, 1))

    if cycle_factor > 6:
        risk += 2
        notes.append("Very high cycle fatigue regime")
    elif cycle_factor > 4:
        risk += 1
        notes.append("High cycle fatigue regime")

    # -----------------------
    # Load amplification
    # -----------------------
    if load_factor > 1.5:
        risk += 1
        notes.append("Elevated cyclic stress amplitude")

    return {
        "fatigue_risk_score": min(3, risk),
        "cycles_estimated": cycles,
        "notes": notes,
    }


# ==========================================================
# ASSEMBLY-LEVEL FATIGUE
# ==========================================================

def assembly_fatigue(assembly, cycles: int = 1_000) -> Dict[str, Any]:
    """
    Aggregates fatigue risk across an assembly.
    """

    max_risk = 0
    fatigue_notes = []

    for p in assembly.parts:
        diag = fatigue_diagnostics(p, cycles=cycles)
        max_risk = max(max_risk, diag["fatigue_risk_score"])
        fatigue_notes.extend(diag["notes"])

    return {
        "max_fatigue_risk": max_risk,
        "unique_fatigue_risks": sorted(set(fatigue_notes)),
        "cycles_estimated": cycles,
    }
