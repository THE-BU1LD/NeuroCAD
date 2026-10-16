"""Native aggregate predicates, with explicit counterexamples to hole inference.

The references below are authored analytic engineering fixtures. They establish
neither arbitrary hole recognition nor independent research confirmation.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

pytest.importorskip("build123d")

from core.exact_build123d import Build123dBackend, Build123dCompileError
from core.feature_ir import Feature, FeatureProgram
from core.requirement_ir import Requirement, RequirementIR, RequirementValue
from core.requirement_verification import (
    ExactRequirementBinding,
    RequirementBindingSet,
    feature_ir_sha256,
    requirement_ir_sha256,
    verify_exact_requirements,
)

WIDTH_MM = 40.0
DEPTH_MM = 30.0
HEIGHT_MM = 8.0
RADIUS_MM = 3.0
BOX_VOLUME_MM3 = WIDTH_MM * DEPTH_MM * HEIGHT_MM
# Integral of the constant circular cross-section through the box thickness.
BORE_VOLUME_MM3 = math.pi * RADIUS_MM**2 * HEIGHT_MM
PERFORATED_VOLUME_MM3 = BOX_VOLUME_MM3 - BORE_VOLUME_MM3
# Fixed absolute tolerance for these millimetre-scale analytic fixtures only.
VOLUME_TOLERANCE_MM3 = 1e-6


def _program(*features: Feature, output: str) -> FeatureProgram:
    return FeatureProgram(
        title="final geometry aggregate native fixture",
        parameters=(),
        features=features,
        outputs=(output,),
    )


def _bore_program(mode: str) -> FeatureProgram:
    body = Feature(
        id="body",
        kind="primitive_box",
        parameters={"size": [WIDTH_MM, DEPTH_MM, HEIGHT_MM]},
    )
    tool = Feature(
        id="tool",
        kind="primitive_cylinder",
        parameters={"radius": RADIUS_MM, "height": HEIGHT_MM},
    )
    perforated = Feature(
        id="perforated", kind="boolean_cut", inputs=("body", "tool"),
    )
    if mode == "through":
        return _program(body, tool, perforated, output="perforated")
    if mode == "unused":
        return _program(body, tool, output="body")
    if mode == "filled":
        filled = Feature(
            id="filled", kind="boolean_union", inputs=("perforated", "tool"),
        )
        return _program(body, tool, perforated, filled, output="filled")
    if mode == "blind":
        # The box spans z=-4..4; this cutter spans z=0..4, leaving a floor.
        profile = Feature(
            id="tool_profile",
            kind="sketch",
            parameters={
                "plane": "XY",
                "entities": [{"kind": "circle", "radius": RADIUS_MM}],
                "constraints": [],
            },
        )
        blind_tool = Feature(
            id="tool",
            kind="extrude",
            inputs=("tool_profile",),
            parameters={"distance": HEIGHT_MM / 2, "operation": "new"},
        )
        return _program(body, profile, blind_tool, perforated, output="perforated")
    raise AssertionError(mode)


def _aggregate_contract(
    program: FeatureProgram,
    *,
    solid_count: int = 1,
    volume_mm3: float = PERFORATED_VOLUME_MM3,
    keep_tool_history: bool = False,
) -> tuple[RequirementIR, RequirementBindingSet]:
    source = "Keep the requested solid count and material volume. Keep the tool history."

    def requirement(
        requirement_id: str,
        phrase: str,
        value: RequirementValue | None,
        verification: str = "geometric_relation",
    ) -> Requirement:
        start = source.index(phrase)
        return Requirement(
            id=requirement_id,
            kind="count" if requirement_id == "solid_count" else "other",
            strength="must",
            target="final_output" if verification == "geometric_relation" else "tool",
            source_start=start,
            source_end=start + len(phrase),
            source_text=phrase,
            provenance="explicit",
            verification=verification,
            value=value,
        )

    requirements = [
        requirement("solid_count", "solid count", RequirementValue(solid_count, "unitless")),
        requirement(
            "material_volume",
            "material volume",
            RequirementValue(volume_mm3, "mm3", VOLUME_TOLERANCE_MM3),
        ),
    ]
    bindings = [
        ExactRequirementBinding(
            "solid_count", program.outputs, "geometric_relation", {"kind": "output_solid_count"},
        ),
        ExactRequirementBinding(
            "material_volume", program.outputs, "geometric_relation", {"kind": "output_volume"},
        ),
    ]
    if keep_tool_history:
        requirements.append(requirement("tool_history", "tool history", None, "feature_presence"))
        bindings.append(
            ExactRequirementBinding(
                "tool_history", ("tool",), "feature_presence", {"kind": "feature_presence"},
            )
        )
    document = RequirementIR(source=source, requirements=tuple(requirements))
    return document, RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=tuple(bindings),
    )


def test_final_geometry_through_bore_matches_analytic_volume_after_step_roundtrip(
    tmp_path: Path,
) -> None:
    program = _bore_program("through")
    document, bindings = _aggregate_contract(program, keep_tool_history=True)
    receipt = Build123dBackend().export_verified_step(
        program,
        tmp_path / "accepted-through-bore",
        requirements=document,
        binding_set=bindings,
    )

    assert receipt.requirements_satisfied is True
    assert receipt.roundtrip_inspection is not None
    assert receipt.roundtrip_inspection.solid_count == 1
    assert receipt.roundtrip_inspection.volume_mm3 == pytest.approx(
        PERFORATED_VOLUME_MM3, rel=0.0, abs=VOLUME_TOLERANCE_MM3,
    )


def test_wrong_final_volume_cannot_publish_a_verified_step_bundle(tmp_path: Path) -> None:
    program = _bore_program("unused")
    document, bindings = _aggregate_contract(program, keep_tool_history=True)
    destination = tmp_path / "must-not-publish"
    with pytest.raises(Build123dCompileError, match="must-level requirement verification failed"):
        Build123dBackend().export_verified_step(
            program, destination, requirements=document, binding_set=bindings,
        )
    assert not destination.exists()


@pytest.mark.parametrize("mode", ["unused", "filled", "blind"])
def test_final_volume_rejects_missing_or_incomplete_bore_despite_tool_history(mode: str) -> None:
    program = _bore_program(mode)
    inspection = Build123dBackend().build_receipt(program).inspection
    document, bindings = _aggregate_contract(program, keep_tool_history=True)
    result = verify_exact_requirements(document, program, inspection, bindings)
    checks = {check.requirement_id: check for check in result.checks}

    expected_actual_volume = (
        BOX_VOLUME_MM3 - BORE_VOLUME_MM3 / 2 if mode == "blind" else BOX_VOLUME_MM3
    )
    assert inspection.volume_mm3 == pytest.approx(
        expected_actual_volume, rel=0.0, abs=VOLUME_TOLERANCE_MM3,
    )
    assert result.errors == ()
    assert not result.satisfied_for_all_must
    assert checks["solid_count"].satisfied
    assert checks["tool_history"].satisfied
    assert checks["tool_history"].basis == "feature_history_presence"
    assert not checks["material_volume"].satisfied


def test_final_solid_count_distinguishes_two_disconnected_solids() -> None:
    profile = Feature(
        id="profile",
        kind="sketch",
        parameters={
            "plane": "XY",
            "entities": [
                {"kind": "rectangle", "width": 10.0, "height": 10.0, "center": [x, 0.0]}
                for x in (-15.0, 15.0)
            ],
            "constraints": [],
        },
    )
    extrusion = Feature(
        id="two_solids",
        kind="extrude",
        inputs=("profile",),
        parameters={"distance": HEIGHT_MM, "operation": "new"},
    )
    program = _program(profile, extrusion, output="two_solids")
    inspection = Build123dBackend().build_receipt(program).inspection
    expected_volume = 2 * 10.0 * 10.0 * HEIGHT_MM
    assert inspection.solid_count == 2
    assert inspection.volume_mm3 == pytest.approx(
        expected_volume, rel=0.0, abs=VOLUME_TOLERANCE_MM3,
    )

    for expected_count in (1, 2):
        document, bindings = _aggregate_contract(
            program, solid_count=expected_count, volume_mm3=expected_volume,
        )
        result = verify_exact_requirements(document, program, inspection, bindings)
        assert result.errors == ()
        assert result.satisfied_for_all_must is (expected_count == 2)


def _shifted_bore_program(center_x_mm: float) -> FeatureProgram:
    profile = Feature(
        id="profile",
        kind="sketch",
        parameters={
            "plane": "XY",
            "entities": [
                {"kind": "rectangle", "width": WIDTH_MM, "height": DEPTH_MM},
                {
                    "kind": "circle",
                    "radius": RADIUS_MM,
                    "center": [center_x_mm, 0.0],
                    "operation": "subtract",
                },
            ],
            "constraints": [],
        },
    )
    extrusion = Feature(
        id="plate",
        kind="extrude",
        inputs=("profile",),
        parameters={"distance": HEIGHT_MM, "operation": "new"},
    )
    return _program(profile, extrusion, output="plate")


def test_equal_volume_shifted_bore_passes_aggregate_checks_without_proving_hole_location() -> None:
    backend = Build123dBackend()
    distances_from_nominal_axis = []
    for center_x_mm in (0.0, 8.0):
        program = _shifted_bore_program(center_x_mm)
        shape = backend.compile(program)["plate"]
        inspection = backend.inspect(shape)
        document, bindings = _aggregate_contract(program)
        result = verify_exact_requirements(document, program, inspection, bindings)

        assert result.errors == ()
        assert result.satisfied_for_all_must
        assert inspection.volume_mm3 == pytest.approx(
            PERFORATED_VOLUME_MM3, rel=0.0, abs=VOLUME_TOLERANCE_MM3,
        )
        distances_from_nominal_axis.append(
            float(shape.distance_to(backend.bd.Vector(0.0, 0.0, HEIGHT_MM / 2)))
        )

    # distance_to measures the nearest boundary, including from inside material.
    # At the nominal axis the centered bore wall is 3 mm away; in the shifted
    # fixture the nearest boundary is a plate face 4 mm away (the bore is 5 mm
    # away). The distinct final geometry still passes both aggregate predicates.
    assert distances_from_nominal_axis == pytest.approx(
        [RADIUS_MM, HEIGHT_MM / 2], rel=0.0, abs=1e-6,
    )
