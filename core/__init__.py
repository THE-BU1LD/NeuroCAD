"""Core text-to-CAD package.

This package contains the structured prompt parser, graph model,
and OpenSCAD exporter used by the higher level entry points.
"""

from .calibration import (
    AxisObservation,
    CalibrationApplicationPlan,
    CalibrationDataset,
    CalibrationProfile,
    ClearanceObservation,
    HoleObservation,
    apply_calibrated_clearance,
    fit_calibration_profile,
    parse_calibration_dataset,
    parse_calibration_profile,
    plan_calibration_application,
    serialize_calibration_dataset,
    serialize_calibration_profile,
)
from .design_graph import Component, Connection, DesignGraph
from .edit_language import EditInterpretationError, edit_project_from_text
from .enclosure import (
    CutoutSpec,
    EnclosureBuild,
    EnclosureSpec,
    HardwareProfile,
    LidSpec,
    ManufacturingProfile,
    PCBSpec,
    SpecValidationReport,
    StandoffSpec,
    VentPatternSpec,
    build_enclosure,
    validate_enclosure_spec,
)
from .engineering_math import (
    CantileverResult,
    LayoutItem,
    LayoutPlacement,
    OrientationCandidate,
    ScoredOrientation,
    ToleranceContribution,
    ToleranceStack,
    pack_rectangles,
    rectangular_cantilever,
    score_orientations,
    symmetric_positions,
    tolerance_stack,
)
from .geometry import Primitive, box, cone, cylinder, sphere, torus
from .ir import CADProgram, Node, Transform, validate_program
from .ir import Constraint as IRConstraint
from .ir import Primitive as IRPrimitive
from .ir_adapter import design_graph_to_ir
from .ir_export import program_to_scad
from .ir_parser import IRParseError, parse_ir_json, serialize_ir_json
from .manufacturing import PreflightReport, fabrication_preflight
from .natural_language import IntentInterpretation, interpret_enclosure, interpret_provider_payload
from .project import (
    EnclosureProject,
    ProjectFormatError,
    parse_project,
    read_project,
    semantic_diff,
    serialize_project,
    update_project,
    write_project,
)
from .prompt_engine import generate_design
from .scad_export import design_to_scad
from .validation import ValidationReport, validate_design
from .workflow import BuildBundle, build_project_bundle, project_from_text

__all__ = [
    "AxisObservation",
    "BuildBundle",
    "CADProgram",
    "CalibrationApplicationPlan",
    "CalibrationDataset",
    "CalibrationProfile",
    "CantileverResult",
    "ClearanceObservation",
    "Component",
    "Connection",
    "CutoutSpec",
    "DesignGraph",
    "EditInterpretationError",
    "EnclosureBuild",
    "EnclosureProject",
    "EnclosureSpec",
    "HardwareProfile",
    "HoleObservation",
    "IRConstraint",
    "IRParseError",
    "IRPrimitive",
    "IntentInterpretation",
    "LayoutItem",
    "LayoutPlacement",
    "LidSpec",
    "ManufacturingProfile",
    "Node",
    "OrientationCandidate",
    "PCBSpec",
    "PreflightReport",
    "Primitive",
    "ProjectFormatError",
    "ScoredOrientation",
    "SpecValidationReport",
    "StandoffSpec",
    "ToleranceContribution",
    "ToleranceStack",
    "Transform",
    "ValidationReport",
    "VentPatternSpec",
    "apply_calibrated_clearance",
    "box",
    "build_enclosure",
    "build_project_bundle",
    "cone",
    "cylinder",
    "design_graph_to_ir",
    "design_to_scad",
    "edit_project_from_text",
    "fabrication_preflight",
    "fit_calibration_profile",
    "generate_design",
    "interpret_enclosure",
    "interpret_provider_payload",
    "pack_rectangles",
    "parse_calibration_dataset",
    "parse_calibration_profile",
    "parse_ir_json",
    "parse_project",
    "plan_calibration_application",
    "program_to_scad",
    "project_from_text",
    "read_project",
    "rectangular_cantilever",
    "score_orientations",
    "semantic_diff",
    "serialize_calibration_dataset",
    "serialize_calibration_profile",
    "serialize_ir_json",
    "serialize_project",
    "sphere",
    "symmetric_positions",
    "tolerance_stack",
    "torus",
    "update_project",
    "validate_design",
    "validate_enclosure_spec",
    "validate_program",
    "write_project",
]
