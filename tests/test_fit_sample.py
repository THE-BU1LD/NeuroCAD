import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from core.artifacts import compile_scad_verified, find_openscad
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec, build_enclosure
from core.fit_sample import cutout_fit_sample
from core.ir_export import program_to_scad
from core.ir_parser import parse_ir_json, serialize_ir_json
from core.project import EnclosureProject, write_project


def project(kind: str = "rectangular", face: str = "front") -> EnclosureProject:
    cutout = CutoutSpec("port", kind, face, (0, 0), size_mm=(12, 7) if kind == "rectangular" else None,
                        diameter_mm=6 if kind == "circular" else None)
    return EnclosureProject("sample-test", EnclosureSpec((80, 60, 30), 2, "fdm_standard", LidSpec("none", 0, 0), cutouts=(cutout,)))


@pytest.mark.parametrize("kind", ["rectangular", "circular"])
@pytest.mark.parametrize("face", ["front", "rear", "left", "right", "bottom"])
def test_sample_retains_compiled_aperture_and_source_identity(kind: str, face: str) -> None:
    source = project(kind, face)
    sample = cutout_fit_sample(source, "port")
    original = next(node for node in build_enclosure(source.spec).parts["body"].nodes if node.id == "port")
    aperture = sample.nodes[1].primitive
    assert aperture is not None and original.primitive is not None
    if kind == "circular":
        assert aperture.parameters["radius"] == original.primitive.parameters["radius"]
    else:
        assert aperture.parameters["size"][:2] == [12, 7]
    assert parse_ir_json(serialize_ir_json(sample)) == sample
    assert len(sample.metadata["source_project_sha256"]) == 64
    assert sample.metadata["source_face"] == face


def test_sample_rejects_unsupported_or_invalid_requests() -> None:
    source = project()
    for margin in [True, float("nan"), 1, 51]:
        with pytest.raises(ValueError):
            cutout_fit_sample(source, "port", margin_mm=margin)
    with pytest.raises(ValueError):
        cutout_fit_sample(source, "missing")
    changed = replace(source, revision=2)
    assert cutout_fit_sample(source, "port").metadata["source_project_sha256"] != cutout_fit_sample(changed, "port").metadata["source_project_sha256"]


@pytest.mark.parametrize("kind", ["rectangular", "circular"])
def test_sample_mesh_has_expected_material_and_open_aperture(tmp_path: Path, kind: str) -> None:
    if not find_openscad():
        pytest.skip("OpenSCAD is not installed")
    import trimesh

    sample = cutout_fit_sample(project(kind), "port")
    scad, stl = tmp_path / "sample.scad", tmp_path / "sample.stl"
    scad.write_text(program_to_scad(sample, fn=128))
    compile_scad_verified(scad, stl)
    mesh = trimesh.load_mesh(stl)
    width, height = sample.metadata["aperture_size_mm"]
    area = width * height if kind == "rectangular" else math.pi * (width / 2) ** 2
    expected = ((width + 10) * (height + 10) - area) * 2
    assert mesh.is_watertight
    assert mesh.volume == pytest.approx(expected, rel=0.001)


def test_fit_sample_cli_preserves_source_and_refuses_collision(tmp_path: Path) -> None:
    source, output = tmp_path / "project.json", tmp_path / "sample.json"
    write_project(source, project())
    command = [sys.executable, "-m", "neurocad_cli", "enclosure", "fit-sample", str(source), "--cutout", "port", "-o", str(output)]
    assert subprocess.run(command, capture_output=True, check=False, timeout=60).returncode == 0
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True, check=False, timeout=60).returncode != 0
    assert output.read_bytes() == before
