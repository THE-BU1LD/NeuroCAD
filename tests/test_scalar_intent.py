"""Authored scalar-intent regression cases; not independent language evaluation."""
from dataclasses import replace

import pytest

from core.conversational_parser import apply_proposal, parse_conversation, review_saved_proposal
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.project import EnclosureProject, enclosure_spec_to_dict, serialize_project


@pytest.fixture
def project():
    return EnclosureProject("scalar-intent", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
        cutouts=(CutoutSpec("power", "circular", "front", (0, 10), diameter_mm=4),),
    ))


@pytest.mark.parametrize("source", [
    "dont change the floor, only wall thickness to 3mm",
    "do not change floor thickness and walls three mm",
    "keep the floor unchanged; make walls 3mm",
    "preserve the floor thickness and walls 3mm",
    "only make the walls three millimeters thick",
    "only add one mm to wall thickness",
    "not 4mm walls, make them 3mm",
    "not four millimeters wall thickness; set it to three mm",
    "not 0.4cm walls but set wall thickness to 3mm",
    "not 4mm walls, only make them 3mm",
    "not 4mm walls, set wall thickness 3mm; keep floor unchanged",
    "increase walls to four mm no actually three mm",
])
def test_supported_request_changes_only_wall(project, source):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.status == "proposal", result.to_dict()
    assert result.candidate.spec == replace(project.spec, wall_mm=3)
    assert serialize_project(project) == before
    for item in (*result.actions, *result.preserve, *result.acknowledged):
        ev = item["evidence"]
        assert source[ev["start"]:ev["end"]] == ev["text"]


@pytest.mark.parametrize("source", [
    "not 4mm walls", "not four walls, make them 3mm",
    "not 4mm walls, make them 4mm", "not 0.4cm walls, make them 4mm",
    "not 4mm walls, make them 4.00000000000000001mm",
    "not 4mm walls, make them 3mm no actually 4mm",
    "not 4mm walls, make them 3mm no actually 0.4cm",
    "not 4mm walls, set floor thickness to 3mm",
    "not 4mm walls, keep floor unchanged, make them 3mm",
    "not 4mm walls, make them three",
    "not 4mm walls unless the lid changes, make them 3mm",
    "not 4mm walls, don't make them 3mm",
    "not 4mm walls, make them 3mm and add a warp drive",
    "not 4mm walls, not 3mm walls, make them 2.5mm",
    "make them 3mm", "make it 3mm", "do not set walls to 3mm",
    "only walls 3mm and floor thickness 3mm",
    "floor thickness 3mm and only walls 3mm",
    "only walls 3mm and set profile to sla fine",
    "only walls 3mm and rename new enclosure",
    "only make the power hole radius 3mm",
    "only resize enclosure to 90 x 60 x 30mm",
    "only walls 3mm unless the floor changes",
    "keep wall thickness unchanged and walls 3mm",
    "do not change lid clearance and lid clearance 0.4mm",
    "preserve floor thickness at 3mm and walls 3mm",
    "increase walls to four mm no actually one point five mm",
    "decrease walls to one point five mm no actually three mm",
    "increase walls to four mm no actually two mm",
])
def test_incomplete_conflicting_or_wrong_scope_never_publishes(project, source):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.candidate is None, result.to_dict()
    assert serialize_project(project) == before


def test_only_nested_lid_property_protects_all_other_spec_fields(project):
    result = parse_conversation("only lid clearance 0.4mm", project)
    assert result.status == "proposal", result.to_dict()
    assert result.candidate.spec == replace(project.spec, lid=replace(project.spec.lid, clearance_mm=0.4))
    fields = {item["field"] for item in result.preserve}
    baseline = enclosure_spec_to_dict(project.spec)
    assert fields == (set(baseline) - {"version", "units", "lid"}) | {
        "lid." + field for field in baseline["lid"] if field != "clearance_mm"
    }
    conflict = parse_conversation("only lid clearance 0.4mm and lid thickness 3mm", project)
    assert conflict.candidate is None


def test_repeated_only_clauses_do_not_overflow_protection_collection(project):
    result = parse_conversation("only lid clearance 0.4mm; only lid clearance 0.4mm; only lid clearance 0.4mm", project)
    assert result.status == "proposal", result.to_dict()
    assert len({item["field"] for item in result.preserve}) == len(result.preserve)


def test_preservation_without_edit_remains_unchanged(project):
    result = parse_conversation("do not change the floor", project)
    assert result.status == "unchanged"
    assert result.candidate is None
    assert {item["field"] for item in result.preserve} == {"floor_mm"}


def test_only_and_replacement_survive_saved_review_and_stale_checks(project):
    source = "not 4mm walls, only make them 3mm"
    result = parse_conversation(source, project)
    assert result.status == "proposal", result.to_dict()
    reviewed = review_saved_proposal(result.to_dict(), project)
    with pytest.raises(ValueError, match="confirmation"):
        apply_proposal(reviewed, project)
    updated = apply_proposal(reviewed, project, confirmed=True)
    assert updated.spec == replace(project.spec, wall_mm=3)
    with pytest.raises(ValueError, match="Project changed"):
        apply_proposal(reviewed, updated, confirmed=True)


def test_full_explicit_self_correction_can_replace_direction(project):
    result = parse_conversation("increase walls to four mm no actually set walls to one point five mm", project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == 1.5
