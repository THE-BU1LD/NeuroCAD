from typing import Union, List
from schema import CADPlan, CADPart, Assembly, Constraint
from physics import mass, structural_diagnostics


class ValidationError(ValueError):
    def __init__(self, message: str, code: str = "GENERIC"):
        super().__init__(message)
        self.code = code


class PlanValidator:
    """
    Physics-aware, assembly-aware validator.
    Designed for autonomous agents.
    """

    def validate(self, obj: Union[CADPlan, Assembly]):
        if isinstance(obj, Assembly):
            self._validate_assembly(obj)
        elif isinstance(obj, CADPlan):
            self._validate_part(obj)
        else:
            raise TypeError("Unsupported CAD object")

    # --------------------------------------------------
    # PART VALIDATION
    # --------------------------------------------------

    def _validate_part(self, p: CADPlan):
        prim = p.primitive.lower()

        if prim == "cube":
            self._require(p.size, "Cube requires size")
            self._positive(p.size, "Cube size must be positive")

        elif prim == "cylinder":
            self._require(p.radius, "Cylinder requires radius")
            self._require(p.height, "Cylinder requires height")
            self._positive(p.radius, "Cylinder radius must be positive")
            self._positive(p.height, "Cylinder height must be positive")

        elif prim == "prism":
            self._require(p.sides, "Prism requires sides")
            if p.sides < 3:
                raise ValidationError("Prism needs ≥ 3 sides", "GEOM")
            self._require(p.radius, "Prism requires radius")
            self._require(p.height, "Prism requires height")

        else:
            raise ValidationError(f"Unknown primitive: {p.primitive}", "GEOM")

        # Fillet sanity
        if p.fillet:
            dims = [v for v in (p.size, p.radius, p.height) if v]
            if dims and p.fillet >= min(dims) / 2:
                raise ValidationError("Fillet radius too large", "GEOM")

        # Structural physics
        for issue in structural_diagnostics(p):
            raise ValidationError(issue, "STRUCT")

    # --------------------------------------------------
    # ASSEMBLY VALIDATION
    # --------------------------------------------------

    def _validate_assembly(self, assembly: Assembly):
        total_mass = 0.0

        for part in assembly.parts:
            self._validate_part(part)
            total_mass += mass(part)

        for c in assembly.constraints:
            self._check_constraint(c, total_mass)

    # --------------------------------------------------
    # CONSTRAINTS
    # --------------------------------------------------

    def _check_constraint(self, c: Constraint, total_mass: float):
        if c.type == "max_mass":
            if total_mass > c.value:
                raise ValidationError(
                    f"Mass exceeded: {total_mass:.2f}g > {c.value}",
                    "MASS"
                )

        elif c.type == "min_mass":
            if total_mass < c.value:
                raise ValidationError(
                    f"Mass below minimum: {total_mass:.2f}g < {c.value}",
                    "MASS"
                )

        else:
            raise ValidationError(f"Unknown constraint: {c.type}", "CONSTRAINT")

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _require(self, v, msg: str):
        if v is None:
            raise ValidationError(msg, "GEOM")

    def _positive(self, v: float, msg: str):
        if v <= 0:
            raise ValidationError(msg, "GEOM")
try:
    from physics import mass, structural_diagnostics
except ImportError as e:
    raise RuntimeError("Physics engine missing required functions") from e
