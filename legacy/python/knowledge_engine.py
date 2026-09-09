"""
knowledge_engine.py
Semantic + geometric knowledge system for CAD-Agent

This engine:
- Parses structured prompts
- Stores domain object knowledge
- Expands objects into parts
- Encodes geometry priors
- Returns structured design specifications
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ===============================
# Knowledge Structures
# ===============================

@dataclass
class PartDefinition:
    name: str
    parameters: Dict[str, Any]
    geometry_type: str
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectDefinition:
    name: str
    category: str
    parts: List[PartDefinition]
    default_material: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ===============================
# Core Knowledge Engine
# ===============================

class KnowledgeEngine:

    def __init__(self):
        self.object_library = {}
        self.material_library = {}
        self._build_materials()
        self._build_objects()

    # ---------------------------
    # Materials
    # ---------------------------

    def _build_materials(self):
        self.material_library = {
            "aluminum": {
                "density": 2700,
                "youngs_modulus": 69e9,
                "type": "metal"
            },
            "carbon_fiber": {
                "density": 1600,
                "youngs_modulus": 150e9,
                "type": "composite"
            },
            "rubber": {
                "density": 1100,
                "youngs_modulus": 0.01e9,
                "type": "polymer"
            }
        }

    # ---------------------------
    # Object Templates
    # ---------------------------

    def _build_objects(self):

        # Fighter jet template
        fighter_parts = [
            PartDefinition("fuselage", {"length": 15, "radius": 1.2}, "loft_surface"),
            PartDefinition("main_wing", {"span": 9, "chord": 3}, "airfoil_surface"),
            PartDefinition("vertical_stabilizer", {"height": 2.5}, "swept_surface"),
            PartDefinition("horizontal_stabilizer", {"span": 4}, "airfoil_surface"),
            PartDefinition("engine_intake", {"radius": 0.6}, "circular_loft")
        ]

        self.object_library["fighter_jet"] = ObjectDefinition(
            name="fighter_jet",
            category="aircraft",
            parts=fighter_parts,
            default_material="aluminum"
        )

        # American football template
        football_parts = [
            PartDefinition("body", {"length": 0.28, "max_radius": 0.09}, "prolate_spheroid"),
            PartDefinition("laces", {"count": 8}, "linear_pattern")
        ]

        self.object_library["american_football"] = ObjectDefinition(
            name="american_football",
            category="sports_equipment",
            parts=football_parts,
            default_material="rubber"
        )

    # ---------------------------
    # Prompt Understanding
    # ---------------------------

    def interpret_prompt(self, prompt: str) -> Dict[str, Any]:

        prompt = prompt.lower()

        spec = {
            "object": None,
            "material": None,
            "resolution": 128,
            "performance": {}
        }

        # Identify object
        for key in self.object_library:
            if key.replace("_", " ") in prompt:
                spec["object"] = key

        # Identify material
        for material in self.material_library:
            if material.replace("_", " ") in prompt:
                spec["material"] = material

        # Detect resolution requests
        res_match = re.search(r"(\d+)\s*polygon", prompt)
        if res_match:
            spec["resolution"] = int(res_match.group(1))

        # Detect performance keywords
        if "stealth" in prompt:
            spec["performance"]["stealth"] = True

        if "high speed" in prompt:
            spec["performance"]["speed_priority"] = True

        return spec

    # ---------------------------
    # Expand to Design Blueprint
    # ---------------------------

    def generate_blueprint(self, spec: Dict[str, Any]) -> Dict[str, Any]:

        if spec["object"] not in self.object_library:
            raise ValueError("Unknown object")

        obj = self.object_library[spec["object"]]

        blueprint = {
            "name": obj.name,
            "category": obj.category,
            "material": spec["material"] or obj.default_material,
            "resolution": spec["resolution"],
            "parts": obj.parts,
            "performance": spec["performance"]
        }

        return blueprint
