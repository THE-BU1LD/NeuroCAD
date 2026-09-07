from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import trimesh

from core import artifacts
from core.artifacts import compile_scad, compile_scad_verified, design_manifest, find_openscad, render_scad_png, verify_stl
from core.design_graph import Component, DesignGraph
from core.ir import CADProgram, Node, Primitive, Transform, program_bounds_are_exact
from core.ir_parser import serialize_ir_json
from core.prompt_engine import generate_design
from core.scad_export import design_to_scad
from core.validation import validate_design
from text_to_cad import TextToCAD


def test_dimensions_are_exported_in_millimetres() -> None:
    design = generate_design("a 100 x 8 x 0.5 cm plate")
    assert design.metadata["dimensions_mm"] == [1000.0, 80.0, 5.0]
    assert "cube(size=[1000, 80, 5]" in design_to_scad(design)


def test_trailing_unit_applies_to_all_sequence_dimensions() -> None:
    design = generate_design("a 120 x 80 x 4 mm plate")
    assert design.metadata["dimensions_mm"] == [120.0, 80.0, 4.0]
    assert validate_design(design).valid


def test_common_adjective_measurements_are_supported() -> None:
    design = generate_design("a plate 120 mm wide 80 mm deep and 4 mm thick")
    assert design.metadata["dimensions_mm"] == [120.0, 80.0, 4.0]
    assert validate_design(design).valid


def test_plate_hole_count_diameter_and_corner_placement() -> None:
    design = generate_design("a 120 x 80 x 4 mm plate with four 4 mm holes")
    holes = [component for component in design.components if component.name.startswith("hole_")]
    assert len(holes) == 4
    assert {hole.geometry()["radius"] for hole in holes} == {2.0}
    assert {hole.transform["translate"][:2] for hole in holes} == {
        (-52.0, -32.0),
        (-52.0, 32.0),
        (52.0, -32.0),
        (52.0, 32.0),
    }
    assert validate_design(design).valid


def test_hollow_enclosure_has_explicit_floor_and_open_top() -> None:
    design = generate_design("a 100 x 80 x 20 mm enclosure with 2 mm wall thickness")
    cavity = next(component for component in design.components if component.name == "cavity")
    assert cavity.geometry()["size"] == (96.0, 76.0, 18.2)
    assert cavity.transform["translate"] == (0.0, 0.0, 1.1)
    assert validate_design(design).valid


def test_explicit_rectangular_slots_are_generated() -> None:
    design = generate_design("a 100 x 60 x 4 mm plate with two 12 x 5 mm slots")
    slots = [component for component in design.components if component.name.startswith("slot_")]
    assert len(slots) == 2
    assert all(slot.geometry()["size"] == (12.0, 5.0, 6.0) for slot in slots)
    assert validate_design(design).valid


@pytest.mark.parametrize(
    "prompt, expected",
    [
        ("a completely unsupported warp drive", "unsupported domain"),
        ("a plate with four holes", "all overall dimensions"),
        ("a 120 x 80 x 4 mm plate with four holes", "hole diameter"),
        ("a 100 x 80 x 20 mm enclosure", "wall thickness"),
        ("a 100 x 80 x 20 mm enclosure with 2 mm walls and a lid", "lids are not implemented"),
        ("a 120 x 80 x 4 mm object with four 4 mm holes", "not recognized"),
    ],
)
def test_semantic_validation_rejects_unsafe_prompts(prompt: str, expected: str) -> None:
    report = validate_design(generate_design(prompt))
    assert not report.valid
    assert expected in " ".join(report.errors)


@pytest.mark.parametrize(
    "prompt, expected",
    [
        ("a 40 x 30 x 20 mm warp drive", "not recognized"),
        ("a plate 0 mm wide 30 mm deep and 3 mm thick", "below 0.1 mm"),
        ("a sphere with radius 0 mm", "non-positive radius"),
        ("a cylinder with radius 5 mm and height 0 mm", "invalid cylinder"),
        ("a 40 x 30 x 3 mm rounded plate", "corner radius must be stated"),
        ("a 40 x 30 x 3 mm rounded plate with corner radius 0 mm", "positive finite"),
        ("a 40 x 30 x 3 mm plate with one 30 mm hole", "smaller than the plate"),
        ("a 40 x 30 x 3 mm plate with one 40 x 5 mm slot", "smaller than the corresponding"),
        ("a 40 x 30 x 20 mm enclosure with 2 mm walls and one 3 mm hole", "holes are supported only"),
        ("a 40 x 30 x 5 mm enclosure with 5 mm walls", "smaller than enclosure height"),
    ],
)
def test_parser_never_approves_defaults_or_out_of_bounds_features(prompt: str, expected: str) -> None:
    report = validate_design(generate_design(prompt))
    assert not report.valid
    assert expected in " ".join(report.errors)


def test_supported_solid_and_explicit_rounded_descriptions_remain_valid() -> None:
    solid = validate_design(generate_design("a solid 40 x 30 x 20 mm box"))
    rounded = validate_design(generate_design("a 40 x 30 x 3 mm rounded plate with corner radius 4 mm"))
    block = validate_design(generate_design("a 40 x 30 x 20 mm rectangular block"))
    assert solid.valid
    assert rounded.valid
    assert block.valid


def test_multiple_overall_dimension_sequences_are_rejected_as_ambiguous() -> None:
    with pytest.raises(ValueError, match="multiple overall dimension sequences"):
        generate_design("a 40 x 30 x 3 mm plate or a 50 x 40 x 4 mm plate")


def test_direct_prompt_api_enforces_input_contract() -> None:
    for prompt in ("", "   "):
        with pytest.raises(ValueError, match="non-empty"):
            generate_design(prompt)
    with pytest.raises(ValueError, match="limited to 4096"):
        generate_design("x" * 4097)


def test_dense_or_cross_family_features_fail_before_export() -> None:
    dense = validate_design(generate_design("a 100 x 100 x 4 mm plate with 256 10 mm holes"))
    mixed = validate_design(generate_design("a 100 x 60 x 4 mm plate with one 4 mm hole and one 12 x 5 mm slot"))
    assert not dense.valid
    assert "hole features overlap" in " ".join(dense.errors)
    assert not mixed.valid
    assert "hole and slot features overlap" in " ".join(mixed.errors)


def test_domain_matching_uses_words_not_substrings() -> None:
    design = generate_design("a postcard holder")
    assert design.metadata["domain"] == "generic"
    assert not validate_design(design).valid


def test_fully_dimensioned_cylinder_is_supported() -> None:
    design = generate_design("a 50 mm radius cylinder height 100 mm")
    body = design.components[0].geometry()
    assert body["radius"] == 50.0
    assert body["height"] == 100.0
    assert validate_design(design).valid


def test_prompt_with_open_scad_suffix_fails_closed() -> None:
    with pytest.raises(ValueError, match="unconsumed or unsupported text"):
        TextToCAD().to_scad("a 10 x 10 x 2 mm plate\ncube(999);")


def test_invalid_fn_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 3 and 1000"):
        design_to_scad(generate_design("a 10 x 10 x 2 mm plate"), fn=2)
    for invalid in (True, 3.5, "96"):
        with pytest.raises(ValueError, match="integer between"):
            TextToCAD(fn=invalid)  # type: ignore[arg-type]


def test_excessive_feature_count_is_rejected_before_generation() -> None:
    with pytest.raises(ValueError, match="above 256"):
        generate_design("a 100 x 100 x 3 mm plate with 1000000 3 mm holes")


def test_export_refuses_invalid_design(tmp_path: Path) -> None:
    output = tmp_path / "unsafe.scad"
    with pytest.raises(ValueError, match="invalid design"):
        TextToCAD(output_path=str(output)).export("an unsupported warp drive")
    assert not output.exists()
    with pytest.raises(ValueError, match="invalid design"):
        TextToCAD().to_scad("an unsupported aircraft")

    analysis = TextToCAD().build("a sphere with radius 0 mm")
    assert not analysis.validation.valid
    assert analysis.program is None
    assert analysis.ir_validation is None
    assert analysis.scad == ""


def test_flat_export_rejects_ambiguous_boolean_combinations_and_sanitizes_comments() -> None:
    design = DesignGraph("direct graph")
    body = Component("body\ncube(999);", {"geometry": {"kind": "box", "size": [10, 10, 2]}})
    overlap = Component(
        "overlap",
        {"geometry": {"kind": "sphere", "radius": 2}},
        operation="intersection",
    )
    design.add_component(body)
    design.add_component(overlap)
    with pytest.raises(ValueError, match="cannot mix intersection"):
        design_to_scad(design)

    design.components.pop()
    scad = design_to_scad(design)
    assert "// component: body cube(999);" in scad
    assert "\ncube(999);\n" not in scad


def test_design_validation_is_total_for_malformed_numeric_and_transform_values() -> None:
    design = generate_design("a 40 x 30 x 3 mm plate")
    design.components[0].params["geometry"]["size"] = [10**1000, "bad", 3]
    design.components[0].transform["scale"] = (1, 0, float("nan"))
    design.metadata["hole_count_requested"] = "four"
    report = validate_design(design)
    assert not report.valid
    combined = " ".join(report.errors)
    assert "three size dimensions" in combined
    assert "transform requires three finite" in combined
    assert "hole count must be an integer" in combined


def test_manifest_contains_validation_and_units() -> None:
    design = generate_design("a 40 x 30 x 3 mm plate with four 3 mm holes")
    report = validate_design(design)
    manifest = design_manifest(design, report)
    assert manifest["schema_version"] == "1.0"
    assert manifest["units"] == "mm"
    assert manifest["validation"]["valid"] is True
    assert len(manifest["components"]) == 5


def test_singular_inch_applies_to_named_measurement() -> None:
    document = TextToCAD().build("a sphere with radius 0.5 inch")
    body = next(node for node in document.program.nodes if node.id == "body")
    assert body.primitive is not None
    assert body.primitive.parameters["radius"] == pytest.approx(12.7)


def test_stl_verifier_accepts_watertight_mesh(tmp_path: Path) -> None:
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=(10, 20, 30)).export(path)
    result = verify_stl(path)
    assert result["watertight"] is True
    assert result["winding_consistent"] is True
    assert result["finite_vertices"] is True
    assert result["body_count"] == 1
    assert result["extents_mm"] == [10.0, 20.0, 30.0]


def test_stl_verifier_checks_expected_extents_and_connectedness(tmp_path: Path) -> None:
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=(10, 20, 30)).export(path)
    result = verify_stl(path, expected_extents_mm=[10, 20, 30])
    assert result["extent_absolute_errors_mm"] == [0.0, 0.0, 0.0]
    with pytest.raises(RuntimeError, match="do not match expected extents"):
        verify_stl(path, expected_extents_mm=[11, 20, 30])

    disconnected = tmp_path / "disconnected.stl"
    combined = trimesh.util.concatenate(
        [
            trimesh.creation.box(extents=(1, 1, 1)),
            trimesh.creation.box(extents=(1, 1, 1), transform=trimesh.transformations.translation_matrix((3, 0, 0))),
        ]
    )
    combined.export(disconnected)
    with pytest.raises(RuntimeError, match="disconnected bodies"):
        verify_stl(disconnected)

    point_contact = tmp_path / "point-contact.stl"
    touching = trimesh.util.concatenate(
        [
            trimesh.creation.box(extents=(1, 1, 1)),
            trimesh.creation.box(
                extents=(1, 1, 1),
                transform=trimesh.transformations.translation_matrix((1, 1, 1)),
            ),
        ]
    )
    touching.export(point_contact)
    with pytest.raises(RuntimeError, match="2 disconnected bodies"):
        verify_stl(point_contact)


def test_artifact_boundaries_reject_invalid_paths_and_controls(tmp_path: Path) -> None:
    missing = tmp_path / "missing.scad"
    with pytest.raises(ValueError, match="existing non-empty"):
        compile_scad(missing, tmp_path / "output.stl")

    source = tmp_path / "source.scad"
    source.write_text("cube([1,1,1]);\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be different"):
        compile_scad(source, source)
    with pytest.raises(ValueError, match="positive integer"):
        render_scad_png(source, tmp_path / "render.png", timeout=0)

    mesh_path = tmp_path / "box.stl"
    trimesh.creation.box(extents=(1, 1, 1)).export(mesh_path)
    for keyword in ("extent_relative_tolerance", "extent_absolute_tolerance_mm"):
        with pytest.raises(ValueError, match=keyword):
            verify_stl(mesh_path, **{keyword: -0.1})
    with pytest.raises(ValueError, match="existing non-empty"):
        verify_stl(tmp_path / "missing.stl")


def test_verified_compile_failure_does_not_clobber_existing_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.scad"
    source.write_text("cube([1,1,1]);\n", encoding="utf-8")
    output = tmp_path / "protected.stl"
    output.write_bytes(b"existing-good-artifact")

    def fake_compile(source_path: Path, staged_path: Path, *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
        del source_path, timeout
        staged_path.write_bytes(b"invalid-staged-artifact")
        return subprocess.CompletedProcess([], 0, "", "")

    def reject_staged_artifact(path: Path, **_: object) -> dict[str, object]:
        assert path != output
        raise RuntimeError("verification rejected staged artifact")

    monkeypatch.setattr(artifacts, "compile_scad", fake_compile)
    monkeypatch.setattr(artifacts, "verify_stl", reject_staged_artifact)
    with pytest.raises(RuntimeError, match="verification rejected"):
        compile_scad_verified(source, output)
    assert output.read_bytes() == b"existing-good-artifact"
    assert not list(tmp_path.glob(".protected.*.stl"))


@pytest.mark.skipif(find_openscad() is None, reason="OpenSCAD is required for kernel-backed difference regression")
def test_cli_accepts_valid_difference_that_trims_conservative_bounds(tmp_path: Path) -> None:
    program = CADProgram(
        title="trimmed solid",
        nodes=(
            Node("body", primitive=Primitive("box", {"size": [10, 10, 10]})),
            Node(
                "cutter",
                primitive=Primitive("box", {"size": [6, 20, 20]}),
                transform=Transform(translate=(4, 0, 0)),
            ),
            Node("trimmed", composition="difference", children=("body", "cutter")),
        ),
        roots=("trimmed",),
    )
    assert not program_bounds_are_exact(program)
    ir_path = tmp_path / "trimmed.ncad.json"
    output = tmp_path / "trimmed.stl"
    ir_path.write_text(serialize_ir_json(program), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "compile",
            str(ir_path),
            "--format",
            "stl",
            "--fn",
            "12",
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    verification = verify_stl(output)
    assert verification["extents_mm"] == pytest.approx([6, 10, 10])


def test_cli_rejects_artifact_path_collisions_before_writing(tmp_path: Path) -> None:
    target = tmp_path / "must-survive"
    commands = [
        [
            "create",
            "a 40 x 30 x 3 mm plate",
            "-o",
            str(target),
            "--manifest",
            str(target),
        ],
        [
            "export",
            "a 40 x 30 x 3 mm plate",
            "--format",
            "scad",
            "-o",
            str(target),
            "--manifest",
            str(target),
        ],
        ["compile", str(target), "--format", "json", "-o", str(target)],
        ["benchmark", "--dataset", str(target), "--output", str(target)],
    ]
    for command in commands:
        target.write_text("sentinel\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "neurocad_cli", *command],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2, (command, result.stderr)
        assert "artifact paths must be distinct" in result.stderr
        assert target.read_text(encoding="utf-8") == "sentinel\n"


def test_cli_refuses_existing_outputs_unless_force_is_explicit(tmp_path: Path) -> None:
    output = tmp_path / "design.scad"
    manifest = tmp_path / "design.json"
    output.write_text("sentinel output\n", encoding="utf-8")
    manifest.write_text("sentinel manifest\n", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "neurocad_cli",
        "create",
        "a 40 x 30 x 3 mm plate",
        "-o",
        str(output),
        "--manifest",
        str(manifest),
    ]

    refused = subprocess.run(command, capture_output=True, text=True, check=False)
    assert refused.returncode == 2
    assert "already exists" in refused.stderr
    assert output.read_text(encoding="utf-8") == "sentinel output\n"
    assert manifest.read_text(encoding="utf-8") == "sentinel manifest\n"

    replaced = subprocess.run([*command, "--force"], capture_output=True, text=True, check=False)
    assert replaced.returncode == 0, replaced.stderr
    assert output.read_text(encoding="utf-8") != "sentinel output\n"
    assert manifest.read_text(encoding="utf-8") != "sentinel manifest\n"


@pytest.mark.parametrize("command", ["export", "ir", "compile"])
def test_core_artifact_commands_refuse_existing_output(tmp_path: Path, command: str) -> None:
    output = tmp_path / "protected.json"
    output.write_text("sentinel\n", encoding="utf-8")
    if command == "export":
        arguments = [command, "a 40 x 30 x 3 mm plate", "--format", "json", "-o", str(output)]
    elif command == "ir":
        arguments = [command, "a 40 x 30 x 3 mm plate", "-o", str(output)]
    else:
        source = tmp_path / "source.ncad.json"
        source.write_text(serialize_ir_json(TextToCAD().build("a 40 x 30 x 3 mm plate").require_program()), encoding="utf-8")
        arguments = [command, str(source), "--format", "json", "-o", str(output)]

    refused = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 2
    assert "already exists" in refused.stderr
    assert output.read_text(encoding="utf-8") == "sentinel\n"


def test_cli_rejects_unsupported_prompt() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "validate", "an unsupported warp drive"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "INVALID" in result.stderr


def test_cli_exports_json_manifest(tmp_path: Path) -> None:
    output = tmp_path / "design.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "neurocad_cli",
            "export",
            "a 40 x 30 x 3 mm plate with four 3 mm holes",
            "--format",
            "json",
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["validation"]["valid"] is True
