from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_physworld_results import compile_results, validate_receipt


def base_receipt() -> dict:
    terminal = {"applicable": True, "status": "pass", "evidence": ["raw/check.txt"]}
    return {
        "schema_version": "physworld-evidence-v1",
        "case_id": "case-a",
        "title": "Case A",
        "source_identity": {"url": "x", "format": "STEP"},
        "baseline_sha256": "a" * 64,
        "provenance": {"tool_versions": {"tool": "1"}, "commands": ["check"], "units": "mm"},
        "visual_plausibility": terminal,
        "geometry_validity": terminal,
        "revision_integrity": {"applicable": False, "status": "na", "evidence": []},
        "meshability": terminal,
        "derived_artifacts": [],
        "notes": "fixture",
    }


def write_receipt(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_terminal_receipt_compiles(tmp_path: Path) -> None:
    receipt = validate_receipt(write_receipt(tmp_path, base_receipt()), strict=True)
    markdown, summary = compile_results([receipt])
    assert "PASS" in markdown
    assert "N/A" in markdown
    assert summary["case_count"] == 1
    assert summary["cases"][0]["results"]["meshability"] == "pass"


def test_terminal_result_requires_evidence(tmp_path: Path) -> None:
    payload = base_receipt()
    payload["meshability"] = {"applicable": True, "status": "fail", "evidence": []}
    with pytest.raises(ValueError, match="requires retained evidence"):
        validate_receipt(write_receipt(tmp_path, payload), strict=True)


def test_strict_mode_rejects_not_run_applicable_dimension(tmp_path: Path) -> None:
    payload = base_receipt()
    payload["geometry_validity"] = {"applicable": True, "status": "not_run", "evidence": []}
    with pytest.raises(ValueError, match="strict mode requires terminal result"):
        validate_receipt(write_receipt(tmp_path, payload), strict=True)


def test_non_applicable_dimension_must_be_na(tmp_path: Path) -> None:
    payload = base_receipt()
    payload["revision_integrity"] = {"applicable": False, "status": "pass", "evidence": ["x"]}
    with pytest.raises(ValueError, match="must use status=na"):
        validate_receipt(write_receipt(tmp_path, payload), strict=False)


def test_bad_baseline_digest_rejected(tmp_path: Path) -> None:
    payload = base_receipt()
    payload["baseline_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="baseline_sha256"):
        validate_receipt(write_receipt(tmp_path, payload), strict=False)
