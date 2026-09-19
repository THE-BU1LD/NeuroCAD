from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S3 = ROOT / "research" / "s3"
sys.path.insert(0, str(S3))

from review_packet import build_review_packet, write_review_packet  # noqa: E402
from selection_freezer import Candidate  # noqa: E402


def candidate(
    candidate_id: str,
    *,
    category: str = "primitive_solids",
    source_kind: str = "internal_synthetic",
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        category=category,
        prompt=f"prompt for {candidate_id}",
        provenance="fixture",
        source_kind=source_kind,
        source_receipt_sha256=hashlib.sha256(candidate_id.encode()).hexdigest(),
    )


class ReviewPacketTests(unittest.TestCase):
    def test_packet_is_deterministic_and_non_authorizing(self) -> None:
        candidates = [
            candidate("external-2", category="external_unmapped", source_kind="external_prompt_only"),
            candidate("internal-1"),
            candidate("external-1", category="external_unmapped", source_kind="external_prompt_only"),
        ]
        first = build_review_packet(candidates)
        second = build_review_packet(list(reversed(candidates)))
        self.assertEqual(first, second)

        packet_bytes, ledger_bytes, manifest = first
        self.assertFalse(manifest["execution_authorized"])
        self.assertFalse(manifest["outcomes_observed"])
        self.assertFalse(manifest["automatic_taxonomy_mapping_performed"])
        self.assertFalse(manifest["automatic_selection_decisions_performed"])
        self.assertFalse(manifest["automatic_semantic_deduplication_performed"])
        self.assertEqual(2, manifest["taxonomy_mapping_required_count"])
        self.assertEqual(hashlib.sha256(packet_bytes).hexdigest(), manifest["packet_sha256"])
        self.assertEqual(hashlib.sha256(ledger_bytes).hexdigest(), manifest["ledger_template_sha256"])

    def test_external_taxonomy_and_all_decisions_remain_human_required(self) -> None:
        packet_bytes, ledger_bytes, _ = build_review_packet(
            [
                candidate("internal-1"),
                candidate("external-1", category="external_unmapped", source_kind="external_prompt_only"),
            ]
        )
        packet = [json.loads(line) for line in packet_bytes.decode().splitlines()]
        by_id = {row["candidate_id"]: row for row in packet}
        self.assertEqual("primitive_solids", by_id["internal-1"]["review_fields"]["category"])
        self.assertIsNone(by_id["internal-1"]["review_fields"]["decision"])
        self.assertIsNone(by_id["external-1"]["review_fields"]["category"])
        self.assertIsNone(by_id["external-1"]["review_fields"]["decision"])
        self.assertFalse(by_id["external-1"]["review_fields"]["semantic_dedup_reviewed"])

        ledger = list(csv.DictReader(io.StringIO(ledger_bytes.decode())))
        ledger_by_id = {row["candidate_id"]: row for row in ledger}
        self.assertEqual("primitive_solids", ledger_by_id["internal-1"]["category"])
        self.assertEqual("", ledger_by_id["internal-1"]["decision"])
        self.assertEqual("", ledger_by_id["external-1"]["category"])
        self.assertEqual("", ledger_by_id["external-1"]["decision"])
        self.assertEqual("false", ledger_by_id["external-1"]["semantic_dedup_reviewed"])

    def test_duplicate_candidate_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate candidate_id"):
            build_review_packet([candidate("dup"), candidate("dup")])

    def test_empty_candidate_universe_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_review_packet([])

    def test_write_packet_binds_exact_input_bytes_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            internal = root / "internal.csv"
            external = root / "external.jsonl"
            packet = root / "review.jsonl"
            ledger = root / "ledger.csv"
            manifest_path = root / "manifest.json"

            internal.write_text(
                "candidate_id,category,prompt,provenance,status\n"
                "S3-0001,primitive_solids,Create a cube,fixture,CANDIDATE_NOT_EVALUATED\n",
                encoding="utf-8",
            )
            external_record = {
                "candidate_id": "EXT-0001",
                "category": "external_unmapped",
                "prompt": "Create a bracket",
                "provenance": "external fixture",
                "status": "CANDIDATE_NOT_EVALUATED",
                "source_row_sha256": "a" * 64,
            }
            external.write_text(json.dumps(external_record) + "\n", encoding="utf-8")

            manifest = write_review_packet(
                internal,
                [external],
                packet_output=packet,
                ledger_output=ledger,
                manifest_output=manifest_path,
            )
            self.assertEqual(2, manifest["candidate_count"])
            self.assertEqual(1, manifest["taxonomy_mapping_required_count"])
            self.assertEqual(hashlib.sha256(internal.read_bytes()).hexdigest(), manifest["source_inputs"][0]["sha256"])
            self.assertEqual(hashlib.sha256(external.read_bytes()).hexdigest(), manifest["source_inputs"][1]["sha256"])
            self.assertFalse(manifest["execution_authorized"])

            with self.assertRaises(FileExistsError):
                write_review_packet(
                    internal,
                    [external],
                    packet_output=packet,
                    ledger_output=ledger,
                    manifest_output=manifest_path,
                )


if __name__ == "__main__":
    unittest.main()
