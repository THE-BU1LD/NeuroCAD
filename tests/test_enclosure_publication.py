"""A new enclosure artifact must never overwrite a concurrent writer's file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.conversational_parser import apply_proposal, parse_conversation
from core.edit_language import edit_project_from_text
from core.enclosure import EnclosureSpec, LidSpec
from core.project import EnclosureProject, write_project
from core.workflow import project_from_interpretation
from neurocad_cli import main

PROMPT = (
    "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
    "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm"
)


@pytest.mark.parametrize("command", [
    "understand-local", "understand-provider", "apply-proposal", "edit", "interpret-project", "interpret-analysis",
])
def test_enclosure_publication_preserves_file_created_after_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: str,
) -> None:
    project = EnclosureProject("publication-fixture", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
    ))
    baseline = tmp_path / "baseline.json"
    write_project(baseline, project)
    before = baseline.read_bytes()
    output = tmp_path / "new-artifact.json"
    other_writer = "Completed by another writer: π\n".encode()

    if command.startswith("understand"):
        arguments = ["enclosure", "understand", str(baseline), "walls 3mm", "-o", str(output)]
        if command == "understand-local":
            target = "core.conversational_parser.parse_conversation"
            operation = parse_conversation
        else:
            arguments += ["--provider-url", "https://example.test/v1/chat/completions", "--model", "fixture-only"]
            target = "core.language_provider.ChatLanguageProvider.interpret"

            def operation(provider, source, current_project, **kwargs):
                # The provider is a local stub; no transport or model call occurs.
                return parse_conversation(source, current_project)
    elif command == "apply-proposal":
        proposal = tmp_path / "reviewed-proposal.json"
        proposal.write_text(json.dumps(parse_conversation("walls 3mm", project).to_dict()), encoding="utf-8")
        arguments = ["enclosure", "apply-proposal", str(baseline), str(proposal), "-o", str(output), "--confirm"]
        target = "core.conversational_parser.apply_proposal"
        operation = apply_proposal
    elif command == "edit":
        arguments = ["enclosure", "edit", str(baseline), "--instruction", "set wall thickness to 3 mm", "-o", str(output)]
        target = "core.edit_language.edit_project_from_text"
        operation = edit_project_from_text
    else:
        arguments = ["enclosure", "interpret", PROMPT, "--project-output", str(output)]
        if command == "interpret-analysis":
            arguments[-1] = str(tmp_path / "new-project.json")
            arguments += ["--output", str(output)]
        target = "core.workflow.project_from_interpretation"
        operation = project_from_interpretation

    def complete_with_competing_output(*args, **kwargs):
        result = operation(*args, **kwargs)
        # Admission has already succeeded. The expensive interpretation/review
        # finishes after another process has published its own complete file.
        output.write_bytes(other_writer)
        return result

    monkeypatch.setattr(target, complete_with_competing_output)
    with pytest.raises(SystemExit) as exit_status:
        main(arguments)
    captured = capsys.readouterr()
    assert output.read_bytes() == other_writer
    assert baseline.read_bytes() == before
    assert exit_status.value.code == 2
    assert "refusing to overwrite" in captured.err
    assert str(output) not in captured.out
    assert not list(tmp_path.glob(".new-artifact.json.*"))
