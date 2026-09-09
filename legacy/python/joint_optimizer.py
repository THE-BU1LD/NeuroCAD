# joint_optimizer.py
import random
import math
from typing import List, Dict
from connector import Joint


class JointOptimizer:
    """
    Constraint-aware joint optimizer.
    Generic across ALL CAD systems (not plane-specific).
    """

    def __init__(
        self,
        joints: List[Joint],
        loads: Dict[Joint, float],
        cycles: Dict[Joint, float] | None = None,
    ):
        self.joints = joints
        self.loads = loads
        self.cycles = cycles or {}

    # ======================================================
    # OBJECTIVE
    # ======================================================

    def total_risk(self) -> float:
        total = 0.0
        for j in self.joints:
            total += j.risk_score(
                applied_load=self.loads.get(j, 0.0),
                cycles=self.cycles.get(j, 0.0),
            )
        return total

    # ======================================================
    # OPTIMIZATION (SIMULATED ANNEALING)
    # ======================================================

    def optimize(
        self,
        steps: int = 300,
        lr: float = 0.15,
        temperature: float = 1.0,
        verbose: bool = True,
    ):
        best_risk = self.total_risk()
        current_risk = best_risk

        for step in range(steps):
            j = random.choice(self.joints)

            load = abs(self.loads.get(j, 1.0))
            scale = 1 + math.log1p(load)

            old_k, old_c = j.stiffness, j.damping

            # Coupled mutation (physics-aware)
            j.stiffness *= 1 + random.uniform(-lr, lr) * scale
            j.damping += random.uniform(-lr, lr) * 0.5

            # Clamp
            j.stiffness = max(0.05, min(j.stiffness, 10.0))
            j.damping = max(0.0, min(j.damping, 5.0))

            new_risk = self.total_risk()
            delta = new_risk - current_risk

            accept = (
                delta < 0
                or random.random()
                < math.exp(-delta / max(temperature, 1e-6))
            )

            if accept:
                current_risk = new_risk
                best_risk = min(best_risk, new_risk)
            else:
                j.stiffness, j.damping = old_k, old_c

            temperature *= 0.995  # anneal

            if verbose and step % 25 == 0:
                print(
                    f"[OPT] step={step:03d} "
                    f"risk={current_risk:.4f} "
                    f"T={temperature:.3f}"
                )

        return best_risk

    # ======================================================
    # REPORT
    # ======================================================

    def summary(self):
        out = []
        for j in self.joints:
            out.append(
                {
                    "joint": j.describe(),
                    "stiffness": round(j.stiffness, 4),
                    "damping": round(j.damping, 4),
                    "risk": round(
                        j.risk_score(
                            self.loads.get(j, 0.0),
                            cycles=self.cycles.get(j, 0.0),
                        ),
                        5,
                    ),
                }
            )
        return out
