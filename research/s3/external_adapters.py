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
class DatasetArtifact:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class SourceSpec:
    key: str
    source_name: str
    repository: str
    revision: str
    license_spdx: str
    dataset_repository: str
    dataset_revision: str
    dataset_license_spdx: str
    dataset_artifacts: tuple[DatasetArtifact, ...]
    allowed_prompt_fields: tuple[str, ...]
    id_fields: tuple[str, ...]


SOURCES = {
    "cadtestbench": SourceSpec(
        key="cadtestbench",
        source_name="CADTestBench",
        repository="dimitrismallis/CADTestBench",
        revision="e29283cc61db7329039d95b429766a50bfd37f89",
        license_spdx="MIT",
        dataset_repository="dimitrismallis/CADTestBench",
        dataset_revision="2b9a4a972d142d2bc634d072e9d4485f171ced06",
        dataset_license_spdx="MIT",
        dataset_artifacts=(
            DatasetArtifact(
                path="samples/abstract.parquet",
                sha256="67a5779bc5114ce4db6bc9be89bf22c25e707bc83e7431214cddfac23f980536",
                size_bytes=17545,
            ),
            DatasetArtifact(
                path="samples/detailed.parquet",
                sha256="76b2d20def7946e1e3216b72a8acb83825c489c373b23ac514b77885ae275b37",
                size_bytes=33726,
            ),
        ),
        allowed_prompt_fields=("prompt", "abstract_prompt", "detailed_prompt"),
        id_fields=("sample_id", "id"),
    ),
    "cadgenbench": SourceSpec(
        key="cadgenbench",
        source_name="CADGenBench",
        repository="huggingface/cadgenbench",
        revision="33304cf771fc5639144b1df9611e347251052cf8",
        license_spdx="Apache-2.0",
        dataset_repository="HuggingAI4Engineering/cadgenbench-data",
        # This is the last data-bearing revision before two README/card-only commits.
        # It removes an unused category field from the public description.yaml inputs;
        # private ground truth is in a different repository and is intentionally absent.
        dataset_revision="569ea565cef25ee690e39bf89941f940027633d6",
        dataset_license_spdx="ODC-By-1.0",
        dataset_artifacts=(),
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


def _dataset_receipt(spec: SourceSpec) -> dict[str, Any]:
    return {
        "repository": spec.dataset_repository,
        "revision": spec.dataset_revision,
        "license": spec.dataset_license_spdx,
        "artifacts": [
            {"path": artifact.path, "sha256": artifact.sha256, "size_bytes": artifact.size_bytes}
            for artifact in spec.dataset_artifacts
        ],
    }


def adapt_rows(
    source_key: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    source_export_sha256: str | None = None,
) -> list[dict[str, Any]]:
    """Convert prompt-only source rows to frozen S3 external candidate records.

    This does not select a held-out set, score a system, infer taxonomy labels, or inspect
    any benchmark outcomes. Exact source-code and public-dataset revisions are hard-coded
    in SOURCES and covered by tests. When rows came from a file, callers should pass the
    exact file digest so every adapted record is also bound to the prompt-only export bytes.
    """

    try:
        spec = SOURCES[source_key]
    except KeyError as exc:
        raise ValueError(f"unsupported external source: {source_key}") from exc

    if source_export_sha256 is not None:
        if len(source_export_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_export_sha256):
            raise ValueError("source_export_sha256 must be a lowercase 64-character SHA-256 digest")

    dataset_receipt = _dataset_receipt(spec)
    dataset_receipt_sha256 = _canonical_sha256(dataset_receipt)
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
            "dataset": dataset_receipt,
            "dataset_receipt_sha256": dataset_receipt_sha256,
            "source_export_sha256": source_export_sha256,
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
                    f"public_dataset={spec.dataset_repository}@{spec.dataset_revision}; "
                    f"source_id={source_id}; prompt_field={prompt_field}; "
                    f"code_license={spec.license_spdx}; dataset_license={spec.dataset_license_spdx}; "
                    f"not derived from NeuroCAD/baseline outcomes"
                ),
                "status": STATUS,
                "source_name": spec.source_name,
                "source_repository": spec.repository,
                "source_revision": spec.revision,
                "source_license": spec.license_spdx,
                "source_dataset_repository": spec.dataset_repository,
                "source_dataset_revision": spec.dataset_revision,
                "source_dataset_license": spec.dataset_license_spdx,
                "source_dataset_receipt_sha256": dataset_receipt_sha256,
                "source_export_sha256": source_export_sha256,
                "source_record_id": source_id,
                "source_prompt_field": prompt_field,
                "source_row_sha256": row_sha256,
            }
        )

    return output


def _read_jsonl_bytes(path: Path) -> tuple[list[Mapping[str, Any]], str]:
    raw = path.read_bytes()
    export_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("prompt-only JSONL input must be UTF-8") from exc

    rows: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(row, Mapping):
            raise ValueError(f"line {line_number} must decode to an object")
        rows.append(row)
    return rows, export_sha256


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

    rows, source_export_sha256 = _read_jsonl_bytes(args.input)
    adapted = adapt_rows(args.source, rows, source_export_sha256=source_export_sha256)
    _write_jsonl(args.output, adapted)
    print(
        json.dumps(
            {
                "source": args.source,
                "records": len(adapted),
                "source_export_sha256": source_export_sha256,
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
