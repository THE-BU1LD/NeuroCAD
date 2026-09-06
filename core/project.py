"""Versioned, human-readable NeuroCAD enclosure project files."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .enclosure import (
    SPEC_VERSION,
    CutoutSpec,
    EnclosureSpec,
    LidSpec,
    PCBSpec,
    StandoffSpec,
    VentPatternSpec,
    validate_enclosure_spec,
)
from .json_io import strict_json_loads

PROJECT_VERSION = "neurocad-project-v1"
MAX_PROJECT_BYTES = 1_048_576
EDITABLE_TOP_LEVEL_FIELDS = {
    "title",
    "outer_size_mm",
    "wall_mm",
    "floor_mm",
    "corner_radius_mm",
    "profile",
    "lid",
    "cutouts",
    "standoffs",
    "vents",
    "pcb",
}
EDITABLE_LID_FIELDS = {
    "kind",
    "thickness_mm",
    "clearance_mm",
    "lip_height_mm",
    "hardware",
    "fastener_positions_xy_mm",
}


class ProjectFormatError(ValueError):
    pass


def _json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class PhraseMapping:
    text: str
    field: str
    start: int
    end: int


@dataclass(frozen=True)
class ChangeRecord:
    revision: int
    field: str
    before: Any
    after: Any
    reason: str


@dataclass(frozen=True)
class EnclosureProject:
    project_id: str
    spec: EnclosureSpec
    revision: int = 1
    source_text: str | None = None
    phrase_mappings: tuple[PhraseMapping, ...] = ()
    changes: tuple[ChangeRecord, ...] = ()
    version: str = PROJECT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_id": self.project_id,
            "revision": self.revision,
            "source_text": self.source_text,
            "phrase_mappings": [asdict(mapping) for mapping in self.phrase_mappings],
            "changes": [asdict(change) for change in self.changes],
            "spec": enclosure_spec_to_dict(self.spec),
        }


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectFormatError(f"{path} must be an object")
    return value


def _only_keys(value: dict[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    unexpected = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unexpected:
        raise ProjectFormatError(f"{path} has unsupported keys: {', '.join(unexpected)}")
    if missing:
        raise ProjectFormatError(f"{path} is missing keys: {', '.join(missing)}")


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ProjectFormatError(f"{path} must be a finite number")
    return float(value)


def _text(value: Any, path: str, *, maximum: int = 256, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ProjectFormatError(f"{path} must be a string")
    if (not allow_empty and not value.strip()) or len(value) > maximum:
        qualifier = f"at most {maximum} characters" if allow_empty else f"1 to {maximum} characters"
        raise ProjectFormatError(f"{path} must contain {qualifier}")
    return value


def _pair(value: Any, path: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ProjectFormatError(f"{path} must contain exactly two numbers")
    return _number(value[0], f"{path}[0]"), _number(value[1], f"{path}[1]")


def _triple(value: Any, path: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ProjectFormatError(f"{path} must contain exactly three numbers")
    return (
        _number(value[0], f"{path}[0]"),
        _number(value[1], f"{path}[1]"),
        _number(value[2], f"{path}[2]"),
    )


def enclosure_spec_to_dict(spec: EnclosureSpec) -> dict[str, Any]:
    return {
        "version": spec.version,
        "units": spec.units,
        "title": spec.title,
        "outer_size_mm": list(spec.outer_size_mm),
        "wall_mm": spec.wall_mm,
        "floor_mm": spec.floor_mm,
        "corner_radius_mm": spec.corner_radius_mm,
        "profile": spec.profile,
        "lid": {
            "kind": spec.lid.kind,
            "thickness_mm": spec.lid.thickness_mm,
            "clearance_mm": spec.lid.clearance_mm,
            "lip_height_mm": spec.lid.lip_height_mm,
            "hardware": spec.lid.hardware,
            "fastener_positions_xy_mm": [list(item) for item in spec.lid.fastener_positions_xy_mm],
        },
        "cutouts": [_json_value(asdict(item)) for item in spec.cutouts],
        "standoffs": [_json_value(asdict(item)) for item in spec.standoffs],
        "vents": [_json_value(asdict(item)) for item in spec.vents],
        "pcb": _json_value(asdict(spec.pcb)) if spec.pcb is not None else None,
    }


def enclosure_spec_from_dict(raw: Any) -> EnclosureSpec:
    value = _require_object(raw, "$.spec")
    allowed = {
        "version",
        "units",
        "title",
        "outer_size_mm",
        "wall_mm",
        "floor_mm",
        "corner_radius_mm",
        "profile",
        "lid",
        "cutouts",
        "standoffs",
        "vents",
        "pcb",
    }
    required = {"version", "units", "title", "outer_size_mm", "wall_mm", "profile", "lid"}
    _only_keys(value, allowed, required, "$.spec")
    if value["version"] != SPEC_VERSION:
        raise ProjectFormatError(f"$.spec.version must be {SPEC_VERSION!r}")
    lid_raw = _require_object(value["lid"], "$.spec.lid")
    _only_keys(
        lid_raw,
        {"kind", "thickness_mm", "clearance_mm", "lip_height_mm", "hardware", "fastener_positions_xy_mm"},
        {"kind", "thickness_mm", "clearance_mm"},
        "$.spec.lid",
    )
    positions_raw = lid_raw.get("fastener_positions_xy_mm", [])
    if not isinstance(positions_raw, list):
        raise ProjectFormatError("$.spec.lid.fastener_positions_xy_mm must be an array")
    lid = LidSpec(
        kind=_text(lid_raw["kind"], "$.spec.lid.kind", maximum=32),
        thickness_mm=_number(lid_raw["thickness_mm"], "$.spec.lid.thickness_mm"),
        clearance_mm=_number(lid_raw["clearance_mm"], "$.spec.lid.clearance_mm"),
        lip_height_mm=_number(lid_raw.get("lip_height_mm", 0.0), "$.spec.lid.lip_height_mm"),
        hardware=(
            None
            if lid_raw.get("hardware") is None
            else _text(lid_raw["hardware"], "$.spec.lid.hardware", maximum=16)
        ),
        fastener_positions_xy_mm=tuple(
            _pair(item, f"$.spec.lid.fastener_positions_xy_mm[{index}]")
            for index, item in enumerate(positions_raw)
        ),
    )

    cutouts_raw = value.get("cutouts", [])
    if not isinstance(cutouts_raw, list):
        raise ProjectFormatError("$.spec.cutouts must be an array")
    cutouts: list[CutoutSpec] = []
    for index, item in enumerate(cutouts_raw):
        path = f"$.spec.cutouts[{index}]"
        entry = _require_object(item, path)
        _only_keys(
            entry,
            {"id", "kind", "face", "center_uv_mm", "size_mm", "diameter_mm", "corner_radius_mm", "purpose"},
            {"id", "kind", "face", "center_uv_mm"},
            path,
        )
        cutouts.append(
            CutoutSpec(
                id=_text(entry["id"], f"{path}.id", maximum=128),
                kind=_text(entry["kind"], f"{path}.kind", maximum=32),
                face=_text(entry["face"], f"{path}.face", maximum=32),
                center_uv_mm=_pair(entry["center_uv_mm"], f"{path}.center_uv_mm"),
                size_mm=None if entry.get("size_mm") is None else _pair(entry["size_mm"], f"{path}.size_mm"),
                diameter_mm=None if entry.get("diameter_mm") is None else _number(entry["diameter_mm"], f"{path}.diameter_mm"),
                corner_radius_mm=_number(entry.get("corner_radius_mm", 0.0), f"{path}.corner_radius_mm"),
                purpose=_text(entry.get("purpose", "generic"), f"{path}.purpose", maximum=128),
            )
        )

    standoffs_raw = value.get("standoffs", [])
    if not isinstance(standoffs_raw, list):
        raise ProjectFormatError("$.spec.standoffs must be an array")
    standoffs: list[StandoffSpec] = []
    for index, item in enumerate(standoffs_raw):
        path = f"$.spec.standoffs[{index}]"
        entry = _require_object(item, path)
        _only_keys(
            entry,
            {"id", "center_xy_mm", "height_mm", "outer_diameter_mm", "hole_diameter_mm", "hardware"},
            {"id", "center_xy_mm", "height_mm", "outer_diameter_mm", "hole_diameter_mm"},
            path,
        )
        standoffs.append(
            StandoffSpec(
                id=_text(entry["id"], f"{path}.id", maximum=128),
                center_xy_mm=_pair(entry["center_xy_mm"], f"{path}.center_xy_mm"),
                height_mm=_number(entry["height_mm"], f"{path}.height_mm"),
                outer_diameter_mm=_number(entry["outer_diameter_mm"], f"{path}.outer_diameter_mm"),
                hole_diameter_mm=_number(entry["hole_diameter_mm"], f"{path}.hole_diameter_mm"),
                hardware=(
                    None
                    if entry.get("hardware") is None
                    else _text(entry["hardware"], f"{path}.hardware", maximum=16)
                ),
            )
        )

    vents_raw = value.get("vents", [])
    if not isinstance(vents_raw, list):
        raise ProjectFormatError("$.spec.vents must be an array")
    vents: list[VentPatternSpec] = []
    for index, item in enumerate(vents_raw):
        path = f"$.spec.vents[{index}]"
        entry = _require_object(item, path)
        _only_keys(
            entry,
            {"id", "face", "center_uv_mm", "rows", "columns", "diameter_mm", "pitch_mm"},
            {"id", "face", "center_uv_mm", "rows", "columns", "diameter_mm", "pitch_mm"},
            path,
        )
        rows, columns = entry["rows"], entry["columns"]
        if isinstance(rows, bool) or not isinstance(rows, int) or isinstance(columns, bool) or not isinstance(columns, int):
            raise ProjectFormatError(f"{path}.rows and columns must be integers")
        vents.append(
            VentPatternSpec(
                id=_text(entry["id"], f"{path}.id", maximum=128),
                face=_text(entry["face"], f"{path}.face", maximum=32),
                center_uv_mm=_pair(entry["center_uv_mm"], f"{path}.center_uv_mm"),
                rows=rows,
                columns=columns,
                diameter_mm=_number(entry["diameter_mm"], f"{path}.diameter_mm"),
                pitch_mm=_number(entry["pitch_mm"], f"{path}.pitch_mm"),
            )
        )

    pcb_raw = value.get("pcb")
    pcb: PCBSpec | None = None
    if pcb_raw is not None:
        entry = _require_object(pcb_raw, "$.spec.pcb")
        _only_keys(
            entry,
            {"size_mm", "origin_xy_mm", "mounting_holes_xy_mm", "component_height_mm"},
            {"size_mm"},
            "$.spec.pcb",
        )
        holes = entry.get("mounting_holes_xy_mm", [])
        if not isinstance(holes, list):
            raise ProjectFormatError("$.spec.pcb.mounting_holes_xy_mm must be an array")
        pcb = PCBSpec(
            size_mm=_triple(entry["size_mm"], "$.spec.pcb.size_mm"),
            origin_xy_mm=_pair(entry.get("origin_xy_mm", [0, 0]), "$.spec.pcb.origin_xy_mm"),
            mounting_holes_xy_mm=tuple(
                _pair(item, f"$.spec.pcb.mounting_holes_xy_mm[{index}]") for index, item in enumerate(holes)
            ),
            component_height_mm=_number(entry.get("component_height_mm", 0.0), "$.spec.pcb.component_height_mm"),
        )

    spec = EnclosureSpec(
        outer_size_mm=_triple(value["outer_size_mm"], "$.spec.outer_size_mm"),
        wall_mm=_number(value["wall_mm"], "$.spec.wall_mm"),
        profile=_text(value["profile"], "$.spec.profile", maximum=64),
        lid=lid,
        corner_radius_mm=_number(value.get("corner_radius_mm", 0.0), "$.spec.corner_radius_mm"),
        floor_mm=None if value.get("floor_mm") is None else _number(value["floor_mm"], "$.spec.floor_mm"),
        cutouts=tuple(cutouts),
        standoffs=tuple(standoffs),
        vents=tuple(vents),
        pcb=pcb,
        title=_text(value["title"], "$.spec.title"),
        units=_text(value["units"], "$.spec.units", maximum=16),
        version=_text(value["version"], "$.spec.version", maximum=64),
    )
    report = validate_enclosure_spec(spec)
    if not report.valid:
        raise ProjectFormatError(
            "invalid enclosure specification: "
            + "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        )
    return spec


def serialize_project(project: EnclosureProject, *, pretty: bool = True) -> str:
    separators = None if pretty else (",", ":")
    return (
        json.dumps(
            project.to_dict(),
            indent=2 if pretty else None,
            sort_keys=True,
            separators=separators,
            allow_nan=False,
        )
        + "\n"
    )


def parse_project(text: str) -> EnclosureProject:
    if len(text.encode("utf-8")) > MAX_PROJECT_BYTES:
        raise ProjectFormatError("project input is limited to 1 MiB")
    try:
        raw = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectFormatError(f"invalid project JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    value = _require_object(raw, "$")
    _only_keys(
        value,
        {"version", "project_id", "revision", "source_text", "phrase_mappings", "changes", "spec"},
        {"version", "project_id", "revision", "spec"},
        "$",
    )
    if value["version"] != PROJECT_VERSION:
        raise ProjectFormatError(f"$.version must be {PROJECT_VERSION!r}")
    project_id = value["project_id"]
    revision = value["revision"]
    project_id = _text(project_id, "$.project_id", maximum=128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", project_id) is None:
        raise ProjectFormatError("$.project_id may contain only letters, digits, underscores, and hyphens")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ProjectFormatError("$.revision must be a positive integer")
    mappings_raw = value.get("phrase_mappings", [])
    changes_raw = value.get("changes", [])
    if not isinstance(mappings_raw, list) or not isinstance(changes_raw, list):
        raise ProjectFormatError("$.phrase_mappings and $.changes must be arrays")
    source_text_raw = value.get("source_text")
    source_text = None if source_text_raw is None else _text(source_text_raw, "$.source_text", maximum=8192)
    mappings: list[PhraseMapping] = []
    occupied_offsets: set[int] = set()
    for index, item in enumerate(mappings_raw):
        entry = _require_object(item, f"$.phrase_mappings[{index}]")
        _only_keys(entry, {"text", "field", "start", "end"}, {"text", "field", "start", "end"}, f"$.phrase_mappings[{index}]")
        if any(isinstance(entry[key], bool) or not isinstance(entry[key], int) for key in ("start", "end")):
            raise ProjectFormatError(f"$.phrase_mappings[{index}] offsets must be integers")
        mapping_text = _text(entry["text"], f"$.phrase_mappings[{index}].text", maximum=8192)
        mapping_field = _text(entry["field"], f"$.phrase_mappings[{index}].field", maximum=128)
        start, end = entry["start"], entry["end"]
        if source_text is None:
            raise ProjectFormatError("$.phrase_mappings require $.source_text")
        if not 0 <= start < end <= len(source_text) or source_text[start:end] != mapping_text:
            raise ProjectFormatError(f"$.phrase_mappings[{index}] does not match $.source_text")
        offsets = set(range(start, end))
        if occupied_offsets & offsets:
            raise ProjectFormatError("$.phrase_mappings must not overlap")
        occupied_offsets.update(offsets)
        mappings.append(PhraseMapping(mapping_text, mapping_field, start, end))
    changes: list[ChangeRecord] = []
    for index, item in enumerate(changes_raw):
        entry = _require_object(item, f"$.changes[{index}]")
        _only_keys(entry, {"revision", "field", "before", "after", "reason"}, {"revision", "field", "before", "after", "reason"}, f"$.changes[{index}]")
        change_revision = entry["revision"]
        if isinstance(change_revision, bool) or not isinstance(change_revision, int) or change_revision < 2:
            raise ProjectFormatError(f"$.changes[{index}].revision must be an integer of at least 2")
        field = _text(entry["field"], f"$.changes[{index}].field", maximum=128)
        reason = _text(entry["reason"], f"$.changes[{index}].reason", maximum=512)
        changes.append(ChangeRecord(change_revision, field, entry["before"], entry["after"], reason))
    expected_revisions = list(range(2, revision + 1))
    if [change.revision for change in changes] != expected_revisions:
        raise ProjectFormatError("$.changes must contain exactly one ordered record for every revision after 1")
    spec = enclosure_spec_from_dict(value["spec"])
    replay = enclosure_spec_to_dict(spec)
    for change in reversed(changes):
        if change.field in EDITABLE_TOP_LEVEL_FIELDS:
            current = replay[change.field]
            if current != change.after:
                raise ProjectFormatError(
                    f"$.changes revision {change.revision} after value does not match the recorded project state"
                )
            replay[change.field] = deepcopy(change.before)
        elif change.field.startswith("lid.") and change.field.removeprefix("lid.") in EDITABLE_LID_FIELDS:
            lid_field = change.field.removeprefix("lid.")
            current = replay["lid"][lid_field]
            if current != change.after:
                raise ProjectFormatError(
                    f"$.changes revision {change.revision} after value does not match the recorded project state"
                )
            replay["lid"][lid_field] = deepcopy(change.before)
        else:
            raise ProjectFormatError(f"$.changes revision {change.revision} uses unsupported field {change.field!r}")
        try:
            enclosure_spec_from_dict(replay)
        except ProjectFormatError as exc:
            raise ProjectFormatError(
                f"$.changes revision {change.revision} cannot be replayed to a valid prior state: {exc}"
            ) from exc
    return EnclosureProject(
        project_id=project_id,
        spec=spec,
        revision=revision,
        source_text=source_text,
        phrase_mappings=tuple(mappings),
        changes=tuple(changes),
    )


def write_project(path: Path, project: EnclosureProject) -> Path:
    return write_text_atomic(path, serialize_project(project))


def read_project(path: Path) -> EnclosureProject:
    raw = path.read_bytes()
    if len(raw) > MAX_PROJECT_BYTES:
        raise ProjectFormatError("project input is limited to 1 MiB")
    return parse_project(raw.decode("utf-8"))


def update_project(project: EnclosureProject, field: str, value: Any, *, reason: str) -> EnclosureProject:
    """Apply a bounded semantic edit and retain an explicit revision record."""

    if not isinstance(field, str):
        raise TypeError("edit field must be a string")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 512:
        raise ValueError("an edit reason of 1 to 512 characters is required")
    raw_spec = enclosure_spec_to_dict(project.spec)
    before: Any
    if field in EDITABLE_TOP_LEVEL_FIELDS:
        before = deepcopy(raw_spec[field])
        raw_spec[field] = deepcopy(value)
    elif field.startswith("lid.") and field.removeprefix("lid.") in EDITABLE_LID_FIELDS:
        lid_field = field.removeprefix("lid.")
        before = deepcopy(raw_spec["lid"][lid_field])
        raw_spec["lid"][lid_field] = deepcopy(value)
    else:
        supported = sorted(EDITABLE_TOP_LEVEL_FIELDS | {f"lid.{item}" for item in EDITABLE_LID_FIELDS})
        raise ValueError(f"unsupported semantic edit field {field!r}; choose one of {', '.join(supported)}")
    try:
        spec = enclosure_spec_from_dict(raw_spec)
    except ProjectFormatError as exc:
        raise ValueError(f"edit would make project invalid: {exc}") from exc
    after_spec = enclosure_spec_to_dict(spec)
    after = deepcopy(after_spec["lid"][field.removeprefix("lid.")]) if field.startswith("lid.") else deepcopy(after_spec[field])
    revision = project.revision + 1
    change = ChangeRecord(revision, field, before, after, reason.strip())
    return replace(project, spec=spec, revision=revision, changes=(*project.changes, change))


def semantic_diff(left: EnclosureProject, right: EnclosureProject) -> tuple[dict[str, Any], ...]:
    """Return stable field-level differences between two project specifications."""

    before, after = enclosure_spec_to_dict(left.spec), enclosure_spec_to_dict(right.spec)
    changes: list[dict[str, Any]] = []

    def walk(path: str, old: Any, new: Any) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new)):
                walk(f"{path}.{key}" if path else key, old.get(key), new.get(key))
        elif old != new:
            changes.append({"field": path, "before": old, "after": new})

    walk("", before, after)
    return tuple(changes)
