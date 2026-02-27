# cadify.py (or main.py)

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Tuple
import math

# ==========================================================
# CAD PLAN
# ==========================================================

@dataclass
class CADPlan:
    primitive: str
    material: str = "PLA"

    # Geometry
    size: Optional[float] = None
    radius: Optional[float] = None
    height: Optional[float] = None
    sides: Optional[int] = None
    fillet: float = 0.0
    hollow: bool = False
    wall_thickness: Optional[float] = None

    # Spatial
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Orientation
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    # -------------------------
    # VALIDATION
    # -------------------------

    def validate(self):
        if self.primitive not in {"cube", "sphere", "cylinder", "prism"}:
            raise ValueError(f"Unsupported primitive: {self.primitive}")

        if self.primitive == "cube" and self.size is None:
            raise ValueError("Cube requires size")

        if self.primitive == "sphere" and self.radius is None:
            raise ValueError("Sphere requires radius")

        if self.primitive == "cylinder":
            if self.radius is None:
                raise ValueError("Cylinder requires radius")
            if self.height is None:
                raise ValueError("Cylinder requires height")

        if self.hollow and not self.wall_thickness:
            raise ValueError("Hollow parts require wall_thickness")

    # -------------------------
    # GEOMETRY
    # -------------------------

    def volume(self) -> float:
        if self.primitive == "cube":
            return self.size ** 3

        if self.primitive == "sphere":
            return (4 / 3) * math.pi * self.radius ** 3

        if self.primitive == "cylinder":
            return math.pi * self.radius ** 2 * self.height

        return 0.0

    def bounding_box(self) -> Tuple[float, float, float]:
        if self.primitive == "cube":
            return (self.size, self.size, self.size)

        if self.primitive == "sphere":
            d = 2 * self.radius
            return (d, d, d)

        if self.primitive == "cylinder":
            return (2 * self.radius, 2 * self.radius, self.height)

        return (0.0, 0.0, 0.0)


# ==========================================================
# PART
# ==========================================================

@dataclass
class CADPart(CADPlan):
    name: str = "part"
    density_override: Optional[float] = None
    streamlined: bool = False

    def signature(self) -> Dict[str, Union[str, float, bool]]:
        """
        ML / optimizer-friendly fingerprint.
        """
        return {
            "primitive": self.primitive,
            "size": self.size,
            "radius": self.radius,
            "height": self.height,
            "hollow": self.hollow,
            "streamlined": self.streamlined,
        }


# ==========================================================
# CONSTRAINT
# ==========================================================

@dataclass
class Constraint:
    type: str
    value: Union[float, str, Tuple]
    weight: float = 1.0
    meta: Dict = field(default_factory=dict)


# ==========================================================
# ASSEMBLY
# ==========================================================

@dataclass
class Assembly:
    name: str
    parts: List[CADPart]
    constraints: List[Constraint] = field(default_factory=list)

    # -------------------------
    # VALIDATION
    # -------------------------

    def validate(self):
        for p in self.parts:
            p.validate()

        for c in self.constraints:
            if c.weight <= 0:
                raise ValueError("Constraint weight must be positive")

    # -------------------------
    # METRICS
    # -------------------------

    def total_volume(self) -> float:
        return sum(p.volume() for p in self.parts)

    def bounding_box(self) -> Tuple[float, float, float]:
        xs, ys, zs = [], [], []
        for p in self.parts:
            bx, by, bz = p.bounding_box()
            xs.append(bx)
            ys.append(by)
            zs.append(bz)

        return (
            max(xs, default=0.0),
            max(ys, default=0.0),
            max(zs, default=0.0),
        )

    def feature_vector(self) -> Dict[str, float]:
        return {
            "num_parts": len(self.parts),
            "total_volume": self.total_volume(),
            "streamlined_ratio": sum(p.streamlined for p in self.parts)
            / max(1, len(self.parts)),
        }
