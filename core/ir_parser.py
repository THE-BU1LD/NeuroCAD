from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .ir import CADProgram, Constraint, Node, Primitive, Transform, validate_program
from .json_io import strict_json_loads


class IRParseError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("invalid NeuroCAD IR:\n- " + "\n- ".join(errors))


def _schema() -> dict[str, Any]:
    resource = Path(__file__).resolve().parent / "schemas" / "neurocad_ir_v1.schema.json"
    return json.loads(resource.read_text(encoding="utf-8"))


SCHEMA = _schema()
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA)


def _format_schema_error(error: Any) -> str:
    path = "$" + "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)
    return f"{path}: {error.message}"


def _vector3(value: list[Any]) -> tuple[float, float, float]:
    return float(value[0]), float(value[1]), float(value[2])


def program_from_dict(value: dict[str, Any]) -> CADProgram:
    schema_errors = sorted(
        SCHEMA_VALIDATOR.iter_errors(value),
        key=lambda error: (tuple(str(item) for item in error.absolute_path), error.message),
    )
    if schema_errors:
        raise IRParseError([_format_schema_error(error) for error in schema_errors])
    nodes: list[Node] = []
    for raw in value["nodes"]:
        transform_raw = raw["transform"]
        transform = Transform(
            translate=_vector3(transform_raw["translate"]),
            rotate=_vector3(transform_raw["rotate"]),
            scale=_vector3(transform_raw["scale"]),
        )
        primitive = None
        if "primitive" in raw:
            primitive = Primitive(raw["primitive"]["kind"], dict(raw["primitive"]["parameters"]))
        nodes.append(
            Node(
                id=raw["id"],
                primitive=primitive,
                composition=raw.get("composition"),
                children=tuple(raw.get("children", [])),
                transform=transform,
                role=raw["role"],
            )
        )
    constraints = tuple(
        Constraint(
            kind=raw["kind"],
            target=raw.get("target"),
            reference=raw.get("reference"),
            parameters=dict(raw["parameters"]),
            tolerance=float(raw["tolerance"]),
        )
        for raw in value["constraints"]
    )
    program = CADProgram(
        title=value["title"],
        nodes=tuple(nodes),
        roots=tuple(value["roots"]),
        constraints=constraints,
        metadata=dict(value["metadata"]),
        version=value["version"],
        units=value["units"],
    )
    report = validate_program(program)
    if not report.valid:
        raise IRParseError([f"{issue.path}: {issue.code}: {issue.message}" for issue in report.errors])
    return program


def parse_ir_json(text: str) -> CADProgram:
    try:
        value = strict_json_loads(text)
    except json.JSONDecodeError as exc:
        raise IRParseError([f"line {exc.lineno}, column {exc.colno}: {exc.msg}"]) from exc
    if not isinstance(value, dict):
        raise IRParseError(["$: root must be a JSON object"])
    return program_from_dict(value)


def serialize_ir_json(program: CADProgram, *, pretty: bool = True) -> str:
    report = validate_program(program)
    if not report.valid:
        raise IRParseError([f"{issue.path}: {issue.code}: {issue.message}" for issue in report.errors])
    if pretty:
        return json.dumps(program.to_dict(), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
