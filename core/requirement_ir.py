"""Requirement-level provenance and coverage contracts for NeuroCAD.

Requirement IR is backend independent. It records what the user asked for and
how each requirement is expected to be verified. Geometry build success alone
never implies requirement satisfaction.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .json_io import strict_json_loads

REQUIREMENT_IR_VERSION = "neurocad-requirement-ir-v0alpha1"
MAX_SOURCE_CHARS = 8192
MAX_REQUIREMENTS = 2048
MAX_REQUIREMENT_JSON_BYTES = 2 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

REQUIREMENT_KINDS = frozenset(
    {
        "dimension",
        "count",
        "topology",
        "relation",
        "material",
        "manufacturing",
        "performance",
        "preference",
        "other",
    }
)
STRENGTHS = frozenset({"must", "should", "preference"})
PROVENANCE = frozenset({"explicit", "user_confirmed", "deterministic_policy", "unresolved"})
VERIFICATION_METHODS = frozenset(
    {
        "exact_dimension",
        "feature_presence",
        "feature_count",
        "geometric_relation",
        "kernel_validity",
        "analytical_model",
        "empirical_profile",
        "simulation",
        "human_review",
        "unsupported",
    }
)


@dataclass(frozen=True)
class RequirementValue:
    value: float
    unit: str
    tolerance: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Requirement:
    id: str
    kind: str
    strength: str
    target: str
    source_start: int
    source_end: int
    source_text: str
    provenance: str
    verification: str
    value: RequirementValue | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "strength": self.strength,
            "target": self.target,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "source_text": self.source_text,
            "provenance": self.provenance,
            "verification": self.verification,
            "value": None if self.value is None else self.value.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class RequirementIR:
    source: str
    requirements: tuple[Requirement, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = REQUIREMENT_IR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "requirements": [requirement.to_dict() for requirement in self.requirements],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RequirementIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RequirementValidationReport:
    structurally_valid: bool
    build_ready: bool
    errors: tuple[RequirementIssue, ...]
    blockers: tuple[RequirementIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "structurally_valid": self.structurally_valid,
            "build_ready": self.build_ready,
            "errors": [issue.to_dict() for issue in self.errors],
            "blockers": [issue.to_dict() for issue in self.blockers],
        }


@dataclass(frozen=True)
class RequirementBinding:
    requirement_id: str
    feature_ids: tuple[str, ...]
    verification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "feature_ids": list(self.feature_ids),
            "verification": self.verification,
        }


@dataclass(frozen=True)
class RequirementCoverageReport:
    complete_for_must: bool
    covered: tuple[str, ...]
    missing_must: tuple[str, ...]
    missing_should: tuple[str, ...]
    invalid_bindings: tuple[RequirementIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete_for_must": self.complete_for_must,
            "covered": list(self.covered),
            "missing_must": list(self.missing_must),
            "missing_should": list(self.missing_should),
            "invalid_bindings": [issue.to_dict() for issue in self.invalid_bindings],
        }


class RequirementIRParseError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("invalid NeuroCAD requirement IR:\n- " + "\n- ".join(errors))


def _finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _strict_json_error(value: Any, path: str) -> str | None:
    if value is None or isinstance(value, (bool, str)):
        return None
    if isinstance(value, (int, float)):
        return None if _finite(value) else f"{path} contains a non-finite number"
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            error = _strict_json_error(item, f"{path}[{index}]")
            if error:
                return error
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"{path} contains a non-string key"
            error = _strict_json_error(item, f"{path}.{key}")
            if error:
                return error
        return None
    return f"{path} contains unsupported type {type(value).__name__}"


def validate_requirement_ir(document: RequirementIR) -> RequirementValidationReport:
    errors: list[RequirementIssue] = []
    blockers: list[RequirementIssue] = []
    if document.version != REQUIREMENT_IR_VERSION:
        errors.append(
            RequirementIssue("unsupported_version", "$.version", f"expected {REQUIREMENT_IR_VERSION}")
        )
    if not isinstance(document.source, str) or len(document.source) > MAX_SOURCE_CHARS:
        errors.append(
            RequirementIssue("invalid_source", "$.source", f"source must be a string of at most {MAX_SOURCE_CHARS} characters")
        )
    if len(document.requirements) > MAX_REQUIREMENTS:
        errors.append(
            RequirementIssue("resource_limit", "$.requirements", f"at most {MAX_REQUIREMENTS} requirements are supported")
        )
    if not isinstance(document.metadata, dict):
        errors.append(RequirementIssue("invalid_metadata", "$.metadata", "metadata must be an object"))
    else:
        metadata_error = _strict_json_error(document.metadata, "$.metadata")
        if metadata_error:
            errors.append(RequirementIssue("invalid_metadata", "$.metadata", metadata_error))

    ids: set[str] = set()
    for index, requirement in enumerate(document.requirements):
        path = f"$.requirements[{index}]"
        if not isinstance(requirement.id, str) or ID_RE.fullmatch(requirement.id) is None:
            errors.append(RequirementIssue("invalid_id", f"{path}.id", "use letters, digits, underscore or hyphen"))
        elif requirement.id in ids:
            errors.append(RequirementIssue("duplicate_id", f"{path}.id", requirement.id))
        ids.add(requirement.id)
        if requirement.kind not in REQUIREMENT_KINDS:
            errors.append(RequirementIssue("invalid_kind", f"{path}.kind", str(requirement.kind)))
        if requirement.strength not in STRENGTHS:
            errors.append(RequirementIssue("invalid_strength", f"{path}.strength", str(requirement.strength)))
        if requirement.provenance not in PROVENANCE:
            errors.append(RequirementIssue("invalid_provenance", f"{path}.provenance", str(requirement.provenance)))
        if requirement.verification not in VERIFICATION_METHODS:
            errors.append(RequirementIssue("invalid_verification", f"{path}.verification", str(requirement.verification)))
        if not isinstance(requirement.target, str) or not requirement.target.strip() or len(requirement.target) > 256:
            errors.append(RequirementIssue("invalid_target", f"{path}.target", "target must contain 1 to 256 characters"))
        if (
            isinstance(requirement.source_start, bool)
            or not isinstance(requirement.source_start, int)
            or isinstance(requirement.source_end, bool)
            or not isinstance(requirement.source_end, int)
            or not 0 <= requirement.source_start < requirement.source_end <= len(document.source)
        ):
            errors.append(RequirementIssue("invalid_source_span", path, "source span is outside the source text"))
        elif document.source[requirement.source_start:requirement.source_end] != requirement.source_text:
            errors.append(RequirementIssue("source_span_mismatch", f"{path}.source_text", "does not match the recorded source span"))

        if requirement.value is not None:
            value = requirement.value
            if not _finite(value.value):
                errors.append(RequirementIssue("invalid_value", f"{path}.value.value", "must be finite"))
            if not isinstance(value.unit, str) or not value.unit.strip() or len(value.unit) > 32:
                errors.append(RequirementIssue("invalid_unit", f"{path}.value.unit", "unit must contain 1 to 32 characters"))
            if value.tolerance is not None and (not _finite(value.tolerance) or float(value.tolerance) < 0):
                errors.append(RequirementIssue("invalid_tolerance", f"{path}.value.tolerance", "must be finite and non-negative"))

        if requirement.strength == "must" and requirement.provenance == "unresolved":
            blockers.append(
                RequirementIssue(
                    "unresolved_must",
                    path,
                    f"must-level requirement {requirement.id!r} requires clarification or an explicit decision",
                )
            )
        if requirement.strength == "must" and requirement.verification == "unsupported":
            blockers.append(
                RequirementIssue(
                    "unsupported_must",
                    path,
                    f"must-level requirement {requirement.id!r} has no supported verification method",
                )
            )

    structurally_valid = not errors
    return RequirementValidationReport(
        structurally_valid=structurally_valid,
        build_ready=structurally_valid and not blockers,
        errors=tuple(errors),
        blockers=tuple(blockers),
    )


def requirement_coverage(
    document: RequirementIR,
    bindings: tuple[RequirementBinding, ...],
    *,
    known_feature_ids: tuple[str, ...] = (),
) -> RequirementCoverageReport:
    validation = validate_requirement_ir(document)
    invalid: list[RequirementIssue] = list(validation.errors)
    requirement_map = {item.id: item for item in document.requirements}
    known_features = set(known_feature_ids)
    bound: set[str] = set()

    seen_requirements: set[str] = set()
    for index, binding in enumerate(bindings):
        path = f"$.bindings[{index}]"
        requirement = requirement_map.get(binding.requirement_id)
        if requirement is None:
            invalid.append(
                RequirementIssue("unknown_requirement", f"{path}.requirement_id", binding.requirement_id)
            )
            continue
        if binding.requirement_id in seen_requirements:
            invalid.append(
                RequirementIssue("duplicate_binding", f"{path}.requirement_id", binding.requirement_id)
            )
            continue
        seen_requirements.add(binding.requirement_id)
        if binding.verification != requirement.verification:
            invalid.append(
                RequirementIssue(
                    "verification_mismatch",
                    f"{path}.verification",
                    f"expected {requirement.verification!r}",
                )
            )
            continue
        if not binding.feature_ids and requirement.verification not in {
            "analytical_model",
            "empirical_profile",
            "simulation",
            "human_review",
            "unsupported",
        }:
            invalid.append(
                RequirementIssue("missing_feature_binding", f"{path}.feature_ids", "geometric verification requires feature ids")
            )
            continue
        missing_features = sorted(set(binding.feature_ids) - known_features) if known_features else []
        if missing_features:
            invalid.append(
                RequirementIssue(
                    "unknown_feature",
                    f"{path}.feature_ids",
                    "unknown feature ids: " + ", ".join(missing_features),
                )
            )
            continue
        bound.add(binding.requirement_id)

    missing_must = tuple(
        item.id
        for item in document.requirements
        if item.strength == "must" and item.id not in bound
    )
    missing_should = tuple(
        item.id
        for item in document.requirements
        if item.strength == "should" and item.id not in bound
    )
    complete_for_must = (
        validation.build_ready
        and not invalid
        and not missing_must
    )
    return RequirementCoverageReport(
        complete_for_must=complete_for_must,
        covered=tuple(sorted(bound)),
        missing_must=missing_must,
        missing_should=missing_should,
        invalid_bindings=tuple(invalid),
    )



def serialize_requirement_ir_json(document: RequirementIR, *, pretty: bool = True) -> str:
    report = validate_requirement_ir(document)
    if not report.structurally_valid:
        raise RequirementIRParseError(
            [f"{issue.path}: {issue.code}: {issue.message}" for issue in report.errors]
        )
    kwargs: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    if pretty:
        return json.dumps(document.to_dict(), indent=2, **kwargs) + "\n"
    return json.dumps(document.to_dict(), separators=(",", ":"), **kwargs)


def _only_keys(value: dict[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    unexpected = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unexpected:
        raise RequirementIRParseError([f"{path}: unsupported keys: {', '.join(unexpected)}"])
    if missing:
        raise RequirementIRParseError([f"{path}: missing keys: {', '.join(missing)}"])


def requirement_ir_from_dict(raw: dict[str, Any]) -> RequirementIR:
    _only_keys(
        raw,
        {"version", "source", "requirements", "metadata"},
        {"version", "source", "requirements", "metadata"},
        "$",
    )
    if not isinstance(raw["requirements"], list):
        raise RequirementIRParseError(["$.requirements: must be an array"])
    if not isinstance(raw["metadata"], dict):
        raise RequirementIRParseError(["$.metadata: must be an object"])

    requirements: list[Requirement] = []
    for index, item in enumerate(raw["requirements"]):
        path = f"$.requirements[{index}]"
        if not isinstance(item, dict):
            raise RequirementIRParseError([f"{path}: must be an object"])
        _only_keys(
            item,
            {
                "id",
                "kind",
                "strength",
                "target",
                "source_start",
                "source_end",
                "source_text",
                "provenance",
                "verification",
                "value",
                "notes",
            },
            {
                "id",
                "kind",
                "strength",
                "target",
                "source_start",
                "source_end",
                "source_text",
                "provenance",
                "verification",
                "value",
                "notes",
            },
            path,
        )
        raw_value = item["value"]
        value = None
        if raw_value is not None:
            if not isinstance(raw_value, dict):
                raise RequirementIRParseError([f"{path}.value: must be null or an object"])
            _only_keys(
                raw_value,
                {"value", "unit", "tolerance"},
                {"value", "unit", "tolerance"},
                f"{path}.value",
            )
            value = RequirementValue(
                value=raw_value["value"],
                unit=raw_value["unit"],
                tolerance=raw_value["tolerance"],
            )
        notes = item["notes"]
        if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
            raise RequirementIRParseError([f"{path}.notes: must be an array of strings"])
        requirements.append(
            Requirement(
                id=item["id"],
                kind=item["kind"],
                strength=item["strength"],
                target=item["target"],
                source_start=item["source_start"],
                source_end=item["source_end"],
                source_text=item["source_text"],
                provenance=item["provenance"],
                verification=item["verification"],
                value=value,
                notes=tuple(notes),
            )
        )

    document = RequirementIR(
        source=raw["source"],
        requirements=tuple(requirements),
        metadata=dict(raw["metadata"]),
        version=raw["version"],
    )
    report = validate_requirement_ir(document)
    if not report.structurally_valid:
        raise RequirementIRParseError(
            [f"{issue.path}: {issue.code}: {issue.message}" for issue in report.errors]
        )
    return document


def parse_requirement_ir_json(text: str) -> RequirementIR:
    if len(text.encode("utf-8")) > MAX_REQUIREMENT_JSON_BYTES:
        raise RequirementIRParseError([f"$: input exceeds {MAX_REQUIREMENT_JSON_BYTES} bytes"])
    try:
        raw = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise RequirementIRParseError(
            [f"line {exc.lineno}, column {exc.colno}: {exc.msg}"]
        ) from exc
    if not isinstance(raw, dict):
        raise RequirementIRParseError(["$: root must be an object"])
    return requirement_ir_from_dict(raw)
