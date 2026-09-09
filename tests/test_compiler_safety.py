from __future__ import annotations

import pytest

from core.design_graph import Component, DesignGraph
from core.ir_adapter import design_graph_to_ir
from core.prompt_engine import generate_design
from core.scad_export import design_to_scad, primitive_to_scad
from core.validation import validate_design
from text_to_cad import TextToCAD


@pytest.mark.parametrize(
    "suffix",
    [
        "wings",
        "a 10 mm boss",
        "threads",
        "two hinges",
        "snap-fits",
        "2 mm fillets",
        "a handle",
        "ribs",
        "embossed text",
        "a teleportation coil",
    ],
)
def test_unconsumed_feature_clauses_fail_closed_at_every_export(suffix: str) -> None:
    design = generate_design(f"a 120 x 80 x 4 mm plate with {suffix}")
    report = validate_design(design)

    assert not report.valid
    assert "unconsumed or unsupported text" in " ".join(report.errors)
    with pytest.raises(ValueError, match="cannot export invalid design"):
        design_to_scad(design)
    with pytest.raises(ValueError, match="cannot adapt invalid design"):
        design_graph_to_ir(design)


@pytest.mark.parametrize("suffix", ["!!!", "🚀", "©"])
def test_normalization_cannot_silently_erase_unsupported_characters(suffix: str) -> None:
    document = TextToCAD().build(f"a 120 x 80 x 4 mm plate {suffix}")
    assert not document.validation.valid
    assert "unconsumed or unsupported text" in " ".join(document.validation.errors)


@pytest.mark.parametrize("feature", ["4 mm holes", "12 x 5 mm slots"])
def test_plural_features_never_default_to_one(feature: str) -> None:
    design = generate_design(f"a 120 x 80 x 4 mm plate with {feature}")
    report = validate_design(design)

    assert not report.valid
    assert "count must be stated explicitly" in " ".join(report.errors)
    assert len(design.components) == 1


@pytest.mark.parametrize("count", [3, 5, 7])
def test_non_rectangular_feature_counts_remain_centered(count: int) -> None:
    design = generate_design(f"a 120 x 80 x 4 mm plate with {count} 3 mm holes")
    holes = [component for component in design.components if component.name.startswith("hole_")]

    assert validate_design(design).valid
    assert sum(component.transform["translate"][0] for component in holes) / count == pytest.approx(0.0, abs=1e-12)
    assert sum(component.transform["translate"][1] for component in holes) / count == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("count", ["-4", "+4", "2.5"])
@pytest.mark.parametrize("feature", ["4 mm holes", "12 x 5 mm slots"])
def test_signed_or_fractional_feature_counts_are_rejected(count: str, feature: str) -> None:
    with pytest.raises(ValueError, match="unsigned whole integers"):
        generate_design(f"a 120 x 80 x 4 mm plate with {count} {feature}")


@pytest.mark.parametrize(
    "prompt",
    [
        "a 120 x 80 x 4 mm plate with one -5 mm hole",
        "a 120 x 80 x 4 mm plate with one 12 x -5 mm slot",
    ],
)
def test_signed_feature_dimensions_remain_signed_and_are_rejected(prompt: str) -> None:
    report = validate_design(generate_design(prompt))
    assert not report.valid
    assert "positive" in " ".join(report.errors) or "non-positive" in " ".join(report.errors)


@pytest.mark.parametrize(
    "prompt",
    [
        "a sphere with radius 0.0000001 mm",
        "a sphere with radius 100001 mm",
        "a cylinder with radius 0.01 mm and height 10 mm",
        "a cylinder with radius 10 mm and height 100001 mm",
        "a 0.01 x 10 x 10 mm block",
        "a 10 x 10 x 100001 mm block",
    ],
)
def test_every_prompt_primitive_obeys_the_supported_length_range(prompt: str) -> None:
    document = TextToCAD().build(prompt)
    assert not document.validation.valid
    assert document.program is None
    assert document.scad == ""


@pytest.mark.parametrize(
    "geometry",
    [
        {"kind": "sphere", "radius": 1e-7},
        {"kind": "sphere", "radius": 100001},
        {"kind": "cylinder", "radius": 1, "height": 1e-7},
        {"kind": "box", "size": [1, 1, 100001]},
        {"kind": "sphere", "radius": 10**1000},
    ],
)
def test_raw_primitive_export_cannot_bypass_length_validation(geometry: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="between 0.1 and 100,000 mm"):
        primitive_to_scad(geometry)


def test_minimum_supported_radius_is_not_serialized_as_zero() -> None:
    assert primitive_to_scad({"kind": "sphere", "radius": 0.1}) == "sphere(r=0.1);"


def test_raw_primitive_center_cannot_be_truthiness_coerced() -> None:
    with pytest.raises(TypeError, match="center must be a boolean"):
        primitive_to_scad({"kind": "box", "size": [1, 1, 1], "center": "false"})


def test_unknown_operation_is_rejected_by_both_public_exporters() -> None:
    design = DesignGraph("invalid operation")
    design.add_component(
        Component(
            "body",
            {"geometry": {"kind": "box", "size": [10, 10, 2], "center": True}},
            operation="difference_typo",
        )
    )

    with pytest.raises(ValueError, match="unsupported operation"):
        design_to_scad(design)
    with pytest.raises(ValueError, match="unsupported operation"):
        design_graph_to_ir(design)


def test_adapter_preserves_non_centered_local_origin() -> None:
    design = DesignGraph("non-centered box")
    design.add_component(
        Component(
            "body",
            {"geometry": {"kind": "box", "size": [4, 6, 8], "center": False}},
            transform={
                "translate": (10, 20, 30),
                "rotate": (0, 0, 0),
                "scale": (1, 1, 1),
            },
        )
    )

    program = design_graph_to_ir(design)
    assert program.nodes[0].transform.translate == (12.0, 23.0, 34.0)


def test_adapter_constraints_do_not_alias_mutable_primitive_parameters() -> None:
    design = DesignGraph("independent constraints")
    design.add_component(
        Component(
            "body",
            {"geometry": {"kind": "box", "size": [4, 6, 8], "center": True}},
        )
    )
    program = design_graph_to_ir(design)
    primitive_size = program.nodes[0].primitive.parameters["size"]  # type: ignore[union-attr]
    constraint_size = program.constraints[0].parameters["value"]

    assert primitive_size is not constraint_size
    primitive_size[0] = 999
    assert constraint_size == [4, 6, 8]
