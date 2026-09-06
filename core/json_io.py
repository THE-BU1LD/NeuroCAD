"""Strict, resource-bounded JSON decoding for untrusted NeuroCAD inputs."""

from __future__ import annotations

import json
import math
from typing import Any

MAX_JSON_NESTING = 256


def _reject_excessive_nesting(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for offset, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_NESTING:
                raise json.JSONDecodeError(
                    f"JSON nesting exceeds the supported depth of {MAX_JSON_NESTING}",
                    text,
                    offset,
                )
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(text: str) -> Any:
    """Decode standard finite JSON while rejecting duplicate object keys."""

    _reject_excessive_nesting(text)

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise json.JSONDecodeError(f"duplicate object key {key!r}", text, 0)
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise json.JSONDecodeError(f"non-standard numeric constant {value}", text, 0)

    def finite_float(value: str) -> float:
        converted = float(value)
        if not math.isfinite(converted):
            raise json.JSONDecodeError("numeric value is outside the finite range", text, 0)
        return converted

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except RecursionError as exc:
        raise json.JSONDecodeError("JSON nesting exceeds the parser recursion limit", text, 0) from exc
    except ValueError as exc:
        if isinstance(exc, json.JSONDecodeError):
            raise
        raise json.JSONDecodeError(str(exc), text, 0) from exc
