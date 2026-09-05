from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S3 = ROOT / "research" / "s3"


def load(name: str) -> dict:
    return json.loads((S3 / name).read_text(encoding="utf-8"))


def test_review_packet_freeze_is_non_authorizing_and_input_bound() -> None:
    freeze = load("HUMAN_REVIEW_PACKET_FREEZE_V0.json")
    external = load("EXTERNAL_MATERIALIZATION_FREEZE_V0.json")

    assert freeze["schema_version"] == "neurocad.s3.human-review-packet-freeze.v1"
    assert freeze["status"] == "FROZEN_REVIEW_PACKET_NOT_EVALUATED"
    assert freeze["execution_authorized"] is False
    assert freeze["outcomes_observed"] is False
    assert freeze["human_review_completed"] is False
    assert freeze["automatic_taxonomy_mapping_performed"] is False
    assert freeze["automatic_selection_decisions_performed"] is False
    assert freeze["automatic_semantic_deduplication_performed"] is False

    assert freeze["candidate_count"] == 591
    assert freeze["source_counts"] == {
        "internal_synthetic": 110,
        "external_prompt_only": 481,
    }
    assert freeze["taxonomy_mapping_required_count"] == 481

    internal = S3 / "benchmark_candidate_pool_v0.csv"
    internal_sha = hashlib.sha256(internal.read_bytes()).hexdigest()
    assert freeze["source_inputs"]["internal_candidate_csv"] == {
        "path": "research/s3/benchmark_candidate_pool_v0.csv",
        "candidate_count": 110,
        "sha256": internal_sha,
    }

    assert freeze["source_inputs"]["cadtestbench_adapted"]["candidate_count"] == 400
    assert (
        freeze["source_inputs"]["cadtestbench_adapted"]["sha256"]
        == external["sources"]["cadtestbench"]["adapted_sha256"]
    )
    assert freeze["source_inputs"]["cadgenbench_adapted"]["candidate_count"] == 81
    assert (
        freeze["source_inputs"]["cadgenbench_adapted"]["sha256"]
        == external["sources"]["cadgenbench"]["adapted_sha256"]
    )

    for section in ("review_packet", "ledger_template", "review_manifest"):
        value = freeze[section]["sha256"]
        assert len(value) == 64
        int(value, 16)

    boundary = freeze["review_boundary"]
    assert boundary["external_taxonomy_labels_filled"] is False
    assert boundary["include_exclude_decisions_filled"] is False
    assert boundary["semantic_dedup_attestations_filled"] is False
    assert boundary["final_selection_sha256"] is None
    assert boundary["next_gate"] == "HUMAN_NON_MODEL_TAXONOMY_MAPPING_AND_SEMANTIC_DEDUP_REVIEW"


def test_review_packet_freeze_hashes_match_first_verified_manifest_contract() -> None:
    freeze = load("HUMAN_REVIEW_PACKET_FREEZE_V0.json")

    assert freeze["first_verified_source_commit"] == "5c8566da5a6c81cd9508faa500163dcb2315ce55"
    assert freeze["first_verified_workflow_run"] == 33987612352
    assert freeze["first_verified_workflow_artifact"]["id"] == 9975638086
    assert freeze["first_verified_workflow_artifact"]["name"] == "s3-human-review-packet"
    digest = freeze["first_verified_workflow_artifact"]["digest"]
    assert digest == "sha256:2e2804ae9fa5a776a36c956fde9a6bf2b50e44400b89494f4ff4801c1903ea8a"

    assert freeze["review_packet"]["records"] == 591
    assert freeze["review_packet"]["sha256"] == "0ee7e8be0b085e3f73a832b7bfcb198acfc63354423d25ae27e40965a48887b2"
    assert freeze["ledger_template"]["records"] == 591
    assert freeze["ledger_template"]["sha256"] == "22f92ebf40050d0ebb6c5e6f450d74339cc68573ca18277eef25805d1e649731"
    assert freeze["review_manifest"]["sha256"] == "ed95d841cb9e888d70992bf7249b157d2c9d21e127ae57ab9c2cbce1e50de443"
