"""Context-bound enclosure edit proposals; no implicit application or geometry claims."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from typing import Any

from .conversation_quantities import MEASURE, UNIT, UNITS, adjusted_value, canonical_number, diameter_from_radius, millimeters
from .edit_language import EditInterpretationError, edit_project_from_text
from .project import EnclosureProject, enclosure_spec_to_dict, parse_project, semantic_diff, serialize_project

VERSION = "neurocad-conversational-edit-v1"
MAX_SOURCE = 8192
SCALARS = {
    "wall thickness": "wall_mm", "floor thickness": "floor_mm",
    "corner radius": "corner_radius_mm", "lid thickness": "lid.thickness_mm",
    "lid clearance": "lid.clearance_mm", "lid lip height": "lid.lip_height_mm",
}
_SCALAR_NOUN = r"floor|walls?(?: thickness)?|" + "|".join(re.escape(name) for name in SCALARS if name != "wall thickness")
_NOUN = rf"(?P<noun>{_SCALAR_NOUN})"
_SCALAR_SET = re.compile(rf"(?:(?P<set_verb>make|set|change|increase|decrease)\s+)?(?:the\s+)?{_NOUN}\s+(?:(?P<relation>to|at|be|like|should be)\s+)?{MEASURE}(?:\s+thick)?")
_SCALAR_DELTA = re.compile(rf"(?P<verb>add|subtract)\s+{MEASURE}\s+(?P<direction>to|from)\s+(?:the\s+)?{_NOUN}")
_SCALAR_BY = re.compile(rf"(?P<verb>increase|decrease)\s+(?:the\s+)?{_NOUN}\s+by\s+{MEASURE}")
_CORRECTION = re.compile(rf"{MEASURE}(?:\s+thick)?")
_RADIUS = re.compile(rf"(?:make|set|change)\s+(?:the\s+)?(?P<id>[a-z0-9_-]+)\s+(?:hole|cutout)\s+radius\s+(?:to\s+)?{MEASURE}")
_SPLITTER = re.compile(r"[;,\n]+|\b(?:and|but)\b|\b(?:no\s+)?actually\b", re.IGNORECASE)
_TYPOS = {"dont": "don't", "wals": "walls", "thikness": "thickness", "thicknes": "thickness",
          "milimeters": "millimeters", "millimetres": "millimeters"}
_TYPO_PATTERN = re.compile(r"\b(?:" + "|".join(_TYPOS) + r")\b")
_PREFIX = re.compile(r"^(?:(?:okay|ok|please|uh|um|just)\s+)+")
_SUFFIX = re.compile(r"\s+please$")
_PRESERVE_OUTSIDE = re.compile(r"(?:keep|preserve|don't (?:change|move|resize)) (?:the )?(?:outside|outer boundary|external boundary|outside dimensions)(?: (?:the )?(?:same|unchanged|fixed))?")
_PRESERVE_HOLES = re.compile(r"(?:keep|preserve|don't (?:change|move|remove|lose)) (?:the |that |all )?(?:holes?|cutouts?)(?: (?:the )?(?:same|unchanged|fixed))?")
_PRESERVE_SCALAR = re.compile(
    rf"(?:keep|preserve|(?:don't|do not) (?:change|modify|adjust)) (?:the )?(?P<noun>floor|{_SCALAR_NOUN})"
    r"(?: (?:the )?(?:same|unchanged|fixed))?"
)
_REJECTED_VALUE = re.compile(rf"not\s+{MEASURE}\s+{_NOUN}")
_ANAPHOR_SET = re.compile(rf"(?:make|set|change)\s+(?:it|them)\s+(?:(?:to|at|be)\s+)?{MEASURE}(?:\s+thick)?")
_ONLY = re.compile(r"only\s+")
_SIZE = re.compile(
    rf"(?:resize|make|set) (?:the |that )?(?:enclosure|box|case)(?: to)? "
    rf"(?P<w>\d+(?:\.\d+)?)\s*(?P<wu>{UNIT})?\s*[x×]\s*"
    rf"(?P<d>\d+(?:\.\d+)?)\s*(?P<du>{UNIT})?\s*[x×]\s*"
    rf"(?P<h>\d+(?:\.\d+)?)\s*(?P<hu>{UNIT})"
)


_REMAINDER = re.compile(r"(?:leave|keep|preserve) (?:all )?(?:the )?(?:other|remaining) (?:bits|fields|properties|dimensions)(?: (?:alone|unchanged|fixed))")
_EXTERNAL_SIZE = re.compile(r"(?:same external size|(?:keep|preserve) (?:the )?external size(?: (?:the )?same)?)")
_GOAL = re.compile(r"(?:i (?:need|want) it|make it) (?:sturdier|stronger|lightweight|lighter)")
_REFERENCE = re.compile(rf"(?:make|set|change) (?:that|it) (?:to )?{MEASURE}(?: instead)?")
_CONTEXT = re.compile(rf"(?:we are|we're|i am) (?:changing|editing|discussing) (?:the )?(?:enclosure )?{_NOUN}[.!]?")
_SEQUENCE = re.compile(_SCALAR_SET.pattern, re.IGNORECASE)


def _split_scalar_sequence(source: str, start: int, end: int) -> list[tuple[int, int]]:
    """Split only completely consumed adjacent scalar clauses; retain original offsets."""
    cursor = start
    spans = []
    while cursor < end:
        while cursor < end and source[cursor].isspace():
            cursor += 1
        if cursor == end:
            break
        match = _SEQUENCE.match(source, cursor, end)
        if match is None or (match.end() < end and not source[match.end()].isspace()):
            return [(start, end)]
        spans.append((cursor, match.end()))
        cursor = match.end()
    return spans if len(spans) > 1 else [(start, end)]


def bind_history(project: EnclosureProject, messages: list[str]) -> dict[str, Any]:
    """Caller asserts these past messages belong to this exact baseline revision."""
    if (not isinstance(messages, list) or len(messages) > 10
            or any(not isinstance(item, str) or not item.strip() or len(item) > 2048 for item in messages)):
        raise ValueError("History requires at most ten nonempty messages of at most 2048 characters")
    return {"version": "neurocad-local-history-v1", "baseline_sha256": context_hash(project), "messages": list(messages)}


def _history_target(history: dict[str, Any] | None, project: EnclosureProject) -> str | None:
    if history is None:
        return None
    if (not isinstance(history, dict) or set(history) != {"version", "baseline_sha256", "messages"}
            or history != bind_history(project, history["messages"])):
        raise ValueError("History must be explicitly bound to the current project revision")
    targets = set()
    for message in history["messages"]:
        match = _CONTEXT.fullmatch(message.strip().lower())
        if match is None:
            return None
        targets.add(_scalar_name(match.group("noun")))
    return next(iter(targets)) if len(targets) == 1 else None


@dataclass(frozen=True)
class _QuantityEdit:
    instruction: str
    label: str | None
    value_mm: float
    relative: bool = False
    direction: str | None = None


def _scalar_name(noun: str) -> str:
    if noun.startswith("wall"):
        return "wall thickness"
    return "floor thickness" if noun == "floor" else noun


def _scalar_value(project: EnclosureProject, label: str) -> float:
    current: Any = project.spec
    for key in SCALARS[label].split("."):
        current = getattr(current, key)
    return float(current)


def _check_direction(value: float, current: float, direction: str | None, label: str) -> None:
    # Check the stored representation, including corrections and sub-resolution deltas.
    if ((direction == "increase" and value <= current)
            or (direction == "decrease" and value >= current)):
        raise ValueError(f"The final value must {direction} the current {label}; clarify the target or direction")


def _other_fields(project: EnclosureProject, edited: str) -> list[str]:
    """ONLY a scalar protects every other specification field, including lid siblings."""
    baseline = enclosure_spec_to_dict(project.spec)
    root = edited.split(".")[0]
    fields = set(baseline) - {"version", "units", root}
    if "." in edited:
        fields.update(f"{root}.{name}" for name in baseline[root] if f"{root}.{name}" != edited)
    return sorted(fields)


def _quantity_instruction(text: str, project: EnclosureProject, previous: _QuantityEdit | None) -> _QuantityEdit | None:
    """Dispatch complete scalar clauses; all outputs still use the shared edit validator."""
    relative = False
    match = _SCALAR_SET.fullmatch(text)
    if match is None:
        match = _SCALAR_DELTA.fullmatch(text) or _SCALAR_BY.fullmatch(text)
        relative = match is not None
    if match:
        name = _scalar_name(match.group("noun"))
        value = millimeters(match.group("value"), match.group("unit"))
        verb = match.group("verb") if relative else match.group("set_verb")
        current = _scalar_value(project, name)
        if verb in {"increase", "decrease"} and not relative and match.group("relation") != "to":
            raise ValueError("Specify a final value with 'to', or an amount of change with 'by'")
        if relative:
            direction = match.groupdict().get("direction")
            if direction is not None and direction != {"add": "to", "subtract": "from"}[verb]:
                raise ValueError("Use 'add ... to' or 'subtract ... from' with an explicit scalar")
            value = adjusted_value(current, value, subtract=verb in {"subtract", "decrease"})
        canonical = canonical_number(value)
        direction = verb if verb in {"increase", "decrease"} else None
        _check_direction(float(value), current, direction, name)
        return _QuantityEdit(f"set {name} to {canonical} mm", name, float(value), relative, direction)
    if previous and previous.label and (match := _CORRECTION.fullmatch(text)):
        value = millimeters(match.group("value"), match.group("unit"))
        canonical = canonical_number(value)
        _check_direction(float(value), _scalar_value(project, previous.label), previous.direction, previous.label)
        return _QuantityEdit(f"set {previous.label} to {canonical} mm", previous.label, float(value), direction=previous.direction)
    if match := _RADIUS.fullmatch(text):
        identifier = match.group("id").casefold()
        holes = [hole for hole in project.spec.cutouts if hole.id.casefold() == identifier]
        if len(holes) != 1 or holes[0].kind != "circular":
            raise ValueError("Radius requires one uniquely named existing circular cutout")
        diameter = diameter_from_radius(millimeters(match.group("value"), match.group("unit")))
        canonical = canonical_number(diameter)
        return _QuantityEdit(f"set circular cutout {holes[0].id} diameter to {canonical} mm", None, float(diameter))
    return None


def context_hash(project: EnclosureProject) -> str:
    normalized = parse_project(serialize_project(project, pretty=False))
    return hashlib.sha256(serialize_project(normalized, pretty=False).encode()).hexdigest()


@dataclass(frozen=True)
class EditProposal:
    source: str
    baseline_sha256: str
    interpreter: str
    status: str
    actions: tuple[dict[str, Any], ...]
    preserve: tuple[dict[str, Any], ...]
    questions: tuple[str, ...]
    unsupported: tuple[dict[str, Any], ...]
    acknowledged: tuple[dict[str, Any], ...]
    candidate: EnclosureProject | None
    provider_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": VERSION, "source": self.source, "baseline_sha256": self.baseline_sha256,
            "interpreter": self.interpreter, "status": self.status,
            "requires_review": self.candidate is not None,
            "actions": list(self.actions), "preserve": list(self.preserve),
            "questions": list(self.questions), "unsupported": list(self.unsupported),
            "acknowledged": list(self.acknowledged),
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "provider_metadata": self.provider_metadata,
            "claim_boundary": "typed enclosure specification validation; not exact CAD or physical verification",
        }


def _evidence(source: str, start: int, end: int) -> dict[str, Any]:
    return {"text": source[start:end], "start": start, "end": end}


def _value_at(spec: dict[str, Any], field: str) -> Any:
    if field.startswith("cutout:"):
        identifier = field.removeprefix("cutout:")
        matches = [item for item in spec["cutouts"] if item["id"] == identifier]
        if len(matches) != 1:
            raise ValueError(f"Protected cutout {identifier!r} does not resolve uniquely")
        return matches[0]
    current: Any = spec
    for key in field.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"Unsupported protected field {field!r}")
        current = current[key]
    return current


def validate_edit_payload(source: str, project: EnclosureProject, payload: Any, *, interpreter: str = "provider") -> EditProposal:
    """Validate bounded, fully accounted-for proposals; model interpretations always need review."""
    if not isinstance(source, str) or not source.strip() or len(source) > MAX_SOURCE:
        raise ValueError(f"source must contain 1 through {MAX_SOURCE} characters")
    keys = {"actions", "preserve", "questions", "unsupported", "acknowledged"}
    if not isinstance(payload, dict) or set(payload) != keys:
        raise ValueError("proposal requires exactly actions, preserve, questions, unsupported, acknowledged")
    if any(not isinstance(payload[key], list) or len(payload[key]) > 32 for key in keys):
        raise ValueError("proposal collections must be arrays with at most 32 entries")
    covered = [False] * len(source)

    def evidence(raw: Any) -> None:
        if not isinstance(raw, dict) or set(raw) != {"text", "start", "end"}:
            raise ValueError("evidence requires text, start, end")
        start, end = raw["start"], raw["end"]
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source)
                or raw["text"] != source[start:end]):
            raise ValueError("evidence must match exact original source offsets")
        for i in range(start, end):
            covered[i] = True

    for action in payload["actions"]:
        if not isinstance(action, dict) or set(action) != {"instruction", "evidence"}:
            raise ValueError("action requires instruction and evidence")
        if not isinstance(action["instruction"], str) or not 1 <= len(action["instruction"]) <= 512:
            raise ValueError("canonical instruction must contain 1 through 512 characters")
        evidence(action["evidence"])
    baseline = enclosure_spec_to_dict(project.spec)
    allowed = set(baseline) - {"version", "units"} | {f"lid.{key}" for key in baseline["lid"]}
    allowed |= {f"cutout:{item['id']}" for item in baseline["cutouts"]}
    for protection in payload["preserve"]:
        if not isinstance(protection, dict) or set(protection) != {"field", "evidence"}:
            raise ValueError("protection requires field and evidence")
        if not isinstance(protection["field"], str) or protection["field"] not in allowed:
            raise ValueError("protection must refer to a supported field or existing cutout ID")
        evidence(protection["evidence"])
    for key in ("unsupported", "acknowledged"):
        for item in payload[key]:
            if not isinstance(item, dict) or set(item) != {"reason", "evidence"}:
                raise ValueError(f"{key} requires reason and evidence")
            if not isinstance(item["reason"], str) or not 1 <= len(item["reason"]) <= 512:
                raise ValueError("annotation reason must contain 1 through 512 characters")
            evidence(item["evidence"])
    questions = list(payload["questions"])
    if any(not isinstance(q, str) or not 1 <= len(q) <= 512 for q in questions):
        raise ValueError("questions must contain 1 through 512 characters")
    unsupported = list(payload["unsupported"])
    missing = [i for i, char in enumerate(source) if char.isalnum() and not covered[i]]
    if missing:
        unsupported.append({"reason": "Unaccounted-for source language",
                            "evidence": _evidence(source, min(missing), max(missing) + 1)})
    candidate = None
    status = "clarification" if questions else "unsupported" if unsupported else "unchanged"
    if not questions and not unsupported and payload["actions"]:
        trial = project
        touched: dict[str, Any] = {}
        try:
            for action in payload["actions"]:
                updated = edit_project_from_text(trial, action["instruction"], reason=action["evidence"]["text"][:512])
                for record in updated.changes[len(trial.changes):]:
                    if record.field not in {"cutouts", "vents", "standoffs"}:
                        if record.field in touched and touched[record.field] != record.after:
                            raise EditInterpretationError(f"Conflicting edits to {record.field}; clarify which value to use")
                        touched[record.field] = record.after
                for change in semantic_diff(trial, updated):
                    field = change["field"]
                    if field in touched and touched[field] != change["after"]:
                        raise EditInterpretationError(f"Conflicting edits to {field}; clarify which value to use")
                    touched[field] = change["after"]
                trial = updated
            after = enclosure_spec_to_dict(trial.spec)
            for protection in payload["preserve"]:
                field = protection["field"]
                if _value_at(baseline, field) != _value_at(after, field):
                    raise EditInterpretationError(f"Edit conflicts with preservation of {field}")
        except EditInterpretationError as exc:
            questions.append(str(exc))
            status = "clarification"
        except ValueError as exc:
            unsupported.append({"reason": str(exc), "evidence": payload["actions"][-1]["evidence"]})
            status = "rejected"
        else:
            candidate, status = trial, "proposal"
    return EditProposal(source, context_hash(project), interpreter, status,
                        tuple(payload["actions"]), tuple(payload["preserve"]), tuple(questions),
                        tuple(unsupported), tuple(payload["acknowledged"]), candidate)


def parse_conversation(source: str, project: EnclosureProject, *, history: dict[str, Any] | None = None) -> EditProposal:
    """Local conservative conversational edits, units, negation and explicit self-correction."""
    if not isinstance(source, str) or not source.strip() or len(source) > MAX_SOURCE:
        raise ValueError(f"source must contain 1 through {MAX_SOURCE} characters")
    payload: dict[str, Any] = {key: [] for key in ("actions", "preserve", "questions", "unsupported", "acknowledged")}
    history_target = _history_target(history, project)
    preserve_remainder = []
    goals = []
    cursor, correction = 0, False
    previous: _QuantityEdit | None = None
    pending_rejection: str | None = None
    forbidden_values: dict[str, set[float]] = {}
    seen_labels: set[str] = set()
    relative_labels: set[str] = set()
    parts = []
    for delimiter in _SPLITTER.finditer(source):
        parts.append((cursor, delimiter.start(), correction))
        payload["acknowledged"].append({"reason": "Clause separator or correction marker",
                                       "evidence": _evidence(source, delimiter.start(), delimiter.end())})
        correction = "actually" in delimiter.group().lower()
        cursor = delimiter.end()
    parts.append((cursor, len(source), correction))
    parts = [(a, b, correcting) for start, end, correcting in parts
             for a, b in _split_scalar_sequence(source, start, end)]
    for start, end, correcting in parts:
        if not source[start:end].strip():
            continue
        ev = _evidence(source, start, end)
        text = source[start:end].strip().lower().replace("’", "'")
        text = _TYPO_PATTERN.sub(lambda match: _TYPOS[match.group()], text)
        text = _PREFIX.sub("", text).rstrip(".!?")
        text = _SUFFIX.sub("", text)
        if pending_rejection is None and (reference := _REFERENCE.fullmatch(text)):
            if history_target is None:
                payload["questions"].append("Which scalar property does 'that' refer to? Supply one explicit target against this revision.")
                payload["acknowledged"].append({"reason": "Unresolved history reference", "evidence": ev})
                continue
            text = f"{history_target} {reference.group('value')} {reference.group('unit')}"
        if _REMAINDER.fullmatch(text):
            preserve_remainder.append(ev)
            continue
        if _EXTERNAL_SIZE.fullmatch(text):
            payload["preserve"].append({"field": "outer_size_mm", "evidence": ev})
            continue
        if _GOAL.fullmatch(text):
            goals.append(ev)
            payload["acknowledged"].append({"reason": "Design motivation only: no strength, mass or physical performance has been verified", "evidence": ev})
            continue
        if re.fullmatch(r"(?:do not|don't) change (?:any )?geometry or material", text):
            payload["questions"].append("Which design variable may change to meet the objective? Geometry and material are currently fixed.")
            payload["acknowledged"].append({"reason": "Fixed design variables require objective clarification", "evidence": ev})
            continue
        if re.search(r"\bholes?\b", text) and re.search(r"\b(?:some|equally spaced)\b", text):
            payload["questions"].append("Specify the hole count, diameter, face, spacing and first center position.")
            payload["acknowledged"].append({"reason": "Incomplete hole layout", "evidence": ev})
            continue
        only_match = _ONLY.match(text)
        only = only_match is not None
        if only_match:
            text = text[only_match.end():]
        quantity = None
        if pending_rejection is not None:
            try:
                if reference := _ANAPHOR_SET.fullmatch(text):
                    text = f"{pending_rejection} {reference.group('value')} {reference.group('unit')}"
                quantity = _quantity_instruction(text, project, None)
                if quantity is None or quantity.label != pending_rejection or quantity.relative:
                    raise ValueError("A rejected scalar value needs an immediately adjacent explicit replacement for the same target")
            except ValueError as exc:
                payload["questions"].append(str(exc))
                payload["acknowledged"].append({"reason": "Unresolved rejected-value replacement", "evidence": ev})
                pending_rejection = None
                continue
            pending_rejection = None
        elif not only and (rejection := _REJECTED_VALUE.fullmatch(text)):
            try:
                value = millimeters(rejection.group("value"), rejection.group("unit"))
                canonical_number(value)
                label = _scalar_name(rejection.group("noun"))
                forbidden_values.setdefault(label, set()).add(float(value))
                pending_rejection = label
                previous = None
                payload["acknowledged"].append({"reason": "Rejected scalar value; an adjacent replacement is required", "evidence": ev})
            except ValueError as exc:
                payload["questions"].append(str(exc))
                payload["acknowledged"].append({"reason": "Invalid rejected quantity", "evidence": ev})
            continue
        if not only and (protection := _PRESERVE_SCALAR.fullmatch(text)):
            field = SCALARS[_scalar_name(protection.group("noun"))]
            payload["preserve"].append({"field": field, "evidence": ev})
            continue
        if not only and _PRESERVE_OUTSIDE.fullmatch(text):
            fields = ("outer_size_mm",) if "dimensions" in text else ("outer_size_mm", "corner_radius_mm", "cutouts", "vents", "lid")
            payload["preserve"].extend({"field": field, "evidence": ev} for field in fields)
            continue
        if not only and _PRESERVE_HOLES.fullmatch(text):
            singular = bool(re.search(r"\b(?:hole|cutout)\b", text)) and "all " not in text
            if singular and len(project.spec.cutouts) != 1:
                payload["questions"].append("Which existing cutout do you mean? Use its feature ID.")
                payload["acknowledged"].append({"reason": "Unresolved cutout reference", "evidence": ev})
            else:
                payload["preserve"].append({"field": "cutouts", "evidence": ev})
            continue
        instruction: str | None = None
        edit_label: str | None = None
        size_match = None if only else _SIZE.fullmatch(text)
        if size_match:
            sizes = [float(size_match.group(axis)) * UNITS[size_match.group(axis + "u") or size_match.group("hu")]
                     for axis in ("w", "d", "h")]
            instruction = f"resize enclosure to {sizes[0]!r} x {sizes[1]!r} x {sizes[2]!r} mm"
        if instruction is None:
            try:
                quantity = quantity or _quantity_instruction(text, project, previous if correcting else None)
                if quantity:
                    instruction, edit_label, relative = quantity.instruction, quantity.label, quantity.relative
                    if only and edit_label is None:
                        raise ValueError("ONLY currently requires one named scalar property")
                    if edit_label:
                        if quantity.value_mm in forbidden_values.get(edit_label, set()):
                            raise ValueError(f"The replacement restores a rejected value for {edit_label}; clarify the final value")
                        if edit_label in relative_labels or (relative and edit_label in seen_labels):
                            raise ValueError("Repeated edits involving a relative quantity need one explicit final value")
                        seen_labels.add(edit_label)
                        if relative:
                            relative_labels.add(edit_label)
                        if only:
                            protected = {item["field"] for item in payload["preserve"]}
                            payload["preserve"].extend({"field": field, "evidence": ev}
                                                       for field in _other_fields(project, SCALARS[edit_label]) if field not in protected)
            except ValueError as exc:
                payload["questions"].append(str(exc))
                payload["acknowledged"].append({"reason": "Unresolved quantity edit", "evidence": ev})
                continue
        if instruction:
            if correcting and previous and edit_label == previous.label and payload["actions"]:
                superseded = payload["actions"].pop()
                payload["acknowledged"].append({"reason": "Superseded by explicit self-correction", "evidence": superseded["evidence"]})
            payload["actions"].append({"instruction": instruction, "evidence": ev})
            previous = quantity
            continue
        try:
            edit_project_from_text(project, source[start:end].strip())
        except (ValueError, TypeError):
            if re.search(r"\b(?:thicker|thinner|bigger|smaller|walls?|thickness)\b", text):
                payload["questions"].append("Which thickness or dimension should change, and what exact value and unit should it have?")
                payload["acknowledged"].append({"reason": "Ambiguous or unsupported edit syntax", "evidence": ev})
            else:
                payload["unsupported"].append({"reason": "Outside local edit grammar; use a configured language provider or an explicit canonical instruction", "evidence": ev})
        else:
            payload["actions"].append({"instruction": source[start:end].strip(), "evidence": ev})
            previous = None
    if goals and not payload["actions"]:
        payload["questions"].append("Specify the dimensional edit and measurable objective; physical improvement cannot be inferred.")
    for ev in preserve_remainder:
        if not seen_labels or any(not action["instruction"].startswith("set ") for action in payload["actions"]):
            payload["questions"].append("Name the scalar fields to edit before preserving all other properties.")
            payload["acknowledged"].append({"reason": "Unresolved preservation scope", "evidence": ev})
        else:
            edited = {SCALARS[label] for label in seen_labels}
            remaining_fields = set.intersection(*(set(_other_fields(project, field)) for field in edited))
            payload["preserve"].extend({"field": field, "evidence": ev} for field in sorted(remaining_fields))
    if pending_rejection:
        payload["questions"].append(f"What exact value and unit should replace the rejected {pending_rejection}?")
    result = validate_edit_payload(source, project, payload, interpreter="local-conversation-v4")
    if result.candidate:
        for label, excluded in forbidden_values.items():
            if _scalar_value(result.candidate, label) in excluded:
                payload["questions"].append(f"The final {label} restores an explicitly rejected value")
        if payload["questions"]:
            return validate_edit_payload(source, project, payload, interpreter="local-conversation-v4")
    if history is not None:
        result = replace(result, provider_metadata={"local_history": history, "live_semantic_accuracy_claim": False})
    return result


def apply_proposal(proposal: EditProposal, project: EnclosureProject, *, confirmed: bool = False) -> EnclosureProject:
    """Apply only after explicit review and only against the exact original context."""
    if confirmed is not True:
        raise ValueError("Explicit proposal review and confirmation is required")
    if proposal.baseline_sha256 != context_hash(project):
        raise ValueError("Project changed since interpretation; parse again against the current revision")
    if proposal.status != "proposal" or proposal.candidate is None:
        raise ValueError("Unresolved interpretation cannot be applied")
    payload = {key: list(getattr(proposal, key)) for key in ("actions", "preserve", "questions", "unsupported", "acknowledged")}
    checked = validate_edit_payload(proposal.source, project, payload, interpreter=proposal.interpreter)
    if checked.candidate is None or serialize_project(checked.candidate) != serialize_project(proposal.candidate):
        raise ValueError("Proposal candidate does not match its validated actions")
    return checked.candidate


def review_saved_proposal(raw: Any, project: EnclosureProject) -> EditProposal:
    """Revalidate saved evidence and candidate; the document cannot grant itself consent."""
    if not isinstance(raw, dict) or raw.get("version") != VERSION or raw.get("baseline_sha256") != context_hash(project):
        raise ValueError("Proposal version or baseline hash does not match the current project")
    if raw.get("status") != "proposal" or raw.get("requires_review") is not True:
        raise ValueError("Saved proposal is unresolved or does not declare review")
    if not isinstance(raw.get("interpreter"), str) or len(raw["interpreter"]) > 512:
        raise ValueError("Saved proposal interpreter metadata is invalid")
    keys = ("actions", "preserve", "questions", "unsupported", "acknowledged")
    if any(key not in raw for key in (*keys, "source", "candidate")):
        raise ValueError("Saved proposal is missing required fields")
    checked = validate_edit_payload(raw["source"], project, {key: raw[key] for key in keys}, interpreter=raw["interpreter"])
    if checked.candidate is None or checked.candidate.to_dict() != raw["candidate"]:
        raise ValueError("Saved candidate differs from its validated actions")
    return checked
