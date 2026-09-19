"""Explainable natural-language interpretation for typed enclosure projects.

The deterministic interpreter accepts a documented clause grammar.  Flexible
language-model providers may propose the same payload, but every meaningful
source character must be accounted for and the resulting specification still
passes the deterministic validator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .enclosure import (
    HARDWARE_PROFILES,
    CutoutSpec,
    EnclosureSpec,
    LidSpec,
    PCBSpec,
    StandoffSpec,
    VentPatternSpec,
    validate_enclosure_spec,
)
from .engineering_math import symmetric_positions
from .project import PhraseMapping, enclosure_spec_from_dict

NUMBER = r"(?:0|[1-9]\d*)(?:\.\d+)?"
SIGNED_NUMBER = rf"-?{NUMBER}"
UNIT = r"(?:mm|millimet(?:er|re)s?|cm|centimet(?:er|re)s?|in|inches?|inch)"
FACE = r"(?:front|rear|back|left|right|bottom|top)"
HARDWARE = r"M(?:2(?:\.5)?|3|4)"
COUNT = r"(?:[1-9]\d*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"

_UNIT_TO_MM = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "millimetre": 1.0,
    "millimetres": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "centimetre": 10.0,
    "centimetres": 10.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
}
_COUNT_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_CLAUSE_LEAD = (
    r"(?:an?\s+)?(?:make|create|design|build|outer|enclosure|case|housing|walls?|wall\s+thickness|"
    r"floor|floor\s+thickness|corner\s+radius|manufacturing\s+profile|profile|fdm|resin|open[- ]top|"
    r"no\s+lid|lidless|screw|slide|friction|rectangular\s+cutout|circular\s+cutout|vent\s+grid|"
    rf"{COUNT}\s+{HARDWARE}\s+standoffs|pcb|title|called|named)"
)


@dataclass(frozen=True)
class InterpretationIssue:
    kind: str  # question | unsupported | invalid
    message: str
    text: str | None = None
    start: int | None = None
    end: int | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class InterpretationAssumption:
    field: str
    value: Any
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "value": self.value, "reason": self.reason}


@dataclass(frozen=True)
class IntentInterpretation:
    source: str
    spec: EnclosureSpec | None
    mappings: tuple[PhraseMapping, ...]
    issues: tuple[InterpretationIssue, ...]
    interpreter: str
    assumptions: tuple[InterpretationAssumption, ...] = ()

    @property
    def ready(self) -> bool:
        return self.spec is not None and not self.issues

    def require_spec(self) -> EnclosureSpec:
        if not self.ready or self.spec is None:
            raise ValueError("interpretation is unresolved: " + "; ".join(issue.message for issue in self.issues))
        return self.spec

    def to_dict(self) -> dict[str, Any]:
        from .project import enclosure_spec_to_dict

        return {
            "source": self.source,
            "ready": self.ready,
            "interpreter": self.interpreter,
            "spec": enclosure_spec_to_dict(self.spec) if self.spec is not None else None,
            "mappings": [
                {"text": mapping.text, "field": mapping.field, "start": mapping.start, "end": mapping.end}
                for mapping in self.mappings
            ],
            "issues": [issue.to_dict() for issue in self.issues],
            "assumptions": [assumption.to_dict() for assumption in self.assumptions],
        }


def _clauses(source: str) -> tuple[tuple[str, int, int], ...]:
    """Return auditable requirement clauses without losing source offsets.

    Semicolons and newlines are unconditional boundaries. Sentence punctuation
    is also accepted, while ``with`` and ``and`` split only before a recognized
    requirement lead. This keeps ordinary prose ergonomic without treating
    arbitrary conjunctions as understood engineering intent.
    """

    clauses: list[tuple[str, int, int]] = []
    primary_boundary = re.compile(r";|\r?\n+|[.!?](?=\s|$)")
    conversational_boundary = re.compile(
        rf"(?:,\s*|\s+)(?:with|and)\s+(?={_CLAUSE_LEAD}\b)",
        re.IGNORECASE,
    )

    def append_segment(start: int, end: int) -> None:
        raw = source[start:end]
        leading = len(raw) - len(raw.lstrip())
        trimmed = raw.rstrip(" \t,.")
        text = trimmed[leading:]
        if text:
            clauses.append((text, start + leading, start + len(trimmed)))

    primary_start = 0
    for boundary in (*primary_boundary.finditer(source), None):
        primary_end = len(source) if boundary is None else boundary.start()
        segment_start = primary_start
        segment = source[primary_start:primary_end]
        for connector in conversational_boundary.finditer(segment):
            append_segment(segment_start, primary_start + connector.start())
            segment_start = primary_start + connector.end()
        append_segment(segment_start, primary_end)
        if boundary is None:
            break
        primary_start = boundary.end()
    return tuple(clauses)


def _float(match: re.Match[str], name: str) -> float:
    return float(match.group(name))


def _millimetres(match: re.Match[str], name: str, unit_name: str = "unit") -> float:
    value = _float(match, name)
    unit = match.group(unit_name).lower()
    return value * _UNIT_TO_MM[unit]


def _bounded_int(match: re.Match[str], name: str, maximum: int) -> int:
    raw = match.group(name)
    if len(raw) > 4:
        raise ValueError(f"{name} exceeds the supported maximum of {maximum}")
    value = int(raw)
    if value > maximum:
        raise ValueError(f"{name} exceeds the supported maximum of {maximum}")
    return value


def _bounded_count(match: re.Match[str], name: str, maximum: int) -> int:
    raw = match.group(name).lower()
    if raw in _COUNT_WORDS:
        return _COUNT_WORDS[raw]
    return _bounded_int(match, name, maximum)


def _face(match: re.Match[str]) -> str:
    face = match.group("face").lower()
    return "rear" if face == "back" else face


def _center_uv(match: re.Match[str]) -> tuple[float, float]:
    if match.groupdict().get("center") is not None:
        return (0.0, 0.0)
    return (
        _millimetres(match, "u", "position_unit"),
        _millimetres(match, "v", "position_unit"),
    )


def _unsupported_suggestion(clause: str) -> str:
    lowered = clause.lower()
    if any(word in lowered for word in ("waterproof", "watertight", "food safe", "load bearing", "certified")):
        return "Safety and environmental ratings require a measurable specification and qualified external review."
    if re.search(r"\d", clause) and not re.search(UNIT, clause, re.IGNORECASE):
        return "Include units after every dimension group, such as '120 x 80 x 30 mm' or '0.25 inch'."
    return (
        "Use a measurable clause such as 'walls 2 mm', 'open top', "
        "'friction lid 3 mm thick clearance 0.25 mm', or 'rectangular cutout 12 x 7 mm on rear at center'."
    )


def _mapping(text: str, field: str, start: int, end: int) -> PhraseMapping:
    return PhraseMapping(text, field, start, end)


def interpret_enclosure(source: str) -> IntentInterpretation:
    """Interpret semicolon-delimited, fully explicit enclosure clauses.

    Semicolons are intentional: they provide an auditable clause boundary.  A
    flexible LLM UI should translate conversational input through
    :func:`interpret_provider_payload`, not relax this deterministic grammar.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    if len(source) > 8192:
        raise ValueError("source is limited to 8192 characters")
    values: dict[str, Any] = {
        "title": "electronics enclosure",
        "corner_radius_mm": 0.0,
        "floor_mm": None,
        "cutouts": [],
        "standoffs": [],
        "vents": [],
        "pcb": None,
    }
    mappings: list[PhraseMapping] = []
    issues: list[InterpretationIssue] = []
    lid_values: dict[str, Any] | None = None
    pending_standoffs: list[dict[str, Any]] = []
    assumptions: list[InterpretationAssumption] = []
    seen_singletons: set[str] = set()

    patterns: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "outer_size_mm",
            re.compile(
                rf"(?:make|create|design|build)?\s*(?:an?\s+)?(?P<w>{NUMBER})\s*[x×]\s*(?P<d>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER})\s*(?P<unit>{UNIT})\s+(?:electronics\s+)?(?:enclosure|case|housing)",
                re.IGNORECASE,
            ),
        ),
        (
            "outer_size_mm",
            re.compile(
                rf"(?:make|create|design|build)?\s*(?:an?\s+)?(?:electronics\s+)?(?:enclosure|case|housing)\s+(?P<w>{NUMBER})\s*[x×]\s*(?P<d>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER})\s*(?P<unit>{UNIT})",
                re.IGNORECASE,
            ),
        ),
        (
            "wall_mm",
            re.compile(rf"(?:wall|walls|wall thickness)\s+(?P<value>{NUMBER})\s*(?P<unit>{UNIT})(?:\s+thick)?", re.IGNORECASE),
        ),
        (
            "floor_mm",
            re.compile(rf"(?:floor|floor thickness)\s+(?P<value>{NUMBER})\s*(?P<unit>{UNIT})(?:\s+thick)?", re.IGNORECASE),
        ),
        ("corner_radius_mm", re.compile(rf"corner radius\s+(?P<value>{NUMBER})\s*(?P<unit>{UNIT})", re.IGNORECASE)),
        (
            "profile",
            re.compile(
                r"(?:an?\s+)?(?:(?:manufacturing\s+)?profile\s+(?P<value>fdm[ _-](?:draft|standard|precision)|resin[ _-]standard)|"
                r"(?P<leading_value>fdm[ _-](?:draft|standard|precision)|resin[ _-]standard)\s+(?:manufacturing\s+)?profile)",
                re.IGNORECASE,
            ),
        ),
        ("lid.none", re.compile(r"(?:an?\s+)?(?:open[- ]top|no lid|lidless)(?:\s+(?:enclosure|case|housing))?", re.IGNORECASE)),
        (
            "lid",
            re.compile(
                rf"(?:an?\s+)?(?P<kind>screw|slide|friction)(?:[- ]fit)?\s+lid\s+(?P<thickness>{NUMBER})\s*(?P<thickness_unit>{UNIT})\s+thick\s+(?:with\s+)?clearance\s+(?P<clearance>{NUMBER})\s*(?P<clearance_unit>{UNIT})"
                rf"(?:\s+(?:with\s+)?lip\s+(?P<lip>{NUMBER})\s*(?P<lip_unit>{UNIT}))?(?:\s+(?:with\s+)?(?P<hardware>{HARDWARE})\s+fasteners\s+at\s+corners\s+inset\s+(?P<inset>{NUMBER})\s*(?P<inset_unit>{UNIT}))?",
                re.IGNORECASE,
            ),
        ),
        (
            "cutout.rectangular",
            re.compile(
                rf"(?:an?\s+)?rectangular\s+cutout\s+(?P<w>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER})\s*(?P<size_unit>{UNIT})\s+on\s+(?:the\s+)?(?P<face>{FACE})(?:\s+face)?\s+at\s+(?:(?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER})\s*(?P<position_unit>{UNIT})|(?P<center>(?:the\s+)?cent(?:er|re)(?:ed)?))(?:\s+for\s+(?P<purpose>[A-Za-z0-9][A-Za-z0-9 _./+-]{{0,63}}))?",
                re.IGNORECASE,
            ),
        ),
        (
            "cutout.circular",
            re.compile(
                rf"(?:an?\s+)?circular\s+cutout\s+(?P<diameter>{NUMBER})\s*(?P<size_unit>{UNIT})\s+diameter\s+on\s+(?:the\s+)?(?P<face>{FACE})(?:\s+face)?\s+at\s+(?:(?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER})\s*(?P<position_unit>{UNIT})|(?P<center>(?:the\s+)?cent(?:er|re)(?:ed)?))(?:\s+for\s+(?P<purpose>[A-Za-z0-9][A-Za-z0-9 _./+-]{{0,63}}))?",
                re.IGNORECASE,
            ),
        ),
        (
            "vent",
            re.compile(
                rf"(?:an?\s+)?vent grid\s+(?P<rows>[1-9]\d*)\s*[x×]\s*(?P<columns>[1-9]\d*)\s+holes\s+(?P<diameter>{NUMBER})\s*(?P<diameter_unit>{UNIT})\s+diameter\s+pitch\s+(?P<pitch>{NUMBER})\s*(?P<pitch_unit>{UNIT})\s+on\s+(?:the\s+)?(?P<face>{FACE})(?:\s+face)?\s+at\s+(?:(?P<u>{SIGNED_NUMBER})\s*[x×,]\s*(?P<v>{SIGNED_NUMBER})\s*(?P<position_unit>{UNIT})|(?P<center>(?:the\s+)?cent(?:er|re)(?:ed)?))",
                re.IGNORECASE,
            ),
        ),
        (
            "standoffs",
            re.compile(
                rf"(?P<count>{COUNT})\s+(?P<hardware>{HARDWARE})\s+standoffs\s+(?P<height>{NUMBER})\s*(?P<height_unit>{UNIT})\s+high\s+at\s+(?:the\s+)?corners\s+inset\s+(?P<inset>{NUMBER})\s*(?P<inset_unit>{UNIT})",
                re.IGNORECASE,
            ),
        ),
        (
            "pcb",
            re.compile(
                rf"(?:an?\s+)?pcb\s+(?P<w>{NUMBER})\s*[x×]\s*(?P<d>{NUMBER})\s*[x×]\s*(?P<t>{NUMBER})\s*(?P<size_unit>{UNIT})(?:\s+(?:with\s+)?component height\s+(?P<component>{NUMBER})\s*(?P<component_unit>{UNIT}))?",
                re.IGNORECASE,
            ),
        ),
        (
            "title",
            re.compile(r"(?:title|called|named)\s+(?:\"(?P<quoted>[A-Za-z0-9][A-Za-z0-9 _.-]{0,127})\"|(?P<value>[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}))", re.IGNORECASE),
        ),
    )

    cutout_index = 0
    vent_index = 0
    for clause, start, end in _clauses(source):
        matched = False
        for kind, pattern in patterns:
            match = pattern.fullmatch(clause)
            if match is None:
                continue
            matched = True
            singleton = "lid" if kind in {"lid", "lid.none"} else kind
            if singleton in {"outer_size_mm", "wall_mm", "floor_mm", "corner_radius_mm", "profile", "lid", "pcb", "title"}:
                if singleton in seen_singletons:
                    issues.append(
                        InterpretationIssue(
                            "invalid",
                            f"conflicting repeated {singleton} clause",
                            clause,
                            start,
                            end,
                        )
                    )
                    break
                seen_singletons.add(singleton)
            mappings.append(_mapping(clause, kind, start, end))
            try:
                if kind == "outer_size_mm":
                    values[kind] = (
                        _millimetres(match, "w"),
                        _millimetres(match, "d"),
                        _millimetres(match, "h"),
                    )
                elif kind in {"wall_mm", "floor_mm", "corner_radius_mm"}:
                    values[kind] = _millimetres(match, "value")
                elif kind == "profile":
                    profile_value = match.group("value") or match.group("leading_value")
                    values[kind] = re.sub(r"[ -]", "_", profile_value.lower())
                elif kind == "lid.none":
                    lid_values = {"kind": "none", "thickness_mm": 0.0, "clearance_mm": 0.0}
                elif kind == "lid":
                    lid_kind = match.group("kind").lower()
                    lid_values = {
                        "kind": lid_kind,
                        "thickness_mm": _millimetres(match, "thickness", "thickness_unit"),
                        "clearance_mm": _millimetres(match, "clearance", "clearance_unit"),
                        "lip_height_mm": (
                            _millimetres(match, "lip", "lip_unit") if match.group("lip") is not None else 0.0
                        ),
                        "hardware": match.group("hardware").upper() if match.group("hardware") else None,
                        "inset_mm": (
                            _millimetres(match, "inset", "inset_unit") if match.group("inset") is not None else None
                        ),
                    }
                elif kind.startswith("cutout"):
                    cutout_index += 1
                    cutout_id = f"cutout_{cutout_index}"
                    face = _face(match)
                    center_uv = _center_uv(match)
                    purpose = match.group("purpose") or "generic"
                    if kind.endswith("rectangular"):
                        values["cutouts"].append(
                            CutoutSpec(
                                id=cutout_id,
                                kind="rectangular",
                                face=face,
                                center_uv_mm=center_uv,
                                size_mm=(
                                    _millimetres(match, "w", "size_unit"),
                                    _millimetres(match, "h", "size_unit"),
                                ),
                                purpose=purpose,
                            )
                        )
                    else:
                        values["cutouts"].append(
                            CutoutSpec(
                                id=cutout_id,
                                kind="circular",
                                face=face,
                                center_uv_mm=center_uv,
                                diameter_mm=_millimetres(match, "diameter", "size_unit"),
                                purpose=purpose,
                            )
                        )
                elif kind == "vent":
                    vent_index += 1
                    values["vents"].append(
                        VentPatternSpec(
                            id=f"vent_{vent_index}",
                            face=_face(match),
                            center_uv_mm=_center_uv(match),
                            rows=_bounded_int(match, "rows", 64),
                            columns=_bounded_int(match, "columns", 64),
                            diameter_mm=_millimetres(match, "diameter", "diameter_unit"),
                            pitch_mm=_millimetres(match, "pitch", "pitch_unit"),
                        )
                    )
                elif kind == "standoffs":
                    pending_standoffs.append(
                        {
                            "count": _bounded_count(match, "count", 256),
                            "hardware": match.group("hardware").upper(),
                            "height_mm": _millimetres(match, "height", "height_unit"),
                            "inset_mm": _millimetres(match, "inset", "inset_unit"),
                        }
                    )
                elif kind == "pcb":
                    values["pcb"] = PCBSpec(
                        size_mm=(
                            _millimetres(match, "w", "size_unit"),
                            _millimetres(match, "d", "size_unit"),
                            _millimetres(match, "t", "size_unit"),
                        ),
                        component_height_mm=(
                            _millimetres(match, "component", "component_unit")
                            if match.group("component") is not None
                            else 0.0
                        ),
                    )
                elif kind == "title":
                    values["title"] = (match.group("quoted") or match.group("value")).strip()
            except (OverflowError, ValueError) as exc:
                issues.append(InterpretationIssue("invalid", str(exc), clause, start, end))
            break
        if not matched:
            issues.append(
                InterpretationIssue(
                    "unsupported",
                    "clause was not understood",
                    clause,
                    start,
                    end,
                    _unsupported_suggestion(clause),
                )
            )

    required_questions = {
        "outer_size_mm": "What exact outer width, depth, and height should the enclosure use?",
        "wall_mm": "What wall thickness should be used?",
        "profile": "Which manufacturing profile should be used?",
    }
    for key, question in required_questions.items():
        if key not in values:
            issues.append(InterpretationIssue("question", question))
    if lid_values is None:
        issues.append(InterpretationIssue("question", "Should the enclosure be open-top or use a screw or friction lid?"))

    outer = values.get("outer_size_mm")
    if lid_values is not None and lid_values["kind"] == "friction" and lid_values["lip_height_mm"] == 0:
        wall = values.get("wall_mm")
        if wall is not None:
            lid_values["lip_height_mm"] = wall
            assumptions.append(
                InterpretationAssumption(
                    "lid.lip_height_mm",
                    wall,
                    "No insertion depth was stated; the deterministic friction-lid rule uses the declared wall thickness.",
                )
            )
        else:
            issues.append(
                InterpretationIssue(
                    "question",
                    "What insertion plug height should the friction lid use?",
                    suggestion="State 'lip 2 mm' or provide wall thickness for the disclosed wall-thickness default.",
                )
            )
    if outer is not None:
        width, depth, _ = outer
        for pending in pending_standoffs:
            hardware = HARDWARE_PROFILES[pending["hardware"]]
            try:
                positions = symmetric_positions(pending["count"], width, depth, pending["inset_mm"])
            except ValueError as exc:
                issues.append(InterpretationIssue("invalid", f"invalid standoff placement: {exc}"))
                continue
            for index, position in enumerate(positions, start=1):
                values["standoffs"].append(
                    StandoffSpec(
                        id=f"standoff_{len(values['standoffs']) + 1}",
                        center_xy_mm=position,
                        height_mm=pending["height_mm"],
                        outer_diameter_mm=hardware.boss_outer_mm,
                        hole_diameter_mm=hardware.pilot_hole_mm,
                        hardware=pending["hardware"],
                    )
                )
        if lid_values is not None and lid_values["kind"] == "screw":
            hardware_name = lid_values.get("hardware")
            inset = lid_values.get("inset_mm")
            if hardware_name is None or inset is None:
                issues.append(
                    InterpretationIssue(
                        "question",
                        "A screw lid requires explicit hardware and corner inset, for example 'M3 fasteners at corners inset 8 mm'.",
                    )
                )
            else:
                try:
                    lid_values["fastener_positions_xy_mm"] = symmetric_positions(4, width, depth, inset)
                except ValueError as exc:
                    issues.append(InterpretationIssue("invalid", f"invalid lid fastener placement: {exc}"))
    elif pending_standoffs:
        issues.append(InterpretationIssue("question", "Standoff placement requires the outer enclosure dimensions."))

    spec: EnclosureSpec | None = None
    if not any(issue.kind in {"question", "unsupported", "invalid"} for issue in issues) and lid_values is not None:
        lid_values.pop("inset_mm", None)
        spec = EnclosureSpec(
            outer_size_mm=values["outer_size_mm"],
            wall_mm=values["wall_mm"],
            profile=values["profile"],
            lid=LidSpec(**lid_values),
            corner_radius_mm=values["corner_radius_mm"],
            floor_mm=values["floor_mm"],
            cutouts=tuple(values["cutouts"]),
            standoffs=tuple(values["standoffs"]),
            vents=tuple(values["vents"]),
            pcb=values["pcb"],
            title=values["title"],
        )
        report = validate_enclosure_spec(spec)
        for issue in report.errors:
            issues.append(InterpretationIssue("invalid", f"{issue.path}: {issue.message}"))
        if issues:
            spec = None
    return IntentInterpretation(
        source,
        spec,
        tuple(mappings),
        tuple(issues),
        "deterministic-clause-v2",
        tuple(assumptions),
    )


def interpret_provider_payload(
    source: str,
    payload: Any,
    *,
    confirmed: bool = False,
) -> IntentInterpretation:
    """Validate a schema-constrained language-model/provider proposal.

    Payload format is ``{spec, mappings, questions, unsupported}``.  Mappings
    contain exact ``text``, ``field``, ``start`` and ``end`` values.  Every
    alphanumeric source character must be covered by a mapping or an unsupported
    span, so providers cannot silently drop requested language.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    if len(source) > 8192:
        raise ValueError("source is limited to 8192 characters")
    if not isinstance(confirmed, bool):
        raise TypeError("confirmed must be a boolean supplied by the trusted caller")
    if not isinstance(payload, dict):
        raise TypeError("provider payload must be an object")
    allowed = {"spec", "mappings", "questions", "unsupported"}
    if set(payload) != allowed:
        raise ValueError("provider payload requires exactly spec, mappings, questions, and unsupported")
    mappings_raw = payload["mappings"]
    questions_raw = payload["questions"]
    unsupported_raw = payload["unsupported"]
    if not isinstance(mappings_raw, list) or not isinstance(questions_raw, list) or not isinstance(unsupported_raw, list):
        raise TypeError("provider mappings, questions, and unsupported must be arrays")
    mappings: list[PhraseMapping] = []
    covered = [False] * len(source)

    def span(entry: Any, *, field_required: bool) -> tuple[str, int, int, str]:
        if not isinstance(entry, dict):
            raise TypeError("provider spans must be objects")
        expected = {"text", "start", "end", "field"} if field_required else {"text", "start", "end", "reason"}
        if set(entry) != expected:
            raise ValueError(f"provider span requires exactly {', '.join(sorted(expected))}")
        start, end = entry["start"], entry["end"]
        if isinstance(start, bool) or not isinstance(start, int) or isinstance(end, bool) or not isinstance(end, int):
            raise TypeError("provider span offsets must be integers")
        entry_text = entry["text"]
        annotation = entry["field"] if field_required else entry["reason"]
        if not isinstance(entry_text, str) or not isinstance(annotation, str) or not annotation.strip():
            raise TypeError("provider span text and annotation must be strings")
        if not 0 <= start < end <= len(source) or source[start:end] != entry_text:
            raise ValueError("provider span does not match the source text")
        return entry_text, start, end, annotation

    for entry in mappings_raw:
        text, start, end, field = span(entry, field_required=True)
        if re.fullmatch(
            r"(?:title|outer_size_mm|wall_mm|floor_mm|corner_radius_mm|profile|"
            r"lid(?:\.(?:kind|thickness_mm|clearance_mm|lip_height_mm|hardware|fastener_positions_xy_mm))?|"
            r"cutouts(?:\[\d+\](?:\.[A-Za-z_][A-Za-z0-9_]*)?)?|"
            r"standoffs(?:\[\d+\](?:\.[A-Za-z_][A-Za-z0-9_]*)?)?|"
            r"vents(?:\[\d+\](?:\.[A-Za-z_][A-Za-z0-9_]*)?)?|"
            r"pcb(?:\.[A-Za-z_][A-Za-z0-9_]*)?)",
            field,
        ) is None:
            raise ValueError(f"provider mapping uses unsupported field {field!r}")
        mappings.append(PhraseMapping(text, field, start, end))
        for index in range(start, end):
            covered[index] = True
    issues: list[InterpretationIssue] = []
    for entry in unsupported_raw:
        text, start, end, reason = span(entry, field_required=False)
        issues.append(InterpretationIssue("unsupported", reason, text, start, end))
        for index in range(start, end):
            covered[index] = True
    for question in questions_raw:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("provider questions must be non-empty strings")
        if len(question) > 512:
            raise ValueError("provider questions are limited to 512 characters")
        issues.append(InterpretationIssue("question", question.strip()))
    unaccounted = [index for index, character in enumerate(source) if character.isalnum() and not covered[index]]
    if unaccounted:
        start, end = min(unaccounted), max(unaccounted) + 1
        issues.append(
            InterpretationIssue(
                "unsupported",
                "provider did not account for all meaningful source text",
                source[start:end],
                start,
                end,
            )
        )
    spec: EnclosureSpec | None = None
    try:
        spec = enclosure_spec_from_dict(payload["spec"])
    except ValueError as exc:
        issues.append(InterpretationIssue("invalid", str(exc)))
        spec = None
    if spec is not None and not confirmed:
        issues.append(
            InterpretationIssue(
                "question",
                "Review and explicitly confirm the provider-proposed specification before generating geometry.",
            )
        )
    if any(issue.kind in {"invalid", "unsupported"} for issue in issues):
        spec = None
    return IntentInterpretation(source, spec, tuple(mappings), tuple(issues), "schema-constrained-provider-v1")
