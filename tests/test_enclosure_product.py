from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from core.artifacts import compile_scad_verified, write_text_atomic
from core.enclosure import (
    CutoutSpec,
    EnclosureSpec,
    LidSpec,
    PCBSpec,
    StandoffSpec,
    VentPatternSpec,
    build_enclosure,
    validate_enclosure_spec,
)
from core.enclosure_verification import verify_enclosure_mesh
from core.engineering_math import (
    LayoutItem,
    OrientationCandidate,
    ToleranceContribution,
    pack_rectangles,
    rectangular_cantilever,
    score_orientations,
    symmetric_positions,
    tolerance_stack,
)
from core.ir_export import program_to_scad
from core.manufacturing import fabrication_preflight
from core.natural_language import interpret_enclosure, interpret_provider_payload
from core.project import (
    EnclosureProject,
    parse_project,
    semantic_diff,
    serialize_project,
    update_project,
)
from core.workflow import build_project_bundle, project_from_text


def _spec() -> EnclosureSpec:
    fasteners = ((-40.0, -25.0), (-40.0, 25.0), (40.0, -25.0), (40.0, 25.0))
    standoffs = tuple(
        StandoffSpec(f"pcb_{index}", point, 6.0, 7.5, 2.5, "M3")
        for index, point in enumerate(((-34.0, -20.0), (-34.0, 20.0), (34.0, -20.0), (34.0, 20.0)), start=1)
    )
    return EnclosureSpec(
        outer_size_mm=(100.0, 70.0, 30.0),
        wall_mm=2.0,
        floor_mm=2.4,
        corner_radius_mm=4.0,
        profile="fdm_standard",
        lid=LidSpec("screw", 3.0, 0.3, lip_height_mm=2.0, hardware="M3", fastener_positions_xy_mm=fasteners),
        cutouts=(
            CutoutSpec("usb_c", "rectangular", "right", (0.0, 9.0), size_mm=(12.0, 7.0), purpose="USB-C"),
            CutoutSpec("power", "circular", "rear", (20.0, 8.0), diameter_mm=8.0, purpose="barrel-jack"),
        ),
        standoffs=standoffs,
        vents=(VentPatternSpec("intake", "front", (0.0, 7.0), 2, 3, 2.0, 4.0),),
        pcb=PCBSpec((80.0, 50.0, 1.6), mounting_holes_xy_mm=tuple(item.center_xy_mm for item in standoffs), component_height_mm=8.0),
        title="controller enclosure",
    )


def test_typed_enclosure_builds_valid_independent_body_and_lid_programs() -> None:
    spec = _spec()
    report = validate_enclosure_spec(spec)
    assert report.valid, report.to_dict()
    build = build_enclosure(spec)
    assert set(build.parts) == {"body", "lid"}
    body_scad = program_to_scad(build.body)
    lid_scad = program_to_scad(build.lid)  # type: ignore[arg-type]
    assert "difference()" in body_scad
    assert "body_cavity" not in body_scad  # identifiers are IR metadata, not executable names
    assert body_scad.count("cylinder(") >= 14
    assert "difference()" in lid_scad
    assert build.body.metadata["feature_ids"] == ["usb_c", "power", "intake", "pcb_1", "pcb_2", "pcb_3", "pcb_4"]


def test_spec_rejects_feature_overlap_edges_unknown_profiles_and_unbacked_screw_lids() -> None:
    base = _spec()
    overlapping = EnclosureSpec(
        outer_size_mm=base.outer_size_mm,
        wall_mm=base.wall_mm,
        profile=base.profile,
        lid=base.lid,
        cutouts=(
            CutoutSpec("one", "rectangular", "front", (0.0, 8.0), size_mm=(12.0, 6.0)),
            CutoutSpec("two", "circular", "front", (2.0, 8.0), diameter_mm=5.0),
        ),
    )
    assert "feature_overlap" in {issue.code for issue in validate_enclosure_spec(overlapping).errors}

    invalid = EnclosureSpec(
        outer_size_mm=(20.0, 20.0, 10.0),
        wall_mm=0.5,
        profile="invented",
        lid=LidSpec("screw", 2.0, 0.2, hardware=None),
        cutouts=(CutoutSpec("edge", "circular", "front", (9.0, 5.0), diameter_mm=8.0),),
    )
    codes = {issue.code for issue in validate_enclosure_spec(invalid).errors}
    assert {"unknown_profile", "unknown_hardware", "missing_fasteners", "edge_clearance"} <= codes


def test_spec_and_builder_share_centered_face_coordinates_and_floor_depth() -> None:
    spec = EnclosureSpec(
        outer_size_mm=(60, 40, 30),
        wall_mm=2,
        floor_mm=8,
        profile="fdm_standard",
        lid=LidSpec("none", 0, 0),
        cutouts=(
            CutoutSpec("front_port", "rectangular", "front", (0, 0), size_mm=(10, 6)),
            CutoutSpec("drain", "circular", "bottom", (10, 0), diameter_mm=4),
        ),
    )
    assert validate_enclosure_spec(spec).valid
    nodes = build_enclosure(spec).body.node_map()
    assert nodes["front_port"].transform.translate[2] == 0
    assert nodes["drain"].primitive is not None
    assert nodes["drain"].primitive.parameters["height"] == 10


def test_validation_rejects_silent_unimplemented_or_oversized_geometry() -> None:
    open_top_feature = EnclosureSpec(
        outer_size_mm=(60, 40, 20),
        wall_mm=2,
        profile="fdm_standard",
        lid=LidSpec("none", 0, 0),
        cutouts=(CutoutSpec("top_port", "circular", "top", (0, 0), diameter_mm=4),),
    )
    assert "top_feature_without_lid" in {issue.code for issue in validate_enclosure_spec(open_top_feature).errors}

    slide = EnclosureSpec(
        outer_size_mm=(60, 40, 20),
        wall_mm=2,
        profile="fdm_standard",
        lid=LidSpec("slide", 2, 0.3, lip_height_mm=2),
    )
    assert "unimplemented_lid" in {issue.code for issue in validate_enclosure_spec(slide).errors}

    oversized_grid = EnclosureSpec(
        outer_size_mm=(10_000, 10_000, 20),
        wall_mm=2,
        profile="fdm_standard",
        lid=LidSpec("friction", 2, 0.3, lip_height_mm=2),
        vents=(VentPatternSpec("too_many", "top", (0, 0), 32, 32, 2, 4),),
    )
    assert "lid_node_budget" in {issue.code for issue in validate_enclosure_spec(oversized_grid).errors}

    reserved = EnclosureSpec(
        outer_size_mm=(60, 40, 20),
        wall_mm=2,
        profile="fdm_standard",
        lid=LidSpec("none", 0, 0),
        cutouts=(CutoutSpec("body_outer", "circular", "front", (0, 0), diameter_mm=4),),
    )
    assert "generated_id_collision" in {issue.code for issue in validate_enclosure_spec(reserved).errors}


def test_pcb_reference_constraints_include_origin_height_holes_and_standoffs() -> None:
    base = EnclosureSpec(
        outer_size_mm=(80, 60, 30),
        wall_mm=2,
        floor_mm=2,
        profile="fdm_standard",
        lid=LidSpec("none", 0, 0),
        standoffs=(StandoffSpec("mount", (10, 0), 5, 7.5, 2.5, "M3"),),
        pcb=PCBSpec((30, 20, 1.6), origin_xy_mm=(10, 0), mounting_holes_xy_mm=((0, 0),), component_height_mm=5),
    )
    assert validate_enclosure_spec(base).valid
    shifted = EnclosureSpec(**{**base.__dict__, "pcb": PCBSpec((60, 20, 1.6), origin_xy_mm=(20, 0))})
    assert "pcb_does_not_fit" in {issue.code for issue in validate_enclosure_spec(shifted).errors}
    unmatched = EnclosureSpec(**{**base.__dict__, "pcb": PCBSpec((30, 20, 1.6), mounting_holes_xy_mm=((5, 5),))})
    unmatched_report = validate_enclosure_spec(unmatched)
    assert unmatched_report.valid
    assert "unmatched_mounting_hole" in {issue.code for issue in unmatched_report.warnings}
    negative = EnclosureSpec(**{**base.__dict__, "pcb": PCBSpec((30, 20, 1.6), component_height_mm=-1)})
    assert "length_out_of_range" in {issue.code for issue in validate_enclosure_spec(negative).errors}


def test_project_round_trip_semantic_edit_and_diff_are_deterministic() -> None:
    project = EnclosureProject("controller-v1", _spec(), source_text="explicit structured specification")
    encoded = serialize_project(project)
    parsed = parse_project(encoded)
    assert serialize_project(parsed) == encoded
    edited = update_project(parsed, "wall_mm", 2.4, reason="increase shell durability")
    assert edited.revision == 2
    assert edited.changes[-1].before == 2.0
    assert semantic_diff(parsed, edited) == ({"field": "wall_mm", "before": 2.0, "after": 2.4},)
    with pytest.raises(ValueError, match="make project invalid"):
        update_project(parsed, "wall_mm", 40, reason="bad edit")


def test_project_parser_rejects_duplicate_and_unknown_fields() -> None:
    encoded = serialize_project(EnclosureProject("controller-v1", _spec()), pretty=False)
    with pytest.raises(ValueError, match="duplicate object key"):
        parse_project(encoded.replace('"project_id":"controller-v1"', '"project_id":"a","project_id":"b"'))
    value = json.loads(encoded)
    value["spec"]["magic"] = True
    with pytest.raises(ValueError, match="unsupported keys: magic"):
        parse_project(json.dumps(value))

    value = json.loads(encoded)
    value["spec"]["title"] = 123
    with pytest.raises(ValueError, match=r"\$\.spec\.title must be a string"):
        parse_project(json.dumps(value))

    value = json.loads(encoded)
    value["revision"] = 2
    with pytest.raises(ValueError, match="one ordered record"):
        parse_project(json.dumps(value))

    value["changes"] = [
        {"revision": 2, "field": "wall_mm", "before": 999, "after": 888, "reason": "forged"}
    ]
    with pytest.raises(ValueError, match="does not match"):
        parse_project(json.dumps(value))


def test_deterministic_language_interpreter_requires_every_clause_and_missing_decision() -> None:
    prompt = (
        "100 x 70 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
        "screw lid 3 mm thick clearance 0.3 mm lip 2 mm M3 fasteners at corners inset 10 mm; "
        "rectangular cutout 12 x 7 mm on right at 0 x 9 mm for USB-C; "
        "4 M3 standoffs 6 mm high at corners inset 15 mm"
    )
    interpretation = interpret_enclosure(prompt)
    assert interpretation.ready, interpretation.to_dict()
    assert len(interpretation.require_spec().standoffs) == 4
    assert len(interpretation.mappings) == 6

    unsupported = interpret_enclosure(prompt + "; make it waterproof and beautiful")
    assert not unsupported.ready
    assert any(issue.kind == "unsupported" for issue in unsupported.issues)

    incomplete = interpret_enclosure("100 x 70 x 30 mm enclosure; walls 2 mm")
    assert not incomplete.ready
    assert {issue.kind for issue in incomplete.issues} == {"question"}

    duplicate = interpret_enclosure(prompt + "; walls 3 mm")
    assert not duplicate.ready
    assert any("repeated wall_mm" in issue.message for issue in duplicate.issues)

    excessive = interpret_enclosure(
        "100 x 70 x 30 mm enclosure; walls 2 mm; profile fdm standard; open top; "
        "257 M3 standoffs 6 mm high at corners inset 10 mm"
    )
    assert not excessive.ready
    assert any(issue.kind == "invalid" for issue in excessive.issues)


def test_provider_interpretation_cannot_silently_drop_source_language() -> None:
    source = "controller enclosure"
    payload = {
        "spec": EnclosureProject("x", _spec()).to_dict()["spec"],
        "mappings": [{"text": "controller", "field": "title", "start": 0, "end": 10}],
        "questions": [],
        "unsupported": [],
    }
    result = interpret_provider_payload(source, payload)
    assert not result.ready
    assert "did not account" in " ".join(issue.message for issue in result.issues)

    payload["mappings"] = [{"text": source, "field": "title", "start": 0, "end": len(source)}]
    proposed = interpret_provider_payload(source, payload)
    assert proposed.spec is not None and not proposed.ready
    assert any("confirm" in issue.message for issue in proposed.issues)
    assert interpret_provider_payload(source, payload, confirmed=True).ready

    payload["mappings"] = [{"text": source, "field": "magic", "start": 0, "end": len(source)}]
    with pytest.raises(ValueError, match="unsupported field"):
        interpret_provider_payload(source, payload, confirmed=True)


def test_semantic_edits_cover_complete_typed_features_without_raw_geometry_mutation() -> None:
    project = EnclosureProject("controller-v1", _spec())
    cutouts = [
        {
            "id": "display",
            "kind": "rectangular",
            "face": "left",
            "center_uv_mm": [0, 8],
            "size_mm": [20, 8],
            "diameter_mm": None,
            "corner_radius_mm": 0,
            "purpose": "display",
        }
    ]
    edited = update_project(project, "cutouts", cutouts, reason="replace connector openings with display")
    assert edited.spec.cutouts[0].id == "display"
    assert edited.changes[-1].after == cutouts
    retitled = update_project(edited, "title", "display controller", reason="clarify artifact name")
    assert retitled.revision == 3
    assert parse_project(serialize_project(retitled)) == retitled


def test_engineering_math_is_explicit_and_deterministic() -> None:
    positions = symmetric_positions(5, 100, 80, 10)
    assert sum(point[0] for point in positions) == pytest.approx(0)
    assert sum(point[1] for point in positions) == pytest.approx(0)

    stack = tolerance_stack(
        0.3,
        (
            ToleranceContribution("printer x", -0.05, 0.04, 0.10),
            ToleranceContribution("material", -0.02, 0.03, 0.08),
        ),
    )
    assert stack.sigma_mm == pytest.approx(0.05)
    assert 0 < stack.success_probability < 1
    assert stack.worst_case_low_mm == pytest.approx(0.05)

    beam = rectangular_cantilever(
        force_n=10,
        length_mm=50,
        width_mm=10,
        thickness_mm=4,
        elastic_modulus_mpa=2200,
        yield_strength_mpa=45,
    )
    assert beam.maximum_stress_mpa > 0
    assert beam.tip_deflection_mm > 0
    assert beam.safety_factor is not None
    unloaded = rectangular_cantilever(
        force_n=0,
        length_mm=50,
        width_mm=10,
        thickness_mm=4,
        elastic_modulus_mpa=2200,
        yield_strength_mpa=45,
    )
    assert unloaded.safety_factor is None
    json.dumps(unloaded.to_dict(), allow_nan=False)

    ranked = score_orientations(
        (
            OrientationCandidate("flat", 0, 30, 0.2, 0.1, 7000),
            OrientationCandidate("upright", 500, 100, 0.8, 0.0, 1000),
        )
    )
    assert ranked[0].name == "flat"

    packed = pack_rectangles(
        (80, 50),
        (LayoutItem("board", (50, 30), False), LayoutItem("battery", (20, 30), True)),
        clearance_mm=2,
    )
    assert {item.id for item in packed} == {"board", "battery"}


def test_fabrication_preflight_discloses_exact_analytical_and_heuristic_results() -> None:
    report = fabrication_preflight(
        _spec(),
        density_g_cm3=1.24,
        material_cost_per_kg=24,
        tolerance_contributions=(ToleranceContribution("printer", -0.05, 0.04, 0.1),),
    )
    assert report.valid
    assert report.measurements["cutout_count"] == 2
    assert report.measurements["vent_hole_count"] == 6
    assert report.estimate.approximate_mass_g is not None
    assert "not safety certification" in report.to_dict()["disclaimer"]


def test_high_level_workflow_is_fail_closed_and_publishes_an_immutable_bundle(tmp_path: Path) -> None:
    source = (
        "100 x 70 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
        "screw lid 3 mm thick clearance 0.3 mm lip 2 mm M3 fasteners at corners inset 10 mm"
    )
    interpretation, project = project_from_text("controller", source)
    assert interpretation.ready and project is not None
    output = tmp_path / "controller-r1"
    bundle = build_project_bundle(project, output)
    assert bundle.directory == output
    assert {artifact.path for artifact in bundle.artifacts} == {
        "body.ncad.json",
        "body.scad",
        "lid.ncad.json",
        "lid.scad",
        "preflight.json",
        "project.ncad.json",
    }
    assert (output / "manifest.json").is_file()
    with pytest.raises(FileExistsError):
        build_project_bundle(project, output)

    failed, missing = project_from_text("bad", source + "; teleportation coil")
    assert not failed.ready and missing is None


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is not installed")
def test_real_kernel_body_and_lid_pass_request_level_feature_probes(tmp_path: Path) -> None:
    spec = _spec()
    build = build_enclosure(spec)
    for part, program in build.parts.items():
        scad = tmp_path / f"{part}.scad"
        stl = tmp_path / f"{part}.stl"
        write_text_atomic(scad, program_to_scad(program, fn=32))
        compile_scad_verified(scad, stl, timeout=120)
        verification = verify_enclosure_mesh(stl, spec, part=part)
        assert verification.valid, verification.to_dict()


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is not installed")
@pytest.mark.parametrize("fault", ["missing_cutout", "misplaced_hole", "filled_cavity", "incorrect_lid"])
def test_independent_mesh_checker_rejects_manufacturable_wrong_parts(tmp_path: Path, fault: str) -> None:
    """Topology alone must not certify a valid solid that violates the request."""
    spec = EnclosureSpec(
        (60, 40, 24), 2, "fdm_standard", LidSpec("friction", 2, 0.3, lip_height_mm=2),
        cutouts=(CutoutSpec("port", "circular", "front", (0, 0), diameter_mm=6),),
    )
    part = "body"
    if fault == "filled_cavity":
        scad_source = "cube([60,40,24], center=true);"
    elif fault == "incorrect_lid":
        part = "lid"
        # Correct bounds and volume topology, but no inset insertion shoulder.
        scad_source = "translate([0,0,-1]) cube([59.4,39.4,4], center=true);"
    else:
        damaged = replace(spec, cutouts=() if fault == "missing_cutout" else (
            replace(spec.cutouts[0], center_uv_mm=(12, 0)),
        ))
        scad_source = program_to_scad(build_enclosure(damaged).body, fn=32)
    scad, stl = tmp_path / f"{fault}.scad", tmp_path / f"{fault}.stl"
    write_text_atomic(scad, scad_source)
    compile_scad_verified(scad, stl, timeout=120)
    result = verify_enclosure_mesh(stl, spec, part=part)
    assert not result.valid, result.to_dict()
    assert any(not probe.passed for probe in result.probes), result.to_dict()


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is not installed")
def test_real_kernel_verifies_thick_floor_cutout_and_feature_safe_sentinels(tmp_path: Path) -> None:
    specifications = (
        EnclosureSpec(
            outer_size_mm=(50, 40, 24),
            wall_mm=2,
            floor_mm=8,
            profile="fdm_standard",
            lid=LidSpec("none", 0, 0),
            cutouts=(CutoutSpec("drain", "circular", "bottom", (0, 0), diameter_mm=5),),
        ),
        EnclosureSpec(
            outer_size_mm=(50, 40, 24),
            wall_mm=2,
            floor_mm=2,
            profile="fdm_standard",
            lid=LidSpec("none", 0, 0),
            standoffs=(StandoffSpec("near_center", (2, 0), 12, 6, 1),),
        ),
    )
    for index, spec in enumerate(specifications):
        program = build_enclosure(spec).body
        scad = tmp_path / f"edge-{index}.scad"
        stl = tmp_path / f"edge-{index}.stl"
        write_text_atomic(scad, program_to_scad(program, fn=24))
        compile_scad_verified(scad, stl, timeout=120)
        verification = verify_enclosure_mesh(stl, spec, part="body")
        assert verification.valid, verification.to_dict()
