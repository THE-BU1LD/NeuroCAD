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
from .requirement_ir import RequirementIR, serialize_requirement_ir_json
from .requirement_verification import (
    RequirementBindingSet,
    serialize_binding_set_json,
    verify_exact_requirements,
)

BUILD_RECEIPT_VERSION = "neurocad-build123d-receipt-v1"
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
                requirement_verification = verify_exact_requirements(
                    requirements,
                    program,
                    roundtrip,
                    binding_set,
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
