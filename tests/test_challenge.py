from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.challenge import load_challenge, main, run_challenge

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "research" / "benchmarks" / "neurocad_prompt_challenge_v1.jsonl"


def test_repository_challenge_is_unique_strict_and_executable() -> None:
    cases = load_challenge(DATASET)
    digest = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    results = run_challenge(cases, dataset_sha256=digest)
    assert len(cases) == 24
    assert results["dataset_sha256"] == digest
    assert results["evidence_class"].startswith("development evidence")
    assert len(results["provenance"]["evaluator_sha256"]) == 64
    assert sum(item["cases"] for item in results["by_split"].values()) == 24


def test_challenge_loader_rejects_duplicate_prompts_and_bad_rejection(tmp_path: Path) -> None:
    base = {
        "case_id": "one",
        "split": "development",
        "family": "x",
        "prompt": "a 1 x 1 x 1 mm box",
        "expected_status": "reject",
        "expected": None,
    }
    records = [base, {**base, "case_id": "two", "split": "validation"}, {**base, "case_id": "three", "split": "test"}]
    path = tmp_path / "duplicate.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    with pytest.raises(ValueError, match="prompts must be unique"):
        load_challenge(path)

    records[1] = {**records[1], "prompt": "different", "expected": {"kind": "box"}}
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    with pytest.raises(ValueError, match="must use null"):
        load_challenge(path)


def test_challenge_cli_refuses_existing_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["challenge", str(DATASET), str(output)])
    status = main()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert status in {0, 1}
    assert payload["cases"] == 24
    with pytest.raises(SystemExit):
        main()
