"""Real optional-kernel interoperability; not solver or safety validation."""
from __future__ import annotations

import hashlib
import json

import pytest

pytest.importorskip("build123d")
pytest.importorskip("gmsh")

from core.exact_build123d import Build123dBackend
from core.feature_ir import EntitySelector, Feature, FeatureProgram, serialize_feature_ir_json
from core.gmsh_backend import GmshBackend
from core.mesh_cli import build_parser as build_mesh_parser
from neurocad_cli import build_parser


def _program(kind: str) -> FeatureProgram:
    body = Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 12.0, 6.0]})
    if kind == "box":
        features = (body,)
    elif kind == "filleted_box":
        features = (
            body,
            Feature(
                id="rounded", kind="fillet", inputs=("body",), parameters={"radius": 1.0},
                selectors=(EntitySelector(
                    entity="edge", generated_by="body",
                    predicates=({"kind": "parallel_to", "axis": [0.0, 0.0, 1.0]},),
                    role="vertical_edges", unique=False,
                ),),
            ),
        )
    else:
        assert kind == "holed_plate"
        features = (
            Feature(id="profile", kind="sketch", parameters={
                "plane": "XY", "constraints": [], "entities": [
                    {"kind": "rectangle", "width": 20.0, "height": 12.0,
                     "operation": "add", "center": [0.0, 0.0]},
                    {"kind": "circle", "radius": 2.0, "operation": "subtract", "center": [0.0, 0.0]},
                ],
            }),
            Feature(id="plate", kind="extrude", inputs=("profile",),
                    parameters={"distance": 4.0, "operation": "new"}),
        )
    return FeatureProgram(title=f"CAD-to-mesh {kind}", parameters=(), features=features,
                          outputs=(features[-1].id,), metadata={"fixture": kind})


def _check_mesh(receipt, source, destination, step_hash: str) -> None:
    assert receipt.source_step_sha256 == step_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt.source_step_bytes == source.stat().st_size
    assert receipt.volume_entity_count == 1
    assert receipt.node_count == receipt.roundtrip_node_count > 0
    assert receipt.volume_element_count == receipt.roundtrip_volume_element_count > 0
    assert receipt.physical_groups == receipt.roundtrip_physical_groups == ("boundary", "domain")
    assert receipt.min_sicn is not None and receipt.min_sicn > 0.0
    assert receipt.roundtrip_verification == "nodes-connectivity-physical-membership-v1"
    assert receipt.mesh_sha256 == hashlib.sha256((destination / "design.msh").read_bytes()).hexdigest()
    stored = json.loads((destination / "meshing-receipt.json").read_text(encoding="utf-8"))
    assert stored == receipt.to_dict()


@pytest.mark.parametrize("kind", ["box", "holed_plate", "filleted_box"])
def test_exact_cad_step_is_meshable_without_losing_provenance(tmp_path, kind):
    exact_dir, mesh_dir = tmp_path / "exact", tmp_path / "mesh"
    exact = Build123dBackend().export_verified_step(_program(kind), exact_dir)
    assert exact.inspection.valid_brep
    assert exact.roundtrip_inspection is not None and exact.roundtrip_inspection.valid_brep
    source = exact_dir / "design.step"
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in exact_dir.iterdir() if p.is_file()}
    mesh = GmshBackend().mesh_step(source, mesh_dir, min_size_mm=0.5, max_size_mm=3.0)
    _check_mesh(mesh, source, mesh_dir, exact.step_sha256)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in exact_dir.iterdir() if p.is_file()}
    assert before == after


def test_both_cli_commands_form_one_hash_bound_pipeline(tmp_path, capsys):
    program_path = tmp_path / "part.ncad2.json"
    program_path.write_text(serialize_feature_ir_json(_program("box")), encoding="utf-8")
    exact_dir, mesh_dir = tmp_path / "exact", tmp_path / "mesh"
    parser = build_parser()
    exact_args = parser.parse_args(["feature", "build", str(program_path), "--output-dir", str(exact_dir)])
    assert exact_args.func(exact_args) == 0
    exact = json.loads(capsys.readouterr().out)
    source = exact_dir / "design.step"
    mesh_args = build_mesh_parser().parse_args(["step", str(source), "--output-dir", str(mesh_dir), "--max-size", "3"])
    assert mesh_args.func(mesh_args) == 0
    mesh = json.loads(capsys.readouterr().out)
    assert exact["step_sha256"] == mesh["source_step_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert mesh["volume_element_count"] == mesh["roundtrip_volume_element_count"] > 0
    assert (mesh_dir / "design.msh").is_file()
    assert (exact_dir / "build-receipt.json").is_file()

    execution = json.loads((mesh_dir / "execution-receipt.json").read_text(encoding="utf-8"))
    assert execution["receipt_version"] == "neurocad-gmsh-worker-execution-v1"
    assert execution["status"] == "success" and execution["worker_returncode"] == 0
    assert execution["timeout_seconds"] == 120.0
    assert execution["source_step_sha256"] == mesh["source_step_sha256"]
    assert execution["mesh_sha256"] == mesh["mesh_sha256"]
    assert execution["meshing_receipt_sha256"] == hashlib.sha256((mesh_dir / "meshing-receipt.json").read_bytes()).hexdigest()
