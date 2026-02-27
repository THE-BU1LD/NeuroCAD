"""
geometry.py

Topology-aware Geometry Engine for NeuroCAD
-------------------------------------------

Key upgrades:
- Structured geometry graph (not string soup)
- Bounding-box propagation
- Topology classification (solid / shell / rib / aero)
- Mesh-safe boolean & offset handling
- Deterministic OpenSCAD compilation
- Future-ready for meshing / FEM / CFD
"""

import math
from typing import List, Iterable, Optional, Tuple

# ==========================================================
# CONSTANTS
# ==========================================================

EPS = 1e-4
FN = 128

# ==========================================================
# NUMERIC SAFETY
# ==========================================================

def pos(x: float, default=1.0) -> float:
    try:
        return max(float(x), EPS)
    except Exception:
        return default


def clamp(x: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(float(x), hi))
    except Exception:
        return lo


# ==========================================================
# BOUNDING BOX
# ==========================================================

class BBox:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            min(self.xmin, other.xmin),
            max(self.xmax, other.xmax),
            min(self.ymin, other.ymin),
            max(self.ymax, other.ymax),
            min(self.zmin, other.zmin),
            max(self.zmax, other.zmax),
        )

    def expand(self, d: float) -> "BBox":
        return BBox(
            self.xmin - d, self.xmax + d,
            self.ymin - d, self.ymax + d,
            self.zmin - d, self.zmax + d,
        )


# ==========================================================
# GEOMETRY NODE (CORE)
# ==========================================================

class GeoNode:
    """
    Internal geometry representation.
    Think: lightweight CAD kernel node.
    """

    def __init__(
        self,
        scad: str,
        bbox: BBox,
        kind: str = "solid",   # solid | shell | rib | aero | cut
        children: Optional[List["GeoNode"]] = None
    ):
        self.scad = scad
        self.bbox = bbox
        self.kind = kind
        self.children = children or []

    def union(self, other: "GeoNode") -> "GeoNode":
        return GeoNode(
            f"union() {{\n{indent(self.scad)}\n{indent(other.scad)}\n}}",
            self.bbox.union(other.bbox),
            kind="solid",
            children=[self, other]
        )

    def difference(self, other: "GeoNode") -> "GeoNode":
        return GeoNode(
            f"difference() {{\n{indent(self.scad)}\n{indent(other.scad)}\n}}",
            self.bbox,
            kind=self.kind,
            children=[self, other]
        )


# ==========================================================
# PRIMITIVES (TOPOLOGY-AWARE)
# ==========================================================

def cube(size: float) -> GeoNode:
    s = pos(size)
    h = s / 2
    return GeoNode(
        f"cube({s}, center=true);",
        BBox(-h, h, -h, h, -h, h),
        kind="solid"
    )


def cylinder(radius: float, height: float) -> GeoNode:
    r = pos(radius)
    h = pos(height) / 2
    return GeoNode(
        f"cylinder(r={r}, h={2*h}, center=true);",
        BBox(-r, r, -r, r, -h, h),
        kind="solid"
    )


# ==========================================================
# SHELLING (MESH SAFE)
# ==========================================================

def shell(node: GeoNode, thickness: float) -> GeoNode:
    t = pos(thickness)
    safe_bbox = node.bbox.expand(-t)

    if safe_bbox.xmax <= safe_bbox.xmin:
        return node  # refuse unsafe shell

    scad = f"""
difference() {{
{indent(node.scad)}
  offset(delta=-{t}) {{
{indent(node.scad, 4)}
  }}
}}
"""
    return GeoNode(scad, node.bbox, kind="shell", children=[node])


# ==========================================================
# AERODYNAMIC ENVELOPE
# ==========================================================

def aero_envelope(node: GeoNode, taper: float = 0.2) -> GeoNode:
    taper = clamp(taper, 0.0, 0.9)
    bb = node.bbox

    r = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin) / 2
    h = bb.zmax - bb.zmin

    r2 = max(r * (1 - taper), EPS)

    scad = f"""
union() {{
{indent(node.scad)}
  cylinder(h={h}, r1={r}, r2={r2}, center=true);
}}
"""
    return GeoNode(scad, bb, kind="aero", children=[node])


# ==========================================================
# RIB GENERATION (STRUCTURAL)
# ==========================================================

def ribs(node: GeoNode, count: int) -> GeoNode:
    count = max(int(count), 1)
    bb = node.bbox
    dz = (bb.zmax - bb.zmin) / (count + 1)

    rib_scad = ""
    for i in range(count):
        z = bb.zmin + (i + 1) * dz
        rib_scad += f"""
translate([0,0,{z}])
rotate_extrude()
translate([{(bb.xmax - bb.xmin)*0.45},0,0])
circle(r={(bb.xmax - bb.xmin)*0.03});
"""

    scad = f"""
union() {{
{indent(node.scad)}
{indent(rib_scad)}
}}
"""
    return GeoNode(scad, bb, kind="rib", children=[node])


# ==========================================================
# TRANSFORMS
# ==========================================================

def transform(node: GeoNode, x=0, y=0, z=0, rx=0, ry=0, rz=0) -> GeoNode:
    scad = f"""
translate([{x},{y},{z}])
rotate([{rx},{ry},{rz}]) {{
{indent(node.scad)}
}}
"""
    bb = BBox(
        node.bbox.xmin + x, node.bbox.xmax + x,
        node.bbox.ymin + y, node.bbox.ymax + y,
        node.bbox.zmin + z, node.bbox.zmax + z,
    )
    return GeoNode(scad, bb, node.kind, [node])


# ==========================================================
# ASSEMBLY
# ==========================================================

def assemble(nodes: Iterable[GeoNode]) -> GeoNode:
    nodes = list(nodes)
    scad = "union() {\n"
    bb = nodes[0].bbox
    for n in nodes:
        scad += indent(n.scad) + "\n"
        bb = bb.union(n.bbox)
    scad += "}"
    return GeoNode(scad, bb, kind="solid", children=nodes)


# ==========================================================
# EXPORT
# ==========================================================

def generate_scad(node: GeoNode) -> str:
    return f"""// =====================================
// NeuroCAD Geometry Output
// Topology-aware engine
// =====================================
$fn = {FN};

{node.scad}
"""


# ==========================================================
# UTIL
# ==========================================================

def indent(txt: str, n: int = 2) -> str:
    pad = " " * n
    return "\n".join(pad + l if l.strip() else l for l in txt.splitlines())
