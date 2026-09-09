"""Mesh-backed estimates require reproducible geometry and exact source identity."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.manufacturing import fabrication_preflight
from core.project import EnclosureProject, update_project
from core.workflow import build_project_bundle, verified_material_report


@pytest.fixture
def source() -> EnclosureProject:
    return EnclosureProject("material", EnclosureSpec(
        (60, 40, 24), 2, "fdm_standard", LidSpec("none", 0, 0),
        cutouts=(CutoutSpec("port", "rectangular", "front", (0, 0), size_mm=(10, 6)),),
    ))


def test_material_report_requires_compiled_artifacts(tmp_path: Path, source: EnclosureProject) -> None:
    bundle = build_project_bundle(source, tmp_path / "source")
    with pytest.raises(ValueError, match="compiled STL"):
        verified_material_report(source, bundle.directory)


@pytest.mark.parametrize("density,cost", [
    (True, None), (0, None), (float("nan"), None), (float("inf"), None),
    (1, True), (1, -1), (1, float("inf")), (1e308, None), (1e300, 1e300),
])
def test_estimates_reject_invalid_and_overflowing_economics(source: EnclosureProject, density: float, cost: float | None) -> None:
    with pytest.raises(ValueError):
        fabrication_preflight(source.spec, density_g_cm3=density, material_cost_per_kg=cost)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is not installed")
def test_material_report_includes_lid_and_insertion_plug(tmp_path: Path, source: EnclosureProject) -> None:
    source = replace(source, spec=replace(source.spec, lid=LidSpec("friction", 2, 0.3, lip_height_mm=2)))
    bundle = build_project_bundle(source, tmp_path / "with-lid", compile_stl=True, fn=24)
    report = verified_material_report(source, bundle.directory)
    expected_body = 60 * 40 * 24 - 56 * 36 * 22 - 10 * 6 * 2
    expected_lid = 59.4 * 39.4 * 2 + 55.4 * 35.4 * 2
    assert report["part_volume_mm3"]["body"] == pytest.approx(expected_body)
    assert report["part_volume_mm3"]["lid"] == pytest.approx(expected_lid)
    assert report["total_volume_mm3"] == pytest.approx(expected_body + expected_lid)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD is not installed")
def test_real_volume_mass_cost_revision_and_tamper_guards(tmp_path: Path, source: EnclosureProject) -> None:
    bundle = build_project_bundle(source, tmp_path / "compiled", compile_stl=True, fn=24)
    report = verified_material_report(source, bundle.directory, density_g_cm3=1.25, material_cost_per_kg=20)
    expected = 60 * 40 * 24 - 56 * 36 * 22 - 10 * 6 * 2
    assert report["total_volume_mm3"] == pytest.approx(expected)
    assert report["solid_model_mass_g"] == pytest.approx(expected / 1000 * 1.25)
    assert report["solid_model_material_cost"] == pytest.approx(expected / 1000 * 1.25 / 1000 * 20)
    assert report["shell_estimate_error_percent"] == pytest.approx(120 / expected * 100)
    assert verified_material_report(source, bundle.directory)["solid_model_mass_g"] is None
    for changed in (update_project(source, "title", "new revision", reason="test stale evidence"), replace(source, project_id="another"),
                    replace(source, spec=replace(source.spec, wall_mm=3))):
        with pytest.raises(ValueError, match="exact project"):
            verified_material_report(changed, bundle.directory)
    result = subprocess.run([
        sys.executable, "-m", "neurocad_cli", "enclosure", "preflight",
        str(bundle.directory / "project.ncad.json"), "--bundle", str(bundle.directory), "--density", "1.25",
    ], capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["compiled_geometry"]["total_volume_mm3"] == pytest.approx(expected)
    (bundle.directory / "body.stl").write_bytes(b"invalid")
    with pytest.raises(ValueError, match="hash or size"):
        verified_material_report(source, bundle.directory)
