from __future__ import annotations

from dataclasses import dataclass

from core.feature_ir import Feature, FeatureProgram
from core.requirement_ir import Requirement, RequirementIR, RequirementValue
from core.requirement_verification import (
    ExactRequirementBinding,
    RequirementBindingSet,
    feature_ir_sha256,
    parse_binding_set_json,
    requirement_ir_sha256,
    serialize_binding_set_json,
    verify_exact_requirements,
)

SOURCE = "Make the box exactly 40 mm wide and keep the body feature."


@dataclass(frozen=True)
class FakeInspection:
    valid_brep: bool
    solid_count: int
    volume_mm3: float
    extents_mm: tuple[float, float, float]


def _program() -> FeatureProgram:
    return FeatureProgram(
        title="bound box",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        ),
        outputs=("body",),
    )


def _requirement(
    requirement_id: str,
    phrase: str,
    *,
    verification: str,
    value: RequirementValue | None = None,
    strength: str = "must",
) -> Requirement:
    start = SOURCE.index(phrase)
    return Requirement(
        id=requirement_id,
        kind="dimension" if verification == "exact_dimension" else "other",
        strength=strength,
        target=requirement_id,
        source_start=start,
        source_end=start + len(phrase),
        source_text=phrase,
        provenance="explicit",
        verification=verification,
        value=value,
    )


def _documents() -> tuple[RequirementIR, FeatureProgram, RequirementBindingSet]:
    program = _program()
    requirements = RequirementIR(
        source=SOURCE,
        requirements=(
            _requirement(
                "width",
                "40 mm wide",
                verification="exact_dimension",
                value=RequirementValue(40.0, "mm", 0.001),
            ),
            _requirement(
                "body_required",
                "body feature",
                verification="feature_presence",
            ),
        ),
    )
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(requirements),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(
            ExactRequirementBinding(
                "width",
                ("body",),
                "exact_dimension",
                {"kind": "output_extent", "axis": "x"},
            ),
            ExactRequirementBinding(
                "body_required",
                ("body",),
                "feature_presence",
                {"kind": "feature_presence"},
            ),
        ),
    )
    return requirements, program, bindings


def test_binding_set_json_roundtrip_is_deterministic() -> None:
    _, _, bindings = _documents()
    encoded = serialize_binding_set_json(bindings)
    decoded = parse_binding_set_json(encoded)
    assert decoded == bindings
    assert serialize_binding_set_json(decoded) == encoded


def test_exact_requirement_verification_passes_bound_musts() -> None:
    requirements, program, bindings = _documents()
    result = verify_exact_requirements(
        requirements,
        program,
        FakeInspection(True, 1, 24000.0, (40.0, 30.0, 20.0)),
        bindings,
    )
    assert result.satisfied_for_all_must
    assert result.errors == ()
    assert {check.requirement_id for check in result.checks} == {"width", "body_required"}
    assert all(check.satisfied for check in result.checks)


def test_valid_brep_still_fails_when_must_dimension_is_wrong() -> None:
    requirements, program, bindings = _documents()
    result = verify_exact_requirements(
        requirements,
        program,
        FakeInspection(True, 1, 24600.0, (41.0, 30.0, 20.0)),
        bindings,
    )
    assert not result.satisfied_for_all_must
    width = next(check for check in result.checks if check.requirement_id == "width")
    assert not width.satisfied
    assert width.actual == 41.0
    assert width.expected == 40.0


def test_missing_must_binding_fails_closed() -> None:
    requirements, program, bindings = _documents()
    incomplete = RequirementBindingSet(
        requirement_ir_sha256=bindings.requirement_ir_sha256,
        feature_ir_sha256=bindings.feature_ir_sha256,
        bindings=(bindings.bindings[0],),
    )
    result = verify_exact_requirements(
        requirements,
        program,
        FakeInspection(True, 1, 24000.0, (40.0, 30.0, 20.0)),
        incomplete,
    )
    assert not result.satisfied_for_all_must
    assert any(error.code == "missing_must_binding" for error in result.errors)


def test_binding_hash_mismatch_fails_before_claim_checks() -> None:
    requirements, program, bindings = _documents()
    mismatched = RequirementBindingSet(
        requirement_ir_sha256="0" * 64,
        feature_ir_sha256=bindings.feature_ir_sha256,
        bindings=bindings.bindings,
    )
    result = verify_exact_requirements(
        requirements,
        program,
        FakeInspection(True, 1, 24000.0, (40.0, 30.0, 20.0)),
        mismatched,
    )
    assert not result.satisfied_for_all_must
    assert any(error.code == "requirement_hash_mismatch" for error in result.errors)


def test_feature_count_uses_explicit_feature_history_only() -> None:
    program = FeatureProgram(
        title="two features",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
            Feature(id="tool", kind="primitive_cylinder", parameters={"radius": 2.0, "height": 20.0}),
        ),
        outputs=("body",),
    )
    phrase = "body feature"
    requirement = _requirement(
        "feature_count",
        phrase,
        verification="feature_count",
        value=RequirementValue(2.0, "unitless"),
    )
    document = RequirementIR(source=SOURCE, requirements=(requirement,))
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(
            ExactRequirementBinding(
                "feature_count",
                ("body", "tool"),
                "feature_count",
                {"kind": "feature_count"},
            ),
        ),
    )
    result = verify_exact_requirements(
        document,
        program,
        FakeInspection(True, 1, 24000.0, (40.0, 30.0, 20.0)),
        bindings,
    )
    assert result.satisfied_for_all_must
    assert result.checks[0].basis == "feature_history_count"


def test_unbound_should_does_not_block_must_acceptance() -> None:
    requirements, program, bindings = _documents()
    should = _requirement(
        "nice_to_have",
        "body feature",
        verification="feature_presence",
        strength="should",
    )
    document = RequirementIR(
        source=SOURCE,
        requirements=(*requirements.requirements, should),
    )
    rebound = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=bindings.feature_ir_sha256,
        bindings=bindings.bindings,
    )
    result = verify_exact_requirements(
        document,
        program,
        FakeInspection(True, 1, 24000.0, (40.0, 30.0, 20.0)),
        rebound,
    )
    assert result.satisfied_for_all_must
