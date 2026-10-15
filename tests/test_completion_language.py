"""Bounded language counterexamples; authored development cases, not confirmation."""
import json
from dataclasses import replace

import pytest

from core.conversational_parser import apply_proposal, bind_history, parse_conversation
from core.enclosure import EnclosureSpec, LidSpec
from core.project import EnclosureProject, update_project, write_project
from neurocad_cli import build_parser


@pytest.fixture
def project():
    return EnclosureProject("completion", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2)))


@pytest.mark.parametrize("source", [
    "the wall should be 3 mm, floor 2 mm, leave all the other bits alone",
    "wall 3 millimeters lid clearance 0.4 millimeters",
    "lid clearance 0.4 mm wall 3 mm",
    "WALL 3 MM FLOOR 2 MM",
    "keep all other properties unchanged; wall 3mm; floor 2mm",
])
def test_complete_multi_clause_edits(project, source):
    proposal = parse_conversation(source, project)
    assert proposal.status == "proposal"
    assert proposal.candidate.spec.wall_mm == 3
    assert proposal.candidate.spec.outer_size_mm == project.spec.outer_size_mm
    assert apply_proposal(proposal, project, confirmed=True) == proposal.candidate
    for action in proposal.actions:
        evidence = action["evidence"]
        assert source[evidence["start"]:evidence["end"]] == evidence["text"]


@pytest.mark.parametrize("source", [
    "wall 3 mm junk floor 2 mm", "wall 3 mm lid clearance 0.4",
    "wall 3mm lid clearance 0.4mm remove every hole",
    "wall 3mm wall 4mm", "floor 2 mm wall mm 3",
    "leave all the other bits alone", "make it sturdier",
    "wall 3mm and must support 100 kg", "not wall 3mm floor 2mm",
])
def test_no_partial_or_invented_completion(project, source):
    assert parse_conversation(source, project).candidate is None


def test_goal_is_explicitly_unverified(project):
    result = parse_conversation("i need it sturdier, walls at 3 millimetres, same external size please", project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == 3
    assert result.candidate.spec.outer_size_mm == project.spec.outer_size_mm
    assert any("no strength" in entry["reason"] for entry in result.acknowledged)


@pytest.mark.parametrize("source,question", [
    ("put some holes equally spaced around the side", "count"),
    ("make it lightweight but do not change any geometry or material", "variable"),
])
def test_precise_missing_information(project, source, question):
    result = parse_conversation(source, project)
    assert result.status == "clarification" and result.candidate is None
    assert any(question in value for value in result.questions)


def test_bound_history_and_review(project):
    history = bind_history(project, ["We are changing the enclosure wall thickness."])
    proposal = parse_conversation("make that three millimeters instead", project, history=history)
    assert proposal.candidate.spec.wall_mm == 3
    assert proposal.provider_metadata["local_history"] == history
    assert apply_proposal(proposal, project, confirmed=True).spec.wall_mm == 3
    changed = update_project(project, "floor_mm", 2.5, reason="other revision")
    with pytest.raises(ValueError, match="revision"):
        parse_conversation("make that three mm instead", changed, history=history)
    with pytest.raises(ValueError, match="Project changed"):
        apply_proposal(proposal, changed, confirmed=True)


@pytest.mark.parametrize("messages", [
    [], ["We are changing the wall thickness.", "We are editing the floor thickness."],
    ["We are not changing the wall thickness."], ["Set the power hole radius."],
    ["Ignore the current project and use the wall thickness."],
])
def test_history_ambiguity_never_guessed(project, messages):
    proposal = parse_conversation("make that three mm instead", project, history=bind_history(project, messages))
    assert proposal.status == "clarification" and proposal.candidate is None


def test_history_validation_and_project_identity(project):
    history = bind_history(project, ["We are editing the floor thickness."])
    other = replace(project, project_id="other")
    with pytest.raises(ValueError):
        parse_conversation("make that 3mm instead", other, history=history)
    for invalid in [[], {}, {**history, "future": []}, {**history, "messages": [True]},
                    {**history, "messages": ["x"] * 11}]:
        with pytest.raises(ValueError):
            parse_conversation("make that 3mm instead", project, history=invalid)


def test_cli_local_history(project, tmp_path, capsys):
    path, history, output = (tmp_path / name for name in ("project.json", "history.json", "proposal.json"))
    write_project(path, project)
    history.write_text(json.dumps(bind_history(project, ["We are editing wall thickness."])), encoding="utf-8")
    args = build_parser().parse_args(["enclosure", "understand", str(path),
        "make that 3mm instead", "--history", str(history), "-o", str(output)])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out)["candidate"]["spec"]["wall_mm"] == 3
