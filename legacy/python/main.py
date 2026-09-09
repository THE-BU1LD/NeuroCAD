import logging
import time
import hashlib
from typing import Any, Dict, List, Optional

from planner import LLMPlanner
from validator import PlanValidator
from optimizer import Optimizer
from critic import Critic
from geometry import generate_scad

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("CAD-Agent")


class CADAgent:
    """
    Autonomous multi-cycle CAD synthesis agent.

    Pipeline:
        Prompt → Plan → Critique → Optimize/Repair → Validate → Export

    Guarantees:
    - Convergence detection
    - Failure recovery
    - Telemetry + explainability
    - Deterministic exit conditions
    """

    def __init__(
        self,
        cycles: int = 6,
        output_path: str = "output.scad",
        mass_epsilon: float = 1e-3,
        stagnation_cycles: int = 2,
    ):
        self.planner = LLMPlanner()
        self.validator = PlanValidator()
        self.optimizer = Optimizer()
        self.critic = Critic()

        self.cycles = cycles
        self.output_path = output_path
        self.mass_epsilon = mass_epsilon
        self.stagnation_cycles = stagnation_cycles

        self.history: List[Dict[str, Any]] = []

        self.metrics = {
            "mass": [],
            "issues": [],
            "hashes": [],
            "stable_cycles": 0,
        }

    # ==========================================================
    # INTERNAL UTILITIES
    # ==========================================================

    def _compute_mass(self, obj) -> float:
        try:
            from physics import mass
            if hasattr(obj, "parts"):
                return sum(mass(p) for p in obj.parts)
            return mass(obj)
        except Exception:
            return 0.0

    def _structure_hash(self, obj) -> str:
        """
        Geometry fingerprint for stagnation detection.
        """
        try:
            payload = repr(obj).encode("utf-8")
            return hashlib.sha256(payload).hexdigest()
        except Exception:
            return "unknown"

    def _record(self, cycle: int, obj, diagnostics: List[str]):
        mass = self._compute_mass(obj)
        hsh = self._structure_hash(obj)

        self.history.append({
            "timestamp": time.time(),
            "cycle": cycle,
            "mass": mass,
            "issues": diagnostics,
            "hash": hsh,
        })

        self.metrics["mass"].append(mass)
        self.metrics["issues"].append(len(diagnostics))
        self.metrics["hashes"].append(hsh)

        # ---- Stability detection ----
        if len(self.metrics["issues"]) < 2:
            return

        issue_plateau = (
            self.metrics["issues"][-1]
            == self.metrics["issues"][-2]
        )

        mass_delta = abs(
            self.metrics["mass"][-1]
            - self.metrics["mass"][-2]
        )

        geometry_static = (
            self.metrics["hashes"][-1]
            == self.metrics["hashes"][-2]
        )

        if issue_plateau and mass_delta < self.mass_epsilon and geometry_static:
            self.metrics["stable_cycles"] += 1
        else:
            self.metrics["stable_cycles"] = 0

    def _converged(self) -> bool:
        return self.metrics["stable_cycles"] >= self.stagnation_cycles

    # ==========================================================
    # MAIN EXECUTION
    # ==========================================================

    def build(self, prompt: str) -> str:
        """
        Executes full CAD synthesis loop.

        Returns:
            Path to generated SCAD file
        """
        log.info("Prompt: %s", prompt)

        obj = self.planner.plan(prompt)

        for cycle in range(1, self.cycles + 1):
            log.info("===== Cycle %d / %d =====", cycle, self.cycles)

            # ---- Critique ----
            diagnostics = self.critic.critique(obj) or []
            log.info("Issues detected: %d", len(diagnostics))

            # ---- Optimize or Repair ----
            if diagnostics:
                try:
                    obj = self.optimizer.optimize(obj, diagnostics)
                    log.info("Optimizer applied")
                except Exception as e:
                    log.warning("Optimizer failed → planner repair (%s)", e)
                    obj = self.planner.repair(obj, diagnostics[0])

            # ---- Validate ----
            try:
                self.validator.validate(obj)

                scad = generate_scad(obj)
                with open(self.output_path, "w") as f:
                    f.write(scad)

                self._record(cycle, obj, diagnostics)

                if self._converged():
                    log.info("✅ Convergence achieved — terminating early")
                    return self.output_path

            except Exception as e:
                log.warning("Validation error: %s", e)
                self._record(cycle, obj, diagnostics)
                obj = self.planner.repair(obj, str(e))

        raise RuntimeError("❌ Design failed to converge within cycle limit")

    # ==========================================================
    # EXPLAINABILITY
    # ==========================================================

    def explain(self) -> str:
        if not self.history:
            return "No execution history available."

        last = self.history[-1]

        lines = [
            "=== CAD AGENT SUMMARY ===",
            f"Final cycle: {last['cycle']}",
            f"Remaining issues: {len(last['issues'])}",
            f"Final mass: {last['mass']:.4f}",
            f"Stability streak: {self.metrics['stable_cycles']}",
            f"Recent mass trend: {self.metrics['mass'][-3:]}",
        ]

        if last["issues"]:
            lines.append("Outstanding diagnostics:")
            for d in last["issues"]:
                lines.append(f" • {d}")

        return "\n".join(lines)

from schema import CADPart, CADPlan, Assembly, Constraint

__all__ = [
    "CADPart",
    "CADPlan",
    "Assembly",
    "Constraint",
]
