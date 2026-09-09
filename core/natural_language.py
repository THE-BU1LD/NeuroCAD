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
FACE = r"(?:front|rear|left|right|bottom|top)"
HARDWARE = r"M(?:2(?:\.5)?|3|4)"


@dataclass(frozen=True)
class InterpretationIssue:
    kind: str  # question | unsupported | invalid
    message: str
    text: str | None = None
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "text": self.text,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class IntentInterpretation:
    source: str
    spec: EnclosureSpec | None
    mappings: tuple[PhraseMapping, ...]
    issues: tuple[InterpretationIssue, ...]
    interpreter: str

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
        }


def _clauses(source: str) -> tuple[tuple[str, int, int], ...]:
    clauses: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^;]+", source):
        raw = match.group(0)
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        text = raw.strip()
        if text:
            clauses.append((text, match.start() + leading, match.start() + trailing))
    return tuple(clauses)


def _float(match: re.Match[str], name: str) -> float:
    return float(match.group(name))


def _bounded_int(match: re.Match[str], name: str, maximum: int) -> int:
    raw = match.group(name)
    if len(raw) > 4:
        raise ValueError(f"{name} exceeds the supported maximum of {maximum}")
    value = int(raw)
    if value > maximum:
        raise ValueError(f"{name} exceeds the supported maximum of {maximum}")
    return value


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
    seen_singletons: set[str] = set()

    patterns: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "outer_size_mm",
            re.compile(
                rf"(?:make|create|design)?\s*(?:an?\s+)?(?P<w>{NUMBER})\s*[x×]\s*(?P<d>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER})\s*mm\s+(?:electronics\s+)?(?:enclosure|case|housing)",
                re.IGNORECASE,
            ),
        ),
        ("wall_mm", re.compile(rf"(?:wall|walls|wall thickness)\s+(?P<value>{NUMBER})\s*mm", re.IGNORECASE)),
        ("floor_mm", re.compile(rf"(?:floor|floor thickness)\s+(?P<value>{NUMBER})\s*mm", re.IGNORECASE)),
        ("corner_radius_mm", re.compile(rf"corner radius\s+(?P<value>{NUMBER})\s*mm", re.IGNORECASE)),
        (
            "profile",
            re.compile(r"(?:manufacturing\s+)?profile\s+(?P<value>fdm[ _-](?:draft|standard|precision)|resin[ _-]standard)", re.IGNORECASE),
        ),
        ("lid.none", re.compile(r"(?:open top|no lid)", re.IGNORECASE)),
        (
            "lid",
            re.compile(
                rf"(?P<kind>screw|slide|friction)(?:[- ]fit)?\s+lid\s+(?P<thickness>{NUMBER})\s*mm\s+thick\s+clearance\s+(?P<clearance>{NUMBER})\s*mm"
                rf"(?:\s+lip\s+(?P<lip>{NUMBER})\s*mm)?(?:\s+(?P<hardware>{HARDWARE})\s+fasteners\s+at\s+corners\s+inset\s+(?P<inset>{NUMBER})\s*mm)?",
                re.IGNORECASE,
            ),
        ),
        (
            "cutout.rectangular",
            re.compile(
                rf"rectangular\s+cutout\s+(?P<w>{NUMBER})\s*[x×]\s*(?P<h>{NUMBER})\s*mm\s+on\s+(?P<face>{FACE})\s+at\s+(?P<u>{NUMBER}|-{NUMBER})\s*[x×,]\s*(?P<v>{NUMBER}|-{NUMBER})\s*mm(?:\s+for\s+(?P<purpose>[A-Za-z0-9_.+-]+))?",
                re.IGNORECASE,
            ),
        ),
        (
            "cutout.circular",
            re.compile(
                rf"circular\s+cutout\s+(?P<diameter>{NUMBER})\s*mm\s+diameter\s+on\s+(?P<face>{FACE})\s+at\s+(?P<u>{NUMBER}|-{NUMBER})\s*[x×,]\s*(?P<v>{NUMBER}|-{NUMBER})\s*mm(?:\s+for\s+(?P<purpose>[A-Za-z0-9_.+-]+))?",
                re.IGNORECASE,
            ),
        ),
        (
            "vent",
            re.compile(
                rf"vent grid\s+(?P<rows>[1-9]\d*)\s*[x×]\s*(?P<columns>[1-9]\d*)\s+holes\s+(?P<diameter>{NUMBER})\s*mm\s+diameter\s+pitch\s+(?P<pitch>{NUMBER})\s*mm\s+on\s+(?P<face>{FACE})\s+at\s+(?P<u>{NUMBER}|-{NUMBER})\s*[x×,]\s*(?P<v>{NUMBER}|-{NUMBER})\s*mm",
                re.IGNORECASE,
            ),
        ),
        (
            "standoffs",
            re.compile(
                rf"(?P<count>[1-9]\d*)\s+(?P<hardware>{HARDWARE})\s+standoffs\s+(?P<height>{NUMBER})\s*mm\s+high\s+at\s+corners\s+inset\s+(?P<inset>{NUMBER})\s*mm",
                re.IGNORECASE,
            ),
        ),
        (
            "pcb",
            re.compile(
                rf"pcb\s+(?P<w>{NUMBER})\s*[x×]\s*(?P<d>{NUMBER})\s*[x×]\s*(?P<t>{NUMBER})\s*mm(?:\s+component height\s+(?P<component>{NUMBER})\s*mm)?",
                re.IGNORECASE,
            ),
        ),
        ("title", re.compile(r"title\s+(?P<value>[A-Za-z0-9][A-Za-z0-9 _.-]{0,127})", re.IGNORECASE)),
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
                    values[kind] = (_float(match, "w"), _float(match, "d"), _float(match, "h"))
                elif kind in {"wall_mm", "floor_mm", "corner_radius_mm"}:
                    values[kind] = _float(match, "value")
                elif kind == "profile":
                    values[kind] = re.sub(r"[ -]", "_", match.group("value").lower())
                elif kind == "lid.none":
                    lid_values = {"kind": "none", "thickness_mm": 0.0, "clearance_mm": 0.0}
                elif kind == "lid":
                    lid_kind = match.group("kind").lower()
                    lid_values = {
                        "kind": lid_kind,
                        "thickness_mm": _float(match, "thickness"),
                        "clearance_mm": _float(match, "clearance"),
                        "lip_height_mm": float(match.group("lip") or 0.0),
                        "hardware": match.group("hardware").upper() if match.group("hardware") else None,
                        "inset_mm": float(match.group("inset")) if match.group("inset") else None,
                    }
                elif kind.startswith("cutout"):
                    cutout_index += 1
                    cutout_id = f"cutout_{cutout_index}"
                    face = match.group("face").lower()
                    center_uv = (_float(match, "u"), _float(match, "v"))
                    purpose = match.group("purpose") or "generic"
                    if kind.endswith("rectangular"):
                        values["cutouts"].append(
                            CutoutSpec(
                                id=cutout_id,
                                kind="rectangular",
                                face=face,
                                center_uv_mm=center_uv,
                                size_mm=(_float(match, "w"), _float(match, "h")),
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
                                diameter_mm=_float(match, "diameter"),
                                purpose=purpose,
                            )
                        )
                elif kind == "vent":
                    vent_index += 1
                    values["vents"].append(
                        VentPatternSpec(
                            id=f"vent_{vent_index}",
                            face=match.group("face").lower(),
                            center_uv_mm=(_float(match, "u"), _float(match, "v")),
                            rows=_bounded_int(match, "rows", 64),
                            columns=_bounded_int(match, "columns", 64),
                            diameter_mm=_float(match, "diameter"),
                            pitch_mm=_float(match, "pitch"),
                        )
                    )
                elif kind == "standoffs":
                    pending_standoffs.append(
                        {
                            "count": _bounded_int(match, "count", 256),
                            "hardware": match.group("hardware").upper(),
                            "height_mm": _float(match, "height"),
                            "inset_mm": _float(match, "inset"),
                        }
                    )
                elif kind == "pcb":
                    values["pcb"] = PCBSpec(
                        size_mm=(_float(match, "w"), _float(match, "d"), _float(match, "t")),
                        component_height_mm=float(match.group("component") or 0.0),
                    )
                elif kind == "title":
                    values["title"] = match.group("value").strip()
            except (OverflowError, ValueError) as exc:
                issues.append(InterpretationIssue("invalid", str(exc), clause, start, end))
            break
        if not matched:
            issues.append(InterpretationIssue("unsupported", "clause was not understood", clause, start, end))

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
    return IntentInterpretation(source, spec, tuple(mappings), tuple(issues), "deterministic-clause-v1")


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
