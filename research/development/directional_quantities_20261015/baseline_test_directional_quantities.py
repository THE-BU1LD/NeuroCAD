"""Adversarial maintenance cases; no protected language evaluation."""
import pytest

from core.conversational_parser import parse_conversation
from core.enclosure import EnclosureSpec, LidSpec
from core.project import EnclosureProject, serialize_project


@pytest.fixture
def project():
    return EnclosureProject("directional-review", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2,
        profile="fdm_standard", lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
    ))


@pytest.mark.parametrize("source", [
    "increase wall thickness one mm",
    "decrease wall thickness three mm",
    "increase walls at one mm",
    "decrease walls be three mm",
    "increase wall thickness to one mm",
    "decrease wall thickness to three mm",
    "increase wall thickness to two mm",
    "decrease wall thickness to two mm",
    "increase wall thickness by zero mm",
    "decrease wall thickness by zero mm",
    "increase wall thickness by 0.0000000000000000000001 mm",
    "decrease wall thickness by 0.0000000000000000000001 mm",
    "set wall thickness to three mm and decrease floor thickness to three mm",
])
def test_directional_ambiguity_or_contradiction_never_publishes_candidate(project, source):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.status == "clarification", result.to_dict()
    assert result.candidate is None
    assert serialize_project(project) == before


@pytest.mark.parametrize("source,expected", [
    ("increase walls to three mm", 3),
    ("decrease walls to one point five mm", 1.5),
    ("increase wall thickness by one mm", 3),
    ("decrease wall thickness by zero point five mm", 1.5),
    ("decrease wall thickness to zero point one cm", 1),
    ("increase wall thickness to zero point three cm", 3),
    ("set walls to two mm", 2),
    ("walls at three mm", 3),
    ("increase walls to four mm no actually three mm", 3),
])
def test_explicit_target_and_delta_controls(project, source, expected):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.status == "proposal", result.to_dict()
    assert result.candidate.spec.wall_mm == expected
    assert result.candidate.spec.floor_mm == project.spec.floor_mm
    assert serialize_project(project) == before
