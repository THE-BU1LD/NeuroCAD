"""Experimental build123d exact-CAD compiler for Feature IR.

This module is optional. Importing core.exact_build123d does not import
build123d; the heavy dependency is loaded only when Build123dBackend is created.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from .feature_ir import (
    EntitySelector,
    Feature,
    FeatureProgram,
    resolve_feature_parameters,
    serialize_feature_ir_json,
    validate_feature_program,
)
from .json_io import strict_json_loads
from .requirement_ir import RequirementIR, serialize_requirement_ir_json
from .requirement_verification import (
    RequirementBindingSet,
    binding_set_sha256,
    requirement_ir_sha256,
    serialize_binding_set_json,
    verify_exact_requirements,
    verify_unchanged_must_requirements,
)

BUILD_RECEIPT_VERSION = "neurocad-build123d-receipt-v1"
REVISION_PILOT_AXIS = "z"
REVISION_PILOT_SIDE = "min"
REVISION_PILOT_EDITED_REQUIREMENT_IDS = ("wall_thickness",)
REVISION_PILOT_LINEAR_TOLERANCE_MM = 1e-6
REVISION_PILOT_RELATIVE_SCALAR_TOLERANCE = 1e-9
REVISION_PILOT_ABSOLUTE_SCALAR_FLOOR = 1e-12
SUPPORTED_FEATURES = frozenset(
    {
        "primitive_box",
        "primitive_cylinder",
        "sketch",
        "extrude",
        "revolve",
        "boolean_union",
        "boolean_cut",
        "boolean_intersect",
        "fillet",
        "chamfer",
        "linear_pattern",
        "circular_pattern",
        "mirror",
    }
)


@dataclass(frozen=True)
class GeometryInspection:
    valid_brep: bool
    manifold: bool
    solid_count: int
    volume_mm3: float
    extents_mm: tuple[float, float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid_brep": self.valid_brep,
            "manifold": self.manifold,
            "solid_count": self.solid_count,
            "volume_mm3": self.volume_mm3,
            "extents_mm": list(self.extents_mm),
        }


@dataclass(frozen=True)
class AnalyticEdgeSignature:
    geom_type: str
    length_mm: float
    bbox_min_mm: tuple[float, float, float]
    bbox_max_mm: tuple[float, float, float]
    endpoints_mm: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class AnalyticWireSignature:
    length_mm: float
    bbox_min_mm: tuple[float, float, float]
    bbox_max_mm: tuple[float, float, float]
    edges: tuple[AnalyticEdgeSignature, ...]


@dataclass(frozen=True)
class PlanarRevisionEvidence:
    backend: str
    backend_version: str
    baseline_feature_ir_sha256: str
    candidate_feature_ir_sha256: str
    axis: str
    side: str
    linear_tolerance_mm: float
    relative_scalar_tolerance: float
    absolute_scalar_floor: float
    baseline_inspection: GeometryInspection
    candidate_inspection: GeometryInspection
    baseline_face_area_mm2: float
    candidate_face_area_mm2: float
    baseline_wall_thickness_mm: float
    candidate_wall_thickness_mm: float
    external_boundary_equivalent: bool
    external_extents_equivalent: bool
    max_external_extent_delta_mm: float
    cutout_count_baseline: int
    cutout_count_candidate: int
    cutouts_equivalent: bool
    max_sampled_external_deviation_mm: float
    max_sampled_cutout_deviation_mm: float
    baseline_self_intersection_free: bool
    candidate_self_intersection_free: bool
    candidate_minimum_material_clearance_mm: float
    candidate_zero_thickness_free: bool
    passed: bool
    claim_boundary: str = (
        "bounded analytic planar-boundary comparison for LINE/CIRCLE edges only; "
        "not arbitrary-surface CAD equivalence or a manufacturing/safety certification"
    )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["baseline_inspection"] = self.baseline_inspection.to_dict()
        value["candidate_inspection"] = self.candidate_inspection.to_dict()
        value["revision_evidence_version"] = "neurocad-planar-revision-evidence-v1"
        return value


@dataclass(frozen=True)
class RevisionBundleReceipt:
    backend: str
    backend_version: str
    baseline_feature_ir_sha256: str
    candidate_feature_ir_sha256: str
    baseline_step_sha256: str
    baseline_build_receipt_sha256: str
    baseline_requirements_sha256: str
    baseline_bindings_sha256: str
    baseline_requirements_verification_sha256: str
    candidate_step_sha256: str
    candidate_build_receipt_sha256: str
    candidate_requirements_sha256: str
    candidate_bindings_sha256: str
    candidate_requirements_verification_sha256: str
    edited_requirement_ids: tuple[str, ...]
    evidence: PlanarRevisionEvidence
    unchanged_requirements_guard_passed: bool
    claim_boundary: str = (
        "transactional publication evidence for one bounded planar revision invariant; "
        "not proof of arbitrary CAD equivalence, manufacturability, physical fit, or safety"
    )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["edited_requirement_ids"] = list(self.edited_requirement_ids)
        value["evidence"] = self.evidence.to_dict()
        value["revision_bundle_receipt_version"] = "neurocad-revision-bundle-receipt-v1"
        return value


@dataclass(frozen=True)
class Build123dReceipt:
    backend: str
    backend_version: str
    feature_ir_sha256: str
    output_feature: str
    inspection: GeometryInspection
    step_path: str | None = None
    step_sha256: str | None = None
    roundtrip_inspection: GeometryInspection | None = None
    requirements_path: str | None = None
    requirements_sha256: str | None = None
    bindings_path: str | None = None
    bindings_sha256: str | None = None
    requirements_verification_path: str | None = None
    requirements_verification_sha256: str | None = None
    requirements_satisfied: bool | None = None
    claim_boundary: str = (
        "exact-kernel build and geometric checks only; not structural, manufacturing, "
        "regulatory, or physical-fit certification"
    )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["inspection"] = self.inspection.to_dict()
        value["roundtrip_inspection"] = (
            None if self.roundtrip_inspection is None else self.roundtrip_inspection.to_dict()
        )
        value["receipt_version"] = BUILD_RECEIPT_VERSION
        return value


class Build123dCompileError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _program_sha256(program: FeatureProgram) -> str:
    payload = serialize_feature_ir_json(program, pretty=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_step_filename(filename: str) -> str:
    """Accept a portable STEP basename, never a path or receipt filename."""
    if not isinstance(filename, str) or re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._ -]*\.(?:step|stp)", filename, flags=re.IGNORECASE | re.ASCII
    ) is None:
        raise Build123dCompileError(
            "filename must be a plain ASCII .step/.stp basename starting with a letter or digit; "
            "only letters, digits, spaces, dots, underscores and hyphens are allowed"
        )
    stem = filename.split(".", 1)[0].rstrip(" ").upper()
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))
    if stem in reserved:
        raise Build123dCompileError("filename cannot use a reserved device basename")
    return filename


class Build123dBackend:
    def __init__(self) -> None:
        try:
            self.bd = importlib.import_module("build123d")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "build123d is not installed; install the exact-build123d optional dependency"
            ) from exc
        try:
            self.version = metadata.version("build123d")
        except metadata.PackageNotFoundError:
            self.version = "unknown"

    def _plane(self, name: str) -> Any:
        planes = {"XY": self.bd.Plane.XY, "XZ": self.bd.Plane.XZ, "YZ": self.bd.Plane.YZ}
        try:
            return planes[name.upper()]
        except (AttributeError, KeyError) as exc:
            raise Build123dCompileError(f"unsupported sketch plane {name!r}; use XY, XZ, or YZ") from exc

    def _build_sketch(self, feature: Feature) -> Any:
        raw_entities = feature.parameters.get("entities")
        if not isinstance(raw_entities, list) or not raw_entities:
            raise Build123dCompileError(f"sketch {feature.id!r} requires at least one entity")
        result: Any | None = None
        for index, raw in enumerate(raw_entities):
            if not isinstance(raw, dict):
                raise Build123dCompileError(f"sketch {feature.id!r} entity {index} must be an object")
            kind = raw.get("kind")
            operation = raw.get("operation", "add")
            center = raw.get("center", [0.0, 0.0])
            if (
                not isinstance(center, list)
                or len(center) != 2
                or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in center)
            ):
                raise Build123dCompileError(f"sketch {feature.id!r} entity {index} center must have two numbers")
            if operation not in {"add", "subtract", "intersect"}:
                raise Build123dCompileError(
                    f"sketch {feature.id!r} entity {index} operation must be add/subtract/intersect"
                )
            if kind == "rectangle":
                width, height = raw.get("width"), raw.get("height")
                if not _positive(width) or not _positive(height):
                    raise Build123dCompileError(
                        f"sketch {feature.id!r} rectangle {index} requires positive width and height"
                    )
                width_value = _as_positive_float(width, "rectangle width")
                height_value = _as_positive_float(height, "rectangle height")
                item = self.bd.Rectangle(width_value, height_value)
            elif kind == "circle":
                radius = raw.get("radius")
                if not _positive(radius):
                    raise Build123dCompileError(f"sketch {feature.id!r} circle {index} requires positive radius")
                radius_value = _as_positive_float(radius, "circle radius")
                item = self.bd.Circle(radius_value)
            else:
                raise Build123dCompileError(
                    f"sketch {feature.id!r} entity {index} uses unsupported kind {kind!r}"
                )
            if float(center[0]) != 0.0 or float(center[1]) != 0.0:
                item = self.bd.Pos(float(center[0]), float(center[1])) * item
            if result is None:
                if operation != "add":
                    raise Build123dCompileError(
                        f"sketch {feature.id!r} must begin with an additive entity"
                    )
                result = item
            elif operation == "add":
                result = result + item
            elif operation == "subtract":
                result = result - item
            else:
                result = result & item
        if result is None:
            raise Build123dCompileError(f"sketch {feature.id!r} produced no profile")
        plane = self._plane(str(feature.parameters.get("plane", "XY")))
        if plane != self.bd.Plane.XY:
            result = plane * result
        return result

    def _selector_edges(self, shape: Any, selectors: tuple[EntitySelector, ...]) -> list[Any]:
        resolved: list[Any] = []
        for selector in selectors:
            if selector.entity != "edge":
                raise Build123dCompileError("build123d fillet/chamfer currently supports edge selectors only")
            candidates = shape.edges()
            for predicate in selector.predicates:
                kind = predicate.get("kind")
                if kind == "parallel_to":
                    axis = predicate.get("axis")
                    if not _vec3(axis):
                        raise Build123dCompileError("parallel_to selector requires a finite 3-vector axis")
                    axis_values = _as_vec3(axis, "parallel_to axis")
                    candidates = candidates.filter_by(
                        self.bd.Axis((0.0, 0.0, 0.0), axis_values)
                    )
                else:
                    raise Build123dCompileError(f"unsupported build123d selector predicate {kind!r}")
            items = list(candidates)
            if selector.unique and len(items) != 1:
                raise Build123dCompileError(
                    f"selector for {selector.generated_by!r} resolved to {len(items)} edges; exactly one required"
                )
            if not items:
                raise Build123dCompileError(
                    f"selector for {selector.generated_by!r} resolved to no edges"
                )
            resolved.extend(items)
        unique: dict[int, Any] = {}
        for edge in resolved:
            unique[id(edge)] = edge
        return list(unique.values())

    def _linear_pattern(self, source: Any, feature: Feature) -> Any:
        count = feature.parameters["count"]
        spacing = float(feature.parameters["spacing"])
        direction = _as_vec3(feature.parameters["direction"], "linear pattern direction")
        norm = math.sqrt(sum(item * item for item in direction))
        if norm == 0:
            raise Build123dCompileError("linear pattern direction cannot be zero")
        unit = tuple(item / norm for item in direction)
        copies = [
            self.bd.Pos(*(unit[axis] * spacing * index for axis in range(3))) * source
            for index in range(int(count))
        ]
        return self.bd.Compound(children=copies)

    def _circular_pattern(self, source: Any, feature: Feature) -> Any:
        count = int(feature.parameters["count"])
        total_angle = float(feature.parameters["angle_deg"])
        axis = _as_vec3(feature.parameters["axis"], "circular pattern axis")
        rounded: tuple[float, float, float] = (
            round(axis[0], 12),
            round(axis[1], 12),
            round(axis[2], 12),
        )
        allowed = {
            (1.0, 0.0, 0.0): 0,
            (-1.0, 0.0, 0.0): 0,
            (0.0, 1.0, 0.0): 1,
            (0.0, -1.0, 0.0): 1,
            (0.0, 0.0, 1.0): 2,
            (0.0, 0.0, -1.0): 2,
        }
        if rounded not in allowed:
            raise Build123dCompileError("circular patterns currently require an axis-aligned unit vector")
        axis_index = allowed[rounded]
        sign = -1.0 if rounded[axis_index] < 0 else 1.0
        denominator = count if math.isclose(total_angle, 360.0) else max(1, count - 1)
        copies = []
        for index in range(count):
            angles = [0.0, 0.0, 0.0]
            angles[axis_index] = sign * total_angle * index / denominator
            copies.append(self.bd.Rot(*angles) * source)
        return self.bd.Compound(children=copies)

    def _mirror(self, source: Any, feature: Feature) -> Any:
        plane = self._plane(str(feature.parameters["plane"]))
        return self.bd.mirror(source, about=plane)

    def compile(self, program: FeatureProgram) -> dict[str, Any]:
        report = validate_feature_program(program)
        if not report.valid:
            raise Build123dCompileError(
                "invalid feature program: " + "; ".join(f"{item.path}: {item.message}" for item in report.errors)
            )
        objects: dict[str, Any] = {}
        for feature in program.features:
            feature = Feature(
                id=feature.id,
                kind=feature.kind,
                inputs=feature.inputs,
                parameters=resolve_feature_parameters(program, feature),
                selectors=feature.selectors,
                role=feature.role,
            )
            if feature.kind not in SUPPORTED_FEATURES:
                raise Build123dCompileError(f"build123d backend does not support feature kind {feature.kind!r}")
            if feature.kind == "primitive_box":
                x, y, z = (float(item) for item in feature.parameters["size"])
                result = self.bd.Box(x, y, z)
            elif feature.kind == "primitive_cylinder":
                result = self.bd.Cylinder(
                    float(feature.parameters["radius"]),
                    float(feature.parameters["height"]),
                )
            elif feature.kind == "sketch":
                result = self._build_sketch(feature)
            elif feature.kind in {"extrude", "revolve"}:
                operation = feature.parameters["operation"]
                if operation == "new":
                    if len(feature.inputs) != 1:
                        raise Build123dCompileError(
                            f"{feature.kind} with operation new requires exactly one profile input"
                        )
                    target = None
                    profile = objects[feature.inputs[0]]
                else:
                    if len(feature.inputs) != 2:
                        raise Build123dCompileError(
                            f"{feature.kind} with operation {operation} requires target and profile inputs"
                        )
                    target, profile = objects[feature.inputs[0]], objects[feature.inputs[1]]
                if feature.kind == "extrude":
                    produced = self.bd.extrude(profile, amount=float(feature.parameters["distance"]))
                else:
                    axis = feature.parameters.get("axis", [0.0, 1.0, 0.0])
                    if not _vec3(axis):
                        raise Build123dCompileError("revolve axis must be a finite 3-vector")
                    axis_values = _as_vec3(axis, "revolve axis")
                    produced = self.bd.revolve(
                        profiles=profile,
                        axis=self.bd.Axis((0.0, 0.0, 0.0), axis_values),
                        revolution_arc=float(feature.parameters["angle_deg"]),
                    )
                if operation == "new":
                    result = produced
                elif operation == "add":
                    result = target + produced
                elif operation == "cut":
                    result = target - produced
                else:
                    result = target & produced
            elif feature.kind in {"boolean_union", "boolean_cut", "boolean_intersect"}:
                inputs = [objects[item] for item in feature.inputs]
                result = inputs[0]
                for item in inputs[1:]:
                    if feature.kind == "boolean_union":
                        result = result + item
                    elif feature.kind == "boolean_cut":
                        result = result - item
                    else:
                        result = result & item
            elif feature.kind == "fillet":
                source = objects[feature.inputs[0]]
                edges = self._selector_edges(source, feature.selectors)
                result = self.bd.fillet(edges, radius=float(feature.parameters["radius"]))
            elif feature.kind == "chamfer":
                source = objects[feature.inputs[0]]
                edges = self._selector_edges(source, feature.selectors)
                result = self.bd.chamfer(edges, length=float(feature.parameters["distance"]))
            elif feature.kind == "linear_pattern":
                result = self._linear_pattern(objects[feature.inputs[0]], feature)
            elif feature.kind == "circular_pattern":
                result = self._circular_pattern(objects[feature.inputs[0]], feature)
            elif feature.kind == "mirror":
                result = self._mirror(objects[feature.inputs[0]], feature)
            else:
                raise AssertionError(feature.kind)
            objects[feature.id] = result
        return {output: objects[output] for output in program.outputs}

    def inspect(self, shape: Any) -> GeometryInspection:
        bounds = shape.bounding_box().size
        return GeometryInspection(
            valid_brep=bool(shape.is_valid),
            manifold=bool(shape.is_manifold),
            solid_count=len(shape.solids()),
            volume_mm3=float(shape.volume),
            extents_mm=(float(bounds.X), float(bounds.Y), float(bounds.Z)),
        )

    @staticmethod
    def _vector_tuple(value: Any) -> tuple[float, float, float]:
        return float(value.X), float(value.Y), float(value.Z)

    def _analytic_edge_signature(self, edge: Any) -> AnalyticEdgeSignature:
        geom_type = getattr(edge.geom_type, "name", str(edge.geom_type)).upper()
        if geom_type not in {"LINE", "CIRCLE"}:
            raise Build123dCompileError(
                "planar revision pilot supports only LINE/CIRCLE boundary edges; "
                f"found {geom_type}"
            )
        bounds = edge.bounding_box()
        endpoints: tuple[tuple[float, float, float], ...]
        if geom_type == "LINE":
            raw_endpoints = (
                self._vector_tuple(edge.position_at(0.0)),
                self._vector_tuple(edge.position_at(1.0)),
            )
            endpoints = tuple(sorted(raw_endpoints))
        else:
            endpoints = ()
        return AnalyticEdgeSignature(
            geom_type=geom_type,
            length_mm=float(edge.length),
            bbox_min_mm=self._vector_tuple(bounds.min),
            bbox_max_mm=self._vector_tuple(bounds.max),
            endpoints_mm=endpoints,
        )

    def _analytic_wire_signature(self, wire: Any) -> AnalyticWireSignature:
        bounds = wire.bounding_box()
        edges = tuple(
            sorted(
                (self._analytic_edge_signature(edge) for edge in wire.edges()),
                key=lambda item: (
                    item.geom_type,
                    item.bbox_min_mm,
                    item.bbox_max_mm,
                    item.length_mm,
                    item.endpoints_mm,
                ),
            )
        )
        return AnalyticWireSignature(
            length_mm=float(wire.length),
            bbox_min_mm=self._vector_tuple(bounds.min),
            bbox_max_mm=self._vector_tuple(bounds.max),
            edges=edges,
        )

    @staticmethod
    def _close_scalar(
        baseline: float,
        candidate: float,
        *,
        linear_tolerance_mm: float,
        relative_scalar_tolerance: float,
        absolute_scalar_floor: float,
        dimension: int = 1,
    ) -> bool:
        absolute = max(absolute_scalar_floor, linear_tolerance_mm**dimension)
        return math.isclose(
            baseline,
            candidate,
            rel_tol=relative_scalar_tolerance,
            abs_tol=absolute,
        )

    def _wire_signatures_equivalent(
        self,
        baseline: AnalyticWireSignature,
        candidate: AnalyticWireSignature,
        *,
        linear_tolerance_mm: float,
        relative_scalar_tolerance: float,
        absolute_scalar_floor: float,
    ) -> bool:
        if len(baseline.edges) != len(candidate.edges):
            return False
        if not self._close_scalar(
            baseline.length_mm,
            candidate.length_mm,
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
        ):
            return False

        def vector_close(
            left: tuple[float, float, float],
            right: tuple[float, float, float],
        ) -> bool:
            return all(
                math.isclose(a, b, rel_tol=0.0, abs_tol=linear_tolerance_mm)
                for a, b in zip(left, right, strict=True)
            )

        if not vector_close(baseline.bbox_min_mm, candidate.bbox_min_mm):
            return False
        if not vector_close(baseline.bbox_max_mm, candidate.bbox_max_mm):
            return False

        for left, right in zip(baseline.edges, candidate.edges, strict=True):
            if left.geom_type != right.geom_type:
                return False
            if not self._close_scalar(
                left.length_mm,
                right.length_mm,
                linear_tolerance_mm=linear_tolerance_mm,
                relative_scalar_tolerance=relative_scalar_tolerance,
                absolute_scalar_floor=absolute_scalar_floor,
            ):
                return False
            if not vector_close(left.bbox_min_mm, right.bbox_min_mm):
                return False
            if not vector_close(left.bbox_max_mm, right.bbox_max_mm):
                return False
            if len(left.endpoints_mm) != len(right.endpoints_mm):
                return False
            if any(
                not vector_close(a, b)
                for a, b in zip(left.endpoints_mm, right.endpoints_mm, strict=True)
            ):
                return False
        return True

    @staticmethod
    def _wire_sort_key(signature: AnalyticWireSignature) -> tuple[Any, ...]:
        return (
            signature.bbox_min_mm,
            signature.bbox_max_mm,
            signature.length_mm,
            tuple((edge.geom_type, edge.length_mm) for edge in signature.edges),
        )

    def _sampled_wire_deviation(self, source: Any, target: Any) -> float:
        maximum = 0.0
        for edge in source.edges():
            for step in range(17):
                point = edge.position_at(step / 16)
                maximum = max(maximum, float(target.distance_to(point)))
        return maximum

    def _validate_planar_prism_program(
        self,
        program: FeatureProgram,
        *,
        axis: str,
    ) -> None:
        if len(program.features) != 2 or len(program.outputs) != 1:
            raise Build123dCompileError(
                "revision pilot requires exactly one sketch followed by one extrusion"
            )
        sketch, extrusion = program.features
        if sketch.kind != "sketch" or extrusion.kind != "extrude":
            raise Build123dCompileError(
                "revision pilot requires exactly one sketch followed by one extrusion"
            )
        if program.outputs != (extrusion.id,) or extrusion.inputs != (sketch.id,):
            raise Build123dCompileError(
                "revision pilot output must be the extrusion of the pilot sketch"
            )
        resolved_extrusion = resolve_feature_parameters(program, extrusion)
        if resolved_extrusion.get("operation") != "new":
            raise Build123dCompileError(
                "revision pilot extrusion must use operation 'new'"
            )
        plane = str(resolve_feature_parameters(program, sketch).get("plane", "XY")).upper()
        expected_axis = {"XY": "z", "XZ": "y", "YZ": "x"}.get(plane)
        if expected_axis is None or expected_axis != axis.lower():
            raise Build123dCompileError(
                "revision pilot comparison axis must be normal to the sketch plane"
            )

    def _self_intersection_free(self, shape: Any) -> bool:
        try:
            bop_algo = importlib.import_module("OCP.BOPAlgo")
        except ModuleNotFoundError as exc:
            raise Build123dCompileError(
                "OCP self-interference analyzer is unavailable; failing closed"
            ) from exc
        analyzer = bop_algo.BOPAlgo_ArgumentAnalyzer()
        for mode in (
            "ArgumentTypeMode",
            "ContinuityMode",
            "CurveOnSurfaceMode",
            "MergeEdgeMode",
            "MergeVertexMode",
            "RebuildFaceMode",
            "SmallEdgeMode",
            "TangentMode",
        ):
            if hasattr(analyzer, mode):
                setattr(analyzer, mode, False)
        analyzer.SelfInterMode = True
        analyzer.SetShape1(shape.wrapped)
        analyzer.Perform()
        if analyzer.HasErrors():
            raise Build123dCompileError(
                "OCP self-interference analysis failed; refusing revision acceptance"
            )
        return not bool(analyzer.HasFaulty())

    @staticmethod
    def _minimum_material_clearance(outer_wire: Any, inner_wires: list[Any]) -> float:
        if not inner_wires:
            raise Build123dCompileError(
                "revision pilot requires at least one cutout boundary"
            )
        distances = [float(outer_wire.distance_to(wire)) for wire in inner_wires]
        for left_index, left in enumerate(inner_wires):
            for right in inner_wires[left_index + 1 :]:
                distances.append(float(left.distance_to(right)))
        return min(distances)

    def _partition_revision_inner_wires(
        self,
        face: Any,
    ) -> tuple[
        tuple[AnalyticWireSignature, Any],
        list[tuple[AnalyticWireSignature, Any]],
    ]:
        authorized: list[tuple[AnalyticWireSignature, Any]] = []
        cutouts: list[tuple[AnalyticWireSignature, Any]] = []
        for wire in face.inner_wires():
            signature = self._analytic_wire_signature(wire)
            edge_types = {edge.geom_type for edge in signature.edges}
            if edge_types == {"LINE"} and len(signature.edges) == 4:
                authorized.append((signature, wire))
            elif edge_types == {"CIRCLE"} and len(signature.edges) == 1:
                cutouts.append((signature, wire))
            else:
                raise Build123dCompileError(
                    "revision pilot inner boundaries must be one four-line cavity "
                    "plus one or more circular cutouts"
                )
        if len(authorized) != 1:
            raise Build123dCompileError(
                "revision pilot requires exactly one four-line authorized cavity boundary"
            )
        if not cutouts:
            raise Build123dCompileError(
                "revision pilot requires at least one circular unaffected cutout"
            )
        return authorized[0], sorted(
            cutouts,
            key=lambda item: self._wire_sort_key(item[0]),
        )

    def _planar_wall_thickness_from_face(self, face: Any) -> float:
        (_authorized_signature, authorized_wire), _cutouts = (
            self._partition_revision_inner_wires(face)
        )
        return float(face.outer_wire().distance_to(authorized_wire))

    def _exact_requirement_measurements(
        self,
        shape: Any,
        binding_set: RequirementBindingSet,
    ) -> dict[str, float]:
        measurements: dict[str, float] = {}
        for binding in binding_set.bindings:
            if (
                binding.verification != "exact_dimension"
                or binding.probe.get("kind") != "planar_wall_thickness"
            ):
                continue
            axis = binding.probe.get("axis")
            side = binding.probe.get("side", "min")
            if not isinstance(axis, str) or not isinstance(side, str):
                raise Build123dCompileError(
                    "planar_wall_thickness probe requires string axis and side"
                )
            face = self._select_planar_extreme_face(
                shape,
                axis=axis,
                side=side,
                tolerance_mm=1e-6,
            )
            measurements[binding.requirement_id] = (
                self._planar_wall_thickness_from_face(face)
            )
        return measurements

    def _select_planar_extreme_face(
        self,
        shape: Any,
        *,
        axis: str,
        side: str,
        tolerance_mm: float,
    ) -> Any:
        axis = axis.lower()
        side = side.lower()
        if axis not in {"x", "y", "z"}:
            raise Build123dCompileError("revision comparison axis must be x, y, or z")
        if side not in {"min", "max"}:
            raise Build123dCompileError("revision comparison side must be min or max")
        coordinate = {
            "x": lambda point: float(point.X),
            "y": lambda point: float(point.Y),
            "z": lambda point: float(point.Z),
        }[axis]
        planar = [
            face
            for face in shape.faces()
            if getattr(face.geom_type, "name", str(face.geom_type)).upper() == "PLANE"
        ]
        if not planar:
            raise Build123dCompileError("revision comparison found no planar faces")
        values = [coordinate(face.center()) for face in planar]
        extreme = min(values) if side == "min" else max(values)
        candidates = [
            face
            for face, value in zip(planar, values, strict=True)
            if math.isclose(value, extreme, rel_tol=0.0, abs_tol=tolerance_mm)
        ]
        if not candidates:
            raise Build123dCompileError("revision comparison could not resolve the requested face")
        ranked = sorted(candidates, key=lambda face: float(face.area), reverse=True)
        if len(ranked) > 1 and math.isclose(
            float(ranked[0].area),
            float(ranked[1].area),
            rel_tol=0.0,
            abs_tol=max(tolerance_mm**2, 1e-12),
        ):
            raise Build123dCompileError(
                "revision comparison face selector is ambiguous at the requested extreme"
            )
        return ranked[0]

    def _verify_planar_step_matches_program(
        self,
        program: FeatureProgram,
        step_path: Path,
        *,
        axis: str,
        side: str,
        linear_tolerance_mm: float,
        relative_scalar_tolerance: float,
        absolute_scalar_floor: float,
    ) -> Any:
        """Prove a STEP artifact still represents the supplied pilot Feature IR."""

        self._validate_planar_prism_program(program, axis=axis)
        outputs = self.compile(program)
        if len(outputs) != 1:
            raise Build123dCompileError(
                "baseline consistency check requires exactly one program output"
            )
        expected_shape = next(iter(outputs.values()))
        try:
            imported_shape = self.bd.import_step(step_path)
        except Exception as exc:
            raise Build123dCompileError(
                "verified STEP could not be imported for consistency verification"
            ) from exc

        expected_inspection = self.inspect(expected_shape)
        imported_inspection = self.inspect(imported_shape)
        try:
            self._verify_step_roundtrip(
                expected_inspection,
                imported_inspection,
                absolute_tolerance_mm=linear_tolerance_mm,
                relative_volume_tolerance=relative_scalar_tolerance,
            )
        except Build123dCompileError as exc:
            raise Build123dCompileError(
                "verified STEP does not match the supplied Feature IR"
            ) from exc
        if (
            not imported_inspection.manifold
            or imported_inspection.solid_count != 1
            or not self._self_intersection_free(imported_shape)
        ):
            raise Build123dCompileError(
                "verified STEP is not one self-intersection-free manifold solid"
            )

        expected_face = self._select_planar_extreme_face(
            expected_shape,
            axis=axis,
            side=side,
            tolerance_mm=linear_tolerance_mm,
        )
        imported_face = self._select_planar_extreme_face(
            imported_shape,
            axis=axis,
            side=side,
            tolerance_mm=linear_tolerance_mm,
        )

        expected_outer = expected_face.outer_wire()
        imported_outer = imported_face.outer_wire()
        if (
            not self._wire_signatures_equivalent(
                self._analytic_wire_signature(expected_outer),
                self._analytic_wire_signature(imported_outer),
                linear_tolerance_mm=linear_tolerance_mm,
                relative_scalar_tolerance=relative_scalar_tolerance,
                absolute_scalar_floor=absolute_scalar_floor,
            )
            or self._sampled_wire_deviation(expected_outer, imported_outer)
            > linear_tolerance_mm
            or self._sampled_wire_deviation(imported_outer, expected_outer)
            > linear_tolerance_mm
        ):
            raise Build123dCompileError(
                "verified STEP external boundary differs from the supplied Feature IR"
            )

        (_expected_cavity_signature, expected_cavity), expected_cutouts = (
            self._partition_revision_inner_wires(expected_face)
        )
        (_imported_cavity_signature, imported_cavity), imported_cutouts = (
            self._partition_revision_inner_wires(imported_face)
        )
        if (
            not self._wire_signatures_equivalent(
                self._analytic_wire_signature(expected_cavity),
                self._analytic_wire_signature(imported_cavity),
                linear_tolerance_mm=linear_tolerance_mm,
                relative_scalar_tolerance=relative_scalar_tolerance,
                absolute_scalar_floor=absolute_scalar_floor,
            )
            or self._sampled_wire_deviation(expected_cavity, imported_cavity)
            > linear_tolerance_mm
            or self._sampled_wire_deviation(imported_cavity, expected_cavity)
            > linear_tolerance_mm
        ):
            raise Build123dCompileError(
                "verified STEP authorized cavity differs from the supplied Feature IR"
            )

        if len(expected_cutouts) != len(imported_cutouts):
            raise Build123dCompileError(
                "verified STEP cutout count differs from the supplied Feature IR"
            )
        for (expected_signature, expected_wire), (
            imported_signature,
            imported_wire,
        ) in zip(expected_cutouts, imported_cutouts, strict=True):
            if (
                not self._wire_signatures_equivalent(
                    expected_signature,
                    imported_signature,
                    linear_tolerance_mm=linear_tolerance_mm,
                    relative_scalar_tolerance=relative_scalar_tolerance,
                    absolute_scalar_floor=absolute_scalar_floor,
                )
                or self._sampled_wire_deviation(expected_wire, imported_wire)
                > linear_tolerance_mm
                or self._sampled_wire_deviation(imported_wire, expected_wire)
                > linear_tolerance_mm
            ):
                raise Build123dCompileError(
                    "verified STEP cutout geometry differs from the supplied Feature IR"
                )

        return imported_shape

    def compare_planar_revision_boundary(
        self,
        baseline_program: FeatureProgram,
        candidate_program: FeatureProgram,
        *,
        axis: str = "z",
        side: str = "min",
        linear_tolerance_mm: float = 1e-6,
        relative_scalar_tolerance: float = 1e-9,
        absolute_scalar_floor: float = 1e-12,
    ) -> PlanarRevisionEvidence:
        if (
            linear_tolerance_mm <= 0
            or relative_scalar_tolerance < 0
            or absolute_scalar_floor < 0
        ):
            raise Build123dCompileError(
                "revision comparison tolerances must be non-negative and "
                "linear tolerance positive"
            )

        self._validate_planar_prism_program(baseline_program, axis=axis)
        self._validate_planar_prism_program(candidate_program, axis=axis)
        baseline_outputs = self.compile(baseline_program)
        candidate_outputs = self.compile(candidate_program)
        if len(baseline_outputs) != 1 or len(candidate_outputs) != 1:
            raise Build123dCompileError(
                "revision comparison currently requires exactly one output "
                "in baseline and candidate"
            )
        baseline_shape = next(iter(baseline_outputs.values()))
        candidate_shape = next(iter(candidate_outputs.values()))
        baseline_inspection = self.inspect(baseline_shape)
        candidate_inspection = self.inspect(candidate_shape)
        for label, inspection in (
            ("baseline", baseline_inspection),
            ("candidate", candidate_inspection),
        ):
            if (
                not inspection.valid_brep
                or not inspection.manifold
                or inspection.solid_count != 1
            ):
                raise Build123dCompileError(
                    f"{label} revision geometry must be one valid manifold solid"
                )

        extent_deltas = tuple(
            abs(left - right)
            for left, right in zip(
                baseline_inspection.extents_mm,
                candidate_inspection.extents_mm,
                strict=True,
            )
        )
        max_external_extent_delta = max(extent_deltas)
        external_extents_equivalent = (
            max_external_extent_delta <= linear_tolerance_mm
        )

        baseline_face = self._select_planar_extreme_face(
            baseline_shape,
            axis=axis,
            side=side,
            tolerance_mm=linear_tolerance_mm,
        )
        candidate_face = self._select_planar_extreme_face(
            candidate_shape,
            axis=axis,
            side=side,
            tolerance_mm=linear_tolerance_mm,
        )
        baseline_outer = baseline_face.outer_wire()
        candidate_outer = candidate_face.outer_wire()
        baseline_outer_signature = self._analytic_wire_signature(baseline_outer)
        candidate_outer_signature = self._analytic_wire_signature(candidate_outer)
        external_boundary_equivalent = self._wire_signatures_equivalent(
            baseline_outer_signature,
            candidate_outer_signature,
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
        )
        max_external_deviation = max(
            self._sampled_wire_deviation(baseline_outer, candidate_outer),
            self._sampled_wire_deviation(candidate_outer, baseline_outer),
        )

        (baseline_cavity_signature, baseline_cavity), baseline_cutouts = (
            self._partition_revision_inner_wires(baseline_face)
        )
        (candidate_cavity_signature, candidate_cavity), candidate_cutouts = (
            self._partition_revision_inner_wires(candidate_face)
        )
        del baseline_cavity_signature, candidate_cavity_signature

        baseline_wall_thickness = float(
            baseline_outer.distance_to(baseline_cavity)
        )
        candidate_wall_thickness = float(
            candidate_outer.distance_to(candidate_cavity)
        )

        cutouts_equivalent = len(baseline_cutouts) == len(candidate_cutouts)
        max_cutout_deviation = 0.0
        if cutouts_equivalent:
            for (left_signature, left_wire), (right_signature, right_wire) in zip(
                baseline_cutouts,
                candidate_cutouts,
                strict=True,
            ):
                if not self._wire_signatures_equivalent(
                    left_signature,
                    right_signature,
                    linear_tolerance_mm=linear_tolerance_mm,
                    relative_scalar_tolerance=relative_scalar_tolerance,
                    absolute_scalar_floor=absolute_scalar_floor,
                ):
                    cutouts_equivalent = False
                max_cutout_deviation = max(
                    max_cutout_deviation,
                    self._sampled_wire_deviation(left_wire, right_wire),
                    self._sampled_wire_deviation(right_wire, left_wire),
                )

        baseline_self_intersection_free = self._self_intersection_free(
            baseline_shape
        )
        candidate_self_intersection_free = self._self_intersection_free(
            candidate_shape
        )
        candidate_inner_wires = [
            candidate_cavity,
            *(wire for _signature, wire in candidate_cutouts),
        ]
        candidate_minimum_material_clearance = self._minimum_material_clearance(
            candidate_outer,
            candidate_inner_wires,
        )
        axis_index = {"x": 0, "y": 1, "z": 2}[axis.lower()]
        candidate_zero_thickness_free = (
            candidate_inspection.extents_mm[axis_index] > linear_tolerance_mm
            and float(candidate_face.area)
            > max(absolute_scalar_floor, linear_tolerance_mm**2)
            and candidate_wall_thickness > linear_tolerance_mm
            and candidate_minimum_material_clearance > linear_tolerance_mm
        )
        passed = (
            external_boundary_equivalent
            and external_extents_equivalent
            and cutouts_equivalent
            and max_external_deviation <= linear_tolerance_mm
            and max_cutout_deviation <= linear_tolerance_mm
            and baseline_self_intersection_free
            and candidate_self_intersection_free
            and candidate_zero_thickness_free
        )
        return PlanarRevisionEvidence(
            backend="build123d",
            backend_version=self.version,
            baseline_feature_ir_sha256=_program_sha256(baseline_program),
            candidate_feature_ir_sha256=_program_sha256(candidate_program),
            axis=axis.lower(),
            side=side.lower(),
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
            baseline_inspection=baseline_inspection,
            candidate_inspection=candidate_inspection,
            baseline_face_area_mm2=float(baseline_face.area),
            candidate_face_area_mm2=float(candidate_face.area),
            baseline_wall_thickness_mm=baseline_wall_thickness,
            candidate_wall_thickness_mm=candidate_wall_thickness,
            external_boundary_equivalent=external_boundary_equivalent,
            external_extents_equivalent=external_extents_equivalent,
            max_external_extent_delta_mm=max_external_extent_delta,
            cutout_count_baseline=len(baseline_cutouts),
            cutout_count_candidate=len(candidate_cutouts),
            cutouts_equivalent=cutouts_equivalent,
            max_sampled_external_deviation_mm=max_external_deviation,
            max_sampled_cutout_deviation_mm=max_cutout_deviation,
            baseline_self_intersection_free=baseline_self_intersection_free,
            candidate_self_intersection_free=candidate_self_intersection_free,
            candidate_minimum_material_clearance_mm=(
                candidate_minimum_material_clearance
            ),
            candidate_zero_thickness_free=candidate_zero_thickness_free,
            passed=passed,
        )

    @staticmethod
    def _require_frozen_revision_pilot_contract(
        *,
        axis: str,
        side: str,
        edited_requirement_ids: tuple[str, ...],
        linear_tolerance_mm: float,
        relative_scalar_tolerance: float,
        absolute_scalar_floor: float,
    ) -> None:
        if axis.lower() != REVISION_PILOT_AXIS or side.lower() != REVISION_PILOT_SIDE:
            raise Build123dCompileError(
                "verified revision publication is frozen to axis='z' and side='min'"
            )
        if tuple(edited_requirement_ids) != REVISION_PILOT_EDITED_REQUIREMENT_IDS:
            raise Build123dCompileError(
                "verified revision publication is frozen to the wall_thickness requirement only"
            )
        if (
            linear_tolerance_mm != REVISION_PILOT_LINEAR_TOLERANCE_MM
            or relative_scalar_tolerance != REVISION_PILOT_RELATIVE_SCALAR_TOLERANCE
            or absolute_scalar_floor != REVISION_PILOT_ABSOLUTE_SCALAR_FLOOR
        ):
            raise Build123dCompileError(
                "verified revision publication requires the frozen C3D pilot tolerances"
            )

    def export_verified_revision(
        self,
        baseline_program: FeatureProgram,
        candidate_program: FeatureProgram,
        baseline_bundle_dir: Path,
        output_dir: Path,
        *,
        baseline_requirements: RequirementIR,
        baseline_binding_set: RequirementBindingSet,
        candidate_requirements: RequirementIR,
        candidate_binding_set: RequirementBindingSet,
        edited_requirement_ids: tuple[str, ...] = (),
        axis: str = "z",
        side: str = "min",
        linear_tolerance_mm: float = 1e-6,
        relative_scalar_tolerance: float = 1e-9,
        absolute_scalar_floor: float = 1e-12,
    ) -> tuple[Build123dReceipt, RevisionBundleReceipt]:
        self._require_frozen_revision_pilot_contract(
            axis=axis,
            side=side,
            edited_requirement_ids=edited_requirement_ids,
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
        )

        baseline_bundle = baseline_bundle_dir.expanduser()
        if baseline_bundle.is_symlink() or not baseline_bundle.is_dir():
            raise Build123dCompileError(
                "baseline bundle must be an existing non-symlink directory"
            )
        baseline_receipt_path = baseline_bundle / "build-receipt.json"
        if baseline_receipt_path.is_symlink() or not baseline_receipt_path.is_file():
            raise Build123dCompileError(
                "baseline bundle must contain a regular build-receipt.json"
            )
        try:
            baseline_receipt_payload = strict_json_loads(
                baseline_receipt_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise Build123dCompileError(
                "baseline build receipt is unreadable or invalid JSON"
            ) from exc
        if not isinstance(baseline_receipt_payload, dict):
            raise Build123dCompileError("baseline build receipt must be a JSON object")
        expected_baseline_hash = _program_sha256(baseline_program)
        if baseline_receipt_payload.get("feature_ir_sha256") != expected_baseline_hash:
            raise Build123dCompileError(
                "baseline build receipt does not target the supplied baseline Feature IR"
            )
        step_name = baseline_receipt_payload.get("step_path")
        if not isinstance(step_name, str):
            raise Build123dCompileError("baseline build receipt is missing step_path")
        step_name = _validate_step_filename(step_name)
        baseline_step = baseline_bundle / step_name
        if baseline_step.is_symlink() or not baseline_step.is_file():
            raise Build123dCompileError(
                "baseline build receipt points to a missing or non-regular STEP file"
            )

        destination_input = output_dir.expanduser()
        if destination_input.exists() or destination_input.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination_input}")
        destination = destination_input.resolve()
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        requirement_items = (
            baseline_requirements,
            baseline_binding_set,
            candidate_requirements,
            candidate_binding_set,
        )
        if any(item is None for item in requirement_items):
            raise Build123dCompileError(
                "verified revisions require baseline/candidate Requirement IR and binding sets"
            )

        baseline_step_sha256 = _sha256(baseline_step)
        receipt_step_sha256 = baseline_receipt_payload.get("step_sha256")
        if receipt_step_sha256 != baseline_step_sha256:
            raise Build123dCompileError(
                "baseline STEP hash does not match its accepted build receipt"
            )
        baseline_build_receipt_sha256 = _sha256(baseline_receipt_path)

        baseline_requirements_path = baseline_bundle / "requirements.json"
        baseline_bindings_path = baseline_bundle / "requirement-bindings.json"
        baseline_verification_path = baseline_bundle / "requirements-verification.json"
        if (
            baseline_requirements_path.is_symlink()
            or baseline_bindings_path.is_symlink()
            or baseline_verification_path.is_symlink()
            or not baseline_requirements_path.is_file()
            or not baseline_bindings_path.is_file()
            or not baseline_verification_path.is_file()
        ):
            raise Build123dCompileError(
                "accepted baseline is missing regular requirement verification artifacts"
            )
        baseline_requirements_sha256 = _sha256(baseline_requirements_path)
        baseline_bindings_sha256 = _sha256(baseline_bindings_path)
        baseline_requirements_verification_sha256 = _sha256(
            baseline_verification_path
        )
        if (
            baseline_receipt_payload.get("requirements_sha256")
            != baseline_requirements_sha256
            or baseline_receipt_payload.get("bindings_sha256")
            != baseline_bindings_sha256
            or baseline_receipt_payload.get("requirements_verification_sha256")
            != baseline_requirements_verification_sha256
        ):
            raise Build123dCompileError(
                "baseline requirement artifact hashes do not match the accepted receipt"
            )
        if baseline_receipt_payload.get("requirements_satisfied") is not True:
            raise Build123dCompileError(
                "baseline build receipt does not record satisfied must-level requirements"
            )
        expected_requirements_sha256 = hashlib.sha256(
            serialize_requirement_ir_json(baseline_requirements).encode("utf-8")
        ).hexdigest()
        expected_bindings_sha256 = hashlib.sha256(
            serialize_binding_set_json(baseline_binding_set).encode("utf-8")
        ).hexdigest()
        if baseline_requirements_sha256 != expected_requirements_sha256:
            raise Build123dCompileError(
                "baseline requirements do not match the supplied accepted contract"
            )
        if baseline_bindings_sha256 != expected_bindings_sha256:
            raise Build123dCompileError(
                "baseline bindings do not match the supplied accepted contract"
            )

        try:
            baseline_verification_payload = strict_json_loads(
                baseline_verification_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise Build123dCompileError(
                "baseline requirement verification evidence is unreadable or invalid JSON"
            ) from exc
        if not isinstance(baseline_verification_payload, dict):
            raise Build123dCompileError(
                "baseline requirement verification evidence must be a JSON object"
            )
        if baseline_verification_payload.get("satisfied_for_all_must") is not True:
            raise Build123dCompileError(
                "baseline requirement verification does not satisfy every must requirement"
            )
        if baseline_verification_payload.get("errors") != []:
            raise Build123dCompileError(
                "baseline requirement verification contains recorded errors"
            )
        if (
            baseline_verification_payload.get("requirement_ir_sha256")
            != requirement_ir_sha256(baseline_requirements)
            or baseline_verification_payload.get("feature_ir_sha256")
            != expected_baseline_hash
            or baseline_verification_payload.get("binding_set_sha256")
            != binding_set_sha256(baseline_binding_set)
        ):
            raise Build123dCompileError(
                "baseline requirement verification provenance does not match the supplied accepted contract"
            )

        baseline_step_shape = self._verify_planar_step_matches_program(
            baseline_program,
            baseline_step,
            axis=axis,
            side=side,
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
        )
        baseline_recomputed_verification = verify_exact_requirements(
            baseline_requirements,
            baseline_program,
            self.inspect(baseline_step_shape),
            baseline_binding_set,
            exact_measurements_mm=self._exact_requirement_measurements(
                baseline_step_shape,
                baseline_binding_set,
            ),
        )
        if not baseline_recomputed_verification.satisfied_for_all_must:
            raise Build123dCompileError(
                "accepted baseline no longer satisfies its must-level requirements"
            )
        if (
            baseline_verification_payload
            != baseline_recomputed_verification.to_dict()
        ):
            raise Build123dCompileError(
                "baseline requirement verification evidence does not reproduce from the accepted STEP"
            )

        evidence = self.compare_planar_revision_boundary(
            baseline_program,
            candidate_program,
            axis=axis,
            side=side,
            linear_tolerance_mm=linear_tolerance_mm,
            relative_scalar_tolerance=relative_scalar_tolerance,
            absolute_scalar_floor=absolute_scalar_floor,
        )
        if not evidence.passed:
            raise Build123dCompileError(
                "revision integrity comparison failed; candidate was not published"
            )

        contract_errors = verify_unchanged_must_requirements(
            baseline_requirements,
            baseline_binding_set,
            candidate_requirements,
            candidate_binding_set,
            edited_requirement_ids=edited_requirement_ids,
        )
        if contract_errors:
            details = ", ".join(error.code for error in contract_errors)
            raise Build123dCompileError(
                "unchanged must-level revision contract failed: " + details
            )
        unchanged_requirements_guard_passed = True

        private_root = Path(
            tempfile.mkdtemp(prefix=f".{destination.name}.revision.", dir=destination.parent)
        )
        private_bundle = private_root / "bundle"
        try:
            candidate_receipt = self.export_verified_step(
                candidate_program,
                private_bundle,
                requirements=candidate_requirements,
                binding_set=candidate_binding_set,
            )
            if candidate_receipt.step_path is None or candidate_receipt.step_sha256 is None:
                raise Build123dCompileError("candidate export did not produce STEP evidence")
            candidate_step = private_bundle / candidate_receipt.step_path
            candidate_build_receipt = private_bundle / "build-receipt.json"
            candidate_requirements_path = private_bundle / "requirements.json"
            candidate_bindings_path = private_bundle / "requirement-bindings.json"
            candidate_verification = private_bundle / "requirements-verification.json"
            candidate_artifacts = (
                candidate_step,
                candidate_build_receipt,
                candidate_requirements_path,
                candidate_bindings_path,
                candidate_verification,
            )
            if any(path.is_symlink() or not path.is_file() for path in candidate_artifacts):
                raise Build123dCompileError(
                    "candidate export did not produce a regular complete verified bundle"
                )

            candidate_step_sha256 = _sha256(candidate_step)
            candidate_requirements_sha256 = _sha256(candidate_requirements_path)
            candidate_bindings_sha256 = _sha256(candidate_bindings_path)
            candidate_verification_sha256 = _sha256(candidate_verification)
            if candidate_step_sha256 != candidate_receipt.step_sha256:
                raise Build123dCompileError(
                    "candidate STEP hash does not match its verified build receipt"
                )
            if candidate_requirements_sha256 != candidate_receipt.requirements_sha256:
                raise Build123dCompileError(
                    "candidate requirements hash does not match its verified build receipt"
                )
            if candidate_bindings_sha256 != candidate_receipt.bindings_sha256:
                raise Build123dCompileError(
                    "candidate bindings hash does not match its verified build receipt"
                )
            if (
                candidate_verification_sha256
                != candidate_receipt.requirements_verification_sha256
            ):
                raise Build123dCompileError(
                    "candidate requirement verification hash does not match its verified build receipt"
                )
            try:
                candidate_receipt_payload = strict_json_loads(
                    candidate_build_receipt.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise Build123dCompileError(
                    "candidate build receipt is unreadable or invalid JSON"
                ) from exc
            if candidate_receipt_payload != candidate_receipt.to_dict():
                raise Build123dCompileError(
                    "candidate build receipt file does not match the verified in-memory receipt"
                )

            self._verify_planar_step_matches_program(
                candidate_program,
                candidate_step,
                axis=axis,
                side=side,
                linear_tolerance_mm=linear_tolerance_mm,
                relative_scalar_tolerance=relative_scalar_tolerance,
                absolute_scalar_floor=absolute_scalar_floor,
            )

            if _sha256(baseline_step) != baseline_step_sha256:
                raise Build123dCompileError(
                    "baseline STEP changed during revision evaluation; refusing publication"
                )
            if _sha256(baseline_receipt_path) != baseline_build_receipt_sha256:
                raise Build123dCompileError(
                    "baseline build receipt changed during revision evaluation; refusing publication"
                )
            if _sha256(baseline_requirements_path) != baseline_requirements_sha256:
                raise Build123dCompileError(
                    "baseline requirements changed during revision evaluation; "
                    "refusing publication"
                )
            if _sha256(baseline_bindings_path) != baseline_bindings_sha256:
                raise Build123dCompileError(
                    "baseline bindings changed during revision evaluation; "
                    "refusing publication"
                )
            if (
                _sha256(baseline_verification_path)
                != baseline_requirements_verification_sha256
            ):
                raise Build123dCompileError(
                    "baseline requirement verification changed during revision evaluation; "
                    "refusing publication"
                )

            revision_receipt = RevisionBundleReceipt(
                backend="build123d",
                backend_version=self.version,
                baseline_feature_ir_sha256=evidence.baseline_feature_ir_sha256,
                candidate_feature_ir_sha256=evidence.candidate_feature_ir_sha256,
                baseline_step_sha256=baseline_step_sha256,
                baseline_build_receipt_sha256=baseline_build_receipt_sha256,
                baseline_requirements_sha256=baseline_requirements_sha256,
                baseline_bindings_sha256=baseline_bindings_sha256,
                baseline_requirements_verification_sha256=(
                    baseline_requirements_verification_sha256
                ),
                candidate_step_sha256=candidate_step_sha256,
                candidate_build_receipt_sha256=_sha256(candidate_build_receipt),
                candidate_requirements_sha256=candidate_requirements_sha256,
                candidate_bindings_sha256=candidate_bindings_sha256,
                candidate_requirements_verification_sha256=(
                    candidate_verification_sha256
                ),
                edited_requirement_ids=tuple(edited_requirement_ids),
                evidence=evidence,
                unchanged_requirements_guard_passed=unchanged_requirements_guard_passed,
            )
            revision_path = private_bundle / "revision-integrity.json"
            revision_path.write_text(
                json.dumps(
                    revision_receipt.to_dict(),
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(private_bundle, destination)
            shutil.rmtree(private_root, ignore_errors=True)
            return candidate_receipt, revision_receipt
        except BaseException:
            shutil.rmtree(private_root, ignore_errors=True)
            raise

    def build_receipt(self, program: FeatureProgram) -> Build123dReceipt:
        outputs = self.compile(program)
        if len(outputs) != 1:
            raise Build123dCompileError("receipt generation currently requires exactly one output feature")
        output_feature, shape = next(iter(outputs.items()))
        return Build123dReceipt(
            backend="build123d",
            backend_version=self.version,
            feature_ir_sha256=_program_sha256(program),
            output_feature=output_feature,
            inspection=self.inspect(shape),
        )

    @staticmethod
    def _verify_step_roundtrip(
        original: GeometryInspection,
        roundtrip: GeometryInspection,
        *,
        absolute_tolerance_mm: float = 1e-6,
        relative_volume_tolerance: float = 1e-9,
    ) -> None:
        if not roundtrip.valid_brep:
            raise Build123dCompileError("STEP re-import produced an invalid B-Rep")
        if roundtrip.solid_count != original.solid_count:
            raise Build123dCompileError(
                f"STEP re-import changed solid count from {original.solid_count} to {roundtrip.solid_count}"
            )
        for axis, (expected, actual) in enumerate(zip(original.extents_mm, roundtrip.extents_mm, strict=True)):
            if not math.isclose(expected, actual, rel_tol=0.0, abs_tol=absolute_tolerance_mm):
                raise Build123dCompileError(
                    f"STEP re-import changed extent axis {axis} from {expected:g} mm to {actual:g} mm"
                )
        if not math.isclose(
            original.volume_mm3,
            roundtrip.volume_mm3,
            rel_tol=relative_volume_tolerance,
            abs_tol=absolute_tolerance_mm**3,
        ):
            raise Build123dCompileError(
                f"STEP re-import changed volume from {original.volume_mm3:g} mm^3 "
                f"to {roundtrip.volume_mm3:g} mm^3"
            )

    def export_verified_step(
        self,
        program: FeatureProgram,
        output_dir: Path,
        *,
        filename: str = "design.step",
        requirements: RequirementIR | None = None,
        binding_set: RequirementBindingSet | None = None,
    ) -> Build123dReceipt:
        filename = _validate_step_filename(filename)
        destination_input = output_dir.expanduser()
        if destination_input.exists() or destination_input.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination_input}")
        output_dir = destination_input.resolve()
        if output_dir.exists() or output_dir.is_symlink():
            raise FileExistsError(f"output directory already exists: {output_dir}")
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
        try:
            outputs = self.compile(program)
            if len(outputs) != 1:
                raise Build123dCompileError("STEP export currently requires exactly one output feature")
            output_feature, shape = next(iter(outputs.items()))
            inspection = self.inspect(shape)
            if not inspection.valid_brep:
                raise Build123dCompileError("build123d produced an invalid B-Rep")
            step_path = staging / filename
            if not self.bd.export_step(shape, step_path):
                raise Build123dCompileError("build123d STEP exporter reported failure")
            imported = self.bd.import_step(step_path)
            roundtrip = self.inspect(imported)
            self._verify_step_roundtrip(inspection, roundtrip)

            if (requirements is None) != (binding_set is None):
                raise Build123dCompileError(
                    "requirements and binding_set must be supplied together"
                )

            requirements_path: Path | None = None
            bindings_path: Path | None = None
            verification_path: Path | None = None
            requirements_satisfied: bool | None = None
            if requirements is not None and binding_set is not None:
                exact_measurements_mm = self._exact_requirement_measurements(
                    imported,
                    binding_set,
                )
                requirement_verification = verify_exact_requirements(
                    requirements,
                    program,
                    roundtrip,
                    binding_set,
                    exact_measurements_mm=exact_measurements_mm,
                )
                requirements_satisfied = requirement_verification.satisfied_for_all_must
                if not requirements_satisfied:
                    failed = [
                        check.requirement_id
                        for check in requirement_verification.checks
                        if check.strength == "must" and not check.satisfied
                    ]
                    errors = [error.code for error in requirement_verification.errors]
                    details = ", ".join((*failed, *errors)) or "unknown must-level failure"
                    raise Build123dCompileError(
                        "must-level requirement verification failed: " + details
                    )
                requirements_path = staging / "requirements.json"
                bindings_path = staging / "requirement-bindings.json"
                verification_path = staging / "requirements-verification.json"
                requirements_path.write_text(
                    serialize_requirement_ir_json(requirements),
                    encoding="utf-8",
                )
                bindings_path.write_text(
                    serialize_binding_set_json(binding_set),
                    encoding="utf-8",
                )
                verification_path.write_text(
                    json.dumps(
                        requirement_verification.to_dict(),
                        indent=2,
                        sort_keys=True,
                        allow_nan=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            receipt = Build123dReceipt(
                backend="build123d",
                backend_version=self.version,
                feature_ir_sha256=_program_sha256(program),
                output_feature=output_feature,
                inspection=inspection,
                step_path=filename,
                step_sha256=_sha256(step_path),
                roundtrip_inspection=roundtrip,
                requirements_path=None if requirements_path is None else requirements_path.name,
                requirements_sha256=None if requirements_path is None else _sha256(requirements_path),
                bindings_path=None if bindings_path is None else bindings_path.name,
                bindings_sha256=None if bindings_path is None else _sha256(bindings_path),
                requirements_verification_path=(
                    None if verification_path is None else verification_path.name
                ),
                requirements_verification_sha256=(
                    None if verification_path is None else _sha256(verification_path)
                ),
                requirements_satisfied=requirements_satisfied,
            )
            receipt_path = staging / "build-receipt.json"
            receipt_path.write_text(
                json.dumps(receipt.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            os.replace(staging, output_dir)
            return receipt
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise


def _as_positive_float(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not _positive(value):
        raise Build123dCompileError(f"{label} must be a positive finite number")
    return float(value)


def _as_vec3(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or not _vec3(value):
        raise Build123dCompileError(f"{label} must be a finite 3-vector")
    return float(value[0]), float(value[1]), float(value[2])


def _positive(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _vec3(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(
            not isinstance(item, bool)
            and isinstance(item, (int, float))
            and math.isfinite(float(item))
            for item in value
        )
    )
