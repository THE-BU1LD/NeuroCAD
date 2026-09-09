from __future__ import annotations

import pytest

from core.edit_language import EditInterpretationError, edit_project_from_text
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.project import EnclosureProject


def _project() -> EnclosureProject:
    return EnclosureProject(
        "editable-enclosure",
        EnclosureSpec(
            outer_size_mm=(80, 60, 30),
            wall_mm=2,
            floor_mm=2,
            corner_radius_mm=3,
            profile="fdm_standard",
            lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
            cutouts=(
                CutoutSpec("usb", "rectangular", "front", (0, 10), size_mm=(12, 7), purpose="USB-C"),
            ),
        ),
    )


def test_scalar_and_geometry_feature_edits_are_audited() -> None:
    project = edit_project_from_text(_project(), "set wall thickness to 2.4 mm")
    assert project.spec.wall_mm == 2.4
    assert project.changes[-1].reason == "set wall thickness to 2.4 mm"

    project = edit_project_from_text(project, "move cutout usb to -5 x 9 mm")
    assert project.spec.cutouts[0].center_uv_mm == (-5.0, 9.0)
    project = edit_project_from_text(project, "resize rectangular cutout usb to 14 x 8 mm")
    assert project.spec.cutouts[0].size_mm == (14.0, 8.0)
    project = edit_project_from_text(project, "add circular cutout power 8 mm diameter on rear at 12 x 9 mm for barrel-jack")
    assert {item.id for item in project.spec.cutouts} == {"usb", "power"}
    project = edit_project_from_text(project, "remove cutout power")
    assert [item.id for item in project.spec.cutouts] == ["usb"]


def test_vent_standoff_resize_and_profile_edits_remain_typed() -> None:
    project = edit_project_from_text(
        _project(),
        "add vent grid intake 2 x 3 holes 2 mm diameter pitch 4 mm on rear at 0 x 10 mm",
    )
    assert project.spec.vents[0].rows == 2
    project = edit_project_from_text(project, "add standoff board_a M3 at -20 x -12 mm height 6 mm")
    assert project.spec.standoffs[0].hardware == "M3"
    project = edit_project_from_text(project, "resize enclosure to 90 x 65 x 32 mm")
    assert project.spec.outer_size_mm == (90.0, 65.0, 32.0)
    project = edit_project_from_text(project, "set manufacturing profile to fdm precision")
    assert project.spec.profile == "fdm_precision"


def test_edits_fail_closed_on_unknown_language_and_invalid_results() -> None:
    with pytest.raises(EditInterpretationError, match="unsupported"):
        edit_project_from_text(_project(), "make the cutout cooler and add wings")
    with pytest.raises(EditInterpretationError, match="was not found"):
        edit_project_from_text(_project(), "remove cutout missing")
    with pytest.raises(ValueError, match="make project invalid"):
        edit_project_from_text(_project(), "set wall thickness to 40 mm")
    with pytest.raises(ValueError, match="make project invalid"):
        edit_project_from_text(_project(), "move cutout usb to 38 x 10 mm")
