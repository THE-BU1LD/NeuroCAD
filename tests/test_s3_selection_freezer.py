import csv
import hashlib
import json
from pathlib import Path

import pytest

from research.s3.selection_freezer import (
    CANDIDATE_STATUS,
    FREEZE_STATUS,
    TAXONOMY,
    Candidate,
    freeze_from_files,
    freeze_selection,
    parse_external_jsonl_bytes,
    parse_internal_csv_bytes,
    parse_ledger_csv_bytes,
)


def _candidate(category: str, index: int, *, external: bool = False) -> Candidate:
    return Candidate(
        candidate_id=f"{'EXT' if external else 'S3C'}-{index:03d}",
        category="external_unmapped" if external else category,
        prompt=f"Prompt {index} for {category}",
        provenance="prompt-only pre-outcome fixture",
        source_kind="external_prompt_only" if external else "internal_synthetic",
        source_receipt_sha256=hashlib.sha256(f"source-{index}".encode()).hexdigest(),
    )


def _full_universe():
    return [_candidate(category, index + 1) for index, category in enumerate(TAXONOMY)]


def _ledger_for(candidates):
    rows = []
    for candidate, category in zip(candidates, TAXONOMY):
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "category": category,
                "decision": "INCLUDE",
                "reason": "",
                "semantic_dedup_reviewed": "true",
            }
        )
    return rows


def test_freeze_is_deterministic_covers_all_taxonomy_and_never_authorizes_execution():
    candidates = _full_universe()
    ledger = _ledger_for(candidates)
    first = freeze_selection(candidates, ledger, ledger_sha256="a" * 64)
    second = freeze_selection(candidates, ledger, ledger_sha256="a" * 64)

    assert first == second
    assert first["status"] == FREEZE_STATUS == "FROZEN_NOT_AUTHORIZED"
    assert first["execution_authorized"] is False
    assert first["outcome_access_allowed"] is False
    assert first["candidate_count"] == 11
    assert first["included_count"] == 11
    assert first["excluded_count"] == 0
    assert set(first["taxonomy_counts"]) == set(TAXONOMY)
    assert all(count == 1 for count in first["taxonomy_counts"].values())
    assert len(first["selection_sha256"]) == 64
    invalid = next(row for row in first["included"] if row["category"] == "invalid_underspecified")
    assert invalid["stratum"] == "response_policy"


def test_external_mapping_is_allowed_only_via_ledger_not_adapter_record():
    candidates = _full_universe()
    external = _candidate("patterns", 99, external=True)
    candidates.append(external)
    ledger = _ledger_for(candidates[:11]) + [
        {
            "candidate_id": external.candidate_id,
            "category": "patterns",
            "decision": "EXCLUDE",
            "reason": "OUT_OF_SCOPE",
            "semantic_dedup_reviewed": "true",
        }
    ]
    frozen = freeze_selection(candidates, ledger)
    assert frozen["excluded"][0]["candidate_id"] == external.candidate_id
    assert frozen["excluded"][0]["category"] == "patterns"
    assert frozen["excluded"][0]["reason"] == "OUT_OF_SCOPE"
    assert frozen["excluded"][0]["source_kind"] == "external_prompt_only"


def test_freeze_rejects_missing_or_unexpected_ledger_rows():
    candidates = _full_universe()
    with pytest.raises(ValueError, match="account for candidate universe exactly"):
        freeze_selection(candidates, _ledger_for(candidates)[:-1])

    ledger = _ledger_for(candidates)
    ledger.append(
        {
            "candidate_id": "GHOST",
            "category": "patterns",
            "decision": "EXCLUDE",
            "reason": "OUT_OF_SCOPE",
            "semantic_dedup_reviewed": "true",
        }
    )
    with pytest.raises(ValueError, match="account for candidate universe exactly"):
        freeze_selection(candidates, ledger)


def test_internal_category_drift_is_rejected():
    candidates = _full_universe()
    ledger = _ledger_for(candidates)
    ledger[0]["category"] = "patterns"
    with pytest.raises(ValueError, match="category drift"):
        freeze_selection(candidates, ledger)


def test_final_selection_must_keep_every_taxonomy_class():
    candidates = _full_universe()
    ledger = _ledger_for(candidates)
    ledger[-1]["decision"] = "EXCLUDE"
    ledger[-1]["reason"] = "OUT_OF_SCOPE"
    with pytest.raises(ValueError, match="preserve all 11 taxonomy classes"):
        freeze_selection(candidates, ledger)


def test_exact_normalized_duplicate_prompts_fail_closed():
    candidates = _full_universe()
    duplicate = Candidate(
        candidate_id=candidates[1].candidate_id,
        category=candidates[1].category,
        prompt="  " + candidates[0].prompt.upper() + "  ",
        provenance=candidates[1].provenance,
        source_kind=candidates[1].source_kind,
        source_receipt_sha256=candidates[1].source_receipt_sha256,
    )
    candidates[1] = duplicate
    ledger = _ledger_for(candidates)
    with pytest.raises(ValueError, match="exact-normalized duplicates"):
        freeze_selection(candidates, ledger)


def test_ledger_requires_explicit_semantic_dedup_attestation_and_predeclared_exclusion_reason():
    header = "candidate_id,category,decision,reason,semantic_dedup_reviewed\n"
    with pytest.raises(ValueError, match="semantic_dedup_reviewed=true"):
        parse_ledger_csv_bytes((header + "S3C-001,primitive_solids,INCLUDE,,false\n").encode())
    with pytest.raises(ValueError, match="EXCLUDE reason must be predeclared"):
        parse_ledger_csv_bytes((header + "S3C-001,primitive_solids,EXCLUDE,MODEL_WAS_BAD,true\n").encode())


def test_external_parser_rejects_outcomes_and_preassigned_taxonomy():
    base = {
        "candidate_id": "EXT-CADTESTBENCH-1",
        "category": "external_unmapped",
        "prompt": "Create a cube.",
        "provenance": "prompt-only",
        "status": CANDIDATE_STATUS,
        "source_row_sha256": "b" * 64,
    }
    with pytest.raises(ValueError, match="outcome-bearing"):
        parse_external_jsonl_bytes((json.dumps({**base, "score": 1.0}) + "\n").encode())
    with pytest.raises(ValueError, match="must remain external_unmapped"):
        parse_external_jsonl_bytes((json.dumps({**base, "category": "primitive_solids"}) + "\n").encode())


def test_internal_csv_binds_exact_bytes_and_rejects_non_candidate_status():
    raw = (
        "candidate_id,category,prompt,provenance,status\n"
        "S3C-001,primitive_solids,Create a cube.,synthetic,CANDIDATE_NOT_EVALUATED\n"
    ).encode()
    [candidate] = parse_internal_csv_bytes(raw)
    assert candidate.source_receipt_sha256 == hashlib.sha256(raw).hexdigest()

    bad = raw.replace(b"CANDIDATE_NOT_EVALUATED", b"EVALUATED")
    with pytest.raises(ValueError, match="must remain CANDIDATE_NOT_EVALUATED"):
        parse_internal_csv_bytes(bad)


def test_file_freeze_refuses_overwrite_and_hashes_source_and_ledger_bytes(tmp_path: Path):
    internal = tmp_path / "candidates.csv"
    ledger = tmp_path / "ledger.csv"
    output = tmp_path / "freeze.json"

    with internal.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "category", "prompt", "provenance", "status"])
        writer.writeheader()
        for index, category in enumerate(TAXONOMY, start=1):
            writer.writerow(
                {
                    "candidate_id": f"S3C-{index:03d}",
                    "category": category,
                    "prompt": f"Prompt {index} for {category}",
                    "provenance": "synthetic pre-outcome fixture",
                    "status": CANDIDATE_STATUS,
                }
            )

    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["candidate_id", "category", "decision", "reason", "semantic_dedup_reviewed"],
        )
        writer.writeheader()
        for index, category in enumerate(TAXONOMY, start=1):
            writer.writerow(
                {
                    "candidate_id": f"S3C-{index:03d}",
                    "category": category,
                    "decision": "INCLUDE",
                    "reason": "",
                    "semantic_dedup_reviewed": "true",
                }
            )

    frozen = freeze_from_files(internal, [], ledger, output)
    parsed = json.loads(output.read_text())
    assert parsed == frozen
    assert frozen["candidate_source_receipts"][0]["sha256"] == hashlib.sha256(internal.read_bytes()).hexdigest()
    assert frozen["ledger_sha256"] == hashlib.sha256(ledger.read_bytes()).hexdigest()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        freeze_from_files(internal, [], ledger, output)
