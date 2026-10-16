"""Authored maintenance cases; not protected language-generalization evidence."""
from dataclasses import replace

import pytest

from core.conversational_parser import apply_proposal, parse_conversation
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.project import EnclosureProject, serialize_project


@pytest.fixture
def project():
    return EnclosureProject("quantity-maintenance", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
        cutouts=(CutoutSpec("power", "circular", "front", (0, 10), diameter_mm=4),),
    ))


@pytest.mark.parametrize("source,field,expected", [
    ("make the walls three millimeters thick", "wall_mm", 3),
    ("walls zero point three cm", "wall_mm", 3),
    ("walls three point one two five mm", "wall_mm", 3.125),
    ("floor thickness two point five mm", "floor_mm", 2.5),
    ("lid clearance zero point four millimetres", "lid.clearance_mm", 0.4),
    ("add one millimeter to the wall thickness", "wall_mm", 3),
    ("subtract 0.05 cm from the wall thickness", "wall_mm", 1.5),
    ("increase wall thickness by one millimeter", "wall_mm", 3),
    ("decrease wall thickness by zero point five mm", "wall_mm", 1.5),
    ("add zero point one mm to the lid clearance", "lid.clearance_mm", 0.4),
    ("add 0.1 mm to the lid clearance", "lid.clearance_mm", 0.4),
    ("set lid lip height to twenty-one mm", "lid.lip_height_mm", 21),
    ("set lid lip height to twenty one mm", "lid.lip_height_mm", 21),
])
def test_complete_quantity_clause_keeps_exact_context_and_source(project, source, field, expected):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.status == "proposal", result.to_dict()
    value = result.candidate.spec
    for component in field.split("."):
        value = getattr(value, component)
    assert value == expected
    assert serialize_project(project) == before
    assert result.candidate.spec.cutouts == project.spec.cutouts
    assert result.candidate.spec.outer_size_mm == project.spec.outer_size_mm
    for action in result.actions:
        evidence = action["evidence"]
        assert source[evidence["start"]:evidence["end"]] == evidence["text"]
    assert result.to_dict()["requires_review"] is True


@pytest.mark.parametrize("source", [
    "make the power hole radius 3mm", "set power cutout radius to three mm",
    "make the power hole radius zero point three centimeters",
])
def test_radius_conversion_preserves_hole_identity_and_position(project, source):
    result = parse_conversation(source, project)
    assert result.status == "proposal"
    assert result.candidate.spec.cutouts == (replace(project.spec.cutouts[0], diameter_mm=6),)
    assert result.candidate.spec.wall_mm == project.spec.wall_mm


@pytest.mark.parametrize("source", [
    "walls three", "add one to the wall thickness", "walls one hundred mm",
    "walls twenty zero mm", "walls three point twenty mm", "walls three point mm",
    "walls minus three mm", "walls -3mm", "walls three and a half mm",
    "walls 3e0mm", "walls NaN mm", "walls infinity mm", "walls 0mm",
    "add -1 mm to the wall thickness", "subtract three mm from the wall thickness",
    "walls three mm and add a warp drive", "walls three mm and walls four mm",
    "add one mm to wall thickness and add one mm to wall thickness",
    "walls three mm and add one mm to wall thickness",
    "add one mm to wall thickness and walls three mm",
    "do not add one mm to wall thickness", "walls three mm unless the lid changes",
    "make the unknown hole radius 3mm", "make the power hole radius 3mm diameter 8mm",
    "make the power hole radius -3mm", "make the power hole radius three",
])
def test_unsupported_or_conflicting_quantity_is_never_partly_applied(project, source):
    before = serialize_project(project)
    result = parse_conversation(source, project)
    assert result.candidate is None, result.to_dict()
    assert result.status != "proposal"
    assert serialize_project(project) == before


def test_relative_proposal_cannot_be_applied_twice(project):
    proposal = parse_conversation("add one mm to wall thickness", project)
    with pytest.raises(ValueError, match="confirmation"):
        apply_proposal(proposal, project)
    updated = apply_proposal(proposal, project, confirmed=True)
    assert updated.spec.wall_mm == 3
    with pytest.raises(ValueError, match="Project changed"):
        apply_proposal(proposal, updated, confirmed=True)


def test_relative_edit_respects_preservation(project):
    result = parse_conversation("add one mm to wall thickness and keep the outside same", project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == 3
    assert result.candidate.spec.outer_size_mm == project.spec.outer_size_mm


def test_rectangular_cutout_is_not_reinterpreted_as_circle(project):
    cutout = CutoutSpec("power", "rectangular", "front", (0, 10), size_mm=(4, 4))
    changed = replace(project, spec=replace(project.spec, cutouts=(cutout,)))
    assert parse_conversation("make the power hole radius 3mm", changed).candidate is None


def test_case_variant_identifier_resolves_only_when_unique(project):
    changed = replace(project, spec=replace(project.spec, cutouts=(replace(project.spec.cutouts[0], id="Power"),)))
    result = parse_conversation("make the power hole radius 3mm", changed)
    assert result.status == "proposal"
    assert result.candidate.spec.cutouts[0].id == "Power"
    second = CutoutSpec("Power", "circular", "rear", (0, 10), diameter_mm=4)
    ambiguous = replace(project, spec=replace(project.spec, cutouts=(*project.spec.cutouts, second)))
    assert parse_conversation("make the power hole radius 3mm", ambiguous).candidate is None


def test_overflowing_quantity_is_refused_without_crashing(project):
    for source in ["walls " + "9" * 400 + " mm", "add " + "9" * 400 + " mm to wall thickness"]:
        assert parse_conversation(source, project).candidate is None


def test_original_explicit_correction_supports_words(project):
    result = parse_conversation("walls four mm no actually three mm", project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == 3
    assert len(result.actions) == 1
    assert any("Superseded" in item["reason"] for item in result.acknowledged)
