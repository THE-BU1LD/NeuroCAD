from __future__ import annotations

import json

import pytest

pytest.importorskip("gmsh")
import gmsh  # noqa: E402

from core.gmsh_backend import GmshBackend


def _write_box_step(path) -> None:
    gmsh.initialize(readConfigFiles=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("source-box")
        gmsh.model.occ.addBox(0.0, 0.0, 0.0, 20.0, 10.0, 5.0)
        gmsh.model.occ.synchronize()
        gmsh.write(str(path))
    finally:
        gmsh.finalize()


def test_gmsh_meshes_step_with_named_domain_and_boundary(tmp_path) -> None:
    source = tmp_path / "box.step"
    _write_box_step(source)

    destination = tmp_path / "mesh-bundle"
    receipt = GmshBackend().mesh_step(
        source,
        destination,
        min_size_mm=1.0,
        max_size_mm=4.0,
    )

    assert receipt.backend == "gmsh"
    assert receipt.volume_entity_count == 1
    assert receipt.boundary_surface_count == 6
    assert receipt.node_count > 0
    assert receipt.volume_element_count > 0
    assert receipt.roundtrip_node_count == receipt.node_count
    assert receipt.roundtrip_volume_element_count == receipt.volume_element_count
    assert receipt.physical_groups == ("boundary", "domain")
    assert receipt.roundtrip_physical_groups == receipt.physical_groups
    assert receipt.min_sicn is not None
    assert receipt.mean_sicn is not None
    assert (destination / "design.msh").is_file()
    receipt_path = destination / "meshing-receipt.json"
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["receipt_version"] == "neurocad-gmsh-mesh-receipt-v1"
    assert payload["mesh_sha256"] == receipt.mesh_sha256


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (0.0, 1.0),
        (2.0, 1.0),
        (1.0, float("inf")),
    ],
)
def test_gmsh_rejects_invalid_mesh_sizes(tmp_path, minimum: float, maximum: float) -> None:
    source = tmp_path / "box.step"
    _write_box_step(source)
    with pytest.raises(ValueError):
        GmshBackend().mesh_step(
            source,
            tmp_path / "bad-mesh",
            min_size_mm=minimum,
            max_size_mm=maximum,
        )
    assert not (tmp_path / "bad-mesh").exists()


def test_gmsh_refuses_existing_output_directory(tmp_path) -> None:
    source = tmp_path / "box.step"
    _write_box_step(source)
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        GmshBackend().mesh_step(source, destination, max_size_mm=4.0)


def test_gmsh_rejects_symlinked_step_input(tmp_path) -> None:
    source = tmp_path / "box.step"
    _write_box_step(source)
    alias = tmp_path / "alias.step"
    try:
        alias.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(FileNotFoundError, match="regular file"):
        GmshBackend().mesh_step(alias, tmp_path / "mesh", max_size_mm=4.0)


def test_gmsh_cli_generates_verified_mesh_bundle(tmp_path, capsys) -> None:
    from neurocad_cli import build_parser

    source = tmp_path / "cli-box.step"
    _write_box_step(source)
    destination = tmp_path / "cli-mesh"
    args = build_parser().parse_args(
        [
            "mesh",
            "step",
            str(source),
            "--output-dir",
            str(destination),
            "--min-size",
            "1",
            "--max-size",
            "4",
        ]
    )
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "gmsh"
    assert payload["physical_groups"] == ["boundary", "domain"]
    assert payload["roundtrip_volume_element_count"] == payload["volume_element_count"]
    assert (destination / "design.msh").is_file()
