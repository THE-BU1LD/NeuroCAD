"""Context-bound enclosure edit proposals; no implicit application or geometry claims."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from .edit_language import EditInterpretationError, edit_project_from_text
from .project import EnclosureProject, enclosure_spec_to_dict, parse_project, semantic_diff, serialize_project

VERSION = "neurocad-conversational-edit-v1"
MAX_SOURCE = 8192
SCALARS = {
    "wall thickness": "wall_mm", "floor thickness": "floor_mm",
    "corner radius": "corner_radius_mm", "lid thickness": "lid.thickness_mm",
    "lid clearance": "lid.clearance_mm", "lid lip height": "lid.lip_height_mm",
}
UNITS = {"mm": 1.0, "millimeter": 1.0, "millimeters": 1.0, "millimetre": 1.0,
         "millimetres": 1.0, "cm": 10.0, "centimeter": 10.0, "centimeters": 10.0,
         "centimetre": 10.0, "centimetres": 10.0, "in": 25.4, "inch": 25.4, "inches": 25.4}
UNIT = "|".join(sorted(UNITS, key=len, reverse=True))
MEASURE = rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{UNIT})"


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


def parse_conversation(source: str, project: EnclosureProject) -> EditProposal:
    """Local conservative conversational edits, units, negation and explicit self-correction."""
    if not isinstance(source, str) or not source.strip() or len(source) > MAX_SOURCE:
        raise ValueError(f"source must contain 1 through {MAX_SOURCE} characters")
    payload: dict[str, Any] = {key: [] for key in ("actions", "preserve", "questions", "unsupported", "acknowledged")}
    splitter = re.compile(r"[;,\n]+|\b(?:and|but)\b|\b(?:no\s+)?actually\b", re.IGNORECASE)
    cursor, correction, previous_label = 0, False, None
    parts = []
    for delimiter in splitter.finditer(source):
        parts.append((cursor, delimiter.start(), correction))
        payload["acknowledged"].append({"reason": "Clause separator or correction marker",
                                       "evidence": _evidence(source, delimiter.start(), delimiter.end())})
        correction = "actually" in delimiter.group().lower()
        cursor = delimiter.end()
    parts.append((cursor, len(source), correction))
    for start, end, correcting in parts:
        if not source[start:end].strip():
            continue
        ev = _evidence(source, start, end)
        text = source[start:end].strip().lower().replace("’", "'")
        for wrong, right in {"dont": "don't", "wals": "walls", "thikness": "thickness", "thicknes": "thickness",
                             "milimeters": "millimeters", "millimetres": "millimeters"}.items():
            text = re.sub(rf"\b{wrong}\b", right, text)
        text = re.sub(r"^(?:(?:okay|ok|please|uh|um|just)\s+)+", "", text).rstrip(".!?")
        text = re.sub(r"\s+please$", "", text)
        if re.fullmatch(r"(?:keep|preserve|don't (?:change|move|resize)) (?:the )?(?:outside|outer boundary|external boundary|outside dimensions)(?: (?:the )?(?:same|unchanged|fixed))?", text):
            fields = ("outer_size_mm",) if "dimensions" in text else ("outer_size_mm", "corner_radius_mm", "cutouts", "vents", "lid")
            payload["preserve"].extend({"field": field, "evidence": ev} for field in fields)
            continue
        if re.fullmatch(r"(?:keep|preserve|don't (?:change|move|remove|lose)) (?:the |that |all )?(?:holes?|cutouts?)(?: (?:the )?(?:same|unchanged|fixed))?", text):
            singular = bool(re.search(r"\b(?:hole|cutout)\b", text)) and "all " not in text
            if singular and len(project.spec.cutouts) != 1:
                payload["questions"].append("Which existing cutout do you mean? Use its feature ID.")
                payload["acknowledged"].append({"reason": "Unresolved cutout reference", "evidence": ev})
            else:
                payload["preserve"].append({"field": "cutouts", "evidence": ev})
            continue
        instruction, label = None, None
        size_match = re.fullmatch(
            rf"(?:resize|make|set) (?:the |that )?(?:enclosure|box|case)(?: to)? "
            rf"(?P<w>\d+(?:\.\d+)?)\s*(?P<wu>{UNIT})?\s*[x×]\s*"
            rf"(?P<d>\d+(?:\.\d+)?)\s*(?P<du>{UNIT})?\s*[x×]\s*"
            rf"(?P<h>\d+(?:\.\d+)?)\s*(?P<hu>{UNIT})", text,
        )
        if size_match:
            sizes = [float(size_match.group(axis)) * UNITS[size_match.group(axis + "u") or size_match.group("hu")]
                     for axis in ("w", "d", "h")]
            instruction = f"resize enclosure to {sizes[0]!r} x {sizes[1]!r} x {sizes[2]!r} mm"
        for name in SCALARS:
            noun = "(?:walls?(?: thickness)?)" if name == "wall thickness" else re.escape(name)
            pattern = rf"(?:(?:make|set|change|increase|decrease)\s+)?(?:the\s+)?{noun}\s+(?:(?:to|at|be|like)\s+)?{MEASURE}(?:\s+thick)?"
            match = re.fullmatch(pattern, text)
            if match:
                value = float(match.group("value")) * UNITS[match.group("unit")]
                instruction, label = f"set {name} to {value!r} mm", name
                break
        if instruction is None and correcting and previous_label and (match := re.fullmatch(rf"{MEASURE}(?:\s+thick)?", text)):
            value = float(match.group("value")) * UNITS[match.group("unit")]
            instruction, label = f"set {previous_label} to {value!r} mm", previous_label
        if instruction:
            if correcting and label == previous_label and payload["actions"]:
                superseded = payload["actions"].pop()
                payload["acknowledged"].append({"reason": "Superseded by explicit self-correction", "evidence": superseded["evidence"]})
            payload["actions"].append({"instruction": instruction, "evidence": ev})
            previous_label = label
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
            previous_label = None
    return validate_edit_payload(source, project, payload, interpreter="local-conversation-v1")


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
