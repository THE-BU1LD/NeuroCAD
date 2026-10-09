"""CLI wrappers retain destination identity before no-replacement publication."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.conversational_parser import parse_conversation
from core.enclosure import EnclosureSpec, LidSpec
from core.project import EnclosureProject, write_project
from neurocad_cli import main

PROMPT = (
    "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
    "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm"
)
COMMANDS = [
    "direct", "generate", "build", "exchange", "understand-local", "understand-provider",
    "apply-proposal", "edit", "interpret-project", "interpret-analysis", "nlp-project", "nlp-analysis",
]


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("existing_link", [True, False], ids=["dangling-link", "new-output"])
def test_cli_preserves_dangling_output_leaf_and_accepts_new_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    command: str, existing_link: bool,
) -> None:
    monkeypatch.setenv("NEUROCAD_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("NEUROCAD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NEUROCAD_STATE_DIR", str(tmp_path / "state"))
    project = EnclosureProject("leaf-admission", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
    ))
    baseline = tmp_path / "baseline.json"
    write_project(baseline, project)
    baseline_bytes = baseline.read_bytes()
    output = tmp_path / "new-output"
    target = tmp_path / "other-writer-target"
    if existing_link:
        try:
            output.symlink_to(target, target_is_directory=command in {"direct", "generate", "build", "exchange"})
        except (OSError, NotImplementedError):
            pytest.skip("destination symlink creation is unavailable")
        original_inode = output.lstat().st_ino

    if command in {"direct", "generate"}:
        arguments = ["a", "20", "x", "30", "x", "4", "mm", "plate", "--local", "--format", "ir", "-o", str(output)]
        if command == "generate":
            arguments.insert(0, "generate")
    elif command in {"build", "exchange"}:
        group, action = ("enclosure", "build") if command == "build" else ("integrations", "export")
        arguments = [group, action, str(baseline), "--output-dir", str(output)]
    elif command.startswith("understand"):
        arguments = ["enclosure", "understand", str(baseline), "walls 3mm", "-o", str(output)]
        if command == "understand-provider":
            arguments += ["--provider-url", "https://example.test/v1/chat/completions", "--model", "fixture-only"]

            def interpret(provider, source, current_project, **kwargs):
                return parse_conversation(source, current_project)

            monkeypatch.setattr("core.language_provider.ChatLanguageProvider.interpret", interpret)
    elif command == "apply-proposal":
        proposal = tmp_path / "reviewed-proposal.json"
        proposal.write_text(json.dumps(parse_conversation("walls 3mm", project).to_dict()), encoding="utf-8")
        arguments = ["enclosure", "apply-proposal", str(baseline), str(proposal), "-o", str(output), "--confirm"]
    elif command == "edit":
        arguments = ["enclosure", "edit", str(baseline), "--instruction", "set wall thickness to 3 mm", "-o", str(output)]
    else:
        arguments = ["nlp"] if command.startswith("nlp") else ["enclosure", "interpret"]
        arguments += [PROMPT, "--project-output" if command.endswith("project") else "--output", str(output)]

    with pytest.raises(SystemExit) as exit_status:
        main(arguments)
    captured = capsys.readouterr()
    assert baseline.read_bytes() == baseline_bytes
    if existing_link:
        assert exit_status.value.code == 2, "the CLI accepted another writer's dangling destination link"
        assert output.is_symlink() and output.lstat().st_ino == original_inode
        assert not target.exists(), "the CLI published into the other writer's missing target"
        assert "already exists" in captured.err
        assert not list(tmp_path.glob(".new-output.*"))
    else:
        assert exit_status.value.code == 0, captured.err
        assert output.exists() and not output.is_symlink()
        assert not target.exists()
