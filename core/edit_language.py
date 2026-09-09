"""Fail-closed natural-language edits for typed enclosure projects.

The grammar is intentionally small and auditable.  Every instruction must
match one complete pattern; unmatched words never become an implicit edit.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .enclosure import HARDWARE_PROFILES
from .project import EnclosureProject, enclosure_spec_to_dict, update_project

NUMBER = r"(?:0|[1-9]\d*)(?:\.\d+)?"
SIGNED_NUMBER = rf"-?{NUMBER}"
IDENTIFIER = r"[A-Za-z][A-Za-z0-9_-]{0,63}"
FACE = r"(?:front|rear|left|right|bottom|top)"
HARDWARE = r"M(?:2(?:\.5)?|3|4)"


class EditInterpretationError(ValueError):
    """Raised when an edit instruction is incomplete, ambiguous, or invalid."""


def _fullmatch(pattern: str, instruction: str) -> re.Match[str] | None:
    return re.fullmatch(pattern, instruction.strip(), flags=re.IGNORECASE)


def _feature_index(items: list[dict[str, Any]], identifier: str, kind: str) -> int:
    matches = [index for index, item in enumerate(items) if item.get("id") == identifier]
    if len(matches) != 1:
        state = "was not found" if not matches else "is duplicated"
        raise EditInterpretationError(f"{kind} {identifier!r} {state}")
    return matches[0]


def edit_project_from_text(
    project: EnclosureProject,
    instruction: str,
    *,
    reason: str | None = None,
) -> EnclosureProject:
    """Apply one complete, typed edit instruction as a new project revision."""

    if not isinstance(instruction, str) or not instruction.strip():
        raise EditInterpretationError("edit instruction must be a non-empty string")
    if len(instruction) > 512:
        raise EditInterpretationError("edit instruction is limited to 512 characters")
    audit_reason = instruction.strip() if reason is None else reason
    if not isinstance(audit_reason, str) or not audit_reason.strip() or len(audit_reason) > 512:
        raise EditInterpretationError("edit reason must contain 1 to 512 characters")

    scalar_patterns = (
        (rf"set (?:the )?wall(?: thickness)? to (?P<value>{NUMBER}) mm", "wall_mm"),
        (rf"set (?:the )?floor(?: thickness)? to (?P<value>{NUMBER}) mm", "floor_mm"),
        (rf"set (?:the )?corner radius to (?P<value>{NUMBER}) mm", "corner_radius_mm"),
        (rf"set (?:the )?lid thickness to (?P<value>{NUMBER}) mm", "lid.thickness_mm"),
        (rf"set (?:the )?lid clearance to (?P<value>{NUMBER}) mm", "lid.clearance_mm"),
        (rf"set (?:the )?lid lip height to (?P<value>{NUMBER}) mm", "lid.lip_height_mm"),
    )
    for pattern, field in scalar_patterns:
        if match := _fullmatch(pattern, instruction):
            return update_project(project, field, float(match.group("value")), reason=audit_reason)

    if match := _fullmatch(
        rf"resize (?:the )?(?:enclosure|case|housing) to (?P<w>{NUMBER})\s*[x×]\s*"
        rf"(?P<d>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER}) mm",
        instruction,
    ):
        size = [float(match.group(axis)) for axis in ("w", "d", "h")]
        return update_project(project, "outer_size_mm", size, reason=audit_reason)

    if match := _fullmatch(
        r"set (?:the )?(?:manufacturing )?profile to (?P<value>fdm[ _-](?:draft|standard|precision)|resin[ _-]standard)",
        instruction,
    ):
        profile = re.sub(r"[ -]", "_", match.group("value").lower())
        return update_project(project, "profile", profile, reason=audit_reason)

    if match := _fullmatch(r"(?:rename|set (?:the )?title to) (?P<value>.+)", instruction):
        return update_project(project, "title", match.group("value").strip(), reason=audit_reason)

    spec = enclosure_spec_to_dict(project.spec)
    for singular, collection in (("cutout", "cutouts"), ("vent", "vents"), ("standoff", "standoffs")):
        if match := _fullmatch(rf"remove (?:the )?{singular} (?P<id>{IDENTIFIER})", instruction):
            items = deepcopy(spec[collection])
            del items[_feature_index(items, match.group("id"), singular)]
            return update_project(project, collection, items, reason=audit_reason)

    if match := _fullmatch(
        rf"move (?:the )?cutout (?P<id>{IDENTIFIER}) to (?P<u>{SIGNED_NUMBER})\s*[x×,]\s*"
        rf"(?P<v>{SIGNED_NUMBER}) mm",
        instruction,
    ):
        cutouts = deepcopy(spec["cutouts"])
        index = _feature_index(cutouts, match.group("id"), "cutout")
        cutouts[index]["center_uv_mm"] = [float(match.group("u")), float(match.group("v"))]
        return update_project(project, "cutouts", cutouts, reason=audit_reason)

    if match := _fullmatch(
        rf"resize (?:the )?rectangular cutout (?P<id>{IDENTIFIER}) to (?P<w>{NUMBER})\s*[x×]\s*"
        rf"(?P<h>{NUMBER}) mm",
        instruction,
    ):
        cutouts = deepcopy(spec["cutouts"])
        index = _feature_index(cutouts, match.group("id"), "cutout")
        if cutouts[index].get("kind") != "rectangular":
            raise EditInterpretationError(f"cutout {match.group('id')!r} is not rectangular")
        cutouts[index]["size_mm"] = [float(match.group("w")), float(match.group("h"))]
        return update_project(project, "cutouts", cutouts, reason=audit_reason)

    if match := _fullmatch(
        rf"set (?:the )?circular cutout (?P<id>{IDENTIFIER}) diameter to (?P<diameter>{NUMBER}) mm",
        instruction,
    ):
        cutouts = deepcopy(spec["cutouts"])
        index = _feature_index(cutouts, match.group("id"), "cutout")
        if cutouts[index].get("kind") != "circular":
            raise EditInterpretationError(f"cutout {match.group('id')!r} is not circular")
        cutouts[index]["diameter_mm"] = float(match.group("diameter"))
        return update_project(project, "cutouts", cutouts, reason=audit_reason)

    if match := _fullmatch(
        rf"add rectangular cutout (?P<id>{IDENTIFIER}) (?P<w>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER}) mm "
        rf"on (?P<face>{FACE}) at (?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER}) mm"
        rf"(?: for (?P<purpose>[A-Za-z0-9_.+-]+))?",
        instruction,
    ):
        cutouts = deepcopy(spec["cutouts"])
        identifier = match.group("id")
        if any(item.get("id") == identifier for item in cutouts):
            raise EditInterpretationError(f"cutout {identifier!r} already exists")
        cutouts.append(
            {
                "id": identifier,
                "kind": "rectangular",
                "face": match.group("face").lower(),
                "center_uv_mm": [float(match.group("u")), float(match.group("v"))],
                "size_mm": [float(match.group("w")), float(match.group("h"))],
                "diameter_mm": None,
                "corner_radius_mm": 0.0,
                "purpose": match.group("purpose") or "generic",
            }
        )
        return update_project(project, "cutouts", cutouts, reason=audit_reason)

    if match := _fullmatch(
        rf"add circular cutout (?P<id>{IDENTIFIER}) (?P<diameter>{NUMBER}) mm diameter "
        rf"on (?P<face>{FACE}) at (?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER}) mm"
        rf"(?: for (?P<purpose>[A-Za-z0-9_.+-]+))?",
        instruction,
    ):
        cutouts = deepcopy(spec["cutouts"])
        identifier = match.group("id")
        if any(item.get("id") == identifier for item in cutouts):
            raise EditInterpretationError(f"cutout {identifier!r} already exists")
        cutouts.append(
            {
                "id": identifier,
                "kind": "circular",
                "face": match.group("face").lower(),
                "center_uv_mm": [float(match.group("u")), float(match.group("v"))],
                "size_mm": None,
                "diameter_mm": float(match.group("diameter")),
                "corner_radius_mm": 0.0,
                "purpose": match.group("purpose") or "generic",
            }
        )
        return update_project(project, "cutouts", cutouts, reason=audit_reason)

    if match := _fullmatch(
        rf"add vent grid (?P<id>{IDENTIFIER}) (?P<rows>[1-9]\d*)\s*[x×]\s*(?P<columns>[1-9]\d*) holes "
        rf"(?P<diameter>{NUMBER}) mm diameter pitch (?P<pitch>{NUMBER}) mm on (?P<face>{FACE}) "
        rf"at (?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER}) mm",
        instruction,
    ):
        vents = deepcopy(spec["vents"])
        identifier = match.group("id")
        if any(item.get("id") == identifier for item in vents):
            raise EditInterpretationError(f"vent {identifier!r} already exists")
        vents.append(
            {
                "id": identifier,
                "face": match.group("face").lower(),
                "center_uv_mm": [float(match.group("u")), float(match.group("v"))],
                "rows": int(match.group("rows")),
                "columns": int(match.group("columns")),
                "diameter_mm": float(match.group("diameter")),
                "pitch_mm": float(match.group("pitch")),
            }
        )
        return update_project(project, "vents", vents, reason=audit_reason)

    if match := _fullmatch(
        rf"add standoff (?P<id>{IDENTIFIER}) (?P<hardware>{HARDWARE}) at "
        rf"(?P<x>{SIGNED_NUMBER})\s*[x×,]\s*(?P<y>{SIGNED_NUMBER}) mm height (?P<height>{NUMBER}) mm",
        instruction,
    ):
        standoffs = deepcopy(spec["standoffs"])
        identifier = match.group("id")
        if any(item.get("id") == identifier for item in standoffs):
            raise EditInterpretationError(f"standoff {identifier!r} already exists")
        hardware_name = match.group("hardware").upper()
        hardware = HARDWARE_PROFILES[hardware_name]
        standoffs.append(
            {
                "id": identifier,
                "center_xy_mm": [float(match.group("x")), float(match.group("y"))],
                "height_mm": float(match.group("height")),
                "outer_diameter_mm": hardware.boss_outer_mm,
                "hole_diameter_mm": hardware.pilot_hole_mm,
                "hardware": hardware_name,
            }
        )
        return update_project(project, "standoffs", standoffs, reason=audit_reason)

    raise EditInterpretationError(
        "unsupported edit instruction; use an exact set/resize/rename/add/move/remove enclosure edit"
    )
