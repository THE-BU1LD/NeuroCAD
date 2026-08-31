from __future__ import annotations

import json

import pytest

from research.vericodegen.structured_spec import (
    SPEC_VERSION,
    StructuredSpecError,
    compile_structured_json,
    parse_structured_json,
    spec_to_design,
    validate_structured_spec,
)


def _valid_spec() -> dict:
    return {
        "spec_version": SPEC_VERSION,
        "title": "plate-with-hole",
        "components": [
            {
                "name": "plate",
                "role": "body",
                "operation": "union",
                "geometry": {"kind": "box", "size": [40, 30, 4], "center": True},
            },
            {
                "name": "hole",
                "role": "cutout",
                "operation": "difference",
                "geometry": {"kind": "cylinder", "radius": 3, "height": 8, "center": True},
                "transform": {"translate": [10, 0, 0]},
            },
        ],
        "connections": [
            {"a": "plate", "b": "hole", "relation": "subtracts-through"}
        ],
    }


def test_valid_successor_spec_passes_and_compiles():
    spec = _valid_spec()
    assert validate_structured_spec(spec) == []
    design = spec_to_design(spec)
    assert len(design.components) == 2
    assert design.metadata["structured_successor"] is True
    assert design.metadata["historical_parser_claim"] == "not_applicable_falsified"

    scad = compile_structured_json(json.dumps(spec), fn=48)
    assert "$fn = 48;" in scad
    assert "difference()" in scad
    assert "cube(size=[40, 30, 4], center=true);" in scad
    assert "translate([10, 0, 0])" in scad
    assert "cylinder(r=3, h=8, center=true);" in scad


def test_markdown_fences_and_prose_are_rejected():
    payload = json.dumps(_valid_spec())
    with pytest.raises(StructuredSpecError, match="not valid JSON"):
        parse_structured_json(f"```json\n{payload}\n```")
    with pytest.raises(StructuredSpecError, match="not valid JSON"):
        parse_structured_json("Here is the design: " + payload)


def test_non_object_root_is_rejected():
    with pytest.raises(StructuredSpecError, match="root must be a JSON object"):
        parse_structured_json("[]")


def test_wrong_version_is_rejected():
    spec = _valid_spec()
    spec["spec_version"] = "legacy-parser-v0"
    errors = validate_structured_spec(spec)
    assert any("spec_version" in error for error in errors)


def test_unknown_top_level_and_component_keys_fail_closed():
    spec = _valid_spec()
    spec["surprise"] = True
    spec["components"][0]["magic"] = "repair"
    errors = validate_structured_spec(spec)
    assert any("unsupported top-level keys" in error for error in errors)
    assert any("unsupported keys: magic" in error for error in errors)


def test_component_names_must_be_unique_and_safe():
    spec = _valid_spec()
    spec["components"][1]["name"] = "plate"
    errors = validate_structured_spec(spec)
    assert any("component names must be unique" in error for error in errors)

    spec = _valid_spec()
    spec["components"][0]["name"] = "plate(); import(\"x\")"
    errors = validate_structured_spec(spec)
    assert any("letters, digits, underscore, or hyphen" in error for error in errors)


def test_geometry_rejects_nonpositive_or_nonfinite_values():
    spec = _valid_spec()
    spec["components"][0]["geometry"]["size"] = [40, 0, 4]
    errors = validate_structured_spec(spec)
    assert any("size must contain values > 0" in error for error in errors)

    spec = _valid_spec()
    spec["components"][1]["geometry"]["radius"] = float("inf")
    errors = validate_structured_spec(spec)
    assert any("radius must be a finite number > 0" in error for error in errors)


def test_transform_scale_must_be_positive():
    spec = _valid_spec()
    spec["components"][0]["transform"] = {"scale": [1, -1, 1]}
    errors = validate_structured_spec(spec)
    assert any("scale must contain values > 0" in error for error in errors)


def test_difference_only_spec_is_rejected():
    spec = _valid_spec()
    for component in spec["components"]:
        component["operation"] = "difference"
    errors = validate_structured_spec(spec)
    assert any("at least one union component" in error for error in errors)


def test_connection_references_must_exist_and_not_self_connect():
    spec = _valid_spec()
    spec["connections"] = [
        {"a": "plate", "b": "missing", "relation": "attached"},
        {"a": "plate", "b": "plate", "relation": "attached"},
    ]
    errors = validate_structured_spec(spec)
    assert any("must reference an existing component" in error for error in errors)
    assert any("cannot connect a component to itself" in error for error in errors)


def test_duplicate_connection_is_rejected_even_if_reversed():
    spec = _valid_spec()
    spec["connections"] = [
        {"a": "plate", "b": "hole", "relation": "related"},
        {"a": "hole", "b": "plate", "relation": "related"},
    ]
    errors = validate_structured_spec(spec)
    assert any("duplicates an existing connection" in error for error in errors)


def test_unsupported_geometry_kind_is_rejected():
    spec = _valid_spec()
    spec["components"][0]["geometry"] = {"kind": "freeform_mesh", "vertices": []}
    errors = validate_structured_spec(spec)
    assert any("kind must be one of" in error for error in errors)


def test_torus_requires_major_radius_greater_than_minor_radius():
    spec = _valid_spec()
    spec["components"] = [
        {
            "name": "ring",
            "geometry": {"kind": "torus", "R": 2, "r": 3},
        }
    ]
    errors = validate_structured_spec(spec)
    assert any("must be greater" in error for error in errors)


def test_cone_allows_zero_tip_radius_but_not_negative():
    spec = _valid_spec()
    spec["components"] = [
        {
            "name": "cone",
            "geometry": {"kind": "cone", "r1": 5, "r2": 0, "height": 10},
        }
    ]
    assert validate_structured_spec(spec) == []

    spec["components"][0]["geometry"]["r2"] = -1
    assert any("r2 must be a finite number >= 0" in error for error in validate_structured_spec(spec))


def test_compile_fn_is_bounded():
    payload = json.dumps(_valid_spec())
    with pytest.raises(StructuredSpecError, match="fn must"):
        compile_structured_json(payload, fn=4)
    with pytest.raises(StructuredSpecError, match="fn must"):
        compile_structured_json(payload, fn=1000)
