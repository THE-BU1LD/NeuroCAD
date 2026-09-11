"""Create a deterministic human-review packet for the pre-outcome NeuroCAD S3 selection gate.

This utility does not assign taxonomy labels, inclusion decisions, or semantic-duplicate
judgments. It packages the already-frozen candidate universe into a reviewer-friendly
JSONL plus a freezer-compatible ledger template whose review fields remain deliberately
unfilled. Execution remains prohibited.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from selection_freezer import Candidate, parse_external_jsonl_bytes, parse_internal_csv_bytes

STATUS = "HUMAN_REVIEW_REQUIRED_NOT_AUTHORIZED"
SCHEMA_VERSION = "neurocad.s3.review-packet.v1"
LEDGER_FIELDS = ["candidate_id", "category", "decision", "reason", "semantic_dedup_reviewed"]


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256(raw)


def _candidate_receipt(candidate: Candidate) -> str:
    return _canonical_sha256(
        {
            "candidate_id": candidate.candidate_id,
            "category": candidate.category,
            "prompt": candidate.prompt,
            "provenance": candidate.provenance,
            "source_kind": candidate.source_kind,
            "source_receipt_sha256": candidate.source_receipt_sha256,
        }
    )


def build_review_packet(candidates: Sequence[Candidate]) -> tuple[bytes, bytes, dict[str, Any]]:
    if not candidates:
        raise ValueError("candidate universe must be non-empty")

    by_id: dict[str, Candidate] = {}
    for candidate in candidates:
        if candidate.candidate_id in by_id:
            raise ValueError(f"duplicate candidate_id in candidate universe: {candidate.candidate_id}")
        by_id[candidate.candidate_id] = candidate

    packet_lines: list[str] = []
    ledger_rows: list[dict[str, str]] = []
    source_counts: dict[str, int] = {}
    mapping_required = 0

    for candidate_id in sorted(by_id):
        candidate = by_id[candidate_id]
        source_counts[candidate.source_kind] = source_counts.get(candidate.source_kind, 0) + 1
        external = candidate.source_kind == "external_prompt_only"
        if external:
            mapping_required += 1

        packet_record = {
            "candidate_id": candidate.candidate_id,
            "source_kind": candidate.source_kind,
            "current_category": candidate.category,
            "taxonomy_mapping_required": external,
            "prompt": candidate.prompt,
            "provenance": candidate.provenance,
            "source_receipt_sha256": candidate.source_receipt_sha256,
            "candidate_receipt_sha256": _candidate_receipt(candidate),
            "review_fields": {
                "category": None if external else candidate.category,
                "decision": None,
                "reason": None,
                "semantic_dedup_reviewed": False,
            },
        }
        packet_lines.append(json.dumps(packet_record, sort_keys=True, ensure_ascii=False))

        ledger_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "category": "" if external else candidate.category,
                "decision": "",
                "reason": "",
                "semantic_dedup_reviewed": "false",
            }
        )

    packet_bytes = ("\n".join(packet_lines) + "\n").encode("utf-8")

    from io import StringIO

    ledger_stream = StringIO(newline="")
    writer = csv.DictWriter(ledger_stream, fieldnames=LEDGER_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(ledger_rows)
    ledger_bytes = ledger_stream.getvalue().encode("utf-8")

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "execution_authorized": False,
        "outcomes_observed": False,
        "automatic_taxonomy_mapping_performed": False,
        "automatic_selection_decisions_performed": False,
        "automatic_semantic_deduplication_performed": False,
        "candidate_count": len(candidates),
        "source_counts": dict(sorted(source_counts.items())),
        "taxonomy_mapping_required_count": mapping_required,
        "packet_sha256": _sha256(packet_bytes),
        "ledger_template_sha256": _sha256(ledger_bytes),
        "ledger_fields": LEDGER_FIELDS,
        "human_completion_requirements": [
            "map every external candidate to one frozen taxonomy category",
            "record INCLUDE or EXCLUDE for every candidate",
            "use only predeclared exclusion reasons",
            "attest semantic_dedup_reviewed=true for every candidate",
            "do not add model outputs, scores, labels, private ground truth, or benchmark outcomes",
            "submit the completed ledger to selection_freezer.py; this review packet cannot authorize execution",
        ],
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return packet_bytes, ledger_bytes, manifest


def write_review_packet(
    internal_csv: Path,
    external_jsonls: Sequence[Path],
    *,
    packet_output: Path,
    ledger_output: Path,
    manifest_output: Path,
) -> dict[str, Any]:
    outputs = [packet_output, ledger_output, manifest_output]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite existing review artifact(s): " + ", ".join(existing))

    internal_raw = internal_csv.read_bytes()
    candidates = parse_internal_csv_bytes(internal_raw)
    source_inputs: list[dict[str, Any]] = [
        {
            "kind": "internal_candidate_csv",
            "path": str(internal_csv),
            "sha256": _sha256(internal_raw),
            "candidate_count": len(candidates),
        }
    ]

    for path in external_jsonls:
        raw = path.read_bytes()
        parsed = parse_external_jsonl_bytes(raw)
        candidates.extend(parsed)
        source_inputs.append(
            {
                "kind": "external_adapter_jsonl",
                "path": str(path),
                "sha256": _sha256(raw),
                "candidate_count": len(parsed),
            }
        )

    packet_bytes, ledger_bytes, manifest = build_review_packet(candidates)
    manifest["source_inputs"] = source_inputs
    manifest["manifest_sha256"] = _canonical_sha256(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )

    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    packet_output.write_bytes(packet_bytes)
    ledger_output.write_bytes(ledger_bytes)
    manifest_output.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a non-model human-review packet for NeuroCAD S3.")
    parser.add_argument("--internal-csv", type=Path, required=True)
    parser.add_argument("--external-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--packet-output", type=Path, required=True)
    parser.add_argument("--ledger-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args()

    manifest = write_review_packet(
        args.internal_csv,
        args.external_jsonl,
        packet_output=args.packet_output,
        ledger_output=args.ledger_output,
        manifest_output=args.manifest_output,
    )
    print(f"status: {manifest['status']}")
    print(f"candidate_count: {manifest['candidate_count']}")
    print(f"taxonomy_mapping_required_count: {manifest['taxonomy_mapping_required_count']}")
    print(f"manifest_sha256: {manifest['manifest_sha256']}")
    print("execution_authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
