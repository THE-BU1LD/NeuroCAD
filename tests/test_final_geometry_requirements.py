"""Final aggregate geometry evidence is separate from feature-history evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import pytest

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
    verify_unchanged_must_requirements,
)


@dataclass(frozen=True)
class Inspection:
    valid_brep: bool = True
    solid_count: int = 1
    volume_mm3: float = 24000.0
    extents_mm: tuple[float, float, float] = (40.0, 30.0, 20.0)


def contract(
    kind: str = "output_volume",
    value: RequirementValue | None = None,
) -> tuple[RequirementIR, FeatureProgram, RequirementBindingSet]:
    source = "Keep the declared final output geometry."
    program = FeatureProgram(
        title="final output contract",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
            Feature(id="unused_tool", kind="primitive_cylinder", parameters={"radius": 2.0, "height": 20.0}),
        ),
        outputs=("body",),
    )
    document = RequirementIR(
        source=source,
        requirements=(Requirement(
            id="aggregate", kind="topology", strength="must", target="all_outputs",
            source_start=0, source_end=len(source), source_text=source,
            provenance="explicit", verification="geometric_relation",
            value=value if value is not None else RequirementValue(24000.0, "mm3", 0.001),
        ),),
    )
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(ExactRequirementBinding("aggregate", program.outputs, "geometric_relation", {"kind": kind}),),
    )
    return document, program, bindings


def test_matching_final_aggregates_roundtrip_and_measure_output() -> None:
    for kind, value, basis in (
        ("output_volume", RequirementValue(24000.0, "mm3", 0.001), "exact_kernel_output_volume"),
        ("output_solid_count", RequirementValue(1.0, "unitless"), "exact_kernel_output_solid_count"),
    ):
        doc, program, bindings = contract(kind, value)
        assert parse_binding_set_json(serialize_binding_set_json(bindings)) == bindings
        result = verify_exact_requirements(doc, program, Inspection(), bindings)
        assert result.satisfied_for_all_must
        assert result.errors == ()
        assert result.checks[0].basis == basis
        assert result.checks[0].actual == value.value


@pytest.mark.parametrize(("kind", "value", "inspection"), [
    ("output_volume", RequirementValue(23500.0, "mm3", 0.001), Inspection()),
    ("output_solid_count", RequirementValue(2.0, "unitless"), Inspection()),
    ("output_solid_count", RequirementValue(1.0, "unitless"), Inspection(solid_count=2)),
])
def test_wrong_final_aggregate_fails_even_when_brep_valid(kind: str, value: RequirementValue, inspection: Inspection) -> None:
    doc, program, bindings = contract(kind, value)
    result = verify_exact_requirements(doc, program, inspection, bindings)
    assert result.errors == ()
    assert not result.satisfied_for_all_must
    assert not result.checks[0].satisfied


@pytest.mark.parametrize(("offset", "passed"), [(0.5, True), (0.500001, False), (-0.5, True), (-0.500001, False)])
def test_volume_uses_explicit_absolute_tolerance_only(offset: float, passed: bool) -> None:
    doc, program, bindings = contract(value=RequirementValue(24000.0, "mm3", 0.5))
    result = verify_exact_requirements(doc, program, Inspection(volume_mm3=24000.0 + offset), bindings)
    assert result.satisfied_for_all_must is passed


@pytest.mark.parametrize(("kind", "value"), [
    ("output_volume", RequirementValue(24000.0, "mm", 0.001)),
    ("output_volume", RequirementValue(24000.0, "mm3")),
    ("output_volume", RequirementValue(0.0, "mm3", 0.001)),
    ("output_volume", RequirementValue(-1.0, "mm3", 0.001)),
    ("output_solid_count", RequirementValue(1.5, "unitless")),
    ("output_solid_count", RequirementValue(0.0, "unitless")),
    ("output_solid_count", RequirementValue(-1.0, "unitless")),
    ("output_solid_count", RequirementValue(1.0, "mm3")),
    ("output_solid_count", RequirementValue(1.0, "unitless", 0.5)),
    ("unimplemented_hole_radius", RequirementValue(2.0, "mm", 0.001)),
])
def test_unsupported_aggregate_contract_is_structured_rejection(kind: str, value: RequirementValue) -> None:
    doc, program, bindings = contract(kind, value)
    result = verify_exact_requirements(doc, program, Inspection(), bindings)
    assert not result.satisfied_for_all_must
    assert any(error.code == "invalid_binding_contract" for error in result.errors)


@pytest.mark.parametrize(("field", "value"), [
    ("valid_brep", False), ("valid_brep", 1), ("valid_brep", "true"),
    ("solid_count", 0), ("solid_count", -1), ("solid_count", 1.0), ("solid_count", True),
    ("volume_mm3", 0.0), ("volume_mm3", -1.0), ("volume_mm3", True),
    ("volume_mm3", float("nan")), ("volume_mm3", float("inf")),
    ("volume_mm3", 10 ** 400), ("volume_mm3", "24000"),
    ("extents_mm", (40.0, 30.0)), ("extents_mm", (40.0, 30.0, 0.0)),
    ("extents_mm", (40.0, 30.0, True)), ("extents_mm", (40.0, 30.0, float("inf"))),
])
def test_invalid_final_evidence_cannot_satisfy_aggregate(field: str, value: Any) -> None:
    doc, program, bindings = contract()
    inspection = replace(Inspection(), **{field: value})
    result = verify_exact_requirements(doc, program, inspection, bindings)
    assert not result.satisfied_for_all_must
    assert any(error.code == "invalid_binding_contract" for error in result.errors)


@pytest.mark.parametrize("ids", [(), ("unused_tool",), ("body", "body"), ("body", "unused_tool"), ("missing",)])
def test_aggregate_scope_must_be_exact_output_set(ids: tuple[str, ...]) -> None:
    doc, program, bindings = contract()
    bindings = replace(bindings, bindings=(replace(bindings.bindings[0], feature_ids=ids),))
    result = verify_exact_requirements(doc, program, Inspection(), bindings)
    assert not result.satisfied_for_all_must
    assert any(error.code == "invalid_binding_contract" for error in result.errors)


def test_unknown_probe_keys_are_not_ignored() -> None:
    doc, program, bindings = contract()
    bindings = replace(bindings, bindings=(replace(bindings.bindings[0], probe={"kind": "output_volume", "relative_tolerance": 1.0}),))
    result = verify_exact_requirements(doc, program, Inspection(), bindings)
    assert not result.satisfied_for_all_must
    assert any(error.code == "invalid_binding_contract" for error in result.errors)


def test_large_integral_count_is_not_rounded_to_a_different_expected_value() -> None:
    expected = 2 ** 53 + 1
    doc, program, bindings = contract("output_solid_count", RequirementValue(expected, "unitless"))
    for actual in (expected - 1, expected):
        result = verify_exact_requirements(doc, program, Inspection(solid_count=actual), bindings)
        assert result.errors == ()
        assert result.satisfied_for_all_must is (actual == expected)
        assert result.checks[0].expected == expected


def test_historical_feature_presence_remains_history_only() -> None:
    doc, program, _ = contract()
    doc = replace(doc, requirements=(replace(doc.requirements[0], verification="feature_presence", value=None),))
    bindings = RequirementBindingSet(
        requirement_ir_sha256(doc), feature_ir_sha256(program),
        (ExactRequirementBinding("aggregate", ("unused_tool",), "feature_presence", {"kind": "feature_presence"}),),
    )
    result = verify_exact_requirements(doc, program, Inspection(), bindings)
    assert result.satisfied_for_all_must
    assert result.checks[0].basis == "feature_history_presence"


def test_unchanged_aggregate_requirement_cannot_be_weakened() -> None:
    doc, program, bindings = contract()
    changed = replace(doc, requirements=(replace(doc.requirements[0], value=RequirementValue(24000.0, "mm3", 1000.0)),))
    changed_bindings = replace(bindings, requirement_ir_sha256=requirement_ir_sha256(changed))
    assert verify_unchanged_must_requirements(doc, bindings, changed, changed_bindings)
    result = verify_exact_requirements(changed, program, Inspection(), bindings)
    assert any(error.code == "requirement_hash_mismatch" for error in result.errors)


@pytest.mark.parametrize("axis", [[], {}, 1, None])
def test_malformed_extent_axis_is_structured_rejection(axis: Any) -> None:
    doc, program, bindings = contract(value=RequirementValue(40.0, "mm", 0.001))
    doc = replace(doc, requirements=(replace(doc.requirements[0], verification="exact_dimension"),))
    bindings = replace(bindings, requirement_ir_sha256=requirement_ir_sha256(doc), bindings=(
        replace(bindings.bindings[0], verification="exact_dimension", probe={"kind": "output_extent", "axis": axis}),
    ))
    result = verify_exact_requirements(doc, program, Inspection(), bindings)
    assert not result.satisfied_for_all_must
    assert any(error.code == "invalid_binding_contract" for error in result.errors)
