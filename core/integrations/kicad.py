"""Strict KiCad IPC/CLI handoff contract for a deliberately bounded board subset."""

from __future__ import annotations

import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..enclosure import MAX_DIMENSION_MM, MIN_DIMENSION_MM, PCBSpec
from ..json_io import strict_json_loads
from ..project import EnclosureProject, enclosure_spec_to_dict, semantic_diff, update_project
from .common import sha256_file, write_json_atomic

KICAD_HANDOFF_VERSION = "neurocad-kicad-handoff-v1"
KICAD_EXTRACTION_DRAFT_VERSION = "neurocad-kicad-extraction-draft-v1"
MAX_HANDOFF_BYTES = 1_048_576
MAX_BOARD_BYTES = 100 * 1_048_576
REQUIRED_COMPLETE_FIELDS = frozenset(
    {"board_outline", "board_thickness", "mounting_holes", "connectors", "max_component_height"}
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class KiCadHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class KiCadMountingHole:
    id: str
    center_xy_mm: tuple[float, float]
    diameter_mm: float


@dataclass(frozen=True)
class KiCadConnector:
    id: str
    kind: str
    center_xy_mm: tuple[float, float]
    height_mm: float


@dataclass(frozen=True)
class KiCadBoard:
    source_name: str
    source_sha256: str
    kicad_version: str
    extraction_method: str
    size_mm: tuple[float, float, float]
    mounting_holes: tuple[KiCadMountingHole, ...]
    connectors: tuple[KiCadConnector, ...]
    max_component_height_mm: float
    source_hash_verified: bool = False

    def to_pcb_spec(self) -> PCBSpec:
        if not self.source_hash_verified:
            raise KiCadHandoffError(
                "PCB conversion requires a handoff hash-bound to the actual source_board file"
            )
        return PCBSpec(
            size_mm=self.size_mm,
            mounting_holes_xy_mm=tuple(hole.center_xy_mm for hole in self.mounting_holes),
            component_height_mm=self.max_component_height_mm,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_sha256": self.source_sha256,
            "kicad_version": self.kicad_version,
            "extraction_method": self.extraction_method,
            "size_mm": list(self.size_mm),
            "mounting_holes": [
                {"id": hole.id, "center_xy_mm": list(hole.center_xy_mm), "diameter_mm": hole.diameter_mm}
                for hole in self.mounting_holes
            ],
            "connectors": [
                {
                    "id": connector.id,
                    "kind": connector.kind,
                    "center_xy_mm": list(connector.center_xy_mm),
                    "height_mm": connector.height_mm,
                }
                for connector in self.connectors
            ],
            "max_component_height_mm": self.max_component_height_mm,
            "source_hash_verified": self.source_hash_verified,
        }


@dataclass(frozen=True)
class KiCadProjectApplication:
    """A versioned project update plus data that still requires human design work."""

    project: EnclosureProject
    source_name: str
    source_sha256: str
    previous_revision: int
    changes: tuple[dict[str, Any], ...]
    connector_review: tuple[KiCadConnector, ...]
    mounting_hole_diameters_mm: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project.project_id,
            "revision": self.project.revision,
            "previous_revision": self.previous_revision,
            "source": {
                "name": self.source_name,
                "sha256": self.source_sha256,
                "hash_verified": True,
            },
            "changes": list(self.changes),
            "connector_review": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "center_xy_mm": list(item.center_xy_mm),
                    "height_mm": item.height_mm,
                }
                for item in self.connector_review
            ],
            "mounting_hole_diameters_mm": [
                {"id": identifier, "diameter_mm": diameter}
                for identifier, diameter in self.mounting_hole_diameters_mm
            ],
            "automatically_created_standoffs": False,
            "automatically_created_cutouts": False,
            "review_required": bool(self.connector_review or self.mounting_hole_diameters_mm),
        }


def apply_kicad_board_to_project(
    project: EnclosureProject,
    board: KiCadBoard,
    *,
    reason: str | None = None,
) -> KiCadProjectApplication:
    """Apply only the proven board envelope to a new project revision.

    Connector cutouts and standoffs remain explicit human-reviewed design
    decisions because a board extraction alone cannot prove their geometry.
    """

    if not isinstance(project, EnclosureProject):
        raise TypeError("project must be an EnclosureProject")
    if not isinstance(board, KiCadBoard):
        raise TypeError("board must be a KiCadBoard")
    pcb = board.to_pcb_spec()
    pcb_value = {
        "size_mm": list(pcb.size_mm),
        "origin_xy_mm": list(pcb.origin_xy_mm),
        "mounting_holes_xy_mm": [list(position) for position in pcb.mounting_holes_xy_mm],
        "component_height_mm": pcb.component_height_mm,
    }
    if enclosure_spec_to_dict(project.spec)["pcb"] == pcb_value:
        raise KiCadHandoffError("project PCB envelope already matches the hash-bound KiCad board")
    provenance = (
        f"Apply PCB envelope from hash-bound KiCad source {board.source_name} "
        f"(sha256:{board.source_sha256})"
    )
    if reason is not None:
        if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 128:
            raise ValueError("a custom KiCad application reason must contain 1 to 128 characters")
        audit_reason = f"{provenance}; {reason.strip()}"
    else:
        audit_reason = provenance
    revised = update_project(project, "pcb", pcb_value, reason=audit_reason)
    return KiCadProjectApplication(
        project=revised,
        source_name=board.source_name,
        source_sha256=board.source_sha256,
        previous_revision=project.revision,
        changes=semantic_diff(project, revised),
        connector_review=board.connectors,
        mounting_hole_diameters_mm=tuple(
            (hole.id, hole.diameter_mm) for hole in board.mounting_holes
        ),
    )


def _object(value: Any, path: str, *, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KiCadHandoffError(f"{path} must be an object")
    keys = set(value)
    missing = sorted(required - keys)
    unexpected = sorted(keys - required - (optional or set()))
    if missing:
        raise KiCadHandoffError(f"{path} is missing required fields: {', '.join(missing)}")
    if unexpected:
        raise KiCadHandoffError(f"{path} contains unsupported fields: {', '.join(unexpected)}")
    return value


def _text(value: Any, path: str, *, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KiCadHandoffError(f"{path} must contain 1 to {maximum} characters")
    return value.strip()


def _number(value: Any, path: str, *, allow_zero: bool = False, signed: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise KiCadHandoffError(f"{path} must be a finite number")
    result = float(value)
    if signed:
        if abs(result) > MAX_DIMENSION_MM:
            raise KiCadHandoffError(f"{path} magnitude exceeds {MAX_DIMENSION_MM:g} mm")
    else:
        minimum = 0.0 if allow_zero else MIN_DIMENSION_MM
        if result < minimum or result > MAX_DIMENSION_MM:
            raise KiCadHandoffError(f"{path} must be between {minimum:g} and {MAX_DIMENSION_MM:g} mm")
    return result


def _pair(value: Any, path: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise KiCadHandoffError(f"{path} must contain exactly two coordinates")
    return _number(value[0], f"{path}[0]", signed=True), _number(value[1], f"{path}[1]", signed=True)


def parse_kicad_handoff(text: str, *, source_board: Path | None = None) -> KiCadBoard:
    """Accept only a complete, explicit rectangular-board extraction receipt."""

    if not isinstance(text, str):
        raise TypeError("KiCad handoff must be JSON text")
    if len(text.encode("utf-8")) > MAX_HANDOFF_BYTES:
        raise KiCadHandoffError("KiCad handoff is limited to 1 MiB")
    try:
        raw = strict_json_loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise KiCadHandoffError(f"invalid KiCad handoff JSON: {exc}") from exc
    root = _object(
        raw,
        "$",
        required={"contract_version", "units", "source", "extraction", "board"},
    )
    if root["contract_version"] != KICAD_HANDOFF_VERSION:
        raise KiCadHandoffError(f"$.contract_version must be {KICAD_HANDOFF_VERSION!r}")
    if root["units"] != "mm":
        raise KiCadHandoffError("$.units must be 'mm'")

    source = _object(root["source"], "$.source", required={"name", "sha256", "kicad_version"})
    source_name = _text(source["name"], "$.source.name", maximum=255)
    if Path(source_name).name != source_name or "/" in source_name or "\\" in source_name:
        raise KiCadHandoffError("$.source.name must be a basename without path separators")
    if not source_name.lower().endswith(".kicad_pcb"):
        raise KiCadHandoffError("$.source.name must identify a .kicad_pcb source")
    source_hash = source["sha256"]
    if not isinstance(source_hash, str) or SHA256_PATTERN.fullmatch(source_hash) is None:
        raise KiCadHandoffError("$.source.sha256 must be a lowercase SHA-256 digest")
    kicad_version = _text(source["kicad_version"], "$.source.kicad_version", maximum=64)

    extraction = _object(
        root["extraction"],
        "$.extraction",
        required={"method", "complete", "complete_fields", "warnings", "unsupported_items"},
    )
    if extraction["method"] not in {"ipc_api", "kicad_cli"}:
        raise KiCadHandoffError("$.extraction.method must be 'ipc_api' or 'kicad_cli'")
    if extraction["complete"] is not True:
        raise KiCadHandoffError("partial KiCad extraction is rejected: $.extraction.complete must be true")
    complete_fields = extraction["complete_fields"]
    if not isinstance(complete_fields, list) or any(not isinstance(item, str) for item in complete_fields):
        raise KiCadHandoffError("$.extraction.complete_fields must be an array of field names")
    if len(complete_fields) != len(set(complete_fields)) or set(complete_fields) != REQUIRED_COMPLETE_FIELDS:
        raise KiCadHandoffError("$.extraction.complete_fields must list every required board field exactly once")
    for field in ("warnings", "unsupported_items"):
        value = extraction[field]
        if not isinstance(value, list):
            raise KiCadHandoffError(f"$.extraction.{field} must be an array")
        if value:
            raise KiCadHandoffError(f"partial KiCad extraction is rejected: $.extraction.{field} is not empty")

    board = _object(
        root["board"],
        "$.board",
        required={
            "outline",
            "thickness_mm",
            "origin",
            "mounting_holes",
            "connectors",
            "max_component_height_mm",
        },
    )
    outline = _object(board["outline"], "$.board.outline", required={"kind", "width_mm", "height_mm"})
    if outline["kind"] != "rectangle":
        raise KiCadHandoffError("only a declared rectangular KiCad board outline is supported")
    width = _number(outline["width_mm"], "$.board.outline.width_mm")
    height = _number(outline["height_mm"], "$.board.outline.height_mm")
    thickness = _number(board["thickness_mm"], "$.board.thickness_mm")
    if board["origin"] != "board_center":
        raise KiCadHandoffError("$.board.origin must be 'board_center'")

    holes_raw = board["mounting_holes"]
    if not isinstance(holes_raw, list) or len(holes_raw) > 256:
        raise KiCadHandoffError("$.board.mounting_holes must be an array of at most 256 items")
    holes: list[KiCadMountingHole] = []
    identifiers: set[str] = set()
    for index, raw_hole in enumerate(holes_raw):
        path = f"$.board.mounting_holes[{index}]"
        hole = _object(raw_hole, path, required={"id", "center_xy_mm", "diameter_mm"})
        identifier = _text(hole["id"], f"{path}.id")
        if identifier in identifiers:
            raise KiCadHandoffError(f"{path}.id is duplicated")
        identifiers.add(identifier)
        center = _pair(hole["center_xy_mm"], f"{path}.center_xy_mm")
        diameter = _number(hole["diameter_mm"], f"{path}.diameter_mm")
        if abs(center[0]) + diameter / 2 > width / 2 or abs(center[1]) + diameter / 2 > height / 2:
            raise KiCadHandoffError(f"{path} lies outside the rectangular board outline")
        holes.append(KiCadMountingHole(identifier, center, diameter))

    connectors_raw = board["connectors"]
    if not isinstance(connectors_raw, list) or len(connectors_raw) > 512:
        raise KiCadHandoffError("$.board.connectors must be an array of at most 512 items")
    connectors: list[KiCadConnector] = []
    for index, raw_connector in enumerate(connectors_raw):
        path = f"$.board.connectors[{index}]"
        connector = _object(raw_connector, path, required={"id", "kind", "center_xy_mm", "height_mm"})
        identifier = _text(connector["id"], f"{path}.id")
        if identifier in identifiers:
            raise KiCadHandoffError(f"{path}.id is duplicated")
        identifiers.add(identifier)
        kind = _text(connector["kind"], f"{path}.kind")
        center = _pair(connector["center_xy_mm"], f"{path}.center_xy_mm")
        if abs(center[0]) > width / 2 or abs(center[1]) > height / 2:
            raise KiCadHandoffError(f"{path} center lies outside the rectangular board outline")
        connector_height = _number(connector["height_mm"], f"{path}.height_mm", allow_zero=True)
        connectors.append(KiCadConnector(identifier, kind, center, connector_height))
    max_height = _number(
        board["max_component_height_mm"],
        "$.board.max_component_height_mm",
        allow_zero=True,
    )
    if any(connector.height_mm > max_height for connector in connectors):
        raise KiCadHandoffError("connector height exceeds $.board.max_component_height_mm")
    source_hash_verified = False
    if source_board is not None:
        source_path = Path(source_board).expanduser().resolve()
        if source_path.suffix.lower() != ".kicad_pcb" or not source_path.is_file():
            raise KiCadHandoffError("source_board must identify an existing .kicad_pcb file")
        source_size = source_path.stat().st_size
        if source_size <= 0 or source_size > MAX_BOARD_BYTES:
            raise KiCadHandoffError("source_board must be non-empty and no larger than 100 MiB")
        if source_path.name != source_name:
            raise KiCadHandoffError("source_board basename does not match $.source.name")
        if sha256_file(source_path) != source_hash:
            raise KiCadHandoffError("source_board hash does not match $.source.sha256")
        source_hash_verified = True
    return KiCadBoard(
        source_name,
        source_hash,
        kicad_version,
        extraction["method"],
        (width, height, thickness),
        tuple(holes),
        tuple(connectors),
        max_height,
        source_hash_verified,
    )


def read_kicad_handoff(path: Path, *, source_board: Path | None = None) -> KiCadBoard:
    path = Path(path)
    if not path.is_file():
        raise KiCadHandoffError("KiCad handoff path must identify a file")
    raw = path.read_bytes()
    if len(raw) > MAX_HANDOFF_BYTES:
        raise KiCadHandoffError("KiCad handoff is limited to 1 MiB")
    try:
        return parse_kicad_handoff(raw.decode("utf-8"), source_board=source_board)
    except UnicodeDecodeError as exc:
        raise KiCadHandoffError("KiCad handoff must be UTF-8 JSON") from exc


def bind_kicad_extraction(text: str, source_board: Path) -> dict[str, Any]:
    """Bind reviewed extraction facts to the exact source board bytes.

    This does not parse KiCad or claim that extraction ran. It removes manual
    filename/hash transcription from the external-extractor boundary and then
    validates the completed receipt against the real board file.
    """

    if not isinstance(text, str):
        raise TypeError("KiCad extraction draft must be JSON text")
    if len(text.encode("utf-8")) > MAX_HANDOFF_BYTES:
        raise KiCadHandoffError("KiCad extraction draft is limited to 1 MiB")
    try:
        raw = strict_json_loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise KiCadHandoffError(f"invalid KiCad extraction draft JSON: {exc}") from exc
    root = _object(
        raw,
        "$",
        required={"draft_version", "units", "source", "extraction", "board"},
    )
    if root["draft_version"] != KICAD_EXTRACTION_DRAFT_VERSION:
        raise KiCadHandoffError(f"$.draft_version must be {KICAD_EXTRACTION_DRAFT_VERSION!r}")
    source = _object(root["source"], "$.source", required={"kicad_version"})
    kicad_version = _text(source["kicad_version"], "$.source.kicad_version", maximum=64)
    request = create_kicad_extraction_request(source_board)
    receipt = {
        "contract_version": KICAD_HANDOFF_VERSION,
        "units": root["units"],
        "source": {
            "name": request["source"]["name"],
            "sha256": request["source"]["sha256"],
            "kicad_version": kicad_version,
        },
        "extraction": root["extraction"],
        "board": root["board"],
    }
    parse_kicad_handoff(json.dumps(receipt, allow_nan=False), source_board=source_board)
    return receipt


def write_bound_kicad_extraction(path: Path, draft_path: Path, source_board: Path) -> Path:
    draft_path = Path(draft_path)
    if not draft_path.is_file():
        raise KiCadHandoffError("KiCad extraction draft path must identify a file")
    raw = draft_path.read_bytes()
    if len(raw) > MAX_HANDOFF_BYTES:
        raise KiCadHandoffError("KiCad extraction draft is limited to 1 MiB")
    try:
        payload = bind_kicad_extraction(raw.decode("utf-8"), source_board)
    except UnicodeDecodeError as exc:
        raise KiCadHandoffError("KiCad extraction draft must be UTF-8 JSON") from exc
    return write_json_atomic(Path(path), payload)


def create_kicad_extraction_request(board_path: Path) -> dict[str, Any]:
    """Describe the external extraction gate without pretending it ran."""

    board_path = Path(board_path).expanduser().resolve()
    if board_path.suffix.lower() != ".kicad_pcb" or not board_path.is_file():
        raise KiCadHandoffError("board_path must identify an existing .kicad_pcb file")
    size = board_path.stat().st_size
    if size <= 0 or size > MAX_BOARD_BYTES:
        raise KiCadHandoffError("KiCad board input must be non-empty and no larger than 100 MiB")
    executable = shutil.which("kicad-cli")
    return {
        "contract_version": KICAD_HANDOFF_VERSION,
        "status": "external_extraction_required",
        "operation_executed": False,
        "raw_board_parsed": False,
        "source": {
            "name": board_path.name,
            "sha256": sha256_file(board_path),
            "bytes": size,
        },
        "detected_prerequisites": {
            "kicad_cli": executable is not None,
            "kicad_ipc_session": False,
        },
        "accepted_extraction_methods": ["ipc_api", "kicad_cli"],
        "required_complete_fields": sorted(REQUIRED_COMPLETE_FIELDS),
        "instructions": (
            "Use a trusted KiCad IPC add-on or reviewed kicad-cli wrapper to produce the complete handoff JSON; "
            "NeuroCAD will reject warnings, unsupported items, missing fields, and non-rectangular outlines."
        ),
    }


def write_kicad_extraction_request(path: Path, board_path: Path) -> Path:
    return write_json_atomic(Path(path), create_kicad_extraction_request(board_path))
