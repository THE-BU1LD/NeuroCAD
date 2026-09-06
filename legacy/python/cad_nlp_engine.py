import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ===============================
# Data Structures
# ===============================

@dataclass
class Transform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotate: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])


@dataclass
class ShapeNode:
    type: str
    params: Dict[str, Any]
    transform: Transform = field(default_factory=Transform)
    operation: str = "union"
    children: List[Any] = field(default_factory=list)


@dataclass
class SceneSpec:
    resolution: int = 256
    bounds: float = 1.5
    smooth: float = 0.0
    shapes: List[ShapeNode] = field(default_factory=list)


# ===============================
# NLP Core
# ===============================

class CADNLP:

    def __init__(self):
        self.units_scale = {
            "mm": 0.001,
            "cm": 0.01,
            "m": 1.0,
            "inch": 0.0254,
            "inches": 0.0254,
        }

    # ---------------------------
    # Entry Point
    # ---------------------------

    def parse(self, text: str) -> SceneSpec:
        text = text.lower()
        scene = SceneSpec()

        scene.resolution = self._extract_resolution(text)
        scene.bounds = self._extract_bounds(text)
        scene.smooth = self._extract_smooth(text)

        shape_blocks = self._split_shapes(text)

        for block in shape_blocks:
            shape = self._parse_shape_block(block)
            if shape:
                scene.shapes.append(shape)

        return scene

    # ---------------------------
    # Global Properties
    # ---------------------------

    def _extract_resolution(self, text):
        m = re.search(r"(resolution|res)\s*(\d+)", text)
        if m:
            return min(int(m.group(2)), 512)
        return 256

    def _extract_bounds(self, text):
        m = re.search(r"(size|bounds)\s*(\d+\.?\d*)", text)
        if m:
            return float(m.group(2))
        return 1.5

    def _extract_smooth(self, text):
        m = re.search(r"(smooth|blend)\s*(\d+\.?\d*)", text)
        if m:
            return float(m.group(2))
        return 0.0

    # ---------------------------
    # Shape Parsing
    # ---------------------------

    def _split_shapes(self, text):
        blocks = re.split(r"\b(and|union|subtract|difference)\b", text)
        return [b.strip() for b in blocks if b.strip()]

    def _parse_shape_block(self, text) -> Optional[ShapeNode]:

        primitive = self._detect_primitive(text)
        if not primitive:
            return None

        params = self._extract_parameters(text, primitive)
        transform = self._extract_transform(text)
        operation = self._detect_operation(text)

        return ShapeNode(
            type=primitive,
            params=params,
            transform=transform,
            operation=operation
        )

    # ---------------------------
    # Primitive Detection
    # ---------------------------

    def _detect_primitive(self, text):

        primitives = [
            "sphere",
            "box",
            "cube",
            "cylinder",
            "torus",
            "gyroid",
            "superquadric",
            "fractal"
        ]

        for p in primitives:
            if p in text:
                return p

        return None

    # ---------------------------
    # Parameter Extraction
    # ---------------------------

    def _extract_parameters(self, text, primitive):

        params = {}

        if primitive == "sphere":
            r = self._extract_number(text, "radius", default=0.5)
            params["radius"] = r

        elif primitive in ["box", "cube"]:
            s = self._extract_number(text, "size", default=1.0)
            params["size"] = s

        elif primitive == "cylinder":
            r = self._extract_number(text, "radius", default=0.3)
            h = self._extract_number(text, "height", default=1.0)
            params["radius"] = r
            params["height"] = h

        elif primitive == "torus":
            r = self._extract_number(text, "radius", default=0.5)
            t = self._extract_number(text, "tube", default=0.2)
            params["radius"] = r
            params["tube"] = t

        elif primitive == "gyroid":
            s = self._extract_number(text, "scale", default=6.0)
            params["scale"] = s

        elif primitive == "superquadric":
            e1 = self._extract_number(text, "e1", default=0.3)
            e2 = self._extract_number(text, "e2", default=0.3)
            params["e1"] = e1
            params["e2"] = e2

        elif primitive == "fractal":
            params["strength"] = self._extract_number(text, "strength", default=1.0)

        return params

    # ---------------------------
    # Transform Extraction
    # ---------------------------

    def _extract_transform(self, text):

        t = Transform()

        translate = re.findall(r"translate\s*\(([^)]*)\)", text)
        if translate:
            t.translate = self._parse_vector(translate[0])

        rotate = re.findall(r"rotate\s*\(([^)]*)\)", text)
        if rotate:
            t.rotate = self._parse_vector(rotate[0])

        scale = re.findall(r"scale\s*\(([^)]*)\)", text)
        if scale:
            t.scale = self._parse_vector(scale[0])

        return t

    # ---------------------------
    # Boolean Operation
    # ---------------------------

    def _detect_operation(self, text):

        if "subtract" in text or "difference" in text:
            return "difference"
        if "intersect" in text:
            return "intersection"
        return "union"

    # ---------------------------
    # Helpers
    # ---------------------------

    def _extract_number(self, text, keyword, default=1.0):

        m = re.search(rf"{keyword}\s*(\d+\.?\d*)", text)
        if m:
            return float(m.group(1))
        return default

    def _parse_vector(self, text):
        parts = [float(x.strip()) for x in text.split(",")]
        while len(parts) < 3:
            parts.append(0.0)
        return parts[:3]


# ===============================
# Advanced Program Builder
# ===============================

class CADProgramCompiler:

    def __init__(self, scene: SceneSpec):
        self.scene = scene

    def build_execution_plan(self):

        plan = {
            "resolution": self.scene.resolution,
            "bounds": self.scene.bounds,
            "smooth": self.scene.smooth,
            "operations": []
        }

        for shape in self.scene.shapes:
            plan["operations"].append(self._compile_shape(shape))

        return plan

    def _compile_shape(self, shape: ShapeNode):

        return {
            "type": shape.type,
            "params": shape.params,
            "transform": {
                "translate": shape.transform.translate,
                "rotate": shape.transform.rotate,
                "scale": shape.transform.scale
            },
            "operation": shape.operation
        }
