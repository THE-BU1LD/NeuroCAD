"""Fail-closed pre-outcome selection freezer for the NeuroCAD S3 benchmark.

This module turns the existing synthetic candidate CSV plus prompt-only external adapter
outputs into a checksummed, pre-outcome final-selection artifact. It never evaluates a
model and deliberately cannot authorize execution. Human/non-model taxonomy and semantic
deduplication decisions are supplied through an explicit ledger and are mechanically
validated before the freeze is written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CANDIDATE_STATUS = "CANDIDATE_NOT_EVALUATED"
FREEZE_STATUS = "FROZEN_NOT_AUTHORIZED"
SCHEMA_VERSION = "neurocad.s3.selection-freeze.v1"

TAXONOMY = (
    "primitive_solids",
    "dimensional_edits",
    "bores_cutouts",
    "patterns",
    "fillets_chamfers",
    "assemblies_compositions",
    "ambiguous_constraints",
    "invalid_underspecified",
    "multi_step_edits",
    "constraint_interactions",
    "reference_frame_language",
)

GEOMETRY_STRATUM = "geometry"
RESPONSE_POLICY_STRATUM = "response_policy"

ALLOWED_DECISIONS = frozenset({"INCLUDE", "EXCLUDE"})
ALLOWED_EXCLUSION_REASONS = frozenset(
    {
        "DUPLICATE",
        "AMBIGUITY_POLICY",
        "UNIMPLEMENTABLE_REFERENCE",
        "OUT_OF_SCOPE",
        "LICENSE_OR_PROVENANCE_BLOCK",
        "MALFORMED_PROMPT",
    }
)

# Any appearance of these keys in an external candidate is treated as accidental outcome
# access. The adapter already rejects them; the freezer independently re-checks the boundary.
FORBIDDEN_OUTCOME_FIELDS = frozenset(
    {
        "answer",
        "baseline",
        "baseline_output",
        "cadtest_results",
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
class Candidate:
    candidate_id: str
    category: str
    prompt: str
    provenance: str
    source_kind: str
    source_receipt_sha256: str


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(raw)


def _normalize_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    if "\x00" in normalized:
        raise ValueError(f"{field} must not contain NUL bytes")
    return normalized


def _reject_outcome_fields(record: Mapping[str, Any], context: str) -> None:
    collisions = sorted(FORBIDDEN_OUTCOME_FIELDS.intersection(record))
    if collisions:
        raise ValueError(f"{context} contains outcome-bearing field(s): {', '.join(collisions)}")


def _candidate_receipt_payload(candidate: Candidate) -> dict[str, str]:
    return {
        "candidate_id": candidate.candidate_id,
        "category": candidate.category,
        "prompt": candidate.prompt,
        "provenance": candidate.provenance,
        "source_kind": candidate.source_kind,
        "source_receipt_sha256": candidate.source_receipt_sha256,
    }


def parse_internal_csv_bytes(raw: bytes) -> list[Candidate]:
    """Parse the exact synthetic candidate CSV bytes and bind every row to that file digest."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("internal candidate CSV must be UTF-8") from exc

    file_sha256 = _sha256_bytes(raw)
    reader = csv.DictReader(text.splitlines())
    required = ["candidate_id", "category", "prompt", "provenance", "status"]
    if reader.fieldnames != required:
        raise ValueError(f"internal CSV columns must be exactly: {', '.join(required)}")

    candidates: list[Candidate] = []
    for line_number, row in enumerate(reader, start=2):
        candidate_id = _normalize_text(row["candidate_id"], f"line {line_number} candidate_id")
        category = _normalize_text(row["category"], f"line {line_number} category")
        prompt = _normalize_text(row["prompt"], f"line {line_number} prompt")
        provenance = _normalize_text(row["provenance"], f"line {line_number} provenance")
        status = _normalize_text(row["status"], f"line {line_number} status")
        if category not in TAXONOMY:
            raise ValueError(f"line {line_number} has unknown taxonomy category: {category}")
        if status != CANDIDATE_STATUS:
            raise ValueError(f"line {line_number} must remain {CANDIDATE_STATUS}")
        candidates.append(
            Candidate(
                candidate_id=candidate_id,
                category=category,
                prompt=prompt,
                provenance=provenance,
                source_kind="internal_synthetic",
                source_receipt_sha256=file_sha256,
            )
        )
    return candidates


def parse_external_jsonl_bytes(raw: bytes) -> list[Candidate]:
    """Parse exact adapter-output bytes without assigning taxonomy labels automatically."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("external adapter JSONL must be UTF-8") from exc

    file_sha256 = _sha256_bytes(raw)
    candidates: list[Candidate] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid external JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(row, Mapping):
            raise ValueError(f"external JSONL line {line_number} must be an object")
        _reject_outcome_fields(row, f"external JSONL line {line_number}")
        candidate_id = _normalize_text(row.get("candidate_id"), f"line {line_number} candidate_id")
        category = _normalize_text(row.get("category"), f"line {line_number} category")
        prompt = _normalize_text(row.get("prompt"), f"line {line_number} prompt")
        provenance = _normalize_text(row.get("provenance"), f"line {line_number} provenance")
        status = _normalize_text(row.get("status"), f"line {line_number} status")
        if category != "external_unmapped":
            raise ValueError(f"external JSONL line {line_number} must remain external_unmapped before ledger mapping")
        if status != CANDIDATE_STATUS:
            raise ValueError(f"external JSONL line {line_number} must remain {CANDIDATE_STATUS}")
        source_row_sha256 = _normalize_text(
            row.get("source_row_sha256"), f"line {line_number} source_row_sha256"
        )
        if len(source_row_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in source_row_sha256):
            raise ValueError(f"external JSONL line {line_number} has invalid source_row_sha256")
        candidates.append(
            Candidate(
                candidate_id=candidate_id,
                category="external_unmapped",
                prompt=prompt,
                provenance=provenance,
                source_kind="external_prompt_only",
                source_receipt_sha256=_canonical_sha256(
                    {
                        "adapter_output_sha256": file_sha256,
                        "source_row_sha256": source_row_sha256,
                    }
                ),
            )
        )
    return candidates


def parse_ledger_csv_bytes(raw: bytes) -> list[dict[str, str]]:
    """Parse the human/non-model mapping, deduplication, and inclusion ledger."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("selection ledger CSV must be UTF-8") from exc

    reader = csv.DictReader(text.splitlines())
    required = ["candidate_id", "category", "decision", "reason", "semantic_dedup_reviewed"]
    if reader.fieldnames != required:
        raise ValueError(f"selection ledger columns must be exactly: {', '.join(required)}")

    rows: list[dict[str, str]] = []
    for line_number, row in enumerate(reader, start=2):
        candidate_id = _normalize_text(row["candidate_id"], f"ledger line {line_number} candidate_id")
        category = _normalize_text(row["category"], f"ledger line {line_number} category")
        decision = _normalize_text(row["decision"], f"ledger line {line_number} decision")
        reason = (row["reason"] or "").strip()
        semantic_dedup_reviewed = _normalize_text(
            row["semantic_dedup_reviewed"], f"ledger line {line_number} semantic_dedup_reviewed"
        ).lower()

        if category not in TAXONOMY:
            raise ValueError(f"ledger line {line_number} has unknown category: {category}")
        if decision not in ALLOWED_DECISIONS:
            raise ValueError(f"ledger line {line_number} decision must be INCLUDE or EXCLUDE")
        if semantic_dedup_reviewed != "true":
            raise ValueError(f"ledger line {line_number} must attest semantic_dedup_reviewed=true")
        if decision == "INCLUDE" and reason:
            raise ValueError(f"ledger line {line_number} INCLUDE rows must not carry an exclusion reason")
        if decision == "EXCLUDE" and reason not in ALLOWED_EXCLUSION_REASONS:
            raise ValueError(
                f"ledger line {line_number} EXCLUDE reason must be predeclared; got {reason or '<empty>'}"
            )
        rows.append(
            {
                "candidate_id": candidate_id,
                "category": category,
                "decision": decision,
                "reason": reason,
                "semantic_dedup_reviewed": "true",
            }
        )
    return rows


def freeze_selection(
    candidates: Iterable[Candidate],
    ledger_rows: Iterable[Mapping[str, str]],
    *,
    candidate_source_receipts: Sequence[Mapping[str, str]] | None = None,
    ledger_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate full accounting and return a deterministic NOT_AUTHORIZED freeze artifact."""

    candidate_list = list(candidates)
    ledger_list = [dict(row) for row in ledger_rows]
    if not candidate_list:
        raise ValueError("candidate universe must be non-empty")

    by_id: dict[str, Candidate] = {}
    for candidate in candidate_list:
        if candidate.candidate_id in by_id:
            raise ValueError(f"duplicate candidate_id in candidate universe: {candidate.candidate_id}")
        by_id[candidate.candidate_id] = candidate

    ledger_by_id: dict[str, dict[str, str]] = {}
    for row in ledger_list:
        candidate_id = row["candidate_id"]
        if candidate_id in ledger_by_id:
            raise ValueError(f"duplicate candidate_id in selection ledger: {candidate_id}")
        ledger_by_id[candidate_id] = row

    missing = sorted(set(by_id) - set(ledger_by_id))
    unexpected = sorted(set(ledger_by_id) - set(by_id))
    if missing or unexpected:
        raise ValueError(
            "selection ledger must account for candidate universe exactly; "
            f"missing={missing[:5]} unexpected={unexpected[:5]}"
        )

    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    normalized_prompt_owner: dict[str, str] = {}

    for candidate_id in sorted(by_id):
        candidate = by_id[candidate_id]
        ledger = ledger_by_id[candidate_id]
        mapped_category = ledger["category"]
        if candidate.source_kind == "internal_synthetic" and mapped_category != candidate.category:
            raise ValueError(
                f"internal candidate {candidate_id} category drift: {candidate.category} -> {mapped_category}"
            )

        record = {
            "candidate_id": candidate_id,
            "category": mapped_category,
            "stratum": RESPONSE_POLICY_STRATUM if mapped_category == "invalid_underspecified" else GEOMETRY_STRATUM,
            "prompt": candidate.prompt,
            "prompt_sha256": _sha256_bytes(candidate.prompt.encode("utf-8")),
            "provenance": candidate.provenance,
            "source_kind": candidate.source_kind,
            "source_receipt_sha256": candidate.source_receipt_sha256,
            "candidate_receipt_sha256": _canonical_sha256(_candidate_receipt_payload(candidate)),
        }

        if ledger["decision"] == "INCLUDE":
            normalized_prompt = " ".join(candidate.prompt.casefold().split())
            previous = normalized_prompt_owner.get(normalized_prompt)
            if previous is not None:
                raise ValueError(
                    f"included prompts are exact-normalized duplicates: {previous} and {candidate_id}; "
                    "exclude one with DUPLICATE after semantic review"
                )
            normalized_prompt_owner[normalized_prompt] = candidate_id
            included.append(record)
        else:
            excluded.append(
                {
                    "candidate_id": candidate_id,
                    "category": mapped_category,
                    "reason": ledger["reason"],
                    "source_kind": candidate.source_kind,
                    "candidate_receipt_sha256": record["candidate_receipt_sha256"],
                }
            )

    counts = {category: 0 for category in TAXONOMY}
    for record in included:
        counts[record["category"]] += 1
    empty_categories = [category for category, count in counts.items() if count == 0]
    if empty_categories:
        raise ValueError("final selection must preserve all 11 taxonomy classes; empty=" + ", ".join(empty_categories))

    core = {
        "schema_version": SCHEMA_VERSION,
        "status": FREEZE_STATUS,
        "execution_authorized": False,
        "outcome_access_allowed": False,
        "candidate_count": len(candidate_list),
        "included_count": len(included),
        "excluded_count": len(excluded),
        "taxonomy_counts": counts,
        "response_policy_count": counts["invalid_underspecified"],
        "candidate_source_receipts": list(candidate_source_receipts or []),
        "ledger_sha256": ledger_sha256,
        "included": included,
        "excluded": excluded,
    }
    core["selection_sha256"] = _canonical_sha256(core)
    return core


def freeze_from_files(
    internal_csv: Path,
    external_jsonls: Sequence[Path],
    ledger_csv: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing freeze: {output}")

    internal_raw = internal_csv.read_bytes()
    candidates = parse_internal_csv_bytes(internal_raw)
    source_receipts: list[dict[str, str]] = [
        {
            "kind": "internal_candidate_csv",
            "path": str(internal_csv),
            "sha256": _sha256_bytes(internal_raw),
        }
    ]

    for path in external_jsonls:
        raw = path.read_bytes()
        candidates.extend(parse_external_jsonl_bytes(raw))
        source_receipts.append(
            {
                "kind": "external_adapter_jsonl",
                "path": str(path),
                "sha256": _sha256_bytes(raw),
            }
        )

    ledger_raw = ledger_csv.read_bytes()
    ledger = parse_ledger_csv_bytes(ledger_raw)
    frozen = freeze_selection(
        candidates,
        ledger,
        candidate_source_receipts=source_receipts,
        ledger_sha256=_sha256_bytes(ledger_raw),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frozen, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return frozen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze a pre-outcome NeuroCAD S3 candidate selection")
    parser.add_argument("--internal-csv", required=True, type=Path)
    parser.add_argument("--external-jsonl", action="append", default=[], type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    frozen = freeze_from_files(args.internal_csv, args.external_jsonl, args.ledger, args.output)
    print(
        json.dumps(
            {
                "status": frozen["status"],
                "execution_authorized": frozen["execution_authorized"],
                "candidate_count": frozen["candidate_count"],
                "included_count": frozen["included_count"],
                "excluded_count": frozen["excluded_count"],
                "selection_sha256": frozen["selection_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
