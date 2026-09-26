"""Bind Requirement IR claims to Feature IR and exact-kernel evidence."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .feature_ir import FeatureProgram, serialize_feature_ir_json
from .json_io import strict_json_loads
from .requirement_ir import (
    Requirement,
    RequirementIR,
    RequirementIssue,
    serialize_requirement_ir_json,
    validate_requirement_ir,
)


class GeometryInspectionLike(Protocol):
    valid_brep: bool
    solid_count: int
    volume_mm3: float
    extents_mm: tuple[float, float, float]


REQUIREMENT_BINDING_VERSION = "neurocad-requirement-binding-v0alpha1"
MAX_BINDING_JSON_BYTES = 2 * 1024 * 1024
SUPPORTED_EXACT_VERIFICATION = frozenset(
    {"exact_dimension", "feature_presence", "feature_count", "kernel_validity"}
)
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


@dataclass(frozen=True)
class ExactRequirementBinding:
    requirement_id: str
    feature_ids: tuple[str, ...]
    verification: str
    probe: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "feature_ids": list(self.feature_ids),
            "verification": self.verification,
            "probe": dict(self.probe),
        }


@dataclass(frozen=True)
class RequirementBindingSet:
    requirement_ir_sha256: str
    feature_ir_sha256: str
    bindings: tuple[ExactRequirementBinding, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = REQUIREMENT_BINDING_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "requirement_ir_sha256": self.requirement_ir_sha256,
            "feature_ir_sha256": self.feature_ir_sha256,
            "bindings": [binding.to_dict() for binding in self.bindings],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RequirementCheck:
    requirement_id: str
    strength: str
    verification: str
    satisfied: bool
    basis: str
    expected: Any
    actual: Any
    tolerance: float | None
    source_start: int
    source_end: int
    source_text: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExactRequirementVerification:
    satisfied_for_all_must: bool
    requirement_ir_sha256: str
    feature_ir_sha256: str
    binding_set_sha256: str
    checks: tuple[RequirementCheck, ...]
    errors: tuple[RequirementIssue, ...]
    claim_boundary: str = (
        "Only explicitly supported exact-kernel and feature-history checks are evaluated; "
        "simulation, material, manufacturing, safety, and human-review claims remain separate."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "satisfied_for_all_must": self.satisfied_for_all_must,
            "requirement_ir_sha256": self.requirement_ir_sha256,
            "feature_ir_sha256": self.feature_ir_sha256,
            "binding_set_sha256": self.binding_set_sha256,
            "checks": [check.to_dict() for check in self.checks],
            "errors": [error.to_dict() for error in self.errors],
            "claim_boundary": self.claim_boundary,
        }


class RequirementBindingError(ValueError):
    pass


def requirement_ir_sha256(document: RequirementIR) -> str:
    return hashlib.sha256(
        serialize_requirement_ir_json(document, pretty=False).encode("utf-8")
    ).hexdigest()


def feature_ir_sha256(program: FeatureProgram) -> str:
    return hashlib.sha256(
        serialize_feature_ir_json(program, pretty=False).encode("utf-8")
    ).hexdigest()


def serialize_binding_set_json(binding_set: RequirementBindingSet, *, pretty: bool = True) -> str:
    errors = validate_binding_set(binding_set)
    if errors:
        raise RequirementBindingError(
            "invalid requirement binding set:\n- "
            + "\n- ".join(f"{error.path}: {error.code}: {error.message}" for error in errors)
        )
    kwargs: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    if pretty:
        return json.dumps(binding_set.to_dict(), indent=2, **kwargs) + "\n"
    return json.dumps(binding_set.to_dict(), separators=(",", ":"), **kwargs)


def binding_set_sha256(binding_set: RequirementBindingSet) -> str:
    return hashlib.sha256(
        serialize_binding_set_json(binding_set, pretty=False).encode("utf-8")
    ).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_probe_error(value: Any, path: str) -> str | None:
    if value is None or isinstance(value, (bool, str)):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, bool):
            return None
        try:
            return None if math.isfinite(float(value)) else f"{path} contains a non-finite number"
        except (OverflowError, ValueError):
            return f"{path} contains a non-finite number"
    if isinstance(value, list):
        for index, item in enumerate(value):
            error = _strict_probe_error(item, f"{path}[{index}]")
            if error:
                return error
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"{path} contains a non-string key"
            error = _strict_probe_error(item, f"{path}.{key}")
            if error:
                return error
        return None
    return f"{path} contains unsupported type {type(value).__name__}"


def validate_binding_set(binding_set: RequirementBindingSet) -> tuple[RequirementIssue, ...]:
    errors: list[RequirementIssue] = []
    if binding_set.version != REQUIREMENT_BINDING_VERSION:
        errors.append(
            RequirementIssue(
                "unsupported_version",
                "$.version",
                f"expected {REQUIREMENT_BINDING_VERSION}",
            )
        )
    for name, value in (
        ("requirement_ir_sha256", binding_set.requirement_ir_sha256),
        ("feature_ir_sha256", binding_set.feature_ir_sha256),
    ):
        if not _valid_sha256(value):
            errors.append(RequirementIssue("invalid_hash", f"$.{name}", "must be lowercase SHA-256"))
    seen: set[str] = set()
    for index, binding in enumerate(binding_set.bindings):
        path = f"$.bindings[{index}]"
        if not isinstance(binding.requirement_id, str) or not binding.requirement_id:
            errors.append(
                RequirementIssue("invalid_requirement_id", f"{path}.requirement_id", "must be non-empty")
            )
        elif binding.requirement_id in seen:
            errors.append(
                RequirementIssue("duplicate_binding", f"{path}.requirement_id", binding.requirement_id)
            )
        seen.add(binding.requirement_id)
        if binding.verification not in SUPPORTED_EXACT_VERIFICATION:
            errors.append(
                RequirementIssue(
                    "unsupported_exact_verification",
                    f"{path}.verification",
                    binding.verification,
                )
            )
        if not isinstance(binding.probe, dict):
            errors.append(RequirementIssue("invalid_probe", f"{path}.probe", "must be an object"))
        else:
            probe_error = _strict_probe_error(binding.probe, f"{path}.probe")
            if probe_error:
                errors.append(RequirementIssue("invalid_probe", f"{path}.probe", probe_error))
            if not isinstance(binding.probe.get("kind"), str):
                errors.append(
                    RequirementIssue("invalid_probe", f"{path}.probe.kind", "must be a string")
                )
        if any(not isinstance(feature_id, str) or not feature_id for feature_id in binding.feature_ids):
            errors.append(
                RequirementIssue("invalid_feature_id", f"{path}.feature_ids", "must contain non-empty strings")
            )
    metadata_error = _strict_probe_error(binding_set.metadata, "$.metadata")
    if metadata_error:
        errors.append(RequirementIssue("invalid_metadata", "$.metadata", metadata_error))
    return tuple(errors)


def _dimension_check(
    requirement: Requirement,
    binding: ExactRequirementBinding,
    inspection: GeometryInspectionLike,
) -> RequirementCheck:
    if requirement.value is None or requirement.value.unit != "mm":
        raise RequirementBindingError(
            f"exact dimension requirement {requirement.id!r} requires a millimetre value"
        )
    if binding.probe.get("kind") != "output_extent":
        raise RequirementBindingError(
            f"exact dimension binding {requirement.id!r} requires probe kind 'output_extent'"
        )
    axis = binding.probe.get("axis")
    if axis not in AXIS_INDEX:
        raise RequirementBindingError(
            f"exact dimension binding {requirement.id!r} axis must be x, y, or z"
        )
    actual = inspection.extents_mm[AXIS_INDEX[axis]]
    expected = float(requirement.value.value)
    tolerance = 1e-6 if requirement.value.tolerance is None else float(requirement.value.tolerance)
    passed = math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)
    return RequirementCheck(
        requirement_id=requirement.id,
        strength=requirement.strength,
        verification=requirement.verification,
        satisfied=passed,
        basis="exact_kernel_output_extent",
        expected=expected,
        actual=actual,
        tolerance=tolerance,
        source_start=requirement.source_start,
        source_end=requirement.source_end,
        source_text=requirement.source_text,
        detail=f"output {axis}-extent is {actual:g} mm; expected {expected:g} ± {tolerance:g} mm",
    )


def _kernel_validity_check(
    requirement: Requirement,
    binding: ExactRequirementBinding,
    inspection: GeometryInspectionLike,
) -> RequirementCheck:
    if binding.probe.get("kind") != "brep_valid":
        raise RequirementBindingError(
            f"kernel validity binding {requirement.id!r} requires probe kind 'brep_valid'"
        )
    passed = bool(inspection.valid_brep)
    return RequirementCheck(
        requirement_id=requirement.id,
        strength=requirement.strength,
        verification=requirement.verification,
        satisfied=passed,
        basis="exact_kernel_brep_validation",
        expected=True,
        actual=passed,
        tolerance=None,
        source_start=requirement.source_start,
        source_end=requirement.source_end,
        source_text=requirement.source_text,
        detail="exact-kernel B-Rep validity check",
    )


def _feature_history_check(
    requirement: Requirement,
    binding: ExactRequirementBinding,
    program: FeatureProgram,
) -> RequirementCheck:
    feature_ids = {feature.id for feature in program.features}
    if binding.verification == "feature_presence":
        if binding.probe.get("kind") != "feature_presence":
            raise RequirementBindingError(
                f"feature presence binding {requirement.id!r} requires probe kind 'feature_presence'"
            )
        missing = sorted(set(binding.feature_ids) - feature_ids)
        passed = not missing and bool(binding.feature_ids)
        return RequirementCheck(
            requirement_id=requirement.id,
            strength=requirement.strength,
            verification=requirement.verification,
            satisfied=passed,
            basis="feature_history_presence",
            expected=list(binding.feature_ids),
            actual={"present": sorted(set(binding.feature_ids) - set(missing)), "missing": missing},
            tolerance=None,
            source_start=requirement.source_start,
            source_end=requirement.source_end,
            source_text=requirement.source_text,
            detail="required Feature IR ids are present" if passed else "one or more required Feature IR ids are missing",
        )

    if binding.probe.get("kind") != "feature_count":
        raise RequirementBindingError(
            f"feature count binding {requirement.id!r} requires probe kind 'feature_count'"
        )
    if requirement.value is None or requirement.value.unit != "unitless":
        raise RequirementBindingError(
            f"feature count requirement {requirement.id!r} requires a unitless value"
        )
    expected = int(requirement.value.value)
    if float(expected) != float(requirement.value.value) or expected < 0:
        raise RequirementBindingError(
            f"feature count requirement {requirement.id!r} must be a non-negative integer"
        )
    present = [feature_id for feature_id in binding.feature_ids if feature_id in feature_ids]
    actual = len(present)
    passed = actual == expected and actual == len(binding.feature_ids)
    return RequirementCheck(
        requirement_id=requirement.id,
        strength=requirement.strength,
        verification=requirement.verification,
        satisfied=passed,
        basis="feature_history_count",
        expected=expected,
        actual=actual,
        tolerance=0.0,
        source_start=requirement.source_start,
        source_end=requirement.source_end,
        source_text=requirement.source_text,
        detail=f"{actual} bound Feature IR ids are present; expected {expected}",
    )


def verify_exact_requirements(
    document: RequirementIR,
    program: FeatureProgram,
    inspection: GeometryInspectionLike,
    binding_set: RequirementBindingSet,
) -> ExactRequirementVerification:
    errors: list[RequirementIssue] = list(validate_binding_set(binding_set))
    validation = validate_requirement_ir(document)
    errors.extend(validation.errors)
    errors.extend(validation.blockers)

    requirement_hash = requirement_ir_sha256(document)
    feature_hash = feature_ir_sha256(program)
    if binding_set.requirement_ir_sha256 != requirement_hash:
        errors.append(
            RequirementIssue(
                "requirement_hash_mismatch",
                "$.requirement_ir_sha256",
                "binding set does not target the supplied Requirement IR",
            )
        )
    if binding_set.feature_ir_sha256 != feature_hash:
        errors.append(
            RequirementIssue(
                "feature_hash_mismatch",
                "$.feature_ir_sha256",
                "binding set does not target the supplied Feature IR",
            )
        )

    requirement_map = {requirement.id: requirement for requirement in document.requirements}
    binding_map = {binding.requirement_id: binding for binding in binding_set.bindings}
    checks: list[RequirementCheck] = []

    if not errors:
        for requirement in document.requirements:
            binding = binding_map.get(requirement.id)
            if binding is None:
                if requirement.strength == "must":
                    errors.append(
                        RequirementIssue(
                            "missing_must_binding",
                            "$.bindings",
                            requirement.id,
                        )
                    )
                continue
            if binding.verification != requirement.verification:
                errors.append(
                    RequirementIssue(
                        "verification_mismatch",
                        "$.bindings",
                        f"{requirement.id}: expected {requirement.verification!r}",
                    )
                )
                continue
            if requirement.verification not in SUPPORTED_EXACT_VERIFICATION:
                if requirement.strength == "must":
                    errors.append(
                        RequirementIssue(
                            "unsupported_must_verification",
                            "$.bindings",
                            requirement.id,
                        )
                    )
                continue
            try:
                if requirement.verification == "exact_dimension":
                    check = _dimension_check(requirement, binding, inspection)
                elif requirement.verification == "kernel_validity":
                    check = _kernel_validity_check(requirement, binding, inspection)
                else:
                    check = _feature_history_check(requirement, binding, program)
            except RequirementBindingError as exc:
                errors.append(
                    RequirementIssue(
                        "invalid_binding_contract",
                        "$.bindings",
                        str(exc),
                    )
                )
                continue
            checks.append(check)

        unknown_bindings = sorted(set(binding_map) - set(requirement_map))
        for requirement_id in unknown_bindings:
            errors.append(
                RequirementIssue(
                    "unknown_requirement",
                    "$.bindings",
                    requirement_id,
                )
            )

    failed_must = any(
        check.strength == "must" and not check.satisfied for check in checks
    )
    satisfied_for_all_must = not errors and not failed_must and all(
        requirement.strength != "must" or requirement.id in {check.requirement_id for check in checks}
        for requirement in document.requirements
    )
    return ExactRequirementVerification(
        satisfied_for_all_must=satisfied_for_all_must,
        requirement_ir_sha256=requirement_hash,
        feature_ir_sha256=feature_hash,
        binding_set_sha256=binding_set_sha256(binding_set),
        checks=tuple(checks),
        errors=tuple(errors),
    )


def _only_keys(value: dict[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    unexpected = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unexpected:
        raise RequirementBindingError(f"{path}: unsupported keys: {', '.join(unexpected)}")
    if missing:
        raise RequirementBindingError(f"{path}: missing keys: {', '.join(missing)}")


def parse_binding_set_json(text: str) -> RequirementBindingSet:
    if len(text.encode("utf-8")) > MAX_BINDING_JSON_BYTES:
        raise RequirementBindingError(f"binding input exceeds {MAX_BINDING_JSON_BYTES} bytes")
    try:
        raw = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise RequirementBindingError(
            f"invalid binding JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(raw, dict):
        raise RequirementBindingError("binding root must be an object")
    _only_keys(
        raw,
        {"version", "requirement_ir_sha256", "feature_ir_sha256", "bindings", "metadata"},
        {"version", "requirement_ir_sha256", "feature_ir_sha256", "bindings", "metadata"},
        "$",
    )
    if not isinstance(raw["bindings"], list):
        raise RequirementBindingError("$.bindings must be an array")
    if not isinstance(raw["metadata"], dict):
        raise RequirementBindingError("$.metadata must be an object")

    bindings: list[ExactRequirementBinding] = []
    for index, item in enumerate(raw["bindings"]):
        path = f"$.bindings[{index}]"
        if not isinstance(item, dict):
            raise RequirementBindingError(f"{path} must be an object")
        _only_keys(
            item,
            {"requirement_id", "feature_ids", "verification", "probe"},
            {"requirement_id", "feature_ids", "verification", "probe"},
            path,
        )
        if not isinstance(item["feature_ids"], list):
            raise RequirementBindingError(f"{path}.feature_ids must be an array")
        if not isinstance(item["probe"], dict):
            raise RequirementBindingError(f"{path}.probe must be an object")
        bindings.append(
            ExactRequirementBinding(
                requirement_id=item["requirement_id"],
                feature_ids=tuple(item["feature_ids"]),
                verification=item["verification"],
                probe=dict(item["probe"]),
            )
        )

    binding_set = RequirementBindingSet(
        requirement_ir_sha256=raw["requirement_ir_sha256"],
        feature_ir_sha256=raw["feature_ir_sha256"],
        bindings=tuple(bindings),
        metadata=dict(raw["metadata"]),
        version=raw["version"],
    )
    errors = validate_binding_set(binding_set)
    if errors:
        raise RequirementBindingError(
            "invalid requirement binding set:\n- "
            + "\n- ".join(f"{error.path}: {error.code}: {error.message}" for error in errors)
        )
    return binding_set
