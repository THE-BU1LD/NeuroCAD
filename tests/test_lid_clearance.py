"""Assembled-clearance regressions use mesh occupancy independent of the IR."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from core.artifacts import compile_scad_verified
from core.enclosure import EnclosureSpec, LidSpec, PCBSpec, StandoffSpec, build_enclosure, validate_enclosure_spec
from core.enclosure_verification import _MeshOccupancy, verify_enclosure_mesh
from core.ir import Primitive
from core.ir_export import program_to_scad


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD required")
@pytest.mark.parametrize("kind", ["friction", "screw"])
def test_lid_clears_rounded_cavity_and_screw_bosses(tmp_path: Path, kind: str) -> None:
    import trimesh

    lid = LidSpec(kind, 3, 0.3, lip_height_mm=2)
    if kind == "screw":
        lid = replace(lid, hardware="M3", fastener_positions_xy_mm=((-20.0, 0.0), (20.0, 0.0)))
    spec = EnclosureSpec((60, 40, 24), 2, "fdm_standard", lid, corner_radius_mm=6)
    program = build_enclosure(spec).lid
    assert program is not None
    source, output = tmp_path / "lid.scad", tmp_path / "lid.stl"
    source.write_text(program_to_scad(program, fn=48), encoding="utf-8")
    compile_scad_verified(source, output)
    occupancy = _MeshOccupancy(trimesh.load_mesh(output, force="mesh"))
    # The cavity's NE corner is a radius-4 arc around (24,14). This
    # point is outside it, but inside the former rectangular insertion plug.
    assert not occupancy.contains((27.5, 17.5, -2.5)), "lid plug collides with the rounded cavity wall"
    assert occupancy.contains((0, 0, -2.5)), "insertion plug material must remain"
    if kind == "screw":
        # The M3 boss radius is 3.75 mm. The lid seats above the rim and its
        # plug extends down into the boss's upper ring; a bore alone cannot fit.
        assert not occupancy.contains((22.8, 0, -2.5)), "lid plug collides with a screw boss"
        assert occupancy.contains((22.8, 0, 0)), "boss relief must preserve the screw-bearing plate"
    assert verify_enclosure_mesh(output, spec, part="lid").valid

    # Deliberately restore the former defective geometry. Extents/topology still
    # pass, but the independent request verifier must reject the wrong surface.
    wrong_nodes = []
    for node in program.nodes:
        if node.id in {"lid_plate", "lid_lip"}:
            node = replace(node, primitive=Primitive("box", {"size": node.primitive.parameters["size"]}))
        elif node.id.startswith("lid_boss_relief_"):
            node = replace(node, primitive=Primitive("cylinder", {**node.primitive.parameters, "radius": 1.8}))
        wrong_nodes.append(node)
    source.write_text(program_to_scad(replace(program, nodes=tuple(wrong_nodes)), fn=48), encoding="utf-8")
    compile_scad_verified(source, output)
    verification = verify_enclosure_mesh(output, spec, part="lid")
    assert not verification.valid
    assert any("rounded corner" in probe.check and not probe.passed for probe in verification.probes)
    if kind == "screw":
        assert any("boss ring" in probe.check and not probe.passed for probe in verification.probes)


@pytest.mark.parametrize("extra", [
    {"lid": LidSpec("friction", 2, 0.3, lip_height_mm=22)},
    {"standoffs": (StandoffSpec("tall", (0.0, 0.0), 21, 7.5, 2.5, "M3"),)},
    {"pcb": PCBSpec((30, 20, 1.6), component_height_mm=19)},
])
def test_insertion_plug_cannot_occupy_floor_mount_or_board_envelope(extra: dict) -> None:
    spec = EnclosureSpec((60, 40, 24), 2, "fdm_standard", LidSpec("friction", 2, 0.3, lip_height_mm=2))
    spec = replace(spec, **extra)
    report = validate_enclosure_spec(spec)
    assert not report.valid
    assert any("lip" in issue.message or "plug" in issue.message for issue in report.errors)


def test_standoff_attachment_stays_within_even_a_thin_explicit_floor() -> None:
    from core.ir import program_bounds

    spec = EnclosureSpec(
        (60, 40, 24), 2, "fdm_standard", LidSpec("none", 0, 0), floor_mm=0.1,
        standoffs=(StandoffSpec("mount", (0.0, 0.0), 6, 7.5, 2.5, "M3"),),
    )
    lower, upper = program_bounds(build_enclosure(spec).body)
    assert lower == (-30, -20, -12)
    assert upper == (30, 20, 12)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD required")
@pytest.mark.parametrize("size,radius", [([20, 20, 2], 10), ([30, 20, 2], 10), ([20, 20, 2], 0), ([20, 20, 2], 0.05)])
def test_rounded_primitive_boundary_radii_compile_to_nonempty_solids(tmp_path: Path, size: list, radius: float) -> None:
    from core.scad_export import primitive_to_scad

    source = tmp_path / "rounded.scad"
    source.write_text("$fn=48;\n" + primitive_to_scad({"kind": "rounded_box", "size": size, "radius": radius, "center": True}))
    _, report = compile_scad_verified(source, tmp_path / "rounded.stl", expected_extents_mm=size)
    assert report["kernel_validity"]
