"""Pure input and geometric binding checks; no native kernel required."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from core.gmsh_backend import DETERMINISTIC_OPTIONS, GmshMeshReceipt
from core.gmsh_integrity import GmshMeshingError
from core.gmsh_process import _verified_receipt
from core.mesh_roles import bind_roles, validate_roles


def request():
    return {"source_step_sha256": "a" * 64,
            "roles": {"fixed_end": {"axis": "x", "side": "min", "expected_surfaces": 1}}}


@pytest.mark.parametrize("change", [
    lambda x: x.update(source_step_sha256="bad"),
    lambda x: x.update(roles={}),
    lambda x: x["roles"].update(boundary={"axis": "x", "side": "min", "expected_surfaces": 1}),
    lambda x: x["roles"]["fixed_end"].update(index=0),
    lambda x: x["roles"]["fixed_end"].update(axis="q"),
    lambda x: x["roles"]["fixed_end"].update(side="front"),
    lambda x: x["roles"]["fixed_end"].update(expected_surfaces=True),
    lambda x: x["roles"]["fixed_end"].update(expected_surfaces=0),
    lambda x: x["roles"].update({"bad name": x["roles"]["fixed_end"]}),
])
def test_role_requests_reject_invalid_or_index_based_selectors(change):
    value = request()
    change(value)
    with pytest.raises(ValueError):
        validate_roles(value)


def test_request_is_copied_before_native_work():
    value = request()
    normalized = validate_roles(value)
    value["roles"]["fixed_end"]["side"] = "max"
    assert normalized == request()


def fake_kernel(bounds, curved=()):
    added = []
    model = SimpleNamespace(
        getBoundingBox=lambda dim, tag: bounds[tag],
        getType=lambda dim, tag: "Cylinder" if tag in curved else "Plane",
        addPhysicalGroup=lambda dim, tags: added.append((dim, tags)) or len(added),
        setPhysicalName=lambda dim, tag, name: None,
    )
    return SimpleNamespace(model=model), added


def test_geometry_predicate_selects_face_without_persisted_kernel_index():
    kernel, added = fake_kernel({87: (0, 0, 0, 0, 4, 3), 23: (9, 0, 0, 9, 4, 3)})
    assert bind_roles(kernel, [(2, 23), (2, 87)], request()) == {"fixed_end": [87]}
    assert added == [(2, [87])]


@pytest.mark.parametrize("curved,expected", [((), 2), ((87,), 1)])
def test_missing_or_wrong_count_selector_fails_closed(curved, expected):
    kernel, added = fake_kernel({87: (0, 0, 0, 0, 4, 3), 23: (9, 0, 0, 9, 4, 3)}, curved)
    value = deepcopy(request())
    value["roles"]["fixed_end"]["expected_surfaces"] = expected
    with pytest.raises(GmshMeshingError, match="matched"):
        bind_roles(kernel, [(2, 23), (2, 87)], value)
    assert not added


@pytest.mark.parametrize("fault", [None, "source", "mesh", "roles", "tags", "group", "options", "missing"])
def test_supervisor_admits_only_matching_role_receipts(tmp_path, fault):
    # Synthetic transport bytes check admission only, never native geometry.
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    mesh = bundle / "design.msh"
    mesh.write_bytes(b"synthetic transport")
    digest = hashlib.sha256(mesh.read_bytes()).hexdigest()
    groups = ("boundary", "domain", "fixed_end")
    receipt = GmshMeshReceipt(
        backend="gmsh", backend_version="test", source_step_sha256="a" * 64, source_step_bytes=1,
        mesh_path="design.msh", mesh_sha256=digest, mesh_bytes=mesh.stat().st_size,
        volume_entity_count=1, boundary_surface_count=4, node_count=4, volume_element_count=1,
        physical_groups=groups, mesh_size_min_mm=1, mesh_size_max_mm=3, min_sicn=0.5, mean_sicn=0.5,
        roundtrip_node_count=4, roundtrip_volume_element_count=1, roundtrip_physical_groups=groups,
    ).to_dict()
    roles = {"receipt_version": "neurocad-mesh-roles-v1", **request(),
             "surface_tags": {"fixed_end": [87]}, "mesh_sha256": digest,
             "selector_tolerance_mm": 1e-6, "meshing_options": dict(DETERMINISTIC_OPTIONS)}
    if fault == "source":
        roles["source_step_sha256"] = "b" * 64
    elif fault == "mesh":
        roles["mesh_sha256"] = "b" * 64
    elif fault == "roles":
        roles["roles"]["fixed_end"]["side"] = "max"
    elif fault == "tags":
        roles["surface_tags"]["fixed_end"] = [True]
    elif fault == "group":
        receipt["physical_groups"] = receipt["roundtrip_physical_groups"] = ["boundary", "domain"]
    elif fault == "options":
        roles["meshing_options"]["Mesh.RandomSeed"] = 2
    (bundle / "meshing-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    if fault != "missing":
        (bundle / "semantic-groups.json").write_text(json.dumps(roles), encoding="utf-8")
    if fault is None:
        assert _verified_receipt(bundle, "a" * 64, 1, 1, 3, request()).physical_groups == groups
    else:
        with pytest.raises(GmshMeshingError):
            _verified_receipt(bundle, "a" * 64, 1, 1, 3, request())
