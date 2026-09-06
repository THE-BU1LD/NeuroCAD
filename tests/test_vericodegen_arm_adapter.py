from __future__ import annotations

import json

import pytest

from research.vericodegen.arm_adapter import (
    ArmAdapterError,
    prepare_arm_scad,
    prepare_direct_scad,
    prepare_structured_scad,
    validate_direct_output,
)
from research.vericodegen.structured_spec import SPEC_VERSION


def _structured_box() -> str:
    return json.dumps(
        {
            "spec_version": SPEC_VERSION,
            "title": "box",
            "components": [
                {
                    "name": "body",
                    "geometry": {"kind": "box", "size": [10, 20, 30], "center": True},
                }
            ],
        }
    )


def test_direct_arm_gets_frozen_resolution_wrapper():
    scad = prepare_direct_scad("cube([10, 20, 30], center=true);", fn=64)
    assert scad.startswith("// VeriCodeGen frozen direct-arm wrapper")
    assert "$fn = 64;" in scad
    assert "cube([10, 20, 30], center=true);" in scad


def test_structured_arm_uses_same_frozen_resolution():
    scad = prepare_structured_scad(_structured_box(), fn=64)
    assert "$fn = 64;" in scad
    assert "cube(size=[10, 20, 30], center=true);" in scad


def test_direct_arm_cannot_override_fn_fa_or_fs():
    for source in (
        "$fn=12; sphere(r=5);",
        "$fa = 1; sphere(r=5);",
        "$fs = 0.1; sphere(r=5);",
    ):
        errors = validate_direct_output(source)
        assert any("resolution_override" in error for error in errors)
        with pytest.raises(ArmAdapterError, match="forbidden construct"):
            prepare_direct_scad(source, fn=64)


def test_direct_arm_cannot_use_external_files_even_inline():
    sources = (
        "include <vendor.scad>; cube(1);",
        "cube(1); include <vendor.scad>;",
        "use <vendor.scad>; vendor_part();",
        "cube(1); use <vendor.scad>;",
        'import("part.stl");',
        'cube(1); import("part.stl");',
        'surface(file="heightmap.dat");',
    )
    for source in sources:
        with pytest.raises(ArmAdapterError, match="forbidden construct"):
            prepare_direct_scad(source, fn=64)


def test_direct_markdown_or_json_is_rejected():
    with pytest.raises(ArmAdapterError):
        prepare_direct_scad("```openscad\ncube(1);\n```", fn=64)
    with pytest.raises(ArmAdapterError, match="appears to be JSON"):
        prepare_direct_scad('{"kind":"box"}', fn=64)


def test_unknown_arm_fails_closed():
    with pytest.raises(ArmAdapterError, match="unknown arm"):
        prepare_arm_scad("hybrid", "cube(1);", fn=64)


def test_resolution_bounds_apply_to_both_arms():
    with pytest.raises(ArmAdapterError, match="openscad_fn"):
        prepare_direct_scad("cube(1);", fn=8)
    with pytest.raises(ArmAdapterError, match="openscad_fn"):
        prepare_structured_scad(_structured_box(), fn=500)
