"""Core text-to-CAD package.

This package contains the structured prompt parser, graph model,
and OpenSCAD exporter used by the higher level entry points.
"""

from .design_graph import Component, Connection, DesignGraph
from .geometry import Primitive, box, cylinder, sphere, cone, torus
from .prompt_engine import generate_design
from .scad_export import design_to_scad

__all__ = [
    "Component",
    "Connection",
    "DesignGraph",
    "Primitive",
    "box",
    "cylinder",
    "sphere",
    "cone",
    "torus",
    "generate_design",
    "design_to_scad",
]
