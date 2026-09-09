"""Real HTTP edit proposals share the CLI's validated revision contract."""

import hashlib
import http.client
import json
import shutil
import threading
from collections.abc import Iterator

import pytest

from core.demo_server import DemoHandler, DemoServer, generate_demo_payload, preview_project_edit
from core.project import parse_project, serialize_project

SOURCE = (
    "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
    "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm"
)


@pytest.fixture
def server() -> Iterator[DemoServer]:
    instance = DemoServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


def post(server: DemoServer, payload: dict, *, path: str = "/api/edit", origin: str | None = None) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=270)
    headers = {"Content-Type": "application/json"}
    if origin is not None:
        headers["Origin"] = origin
    try:
        connection.request("POST", path, json.dumps(payload), headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def project_text() -> str:
    return json.dumps(generate_demo_payload(SOURCE, "enclosure")["project"])


def test_proposal_is_bound_to_original_and_uses_canonical_revision(server: DemoServer) -> None:
    source = project_text()
    status, payload = post(server, {"source": source, "instruction": "set wall thickness to 2.4 mm", "reason": "stronger shell"})
    assert status == 200
    original = parse_project(source)
    revised = parse_project(json.dumps(payload["project"]))
    assert original.revision == 1 and original.spec.wall_mm == 2
    assert revised.revision == 2 and revised.spec.wall_mm == 2.4
    assert revised.source_text == SOURCE
    assert revised.changes[-1].reason == "stronger shell"
    assert payload["evaluation"]["kernel_validity"] is None
    assert "mesh_artifacts" not in payload
    assert payload["edit"] == {
        "base_revision": 1,
        "base_project_sha256": hashlib.sha256(serialize_project(original).encode()).hexdigest(),
        "changes": [{"field": "wall_mm", "before": 2, "after": 2.4}],
        "reason": "stronger shell",
    }


@pytest.mark.parametrize("extra", [
    {"instruction": "make it better"}, {"instruction": "set wall thickness to 40 mm"},
    {"instruction": "set wall thickness to 2 mm"}, {"instruction": "x" * 513},
    {"instruction": None}, {"instruction": []}, {"instruction": True},
    {"instruction": "rename good", "reason": " "}, {"instruction": "rename good", "reason": False},
    {"instruction": "rename good", "compile_mesh": True},
])
def test_invalid_proposals_fail_and_the_server_recovers(server: DemoServer, extra: dict) -> None:
    source = project_text()
    status, payload = post(server, {"source": source, **extra})
    assert status == 400 and "error" in payload
    status, payload = post(server, {"source": source, "instruction": "rename recovered"})
    assert status == 200 and payload["project"]["revision"] == 2


def test_proposals_retain_origin_and_history_validation(server: DemoServer) -> None:
    source = project_text()
    assert post(server, {"source": source, "instruction": "rename good"}, origin="https://evil.example")[0] == 403
    forged = json.loads(source)
    forged["revision"] = 999
    assert post(server, {"source": json.dumps(forged), "instruction": "rename good"})[0] == 400


def test_add_move_remove_and_resize_reopen_with_complete_history() -> None:
    source = project_text()
    for revision, instruction in enumerate([
        "resize enclosure to 90 x 65 x 32 mm",
        "add circular cutout power 8 mm diameter on rear at 12 x 9 mm",
        "move cutout power to 10 x 9 mm", "remove cutout power",
    ], start=2):
        payload = preview_project_edit(source, instruction)
        source = json.dumps(payload["project"])
        project = parse_project(source)
        assert project.revision == revision
        assert len(project.changes) == revision - 1
        assert project.source_text == SOURCE
    assert not project.spec.cutouts
    assert project.spec.outer_size_mm == (90, 65, 32)


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD required")
def test_http_proposal_compiles_the_revised_project_and_downloads_exact_mesh(server: DemoServer) -> None:
    status, edited = post(server, {"source": project_text(), "instruction": "set wall thickness to 2.4 mm"})
    assert status == 200
    status, compiled = post(server, {
        "source": json.dumps(edited["project"]), "source_type": "project", "compile_mesh": True,
    }, path="/api/generate")
    assert status == 200
    assert compiled["evaluation"]["kernel_validity"] is True
    assert compiled["spec"]["wall_mm"] == 2.4
    assert set(compiled["mesh_artifacts"]) == {"body", "lid"}
    for artifact in compiled["mesh_artifacts"].values():
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        try:
            connection.request("GET", artifact["download_url"])
            response = connection.getresponse()
            assert response.status == 200
            assert hashlib.sha256(response.read()).hexdigest() == artifact["sha256"]
            assert artifact["verification"]["enclosure_features"]["valid"]
        finally:
            connection.close()


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD required")
@pytest.mark.parametrize("mode,source,parts", [
    ("prompt", "a 40 x 30 x 3 mm plate with four 3 mm holes", {"model"}),
    ("enclosure", "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; no lid", {"body"}),
    ("enclosure", ("80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
     "screw lid 2.5 mm thick clearance 0.3 mm M3 fasteners at corners inset 8 mm"), {"body", "lid"}),
    ("enclosure", SOURCE + "; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C; "
     "vent grid 2 x 3 holes 2 mm diameter pitch 4 mm on rear at 0 x 8 mm; "
     "4 M3 standoffs 6 mm high at corners inset 8 mm", {"body", "lid"}),
])
def test_supported_workbench_family_acceptance(server: DemoServer, mode: str, source: str, parts: set[str]) -> None:
    status, payload = post(server, {
        "source": source, "source_type": mode, "compile_mesh": True, "timeout_seconds": 120,
    }, path="/api/generate")
    assert status == 200, payload
    assert payload["evaluation"]["kernel_validity"] is True
    assert set(payload["mesh_artifacts"]) == parts
    if mode == "enclosure":
        project = parse_project(json.dumps(payload["project"]))
        reopened = generate_demo_payload(serialize_project(project), "project")
        assert reopened["project"] == payload["project"]
        assert reopened["scad"] == payload["scad"]
    for artifact in payload["mesh_artifacts"].values():
        if mode == "enclosure":
            assert artifact["verification"]["enclosure_features"]["valid"]
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        try:
            connection.request("GET", artifact["download_url"])
            response = connection.getresponse()
            assert response.status == 200
            assert hashlib.sha256(response.read()).hexdigest() == artifact["sha256"]
        finally:
            connection.close()
