# material_engine.py
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
import math


# ==========================================================
# MATERIAL MODEL
# ==========================================================

@dataclass(frozen=True)
class Material:
    name: str
    density: float            # g/cm^3
    tensile_strength: float   # MPa
    youngs_modulus: float     # GPa
    max_temp: float           # °C
    cost_index: float         # relative (1 = cheap)
    printable: bool = True

    # -------- Derived Properties (physics helpers) --------

    @property
    def density_si(self) -> float:
        """kg/m^3"""
        return self.density * 1000

    @property
    def tensile_strength_si(self) -> float:
        """Pa"""
        return self.tensile_strength * 1e6

    @property
    def stiffness_efficiency(self) -> float:
        """Young's modulus per density"""
        return self.youngs_modulus / max(self.density, 1e-6)

    @property
    def strength_efficiency(self) -> float:
        """Strength-to-weight"""
        return self.tensile_strength / max(self.density, 1e-6)


# ==========================================================
# MATERIAL DATABASE
# ==========================================================

MATERIAL_DB: Dict[str, Material] = {
    "PLA": Material("PLA", 1.24, 60, 3.5, 60, 1.0),
    "ABS": Material("ABS", 1.04, 40, 2.1, 100, 1.2),
    "NYLON": Material("NYLON", 1.15, 75, 2.8, 120, 1.6),
    "PETG": Material("PETG", 1.27, 50, 2.3, 85, 1.3),
    "ALUMINUM": Material("ALUMINUM", 2.70, 310, 69, 660, 3.5, printable=False),
}


# ==========================================================
# MATERIAL ENGINE
# ==========================================================

class MaterialEngine:
    """
    Physics-aware, multi-objective material intelligence.
    Designed for AI-assisted CAD decisions.
    """

    # -------------------------
    # Public API
    # -------------------------

    def select(
        self,
        *,
        target_mass: Optional[float] = None,
        min_strength: Optional[float] = None,
        operating_temp: Optional[float] = None,
        min_stiffness: Optional[float] = None,
        printable_only: bool = True,
    ) -> Tuple[Material, Dict[str, float]]:
        """
        Returns best material AND scoring breakdown.
        """

        scored: List[Tuple[float, Material, Dict]] = []

        for m in MATERIAL_DB.values():
            if printable_only and not m.printable:
                continue
            if min_strength and m.tensile_strength < min_strength:
                continue
            if min_stiffness and m.youngs_modulus < min_stiffness:
                continue
            if operating_temp and m.max_temp < operating_temp:
                continue

            score, breakdown = self._score_material(
                m,
                target_mass,
                min_strength,
                min_stiffness,
                operating_temp,
            )

            scored.append((score, m, breakdown))

        if not scored:
            raise ValueError("No materials satisfy constraints")

        scored.sort(key=lambda x: x[0])
        _, best, breakdown = scored[0]
        return best, breakdown


    def validate(self, material_name: str):
        if material_name not in MATERIAL_DB:
            raise ValueError(f"Unknown material: {material_name}")


    # -------------------------
    # Scoring Logic
    # -------------------------

    def _score_material(
        self,
        m: Material,
        target_mass: Optional[float],
        min_strength: Optional[float],
        min_stiffness: Optional[float],
        operating_temp: Optional[float],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Lower score = better.
        All terms are normalized or bounded.
        """

        # --- Efficiency Metrics ---
        strength_eff = m.strength_efficiency
        stiffness_eff = m.stiffness_efficiency

        # --- Thermal Margin ---
        temp_margin = (
            max(0.0, m.max_temp - operating_temp)
            if operating_temp else m.max_temp
        )
        thermal_score = math.exp(-temp_margin / 100)

        # --- Cost Penalty ---
        cost_penalty = math.log1p(m.cost_index)

        # --- Printability Penalty ---
        print_penalty = 0.0 if m.printable else 3.0

        # --- Constraint Penalties ---
        strength_penalty = 0.0
        if min_strength:
            strength_penalty = max(0, min_strength - m.tensile_strength) / min_strength

        stiffness_penalty = 0.0
        if min_stiffness:
            stiffness_penalty = max(0, min_stiffness - m.youngs_modulus) / min_stiffness

        # --- Mass Heuristic ---
        mass_penalty = m.density if target_mass else 0.0

        # --- Final Score ---
        score = (
            + 0.9 * mass_penalty
            - 0.7 * strength_eff
            - 0.4 * stiffness_eff
            + 1.1 * thermal_score
            + 0.8 * cost_penalty
            + 2.5 * strength_penalty
            + 1.5 * stiffness_penalty
            + print_penalty
        )

        breakdown = {
            "density_gcm3": m.density,
            "strength_efficiency": round(strength_eff, 3),
            "stiffness_efficiency": round(stiffness_eff, 3),
            "thermal_margin_C": round(temp_margin, 1),
            "thermal_penalty": round(thermal_score, 3),
            "cost_penalty": round(cost_penalty, 3),
            "print_penalty": print_penalty,
            "strength_penalty": round(strength_penalty, 3),
            "stiffness_penalty": round(stiffness_penalty, 3),
            "final_score": round(score, 3),
        }

        return score, breakdown
