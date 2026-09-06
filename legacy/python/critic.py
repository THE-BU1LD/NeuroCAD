# critic.py
from typing import List

from aerodynamics import analyze, analyze_assembly
from physics import structural_diagnostics, mass
from engineering import manufacturability_checks


class Critic:
    """
    Physics-aware, manufacturing-aware critic.
    Emits ranked, actionable diagnostics with severity ordering.
    """

    def critique(self, obj) -> List[str]:
        issues: List[str] = []

        parts = obj.parts if hasattr(obj, "parts") else [obj]

        # -------------------------
        # Aerodynamics
        # -------------------------
        aero = (
            analyze_assembly(parts)
            if hasattr(obj, "parts")
            else analyze(obj)
        )

        drag = aero.get("drag_force", aero.get("total_drag", 0.0))
        if drag > 8.0:
            issues.append("[AERO] Critical drag – geometry fundamentally inefficient")
        elif drag > 4.0:
            issues.append("[AERO] High drag – tapering / fillets recommended")

        for d in aero.get("diagnostics", []):
            issues.append(f"[AERO] {d}")

        # -------------------------
        # Structural physics
        # -------------------------
        for s in structural_diagnostics(obj):
            issues.append(f"[STRUCT] {s}")

        # -------------------------
        # Manufacturing
        # -------------------------
        for m in manufacturability_checks(obj):
            issues.append(f"[MFG] {m}")

        # -------------------------
        # Mass sanity
        # -------------------------
        total_mass = sum(mass(p) for p in parts)
        if total_mass > 1200:
            issues.append(
                f"[MASS] Excessive mass ({total_mass:.1f} g) – redesign recommended"
            )

        # -------------------------
        # Severity ordering
        # -------------------------
        priority = {
            "[STRUCT]": 0,
            "[MFG]": 1,
            "[AERO]": 2,
            "[MASS]": 3,
        }

        issues.sort(key=lambda x: priority.get(x[:8], 9))
        return issues