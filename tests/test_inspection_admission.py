"""Counterexamples for typed final-measurement admission; no CAD engine required."""
from dataclasses import replace

import pytest

from core.feature_ir import Feature, FeatureIRParseError, FeatureProgram
from core.requirement_ir import Requirement, RequirementIR, RequirementValue
from core.requirement_verification import (
    ExactRequirementBinding,
    RequirementBindingSet,
    feature_ir_sha256,
    requirement_ir_sha256,
    verify_exact_requirements,
)


class Inspection:
    valid_brep = True
    solid_count = 1
    volume_mm3 = 1.0
    extents_mm = (1.0, 1.0, 1.0)


def verify(inspection, *, method="exact_dimension", probe=None, measurements=None, program=None, value=None):
    program = program or FeatureProgram(title="unit box", parameters=(), features=(
        Feature(id="body", kind="primitive_box", parameters={"size": [1, 1, 1]}),), outputs=("body",))
    requirement = Requirement("r1", "dimension" if method == "exact_dimension" else "topology",
                              "must", "body", 0, 3, "box", "explicit", method,
                              (value or RequirementValue(1, "mm", 0)) if method == "exact_dimension" else None)
    document = RequirementIR("box", (requirement,))
    binding = ExactRequirementBinding("r1", ("body",), method, probe or {"kind": "output_extent", "axis": "x"})
    bindings = RequirementBindingSet(requirement_ir_sha256(document), feature_ir_sha256(program), (binding,))
    return verify_exact_requirements(document, program, inspection, bindings, exact_measurements_mm=measurements)


@pytest.mark.parametrize("bad", [True, "1", None, float("nan"), float("inf"), -1, 10**400])
@pytest.mark.parametrize("kind", ["output_extent", "planar_wall_thickness"])
def test_invalid_measurement_is_structured_rejection(kind, bad):
    inspection = Inspection()
    inspection.extents_mm = (bad, 1, 1)
    probe = {"kind": kind, "axis": "x"} if kind == "output_extent" else {"kind": kind}
    result = verify(inspection, probe=probe, measurements={"r1": bad})
    assert not result.satisfied_for_all_must
    assert any(issue.code == "invalid_binding_contract" for issue in result.errors)


@pytest.mark.parametrize("bad", [None, (), (1,), "111", (1, 1, 1, 1)])
def test_extent_vector_requires_three_numeric_coordinates(bad):
    inspection = Inspection()
    inspection.extents_mm = bad
    result = verify(inspection)
    assert not result.satisfied_for_all_must
    assert result.errors


@pytest.mark.parametrize("bad", ["false", "true", 1, 0, None, [], {}])
def test_kernel_validity_is_not_python_truthiness(bad):
    inspection = Inspection()
    inspection.valid_brep = bad
    result = verify(inspection, method="kernel_validity", probe={"kind": "brep_valid"})
    assert not result.satisfied_for_all_must
    assert result.errors


@pytest.mark.parametrize("valid", [True, False])
def test_boolean_kernel_control(valid):
    inspection = Inspection()
    inspection.valid_brep = valid
    result = verify(inspection, method="kernel_validity", probe={"kind": "brep_valid"})
    assert result.satisfied_for_all_must is valid
    assert not result.errors


def test_numeric_control():
    assert verify(Inspection()).satisfied_for_all_must


@pytest.mark.parametrize("mutation", ["negative_size", "unknown_kind", "missing_output", "duplicate_id"])
def test_invalid_feature_program_cannot_be_verified(mutation):
    body = Feature(id="body", kind="primitive_box", parameters={"size": [1, 1, 1]})
    program = FeatureProgram(title="unit box", parameters=(), features=(body,), outputs=("body",))
    if mutation == "negative_size":
        program = replace(program, features=(replace(body, parameters={"size": [-1, 1, 1]}),))
    elif mutation == "unknown_kind":
        program = replace(program, features=(replace(body, kind="not_a_feature"),))
    elif mutation == "missing_output":
        program = replace(program, outputs=("absent",))
    else:
        program = replace(program, features=(body, body))
    # Serialization already validates Feature IR. This is an existing rejection
    # control, not a new defect or a claimed production repair.
    with pytest.raises(FeatureIRParseError):
        verify(Inspection(), program=program)


@pytest.mark.parametrize("field", ["expected", "actual", "tolerance"])
def test_lossy_integer_dimension_is_not_silently_rounded(field):
    inspection = Inspection()
    expected, actual, tolerance = 2**53, 2**53, 0
    if field == "expected":
        expected += 1
    elif field == "actual":
        actual += 1
    else:
        tolerance = 2**53 + 1
    inspection.extents_mm = (actual, 1, 1)
    result = verify(inspection, value=RequirementValue(expected, "mm", tolerance))
    assert not result.satisfied_for_all_must
    assert any(issue.code == "invalid_binding_contract" for issue in result.errors)


def test_exactly_representable_large_integer_dimension_control():
    inspection = Inspection()
    inspection.extents_mm = (2**54, 1, 1)
    assert verify(inspection, value=RequirementValue(2**54, "mm", 0)).satisfied_for_all_must
