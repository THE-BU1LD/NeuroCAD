import hashlib
import io
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.demo_server import generate_demo_payload
from core.integrations.handoff import _verified_spec
from core.integrations.kicad import read_kicad_handoff, write_bound_kicad_extraction
from core.integrations.kicad_file import write_kicad_file_receipt
from core.json_io import read_bounded_utf8
from core.mesh_preview import compile_payload_meshes
from core.project import MAX_PROJECT_BYTES, parse_project, read_project, serialize_project, update_project

SOURCE = "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm"


def test_enclosure_project_roundtrip_preserves_revisions_and_source() -> None:
    original = generate_demo_payload(SOURCE, "enclosure")
    project = parse_project(json.dumps(original["project"]))
    revised = update_project(project, "wall_mm", 2.4, reason="stronger shell")
    reopened = generate_demo_payload(serialize_project(revised), "project")
    assert reopened["project"] == revised.to_dict()
    assert reopened["prompt"] == SOURCE
    assert reopened["spec"]["wall_mm"] == 2.4
    assert reopened["scad"] != original["scad"]
    assert reopened["evaluation"]["kernel_validity"] is None


def test_huge_revision_is_rejected_without_allocating_a_revision_range() -> None:
    value = generate_demo_payload(SOURCE, "enclosure")["project"]
    value["revision"] = 10**100
    with pytest.raises(ValueError, match="one ordered record"):
        parse_project(json.dumps(value))


@pytest.mark.parametrize("project_reader", [False, True])
def test_file_limits_are_applied_before_reading_entire_input(project_reader: bool) -> None:
    class BoundedRead(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            assert size == MAX_PROJECT_BYTES + 1
            return super().read(size)

    stream = BoundedRead(b" " * (MAX_PROJECT_BYTES + 2))
    with patch.object(Path, "open", return_value=stream), pytest.raises(ValueError, match="limit"):
        if project_reader:
            read_project(Path("oversized.json"))
        else:
            read_bounded_utf8(Path("oversized.json"), max_bytes=MAX_PROJECT_BYTES, label="test input")


def test_bounded_reader_preserves_utf8_and_rejects_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "input.json"
    path.write_bytes("μm".encode())
    assert read_bounded_utf8(path, max_bytes=3, label="test") == "μm"
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        read_bounded_utf8(path, max_bytes=3, label="test")


@pytest.mark.parametrize("reader", ["handoff", "draft", "review"])
def test_kicad_reads_are_bounded_even_if_file_grows_after_stat(reader: str) -> None:
    class BoundedRead(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            assert size == MAX_PROJECT_BYTES + 1
            return super().read(size)

    stream = BoundedRead(b" " * (MAX_PROJECT_BYTES + 2))
    with (
        patch.object(Path, "open", return_value=stream),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "stat", return_value=SimpleNamespace(st_size=1)),
        pytest.raises(ValueError, match="limited to 1 MiB"),
    ):
        if reader == "handoff":
            read_kicad_handoff(Path("receipt.json"))
        elif reader == "draft":
            write_bound_kicad_extraction(Path("out.json"), Path("draft.json"), Path("board.kicad_pcb"))
        else:
            write_kicad_file_receipt(Path("out.json"), Path("board.kicad_pcb"), Path("review.json"))


def test_bundle_spec_hash_is_bound_to_parsed_bytes(tmp_path: Path) -> None:
    spec = generate_demo_payload(SOURCE, "enclosure")["spec"]
    raw = json.dumps(spec).encode()
    path = tmp_path / "spec.json"
    path.write_bytes(raw)
    manifest = {
        "source": {
            "spec_filename": path.name,
            "spec_sha256": hashlib.sha256(raw).hexdigest(),
            "spec_version": spec["version"],
            "profile": spec["profile"],
        },
        "title": spec["title"],
        "units": spec["units"],
    }
    with patch("core.integrations.handoff.sha256_file", side_effect=AssertionError("must hash the parsed bytes")):
        assert _verified_spec(manifest, tmp_path.resolve()).wall_mm == 2


@pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD required")
def test_revised_project_mesh_uses_current_spec_not_historical_prompt() -> None:
    project = parse_project(json.dumps(generate_demo_payload(SOURCE, "enclosure")["project"]))
    project = update_project(project, "wall_mm", 2.4, reason="stronger shell")
    payload = compile_payload_meshes(generate_demo_payload(serialize_project(project), "project"))
    assert payload["evaluation"]["kernel_validity"] is True
    for artifact in payload["mesh_artifacts"].values():
        assert artifact["verification"]["enclosure_features"]["valid"]
