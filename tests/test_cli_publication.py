from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import neurocad_cli as cli
from core import artifacts
from core.ir_parser import serialize_ir_json
from text_to_cad import TextToCAD

PROMPT = "a 40 x 30 x 3 mm plate"
WINNER = b"completed artifact from another writer\n"
CASES = [
    ("create", "output"),
    ("create", "manifest"),
    ("export-scad", "output"),
    ("export-json", "output"),
    ("export-stl", "output"),
    ("export-scad", "manifest"),
    ("verify", "report"),
    ("verify", "scad"),
    ("ir", "output"),
    ("compile-json", "output"),
    ("compile-scad", "output"),
    ("compile-stl", "output"),
]


def command_arguments(kind: str, root: Path) -> list[str]:
    if kind == "create":
        return [kind, PROMPT, "-o", str(root / "output.scad"), "--manifest", str(root / "manifest.json")]
    if kind.startswith("export-"):
        format_name = kind.removeprefix("export-")
        return [
            "export", PROMPT, "--format", format_name,
            "-o", str(root / f"output.{format_name}"), "--manifest", str(root / "manifest.json"),
        ]
    if kind == "verify":
        return [kind, PROMPT, "--json-output", str(root / "report.json"), "--scad-output", str(root / "output.scad")]
    if kind == "ir":
        return [kind, PROMPT, "-o", str(root / "output.json")]
    format_name = kind.removeprefix("compile-")
    source = root / "source.json"
    source.write_text(serialize_ir_json(TextToCAD().build(PROMPT).require_program()), encoding="utf-8")
    return ["compile", str(source), "--format", format_name, "-o", str(root / f"output.{format_name}")]


@pytest.mark.parametrize("kind,target", CASES)
@pytest.mark.parametrize("force", [False, True])
def test_public_cli_preserves_concurrent_output_unless_forced(tmp_path, monkeypatch, kind, target, force):
    arguments = command_arguments(kind, tmp_path)
    if force:
        arguments.append("--force")
    original_admission = cli._require_new_paths
    observed = []

    def publish_after_admission(*, force, **paths):
        original_admission(force=force, **paths)
        destination = paths[target]
        destination.write_bytes(WINNER)
        observed.append(destination)

    def compiled_fixture(source, output, *, timeout):
        output.write_bytes(b"verified fixture mesh\n")
        return subprocess.CompletedProcess(["openscad-fixture"], 0, "", "")

    monkeypatch.setattr(cli, "_require_new_paths", publish_after_admission)
    monkeypatch.setattr(artifacts, "compile_scad", compiled_fixture)
    monkeypatch.setattr(artifacts, "verify_stl", lambda *args, **kwargs: {"kernel_validity": True})

    with pytest.raises(SystemExit) as exit_info:
        cli.main(arguments)
    status = exit_info.value.code

    assert len(observed) == 1
    if force:
        assert status == 0
        assert observed[0].read_bytes() != WINNER
    else:
        assert observed[0].read_bytes() == WINNER
        assert status == 2
    assert not list(tmp_path.glob(".*"))


def test_verified_mesh_collision_does_not_replace_a_symlink(tmp_path, monkeypatch):
    source = tmp_path / "part.scad"
    source.write_text("cube([1, 1, 1]);\n", encoding="utf-8")
    target = tmp_path / "other.stl"
    target.write_bytes(WINNER)
    output = tmp_path / "part.stl"

    def compiled_fixture(source, temporary, *, timeout):
        temporary.write_bytes(b"verified fixture mesh\n")
        return subprocess.CompletedProcess(["openscad-fixture"], 0, "", "")

    def verify_fixture(*args, **kwargs):
        output.symlink_to(target)
        return {"kernel_validity": True}

    monkeypatch.setattr(artifacts, "compile_scad", compiled_fixture)
    monkeypatch.setattr(artifacts, "verify_stl", verify_fixture)
    with pytest.raises(FileExistsError):
        artifacts.compile_scad_verified(source, output, overwrite=False)
    assert output.is_symlink()
    assert target.read_bytes() == WINNER
    assert not list(tmp_path.glob(".*"))
