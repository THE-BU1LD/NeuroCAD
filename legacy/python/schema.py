# schema.py
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Tuple
import math

# ==========================================================
# PRIMITIVE NORMALIZATION
# ==========================================================

SEMANTIC_MAP = {
    "nose": "cone",
    "tip": "cone",
}

VALID_PRIMITIVES = {
    "cube",
    "cylinder",
    "sphere",
    "prism",
    "cone",
}

# ==========================================================
# BASE GEOMETRY PLAN
# ==========================================================

@dataclass
class CADPlan:
    """
    Parametric CAD blueprint.
    """
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

    # Orientation (radians)
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    # --------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------

    def normalized_primitive(self) -> str:
        return SEMANTIC_MAP.get(self.primitive, self.primitive)

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    def validate(self):
        prim = self.normalized_primitive()

        if prim not in VALID_PRIMITIVES:
            raise ValueError(f"Unsupported primitive: {self.primitive}")

        if prim == "cube" and self.size is None:
            raise ValueError("Cube requires size")

        if prim in {"sphere", "cylinder", "cone"} and self.radius is None:
            raise ValueError(f"{prim} requires radius")

        if prim in {"cylinder", "cone"} and self.height is None:
            # intelligent default for cones / noses
            self.height = 3 * self.radius

        if prim == "prism" and (self.sides is None or self.height is None):
            raise ValueError("Prism requires sides and height")

        if self.hollow and not self.wall_thickness:
            raise ValueError("Hollow parts require wall_thickness")

    # --------------------------------------------------
    # DERIVED PROPERTIES
    # --------------------------------------------------

    def volume(self) -> float:
        prim = self.normalized_primitive()

        if prim == "cube":
            return self.size ** 3

        if prim == "sphere":
            return (4 / 3) * math.pi * self.radius ** 3

        if prim == "cylinder":
            return math.pi * self.radius ** 2 * self.height

        if prim == "cone":
            return (1 / 3) * math.pi * self.radius ** 2 * self.height

        if prim == "prism":
            base = self.sides * self.radius ** 2 * math.tan(math.pi / self.sides)
            return base * self.height

        return 0.0

    def bounding_box(self) -> Tuple[float, float, float]:
        prim = self.normalized_primitive()

        if prim == "cube":
            return (self.size, self.size, self.size)

        if prim == "sphere":
            d = 2 * self.radius
            return (d, d, d)

        if prim in {"cylinder", "cone"}:
            return (2 * self.radius, 2 * self.radius, self.height)

        return (0, 0, 0)


# ==========================================================
# PART
# ==========================================================

@dataclass
class CADPart(CADPlan):
    name: str = "part"
    density_override: Optional[float] = None
    streamlined: bool = False

    def signature(self) -> Dict:
        return {
            "primitive": self.normalized_primitive(),
            "size": self.size,
            "radius": self.radius,
            "height": self.height,
            "hollow": self.hollow,
            "streamlined": self.streamlined,
        }


# ==========================================================
# CONSTRAINTS
# ==========================================================

@dataclass
class Constraint:
    type: str
    value: Union[float, Tuple]
    weight: float = 1.0
    meta: Dict = field(default_factory=dict)

    def describe(self) -> str:
        return f"{self.type} ≤ {self.value} (w={self.weight})"


# ==========================================================
# ASSEMBLY
# ==========================================================

@dataclass
class Assembly:
    name: str
    parts: List[CADPart]
    constraints: List[Constraint] = field(default_factory=list)

    def total_volume(self) -> float:
        return sum(p.volume() for p in self.parts)

    def bounding_box(self) -> Tuple[float, float, float]:
        xs, ys, zs = [], [], []
        for p in self.parts:
            bx, by, bz = p.bounding_box()
            xs.append(bx)
            ys.append(by)
            zs.append(bz)
        return (max(xs, default=0), max(ys, default=0), max(zs, default=0))

    def feature_vector(self) -> Dict:
        return {
            "num_parts": len(self.parts),
            "total_volume": round(self.total_volume(), 4),
            "streamlined_ratio": sum(p.streamlined for p in self.parts) / max(1, len(self.parts)),
        }

    def validate(self):
        for p in self.parts:
            p.validate()

        for c in self.constraints:
            if c.weight <= 0:
                raise ValueError("Constraint weight must be positive")
        
