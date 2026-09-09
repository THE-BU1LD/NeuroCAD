# connectors.py
import math
from typing import List, Dict, Tuple, Optional


class Joint:
    """
    General-purpose mechanical joint abstraction.
    Works for any mechanical design (vehicles, engines, robotics, structures).
    """

    _id_counter = 0

    def __init__(
        self,
        type_: str,
        part_a,
        part_b,
        position: Tuple[float, float, float],
        axis: Optional[Tuple[float, float, float]] = None,
        limits: Optional[Tuple[float, float]] = None,
        stiffness: float = 1.0,
        damping: float = 0.1,
        max_load: float = 100.0,
        fatigue_limit: float = 1e6,
        dof: Optional[Dict[str, float]] = None,
    ):
        self.id = Joint._id_counter
        Joint._id_counter += 1

        self.type = type_.lower()
        self.part_a = part_a
        self.part_b = part_b
        self.position = position
        self.axis = self._normalize(axis) if axis else None
        self.limits = limits
        self.stiffness = stiffness
        self.damping = damping
        self.max_load = max_load
        self.fatigue_limit = fatigue_limit

        # Generic degrees of freedom (translation_x, rotation_z, etc.)
        self.dof = dof or self._default_dof()

        self._validate()

    # ======================================================
    # CORE IDENTITY
    # ======================================================

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, Joint) and self.id == other.id

    # ======================================================
    # VALIDATION
    # ======================================================

    def _validate(self):
        if self.stiffness <= 0:
            raise ValueError("Joint stiffness must be > 0")

        if self.max_load <= 0:
            raise ValueError("Joint max_load must be > 0")

        if self.damping < 0:
            raise ValueError("Joint damping must be ≥ 0")

        if self.limits:
            lo, hi = self.limits
            if lo >= hi:
                raise ValueError("Invalid joint limits")

    # ======================================================
    # UTIL
    # ======================================================

    @staticmethod
    def _normalize(v):
        mag = math.sqrt(sum(x * x for x in v))
        if mag < 1e-9:
            raise ValueError("Zero-length axis vector")
        return tuple(x / mag for x in v)

    def _default_dof(self):
        if self.type == "fixed":
            return {}
        if self.type == "revolute":
            return {"rotation": 1.0}
        if self.type == "ball":
            return {"rotation_x": 1.0, "rotation_y": 1.0, "rotation_z": 1.0}
        return {"translation": 1.0, "rotation": 1.0}

    # ======================================================
    # MECHANICS
    # ======================================================

    def allowed_motion(self) -> Dict[str, float]:
        motion = {}
        for k, v in self.dof.items():
            if "rotation" in k:
                lo, hi = self.limits or (-180, 180)
                motion[k] = (hi - lo) * v
            else:
                motion[k] = v
        return motion

    def load_ratio(self, applied_load: float) -> float:
        return applied_load / self.max_load

    def elastic_energy(self, displacement: float) -> float:
        """
        ½ k x²
        """
        return 0.5 * self.stiffness * displacement ** 2

    def damping_loss(self, velocity: float) -> float:
        """
        c v²
        """
        return self.damping * velocity ** 2

    def fatigue_damage(self, cycles: float, applied_load: float) -> float:
        stress_ratio = applied_load / self.max_load
        return (cycles / self.fatigue_limit) * stress_ratio ** 2

    # ======================================================
    # RISK MODEL
    # ======================================================

    def risk_score(
        self,
        applied_load: float,
        displacement: float = 0.0,
        velocity: float = 0.0,
        cycles: float = 0.0,
    ) -> float:
        overload = max(0.0, self.load_ratio(applied_load) - 1.0)
        fatigue = self.fatigue_damage(cycles, applied_load)

        energy = self.elastic_energy(displacement)
        damping = self.damping_loss(velocity)

        return (
            0.45 * overload ** 2
            + 0.25 * fatigue
            + 0.2 * energy
            + 0.1 * damping
        )

    # ======================================================
    # DESCRIPTION
    # ======================================================

    def describe(self):
        return (
            f"Joint<{self.type}> "
            f"{self.part_a.name} ↔ {self.part_b.name} | "
            f"k={self.stiffness:.2f}, c={self.damping:.2f}, "
            f"max_load={self.max_load}"
        )


# ==========================================================
# SYSTEM DIAGNOSTICS
# ==========================================================

def joint_diagnostics(
    joints: List[Joint],
    loads: Dict[Joint, float],
    cycles: Dict[Joint, float] = None,
):
    cycles = cycles or {}
    issues = []

    for j in joints:
        load = loads.get(j, 0.0)
        c = cycles.get(j, 0.0)

        if j.load_ratio(load) > 1.25:
            issues.append(f"[JOINT] Critical overload in {j.describe()}")

        if j.fatigue_damage(c, load) > 1.0:
            issues.append(f"[JOINT] Fatigue failure risk in {j.describe()}")

        if j.stiffness < 0.3:
            issues.append(f"[JOINT] Excessive compliance in {j.describe()}")

    return issues
