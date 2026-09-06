"""Bounded extraction of a deliberately small KiCad PCB file subset.

The extractor handles one axis-aligned rectangular Edge.Cuts outline made from
four ``gr_line`` items or one ``gr_rect`` item, the board thickness, and round
NPTH pads inside footprints whose library/name identifies them as mounting
holes. Connector inventory and maximum component height remain explicit human
review inputs because the board file does not provide a trustworthy universal
mechanical-height contract.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from ..enclosure import MAX_DIMENSION_MM, MIN_DIMENSION_MM
from ..json_io import strict_json_loads
from .common import write_json_atomic
from .kicad import (
    KICAD_FILE_EXTRACTOR_VERSION,
    KICAD_HANDOFF_VERSION,
    KICAD_MECHANICAL_REVIEW_VERSION,
    REQUIRED_COMPLETE_FIELDS,
    KiCadHandoffError,
    parse_kicad_handoff,
)

MAX_LOCAL_BOARD_BYTES = 16 * 1_048_576
MAX_SEXPR_TOKENS = 1_000_000
MAX_SEXPR_DEPTH = 64
MAX_ATOM_LENGTH = 4096
COORDINATE_DIGITS = 6
NUMBER_PATTERN = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d{1,6})?\Z")


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if character in "()":
            tokens.append(("open" if character == "(" else "close", character))
            index += 1
        elif character == '"':
            index += 1
            value: list[str] = []
            while index < len(text):
                character = text[index]
                if character == '"':
                    index += 1
                    break
                if character == "\\":
                    index += 1
                    if index >= len(text):
                        raise KiCadHandoffError("unterminated escape in KiCad quoted string")
                    escaped = text[index]
                    translations = {'"': '"', "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}
                    if escaped not in translations:
                        raise KiCadHandoffError(f"unsupported KiCad string escape: \\{escaped}")
                    value.append(translations[escaped])
                else:
                    value.append(character)
                if len(value) > MAX_ATOM_LENGTH:
                    raise KiCadHandoffError("KiCad quoted string exceeds the bounded parser limit")
                index += 1
            else:
                raise KiCadHandoffError("unterminated KiCad quoted string")
            tokens.append(("value", "".join(value)))
        else:
            start = index
            while index < len(text) and not text[index].isspace() and text[index] not in "()":
                index += 1
            atom = text[start:index]
            if not atom or len(atom) > MAX_ATOM_LENGTH or ";" in atom:
                raise KiCadHandoffError("invalid or oversized KiCad atom")
            tokens.append(("value", atom))
        if len(tokens) > MAX_SEXPR_TOKENS:
            raise KiCadHandoffError("KiCad board exceeds the bounded parser token limit")
    return tokens


def _parse_sexpr(text: str) -> list[Any]:
    stack: list[list[Any]] = []
    root: list[Any] | None = None
    for kind, lexeme in _tokenize(text):
        if kind == "open":
            if len(stack) >= MAX_SEXPR_DEPTH:
                raise KiCadHandoffError("KiCad board exceeds the bounded parser nesting limit")
            node: list[Any] = []
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise KiCadHandoffError("KiCad board must contain exactly one root expression")
            else:
                root = node
            stack.append(node)
        elif kind == "close":
            if not stack:
                raise KiCadHandoffError("unmatched closing parenthesis in KiCad board")
            stack.pop()
        else:
            if not stack:
                raise KiCadHandoffError("KiCad atoms must be inside the root expression")
            stack[-1].append(lexeme)
    if stack:
        raise KiCadHandoffError("unterminated expression in KiCad board")
    if root is None or not root or root[0] != "kicad_pcb":
        raise KiCadHandoffError("source is not a KiCad PCB s-expression")
    return root


def _head(node: Any) -> str | None:
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def _children(node: list[Any], name: str) -> list[list[Any]]:
    return [item for item in node[1:] if isinstance(item, list) and _head(item) == name]


def _one_child(node: list[Any], name: str, path: str) -> list[Any]:
    values = _children(node, name)
    if len(values) != 1:
        raise KiCadHandoffError(f"{path} must contain exactly one {name} expression")
    return values[0]


def _number(value: Any, path: str, *, allow_zero: bool = False, signed: bool = False) -> float:
    if not isinstance(value, str) or NUMBER_PATTERN.fullmatch(value) is None:
        raise KiCadHandoffError(f"{path} must be a non-exponential number with at most six decimal places")
    result = float(value)
    minimum = 0.0 if allow_zero else MIN_DIMENSION_MM
    if not math.isfinite(result) or (not signed and not minimum <= result <= MAX_DIMENSION_MM):
        raise KiCadHandoffError(f"{path} is outside the supported millimetre range")
    if signed and abs(result) > MAX_DIMENSION_MM:
        raise KiCadHandoffError(f"{path} magnitude exceeds {MAX_DIMENSION_MM:g} mm")
    return result


def _xy(node: list[Any], path: str) -> tuple[float, float]:
    if len(node) < 3:
        raise KiCadHandoffError(f"{path} must contain X and Y")
    return _number(node[1], f"{path}.x", signed=True), _number(node[2], f"{path}.y", signed=True)


def _layer(node: list[Any]) -> str | None:
    layers = _children(node, "layer")
    if len(layers) != 1 or len(layers[0]) != 2 or not isinstance(layers[0][1], str):
        return None
    return layers[0][1]


def _all_nodes(node: list[Any]):
    yield node
    for item in node[1:]:
        if isinstance(item, list):
            yield from _all_nodes(item)


def _outline(root: list[Any]) -> tuple[float, float, float, float]:
    accepted: list[list[Any]] = []
    top_level_ids = {id(item) for item in root[1:] if isinstance(item, list)}
    for node in _all_nodes(root):
        name = _head(node)
        if name is None or _layer(node) != "Edge.Cuts":
            continue
        if id(node) in top_level_ids and name in {"gr_line", "gr_rect"}:
            accepted.append(node)
        else:
            raise KiCadHandoffError(f"unsupported Edge.Cuts item for bounded extraction: {name}")

    rectangles = [node for node in accepted if _head(node) == "gr_rect"]
    lines = [node for node in accepted if _head(node) == "gr_line"]
    if rectangles:
        if len(rectangles) != 1 or lines:
            raise KiCadHandoffError("bounded extraction requires exactly one rectangular Edge.Cuts definition")
        start = _xy(_one_child(rectangles[0], "start", "gr_rect"), "gr_rect.start")
        end = _xy(_one_child(rectangles[0], "end", "gr_rect"), "gr_rect.end")
        x_values = sorted((start[0], end[0]))
        y_values = sorted((start[1], end[1]))
    else:
        if len(lines) != 4:
            raise KiCadHandoffError("bounded extraction requires four Edge.Cuts gr_line items or one gr_rect")
        segments: set[tuple[tuple[float, float], tuple[float, float]]] = set()
        points: set[tuple[float, float]] = set()
        for index, line in enumerate(lines):
            start = _xy(_one_child(line, "start", f"gr_line[{index}]"), f"gr_line[{index}].start")
            end = _xy(_one_child(line, "end", f"gr_line[{index}]"), f"gr_line[{index}].end")
            start = (round(start[0], COORDINATE_DIGITS), round(start[1], COORDINATE_DIGITS))
            end = (round(end[0], COORDINATE_DIGITS), round(end[1], COORDINATE_DIGITS))
            if start == end or (start[0] != end[0] and start[1] != end[1]):
                raise KiCadHandoffError("bounded extraction supports only non-zero axis-aligned Edge.Cuts lines")
            segment = (start, end) if start <= end else (end, start)
            segments.add(segment)
            points.update((start, end))
        x_values = sorted({point[0] for point in points})
        y_values = sorted({point[1] for point in points})
        if len(points) != 4 or len(x_values) != 2 or len(y_values) != 2:
            raise KiCadHandoffError("Edge.Cuts lines do not form one rectangle")
        corners = {(x, y) for x in x_values for y in y_values}
        expected = {
            tuple(sorted(((x_values[0], y_values[0]), (x_values[1], y_values[0])))),
            tuple(sorted(((x_values[1], y_values[0]), (x_values[1], y_values[1])))),
            tuple(sorted(((x_values[0], y_values[1]), (x_values[1], y_values[1])))),
            tuple(sorted(((x_values[0], y_values[0]), (x_values[0], y_values[1])))),
        }
        if points != corners or segments != expected:
            raise KiCadHandoffError("Edge.Cuts lines do not form one closed rectangle")
    if x_values[0] == x_values[1] or y_values[0] == y_values[1]:
        raise KiCadHandoffError("rectangular Edge.Cuts outline must have positive area")
    return x_values[0], y_values[0], x_values[1], y_values[1]


def _reference(footprint: list[Any], fallback: str) -> str:
    for prop in _children(footprint, "property"):
        if len(prop) >= 3 and prop[1] == "Reference" and isinstance(prop[2], str) and prop[2].strip():
            return prop[2].strip()
    for text in _children(footprint, "fp_text"):
        if len(text) >= 3 and text[1] == "reference" and isinstance(text[2], str) and text[2].strip():
            return text[2].strip()
    return fallback


def _mounting_holes(root: list[Any], bounds: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    minimum_x, minimum_y, maximum_x, maximum_y = bounds
    board_center = ((minimum_x + maximum_x) / 2, (minimum_y + maximum_y) / 2)
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_npth_ids = {
        id(node)
        for node in _all_nodes(root)
        if _head(node) == "pad" and len(node) >= 3 and node[2] == "np_thru_hole"
    }
    handled_npth_ids: set[int] = set()
    for footprint_index, footprint in enumerate(_children(root, "footprint")):
        name = footprint[1] if len(footprint) > 1 and isinstance(footprint[1], str) else ""
        pads = [pad for pad in _children(footprint, "pad") if len(pad) >= 3 and pad[2] == "np_thru_hole"]
        if not pads:
            continue
        handled_npth_ids.update(id(pad) for pad in pads)
        if "mountinghole" not in re.sub(r"[^a-z0-9]", "", name.lower()):
            raise KiCadHandoffError(
                f"footprint {name or footprint_index!r} contains NPTH pads but is not explicitly named as a mounting hole"
            )
        origin_node = _one_child(footprint, "at", f"footprint[{footprint_index}]")
        origin = _xy(origin_node, f"footprint[{footprint_index}].at")
        rotation = _number(origin_node[3], f"footprint[{footprint_index}].rotation", allow_zero=True, signed=True) if len(origin_node) >= 4 else 0.0
        radians = math.radians(rotation)
        cosine, sine = math.cos(radians), math.sin(radians)
        reference = _reference(footprint, f"MH{footprint_index + 1}")
        for pad_index, pad in enumerate(pads):
            if len(pad) < 4 or pad[3] != "circle":
                raise KiCadHandoffError(f"mounting-hole pad {reference!r} must be circular")
            at = _xy(_one_child(pad, "at", f"mounting-hole pad {reference!r}"), f"mounting-hole pad {reference!r}.at")
            drill = _one_child(pad, "drill", f"mounting-hole pad {reference!r}")
            if len(drill) != 2:
                raise KiCadHandoffError(f"mounting-hole pad {reference!r} must use one round drill diameter")
            diameter = _number(drill[1], f"mounting-hole pad {reference!r}.drill")
            absolute_x = origin[0] + at[0] * cosine - at[1] * sine
            absolute_y = origin[1] + at[0] * sine + at[1] * cosine
            centered = (absolute_x - board_center[0], absolute_y - board_center[1])
            identifier = reference if len(pads) == 1 else f"{reference}:{pad[1] or pad_index + 1}"
            if identifier in seen:
                raise KiCadHandoffError(f"duplicate extracted mounting-hole id: {identifier!r}")
            seen.add(identifier)
            result.append(
                {
                    "id": identifier,
                    "center_xy_mm": [round(centered[0], COORDINATE_DIGITS), round(centered[1], COORDINATE_DIGITS)],
                    "diameter_mm": diameter,
                }
            )
    if all_npth_ids != handled_npth_ids:
        raise KiCadHandoffError("NPTH pads outside supported footprint records cannot be classified as mounting holes")
    return result


def _review(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 1_048_576:
        raise KiCadHandoffError("KiCad mechanical review must be JSON text no larger than 1 MiB")
    try:
        raw = strict_json_loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise KiCadHandoffError(f"invalid KiCad mechanical review JSON: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != {
        "review_version",
        "connector_inventory_complete",
        "component_height_measured",
        "max_component_height_mm",
        "connectors",
    }:
        raise KiCadHandoffError("KiCad mechanical review has unsupported or missing fields")
    if raw["review_version"] != KICAD_MECHANICAL_REVIEW_VERSION:
        raise KiCadHandoffError("unsupported KiCad mechanical review version")
    if raw["connector_inventory_complete"] is not True or raw["component_height_measured"] is not True:
        raise KiCadHandoffError("connector inventory and component-height measurement must be explicitly complete")
    if not isinstance(raw["connectors"], list):
        raise KiCadHandoffError("KiCad mechanical review connectors must be an array")
    return raw


def _extract_source_fields(
    source: Path,
) -> tuple[str, float, float, float, list[dict[str, Any]], str]:
    if source.suffix.lower() != ".kicad_pcb" or not source.is_file():
        raise KiCadHandoffError("board_path must identify an existing .kicad_pcb file")
    with source.open("rb") as board_file:
        raw = board_file.read(MAX_LOCAL_BOARD_BYTES + 1)
    if not raw:
        raise KiCadHandoffError("bounded KiCad file extraction requires a non-empty board")
    if len(raw) > MAX_LOCAL_BOARD_BYTES:
        raise KiCadHandoffError("bounded KiCad file extraction is limited to 16 MiB")
    try:
        root = _parse_sexpr(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise KiCadHandoffError("KiCad board must be UTF-8") from exc
    version = _one_child(root, "version", "kicad_pcb")
    if len(version) != 2 or not isinstance(version[1], str) or not version[1].isdigit():
        raise KiCadHandoffError("KiCad board version must be an integer date token")
    general = _one_child(root, "general", "kicad_pcb")
    thickness_node = _one_child(general, "thickness", "kicad_pcb.general")
    if len(thickness_node) != 2:
        raise KiCadHandoffError("KiCad board thickness must contain exactly one value")
    thickness = _number(thickness_node[1], "kicad_pcb.general.thickness")
    bounds = _outline(root)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    if width < MIN_DIMENSION_MM or height < MIN_DIMENSION_MM or width > MAX_DIMENSION_MM or height > MAX_DIMENSION_MM:
        raise KiCadHandoffError("KiCad board outline dimensions are outside the supported range")
    return version[1], width, height, thickness, _mounting_holes(root, bounds), hashlib.sha256(raw).hexdigest()


def verify_kicad_file_geometry(
    board_path: Path,
    expected_size_mm: tuple[float, float, float],
    expected_holes: tuple[tuple[str, tuple[float, float], float], ...],
) -> None:
    """Re-extract source-derived fields before trusting a bounded receipt."""

    source = Path(board_path).expanduser().resolve()
    _, width, height, thickness, holes, _ = _extract_source_fields(source)
    actual_size = (width, height, thickness)
    if any(not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-6) for actual, expected in zip(actual_size, expected_size_mm)):
        raise KiCadHandoffError("bounded receipt board dimensions do not match the source KiCad file")
    actual_holes = tuple(
        (
            str(hole["id"]),
            (float(hole["center_xy_mm"][0]), float(hole["center_xy_mm"][1])),
            float(hole["diameter_mm"]),
        )
        for hole in holes
    )
    if actual_holes != expected_holes:
        raise KiCadHandoffError("bounded receipt mounting holes do not match the source KiCad file")


def extract_kicad_file_receipt(board_path: Path, review_text: str) -> dict[str, Any]:
    """Extract bounded board facts and bind reviewed mechanical facts to bytes."""

    source = Path(board_path).expanduser().resolve()
    version, width, height, thickness, mounting_holes, source_hash = _extract_source_fields(source)
    review = _review(review_text)
    receipt = {
        "contract_version": KICAD_HANDOFF_VERSION,
        "units": "mm",
        "source": {
            "name": source.name,
            "sha256": source_hash,
            "kicad_version": f"file-format-{version}",
        },
        "extraction": {
            "method": "bounded_file_parser",
            "complete": True,
            "complete_fields": sorted(REQUIRED_COMPLETE_FIELDS),
            "warnings": [],
            "unsupported_items": [],
            "review": {
                "review_version": KICAD_MECHANICAL_REVIEW_VERSION,
                "connector_inventory_complete": True,
                "component_height_measured": True,
                "extractor_version": KICAD_FILE_EXTRACTOR_VERSION,
            },
        },
        "board": {
            "outline": {"kind": "rectangle", "width_mm": width, "height_mm": height},
            "thickness_mm": thickness,
            "origin": "board_center",
            "mounting_holes": mounting_holes,
            "connectors": review["connectors"],
            "max_component_height_mm": review["max_component_height_mm"],
        },
    }
    parse_kicad_handoff(json.dumps(receipt, allow_nan=False), source_board=source)
    return receipt


def write_kicad_file_receipt(path: Path, board_path: Path, review_path: Path) -> Path:
    review = Path(review_path)
    if not review.is_file() or review.stat().st_size > 1_048_576:
        raise KiCadHandoffError("KiCad mechanical review path must identify a JSON file no larger than 1 MiB")
    try:
        review_text = review.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise KiCadHandoffError("KiCad mechanical review must be UTF-8 JSON") from exc
    return write_json_atomic(Path(path), extract_kicad_file_receipt(board_path, review_text))
