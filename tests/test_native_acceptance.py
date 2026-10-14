"""Native failures and semantic membership checks for the declared fixtures."""
from __future__ import annotations

import json
from importlib.metadata import version

import pytest

pytest.importorskip("build123d")
gmsh = pytest.importorskip("gmsh")

from core.exact_build123d import Build123dBackend
from core.gmsh_integrity import GmshMeshingError
from core.gmsh_process import GmshProcessBackend
from scripts.verify_native_acceptance import golden_programs


def test_tagged_beam_membership_survives_native_serialization(tmp_path):
    program, _, _ = golden_programs()["beam"]
    exact = Build123dBackend().export_verified_step(program, tmp_path / "exact")
    assert exact.kernel_version == version("cadquery-ocp-novtk")
    request = {"source_step_sha256": exact.step_sha256,
               "roles": {"fixed_end": {"axis": "x", "side": "min", "expected_surfaces": 1}}}
    destination = tmp_path / "mesh"
    receipt = GmshProcessBackend().mesh_step(tmp_path / "exact/design.step", destination,
                                           max_size_mm=3, boundary_roles=request)
    assert receipt.physical_groups == ("boundary", "domain", "fixed_end")
    gmsh.initialize(readConfigFiles=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(destination / "design.msh"))
        groups = [(dim, tag) for dim, tag in gmsh.model.getPhysicalGroups()
                  if gmsh.model.getPhysicalName(dim, tag) == "fixed_end"]
        assert len(groups) == 1 and groups[0][0] == 2
        tags, coords = gmsh.model.mesh.getNodesForPhysicalGroup(*groups[0])
        assert len(tags) > 0
        assert all(abs(float(x) + 20.0) < 1e-6 for x in coords[::3])
    finally:
        gmsh.finalize()
    stored = json.loads((destination / "semantic-groups.json").read_text(encoding="utf-8"))
    assert stored["source_step_sha256"] == exact.step_sha256
    assert stored["mesh_sha256"] == receipt.mesh_sha256


@pytest.mark.parametrize("failure", ["wrong_source", "wrong_count"])
def test_role_mismatch_cannot_publish_mesh(tmp_path, failure):
    program, _, _ = golden_programs()["beam"]
    exact = Build123dBackend().export_verified_step(program, tmp_path / "exact")
    request = {"source_step_sha256": "0" * 64 if failure == "wrong_source" else exact.step_sha256,
               "roles": {"fixed_end": {"axis": "x", "side": "min", "expected_surfaces": 2}}}
    destination = tmp_path / "mesh"
    with pytest.raises(GmshMeshingError):
        GmshProcessBackend().mesh_step(tmp_path / "exact/design.step", destination,
                                     max_size_mm=3, boundary_roles=request)
    assert not destination.exists()


@pytest.mark.parametrize("kind", ["invalid", "surface_only"])
def test_non_volume_step_is_rejected_without_publication(tmp_path, kind):
    source = tmp_path / "source.step"
    if kind == "invalid":
        source.write_text("This is not STEP geometry\n", encoding="utf-8")
    else:
        gmsh.initialize(readConfigFiles=False)
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("open_surface")
            gmsh.model.occ.addRectangle(0, 0, 0, 10, 10)
            gmsh.model.occ.synchronize()
            gmsh.write(str(source))
        finally:
            gmsh.finalize()
    destination = tmp_path / "mesh"
    with pytest.raises(GmshMeshingError):
        GmshProcessBackend().mesh_step(source, destination, max_size_mm=3)
    assert not destination.exists()
