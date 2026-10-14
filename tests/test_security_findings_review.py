"""Fail-closed tests for exact source-bound static security adjudication."""

import hashlib
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("security_review", Path(__file__).parents[1] / "scripts/review_security_findings.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_review_rejects_every_unreviewed_change(tmp_path):
    source = tmp_path / "fixture.py"
    source.write_text("import subprocess\n", encoding="utf-8")
    review = {"findings": [{"path": source.name, "test_id": "B404", "line": 1,
                            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]}
    finding = {"filename": str(source), "test_id": "B404", "line_number": 1,
               "issue_severity": "LOW", "issue_confidence": "HIGH"}
    report = {"results": [finding], "metrics": {"_totals": {}}, "errors": []}
    assert MODULE.adjudicate(report, review, tmp_path)["status"] == "PASS"
    for field, value in [("line_number", 2), ("test_id", "B602"), ("issue_severity", "HIGH")]:
        changed = {**report, "results": [{**finding, field: value}]}
        assert MODULE.adjudicate(changed, review, tmp_path)["status"] == "FAIL"
    for changed in ({**report, "results": []}, {**report, "results": [finding, finding]},
                    {**report, "errors": ["could not scan"]}, {"results": []}):
        assert MODULE.adjudicate(changed, review, tmp_path)["status"] == "FAIL"
    source.write_text("import os\n", encoding="utf-8")
    assert MODULE.adjudicate(report, review, tmp_path)["status"] == "FAIL"
