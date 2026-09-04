"""Fail-closed, pre-outcome adapters for external NeuroCAD S3 benchmark candidates.

The adapters intentionally ingest prompt metadata only. They reject rows carrying outcome,
score, generated-output, or ground-truth fields so benchmark import cannot accidentally
turn into evaluation access. Imported records remain CANDIDATE_NOT_EVALUATED and are
not assigned to the internal S3 taxonomy automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


STATUS = "CANDIDATE_NOT_EVALUATED"
CATEGORY = "external_unmapped"

# Conservative on purpose. A source export containing any of these fields must be
# stripped upstream into a prompt-only export before this adapter will accept it.
FORBIDDEN_OUTCOME_FIELDS = frozenset(
    {
        "answer",
        "baseline",
        "baseline_output",
        "cadtest_results",
        "candidate",
        "evaluation",
        "ground_truth",
        "label",
        "metric",
        "metrics",
        "model_output",
        "output",
        "prediction",
        "result",
        "results",
        "score",
        "scores",
        "success",
    }
)


@dataclass(frozen=True)
class SourceSpec:
    key: str
    source_name: str
    repository: str
    revision: str
    license_spdx: str
    allowed_prompt_fields: tuple[str, ...]
    id_fields: tuple[str, ...]


SOURCES = {
    "cadtestbench": SourceSpec(
        key="cadtestbench",
        source_name="CADTestBench",
        repository="dimitrismallis/CADTestBench",
        revision="e29283cc61db7329039d95b429766a50bfd37f89",
        license_spdx="MIT",
        allowed_prompt_fields=("prompt", "abstract_prompt", "detailed_prompt"),
        id_fields=("sample_id", "id"),
    ),
    "cadgenbench": SourceSpec(
        key="cadgenbench",
        source_name="CADGenBench",
        repository="huggingface/cadgenbench",
        revision="33304cf771fc5639144b1df9611e347251052cf8",
        license_spdx="Apache-2.0",
        allowed_prompt_fields=("prompt", "description", "instruction", "edit_request"),
        id_fields=("sample_id", "id", "name"),
    ),
}


def _normalize_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    if "\x00" in normalized:
        raise ValueError(f"{field} must not contain NUL bytes")
    return normalized


def _find_first(row: Mapping[str, Any], fields: Sequence[str], kind: str) -> tuple[str, str]:
    present = [(field, row[field]) for field in fields if field in row and row[field] not in (None, "")]
    if len(present) != 1:
        names = ", ".join(fields)
        raise ValueError(f"row must contain exactly one {kind} field from: {names}")
    field, value = present[0]
    return field, _normalize_text(value, field)


def _reject_outcome_fields(row: Mapping[str, Any]) -> None:
    collisions = sorted(FORBIDDEN_OUTCOME_FIELDS.intersection(row))
    if collisions:
        raise ValueError(
            "prompt-only import rejected outcome-bearing field(s): " + ", ".join(collisions)
        )


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def adapt_rows(source_key: str, rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert prompt-only source rows to frozen S3 external candidate records.

    This does not select a held-out set, score a system, infer taxonomy labels, or inspect
    any benchmark outcomes. Exact source repository revisions and licenses are hard-coded
    in SOURCES and covered by tests.
    """

    try:
        spec = SOURCES[source_key]
    except KeyError as exc:
        raise ValueError(f"unsupported external source: {source_key}") from exc

    output: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()

    for index, raw_row in enumerate(rows, start=1):
        if not isinstance(raw_row, Mapping):
            raise ValueError(f"row {index} must be an object")
        row = dict(raw_row)
        _reject_outcome_fields(row)
        id_field, source_id = _find_first(row, spec.id_fields, "source id")
        prompt_field, prompt = _find_first(row, spec.allowed_prompt_fields, "prompt")

        if source_id in seen_source_ids:
            raise ValueError(f"duplicate source id: {source_id}")
        seen_source_ids.add(source_id)

        source_identity = {
            "source": spec.source_name,
            "repository": spec.repository,
            "revision": spec.revision,
            "license": spec.license_spdx,
            "source_id_field": id_field,
            "source_id": source_id,
            "prompt_field": prompt_field,
            "prompt": prompt,
        }
        row_sha256 = _canonical_sha256(source_identity)
        output.append(
            {
                "candidate_id": f"EXT-{spec.key.upper()}-{source_id}",
                "category": CATEGORY,
                "prompt": prompt,
                "provenance": (
                    f"external candidate from {spec.repository}@{spec.revision}; "
                    f"source_id={source_id}; prompt_field={prompt_field}; "
                    f"license={spec.license_spdx}; not derived from NeuroCAD/baseline outcomes"
                ),
                "status": STATUS,
                "source_name": spec.source_name,
                "source_repository": spec.repository,
                "source_revision": spec.revision,
                "source_license": spec.license_spdx,
                "source_record_id": source_id,
                "source_prompt_field": prompt_field,
                "source_row_sha256": row_sha256,
            }
        )

    return output


def _read_jsonl(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(row, Mapping):
            raise ValueError(f"line {line_number} must decode to an object")
        rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adapt prompt-only external CAD benchmark exports for S3")
    parser.add_argument("--source", required=True, choices=sorted(SOURCES))
    parser.add_argument("--input", required=True, type=Path, help="prompt-only JSONL export")
    parser.add_argument("--output", required=True, type=Path, help="new JSONL path; must not exist")
    args = parser.parse_args(argv)

    adapted = adapt_rows(args.source, _read_jsonl(args.input))
    _write_jsonl(args.output, adapted)
    print(json.dumps({"source": args.source, "records": len(adapted), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
